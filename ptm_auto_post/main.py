"""
main.py — Điểm khởi chạy chính của hệ thống PTM Auto Post.

Đây là file duy nhất bạn cần chạy mỗi ngày:
    python main.py

Luồng chạy:
    [Pre-pipeline] Chọn chủ đề qua Telegram (không LLM)
    → Viết bài → Chọn ảnh → Gửi Telegram → Chọn Page → Đăng Facebook

Các nút tương tác trên Telegram:
    ✅ Duyệt đăng   → Chọn page → Đăng Facebook
    🔄 Cùng chủ đề → Viết lại bài (giữ nguyên chủ đề)
    🎲 Chủ đề khác → Quay về chọn chủ đề mới
    🖼️ Gửi ảnh     → Bot chờ nhận ảnh từ bạn → Gửi lại preview
    ❌ Bỏ qua       → Kết thúc, không đăng hôm nay
"""

from langgraph.graph import StateGraph, END

from config.settings import validate_settings
from agents.state import PostState
from agents.topic_picker import pick_topic
from agents.content_writer import write_content
from agents.image_picker import pick_images
from agents.approver import send_for_approval
from agents.page_selector import select_pages_for_post
from agents.publisher import publish_post
from agents.topic_selector import select_topic_interactively

import threading
import uvicorn
import requests
import subprocess
import re
import time
from config.settings import TELEGRAM_BOT_TOKEN


# ==============================================
# HÀM ĐỊNH TUYẾN (Routing)
# ==============================================

def route_after_approval(state: PostState) -> str:
    """
    Quyết định bước tiếp theo dựa vào kết quả duyệt bài.

    - "approved"        → Chọn page rồi đăng bài
    - "regenerate_same" → Viết lại bài (giữ nguyên chủ đề)
    - "regenerate_new"  → Quay về chọn chủ đề mới
    - "rejected"        → Kết thúc, không đăng
    - "timeout"         → Kết thúc, không đăng
    """
    status = state.get("approval_status", "rejected")
    print(f"[router] Trạng thái duyệt: {status}")

    if status == "approved":
        return "select_pages"
    elif status == "regenerate_same":
        return "write_again"
    elif status == "regenerate_new":
        return "pick_new_topic"
    else:
        print("[router] Bài bị từ chối hoặc hết thời gian chờ. Kết thúc hôm nay.")
        return "end"


# ==============================================
# XÂY DỰNG GRAPH LANGGRAPH
# ==============================================

def build_graph() -> StateGraph:
    """
    Lắp ráp toàn bộ pipeline bằng LangGraph StateGraph.

    Sơ đồ luồng:
        pick_topic → write_content → pick_images → send_for_approval
                         ↑                               │
                         │            ┌──────────────────┤
                    [regen_same]  [regen_new]        [approved]   [rejected/timeout]
                         │            │                  │              │
                    write_content  pick_topic      select_pages        END
                                                         │
                                                   publish_post → END
    """
    graph = StateGraph(PostState)

    # --- Thêm các nodes ---
    graph.add_node("pick_topic",        pick_topic)
    graph.add_node("write_content",     write_content)
    graph.add_node("pick_images",       pick_images)
    graph.add_node("send_for_approval", send_for_approval)
    graph.add_node("select_pages",      select_pages_for_post)
    graph.add_node("publish_post",      publish_post)

    # --- Luồng chính ---
    graph.set_entry_point("pick_topic")
    graph.add_edge("pick_topic",    "write_content")
    graph.add_edge("write_content", "pick_images")
    graph.add_edge("pick_images",   "send_for_approval")

    # --- Nhánh sau bước duyệt bài ---
    graph.add_conditional_edges(
        "send_for_approval",
        route_after_approval,
        {
            "select_pages":   "select_pages",   # Duyệt → Chọn page
            "write_again":    "write_content",  # Viết lại cùng chủ đề
            "pick_new_topic": "pick_topic",     # Chủ đề khác hoàn toàn
            "end":            END,              # Từ chối / Timeout
        },
    )

    # --- Sau chọn page → đăng bài → kết thúc ---
    graph.add_edge("select_pages", "publish_post")
    graph.add_edge("publish_post", END)

    return graph.compile()


# ==============================================
# WEBHOOK SERVER SETUP
# ==============================================

def run_cloudflared() -> str | None:
    """Chạy cloudflared ngầm và lấy URL."""
    print("☁️ Đang khởi động Cloudflare Tunnel...")
    try:
        # Chạy cloudflared trong subprocess
        p = subprocess.Popen(
            ["cloudflared.exe", "tunnel", "--url", "http://127.0.0.1:8888"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Đọc stderr để lấy URL (Cloudflared log ra stderr)
        start_time = time.time()
        while time.time() - start_time < 15:
            line = p.stderr.readline()
            if not line:
                break
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                url = match.group(0)
                print(f"✅ Cloudflare Tunnel OK: {url}")
                return url
                
        print("❌ Lỗi: Không lấy được URL từ Cloudflare sau 15 giây.")
        p.kill()
        return None
    except FileNotFoundError:
        print("❌ Lỗi: Không tìm thấy file 'cloudflared.exe'. Hãy chắc chắn file nằm chung thư mục với main.py")
        return None

def setup_webhook_server():
    """Tự động chạy Tunnel, Đăng ký Webhook và chạy FastAPI."""
    # 1. Khởi động FastAPI server trước
    def _run_server():
        uvicorn.run("api.webhook_server:app", host="127.0.0.1", port=8888, log_level="error")
    t = threading.Thread(target=_run_server, daemon=True)
    t.start()
    time.sleep(1)  # Chờ server sẵn sàng

    # 2. Khởi động cloudflared lấy URL
    webhook_url = run_cloudflared()
    if not webhook_url:
        return False

    # 3. Chờ DNS propagate rồi retry đăng ký (tối đa 5 lần)
    print("⏳ Chờ DNS propagate...")
    time.sleep(5)  # DNS của Cloudflare cần vài giây để đi vào hệ thống

    for attempt in range(1, 6):
        print(f"🔗 Đăng ký Webhook (lần {attempt}/5): {webhook_url}/webhook")
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={"url": f"{webhook_url}/webhook"},
                timeout=10,
            )
            result = response.json()
            if result.get("ok"):
                print("✅ Webhook đã đăng ký thành công!")
                return True
            
            desc = result.get("description", "")
            print(f"   ⚠️ Telegram báo: {desc}")
            
            # Nếu lỗi DNS → chờ thêm rồi thử lại
            if "resolve host" in desc or "Name or service" in desc:
                if attempt < 5:
                    wait = attempt * 3  # 3s, 6s, 9s, 12s
                    print(f"   ⏳ Chờ thêm {wait}s cho DNS...")
                    time.sleep(wait)
                    continue
            
            # Lỗi khác (không phải DNS) → không cần retry
            print(f"❌ Lỗi đăng ký Webhook: {result}")
            return False

        except requests.RequestException as e:
            print(f"   Lỗi kết nối: {e}")
            if attempt < 5:
                time.sleep(attempt * 3)

    print("❌ Không đăng ký được Webhook sau 5 lần thử.")
    return False


# ==============================================
# ĐIỂM KHỞI CHẠY
# ==============================================

def main():
    print("=" * 50)
    print("🚀 PTM Auto Post — Khởi động")
    print("=" * 50)

    # Kiểm tra cấu hình trước khi chạy
    missing_keys = validate_settings()
    if missing_keys:
        print("\n❌ Lỗi: Thiếu các API key sau trong file config/.env:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\nHướng dẫn: Copy file config/.env.example thành config/.env và điền đầy đủ.")
        return

    # Khởi động Webhook server
    if not setup_webhook_server():
        return

    # ==============================================
    # PHASE 1: Chọn chủ đề qua Telegram (không LLM)
    # ==============================================
    print("\n📌 Giai đoạn chọn chủ đề...")
    selected_topic_id = select_topic_interactively()

    if selected_topic_id is None:
        print("❌ Không chọn được chủ đề. Kết thúc.")
        return

    # ==============================================
    # PHASE 2: Chạy LangGraph pipeline
    # ==============================================
    print(f"\n🚀 Bắt đầu viết bài cho topic #{selected_topic_id}...")

    # Khởi tạo state — topic_id đã được chọn sẵn
    initial_state: PostState = {
        "topic_id":         selected_topic_id,
        "topic_title":      "",
        "mode":             "",
        "san_pham":         "",
        "media_folder_key": "",
        "post_content":     "",
        "image_paths":      [],
        "image_raw_bytes":  [],
        "selected_page_ids": [],
        "approval_status":  "",
        "telegram_message_id": None,
        "facebook_post_id": None,
        "error_message":    None,
    }

    # Chạy graph
    app = build_graph()
    final_state = app.invoke(initial_state)

    # Báo cáo kết quả
    print("\n" + "=" * 50)
    if final_state.get("facebook_post_id"):
        print(f"✅ Đăng bài thành công! Post ID: {final_state['facebook_post_id']}")
    elif final_state.get("approval_status") == "rejected":
        print("⏭️  Bài bị bỏ qua hôm nay.")
    elif final_state.get("approval_status") == "timeout":
        print("⏰ Hết thời gian chờ duyệt bài.")
    elif final_state.get("error_message"):
        print(f"❌ Có lỗi xảy ra: {final_state['error_message']}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng chương trình (Ctrl+C).")
