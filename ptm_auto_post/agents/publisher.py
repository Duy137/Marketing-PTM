"""
publisher.py — Node 5: Đăng bài lên các Facebook Fanpage đã chọn.

Hỗ trợ:
- Đăng lên nhiều page cùng lúc (multi-page)
- Ảnh từ thư mục media/ (file path) hoặc ảnh user upload (raw bytes trong RAM)
- Sử dụng chuẩn FacebookPage Schema từ settings.py (id, name, access_token)
"""

import io
import requests
import concurrent.futures
from datetime import datetime

from config.settings import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    FACEBOOK_PAGES,
    FacebookPage,
    POST_HISTORY_LOG,
    LOGS_DIR,
)
from api.pending_store import register_callback, unregister_callback
import queue
from agents.state import PostState
from services.topic_service import mark_topic_as_posted

FB_API_BASE = "https://graph.facebook.com/v19.0"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _upload_photo_from_path(image_path: str, page_id: str, token: str) -> str | None:
    """Upload 1 ảnh từ file path lên Facebook (chưa publish)."""
    url = f"{FB_API_BASE}/{page_id}/photos"
    with open(image_path, "rb") as img:
        response = requests.post(
            url,
            data={"access_token": token, "published": "false"},
            files={"source": img},
            timeout=30,
        )
    data = response.json()
    if "id" in data:
        return data["id"]
    print(f"[publisher] Lỗi upload ảnh path ({page_id}): {data}")
    return None


def _upload_photo_from_bytes(raw_bytes: bytes, page_id: str, token: str) -> str | None:
    """Upload 1 ảnh từ raw bytes (lưu RAM) lên Facebook (chưa publish)."""
    url = f"{FB_API_BASE}/{page_id}/photos"
    response = requests.post(
        url,
        data={"access_token": token, "published": "false"},
        files={"source": ("photo.jpg", io.BytesIO(raw_bytes), "image/jpeg")},
        timeout=30,
    )
    data = response.json()
    if "id" in data:
        return data["id"]
    print(f"[publisher] Lỗi upload ảnh bytes ({page_id}): {data}")
    return None


def _publish_to_single_page(page: FacebookPage, message: str, image_paths: list, raw_bytes_list: list) -> dict:
    """Đăng bài lên 1 Fanpage cụ thể theo chuẩn FacebookPage Schema."""
    page_id = page["id"]
    page_name = page["name"]
    token = page["access_token"]
    print(f"[publisher] Đang đăng lên: {page_name} ({page_id})...")

    uploaded_photo_ids = []

    if raw_bytes_list:
        for raw in raw_bytes_list[:4]:
            pid = _upload_photo_from_bytes(raw, page_id, token)
            if pid:
                uploaded_photo_ids.append(pid)
    elif image_paths:
        for path_str in image_paths[:4]:
            pid = _upload_photo_from_path(path_str, page_id, token)
            if pid:
                uploaded_photo_ids.append(pid)

    if uploaded_photo_ids:
        payload = {"access_token": token, "message": message}
        for i, pid in enumerate(uploaded_photo_ids):
            payload[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'
        url = f"{FB_API_BASE}/{page_id}/feed"
    else:
        url = f"{FB_API_BASE}/{page_id}/feed"
        payload = {"access_token": token, "message": message}

    try:
        response = requests.post(url, data=payload, timeout=30)
        res_data = response.json()
        if "id" in res_data:
            post_id = res_data["id"]
            print(f"[publisher] ✅ Đã đăng lên {page_name}! Post ID: {post_id}")
            return {"page_id": page_id, "page_name": page_name, "success": True, "post_id": post_id}
        else:
            print(f"[publisher] ❌ Lỗi đăng lên {page_name}: {res_data}")
            return {"page_id": page_id, "page_name": page_name, "success": False, "error": str(res_data)}
    except Exception as e:
        print(f"[publisher] ❌ Exception khi đăng lên {page_name}: {e}")
        return {"page_id": page_id, "page_name": page_name, "success": False, "error": str(e)}


def publish_post(state: PostState) -> PostState:
    """Node 5 trong LangGraph — Đăng bài lên Facebook."""
    content = state.get("post_content", "")
    image_paths = state.get("image_paths", [])
    raw_bytes_list = state.get("image_raw_bytes", [])
    selected_page_ids = state.get("selected_page_ids", [])
    topic_id = state.get("topic_id", 0)

    if not content:
        print("[publisher] Lỗi: Nội dung bài viết rỗng!")
        return {**state, "error_message": "Nội dung bài viết rỗng."}

    target_pages = [p for p in FACEBOOK_PAGES if p["id"] in selected_page_ids]
    if not target_pages:
        target_pages = FACEBOOK_PAGES

    print(f"[publisher] Bắt đầu đăng bài lên {len(target_pages)} Fanpage...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_pages)) as executor:
        futures = [
            executor.submit(_publish_to_single_page, p, content, image_paths, raw_bytes_list)
            for p in target_pages
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    successful_posts = [r for r in results if r["success"]]

    if successful_posts:
        if topic_id:
            mark_topic_as_posted(topic_id)

        first_post_id = successful_posts[0]["post_id"]
        names_str = ", ".join(r["page_name"] for r in successful_posts)

        try:
            requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": f"🎉 <b>ĐÃ ĐĂNG BÀI THÀNH CÔNG!</b>\n\n📢 <b>Fanpage:</b> {names_str}\n🆔 <b>Post ID:</b> {first_post_id}",
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
        except Exception:
            pass

        return {**state, "facebook_post_id": first_post_id}
    else:
        errors = [f"{r['page_name']}: {r.get('error')}" for r in results]
        err_msg = " | ".join(errors)
        return {**state, "error_message": f"Đăng bài thất bại: {err_msg}"}
