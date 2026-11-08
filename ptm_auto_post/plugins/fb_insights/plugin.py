"""
Plugin: FB Insights
═══════════════════
Mô tả:
    Ghi log mỗi bài đăng thành công. Khi có yêu cầu báo cáo (on_report_requested),
    fetch Facebook Insights API, JOIN với post_log.csv, dùng LLM phân tích,
    gửi báo cáo qua Telegram.

Hooks đăng ký:
    - on_post_published   → ghi metadata bài vào post_log.csv
    - on_report_requested → fetch + phân tích + gửi Telegram

Bật/tắt:
    Thêm/xóa dòng import trong plugins/__init__.py

Không cần cấu hình thêm:
    Dùng FACEBOOK_PAGES + LOGS_DIR đã có trong settings.py
"""

import json
import requests
from datetime import datetime, timezone, timedelta

from shared.hooks import on
from services.post_log_service import log_published_post, read_post_log
from shared.llm_factory import create_llm_for_task
from config.settings import FACEBOOK_PAGES, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

FB_API_BASE = "https://graph.facebook.com/v19.0"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Metrics cần fetch từ Facebook (per-post)
_POST_METRICS = "post_impressions_unique,post_engaged_users,post_clicks"


# ── Handler 1: Ghi log khi đăng bài ──────────────────────────────────────────

def _on_post_published(payload: dict) -> None:
    """Ghi metadata bài đăng vào post_log.csv để dùng cho báo cáo sau."""
    if not payload.get("facebook_post_id"):
        return
    log_published_post(payload)


# ── Handler 2: Fetch insights + phân tích khi user yêu cầu báo cáo ──────────

def _fetch_post_insights(page_id: str, token: str, since_days: int = 30) -> list[dict]:
    """
    Gọi Facebook Graph API lấy tất cả bài đăng trong N ngày qua kèm insights.
    Trả về list of dict: {post_id, message_preview, reach, engaged_users, clicks, created_time}
    """
    since_ts = int((datetime.now(timezone.utc) - timedelta(days=since_days)).timestamp())
    url = (
        f"{FB_API_BASE}/{page_id}/published_posts"
        f"?fields=id,message,created_time,insights.metric({_POST_METRICS})"
        f"&since={since_ts}"
        f"&limit=50"
        f"&access_token={token}"
    )
    try:
        resp = requests.get(url, timeout=20)
        data = resp.json()
        posts = data.get("data", [])
        result = []
        for p in posts:
            insights = {
                m["name"]: m["values"][0]["value"]
                for m in p.get("insights", {}).get("data", [])
                if m.get("values")
            }
            result.append({
                "post_id":       p["id"],
                "message":       (p.get("message") or "")[:120],
                "created_time":  p.get("created_time", ""),
                "reach":         insights.get("post_impressions_unique", 0),
                "engaged_users": insights.get("post_engaged_users", 0),
                "clicks":        insights.get("post_clicks", 0),
            })
        return result
    except Exception as exc:
        print(f"[fb_insights] Lỗi fetch insights từ page {page_id}: {exc}")
        return []


def _on_report_requested(payload: dict) -> None:
    """
    Fetch Facebook Insights cho tất cả pages, JOIN với post_log,
    dùng LLM phân tích, gửi báo cáo qua Telegram.
    """
    days = payload.get("days", 30)
    _send_telegram("⏳ <b>Đang lấy dữ liệu từ Facebook...</b> Chờ 10–30 giây.")

    # 1. Fetch Facebook Insights
    all_fb_posts: list[dict] = []
    for page in FACEBOOK_PAGES:
        posts = _fetch_post_insights(page["id"], page["access_token"], since_days=days)
        for p in posts:
            p["page_name"] = page["name"]
        all_fb_posts.extend(posts)

    if not all_fb_posts:
        _send_telegram("❌ Không lấy được dữ liệu từ Facebook. Kiểm tra token và thử lại.")
        return

    # 2. Đọc post_log nội bộ
    local_logs = read_post_log(days=days)
    local_by_id = {row["facebook_post_id"]: row for row in local_logs}

    # 3. JOIN: ghép metadata nội bộ vào từng bài Facebook
    enriched = []
    for p in all_fb_posts:
        local = local_by_id.get(p["post_id"], {})
        enriched.append({
            **p,
            "san_pham":    local.get("san_pham", "Không rõ"),
            "mode":        local.get("mode", "Không rõ"),
            "image_types": local.get("image_types", "Không rõ"),
            "topic_title": local.get("topic_title", ""),
        })

    # 4. Sắp xếp theo reach giảm dần
    enriched.sort(key=lambda x: x.get("reach", 0), reverse=True)

    # 5. LLM phân tích
    summary_prompt = f"""Bạn là chuyên gia phân tích marketing cho PTM — công ty sản xuất nẹp inox và phụ kiện xây dựng B2B.

Dưới đây là dữ liệu {len(enriched)} bài đăng Facebook trong {days} ngày qua:

{json.dumps(enriched[:30], ensure_ascii=False, indent=2)}

Hãy phân tích ngắn gọn (dưới 300 từ, dùng tiếng Việt):
1. Top 3 bài đăng reach cao nhất — chúng có điểm chung gì?
2. Mode nào (Product/Educational/Social Proof...) hiệu quả hơn?
3. Sản phẩm nào được reach tốt nhất?
4. Loại ảnh nào (tai_xuong / gia_cong / thuong...) đi kèm các bài reach cao?
5. 1 khuyến nghị cụ thể cho chiến lược nội dung tuần tới.

Trả lời ngắn gọn, súc tích, dùng emoji cho dễ đọc trên Telegram."""

    try:
        llm = create_llm_for_task("image_picker")   # Model rẻ đủ dùng cho phân tích
        response = llm.invoke(summary_prompt)
        analysis = response.content.strip()
    except Exception as exc:
        analysis = f"(Không thể phân tích tự động: {exc})"

    # 6. Gửi báo cáo qua Telegram
    top3 = enriched[:3]
    top3_text = "\n".join(
        f"  {i+1}. {p['san_pham']} [{p['mode']}] — Reach: {p['reach']:,} | Engage: {p['engaged_users']:,}"
        for i, p in enumerate(top3)
    )
    report = (
        f"📊 <b>BÁO CÁO {days} NGÀY QUA</b>\n"
        f"Tổng số bài: {len(enriched)} | Pages: {len(FACEBOOK_PAGES)}\n\n"
        f"🏆 <b>Top 3 Reach cao nhất:</b>\n{top3_text}\n\n"
        f"🤖 <b>Phân tích AI:</b>\n{analysis}"
    )
    _send_telegram(report)


# ── Helper ────────────────────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        print(f"[fb_insights] Lỗi gửi Telegram: {exc}")


# ── Đăng ký hooks ─────────────────────────────────────────────────────────────
on("on_post_published",   _on_post_published)
on("on_report_requested", _on_report_requested)
