"""
main.py — Điểm khởi chạy chính của hệ thống PTM Auto Post.

Đây là file duy nhất bạn cần chạy:
    python main.py

Hệ thống chạy mãi mãi (không tự thoát), điều hướng qua Telegram:
    🏠 Main Menu → ✍️ Viết bài → Chọn topic → Viết bài → Duyệt → Đăng
    Sau khi đăng hoặc bỏ qua → quay lại Main Menu (chờ lần tiếp theo)

Điều hướng đầy đủ tại màn hình Duyệt bài:
    ✅ Duyệt đăng     → Chọn page → Đăng Facebook → Main Menu
    🔄 Cùng chủ đề   → Viết lại bài (giữ nguyên chủ đề)
    ⬅️ Chọn lại topic → Quay về màn hình chọn chủ đề
    🖼️ Gửi ảnh       → Bot chờ nhận ảnh từ bạn → Gửi lại preview
    ❌ Bỏ qua         → Main Menu (không đăng)
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
from views.telegram_views import render_main_menu_text, render_main_menu_keyboard
from services.telegram_service import send_message
from api.pending_store import register_callback, unregister_callback

import threading
import queue
import uvicorn
import requests
import subprocess
import re
import time
from config.settings import TELEGRAM_BOT_TOKEN
from services.telegram_service import answer_callback


# ==============================================
# HÀM ĐỊNH TUYẾN (Routing)
# ==============================================

def route_after_approval(state: PostState) -> str:
    """
    Quyết định bước tiếp theo dựa vào kết quả duyệt bài.

    - "approved"        → Chọn page rồi đăng bài
    - "regenerate_same" → Viết lại bài (giữ nguyên chủ đề)
    - "back_to_topic"   → Báo hiệu thoát graph — xử lý ở session loop
    - "rejected"        → Báo hiệu thoát graph — xử lý ở session loop
    - "timeout"         → Báo hiệu thoát graph — xử lý ở session loop
    """
    status = state.get("approval_status", "rejected")
    print(f"[router] Trạng thái duyệt: {status}")

    if status == "approved":
        return "select_pages"
    elif status == "regenerate_same":
        return "write_again"
    else:
        # back_to_topic / rejected / timeout → thoát graph, xử lý ở session loop
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
                    [regen_same]   [back_to_topic/     [approved]
                         │          rejected/timeout]      │
                    write_content         END          select_pages
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
            "select_pages": "select_pages",   # Duyệt → Chọn page
            "write_again":  "write_content",  # Viết lại cùng chủ đề
            "end":          END,              # back_to_topic / rejected / timeout
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
# SESSION HELPERS
# ==============================================

def send_main_menu() -> int | None:
    """Gửi tin nhắn Main Menu mới xuống Telegram. Trả về message_id."""
    text = render_main_menu_text()
    keyboard = render_main_menu_keyboard()
    return send_message(text, keyboard)


def wait_main_menu_action(msg_id: int) -> str:
    """
    Chờ user bấm nút trên tin nhắn Main Menu.
    Trả về action string (ví dụ: "menu_write") hoặc "timeout".

    Dùng polling loop thay vì 1 blocking call dài để Ctrl+C hoạt động trên Windows.
    """
    MENU_TIMEOUT = 86400   # 24 giờ tổng cộng
    POLL_INTERVAL = 1.0    # Kiểm tra mỗi 1 giây → Ctrl+C phản hồi trong ~1 giây
    elapsed = 0.0

    callback_q = register_callback(msg_id)
    try:
        while elapsed < MENU_TIMEOUT:
            try:
                callback = callback_q.get(timeout=POLL_INTERVAL)
                cb_id = callback["id"]
                action = callback.get("data", "")
                answer_callback(cb_id)
                return action
            except queue.Empty:
                elapsed += POLL_INTERVAL
                continue
        return "timeout"
    finally:
        unregister_callback(msg_id)


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

    send_message("✅ <b>Hệ thống PTM Auto Post đã online!</b>")
    app = build_graph()

    # ==============================================
    # SESSION LOOP — chạy mãi mãi, không tự thoát
    # ==============================================
    print("\n🔄 Bắt đầu session loop...")

    while True:
        # ── BƯỚC 1: Hiển thị Main Menu ──────────────────────────────────────
        print("\n[session] Hiển thị Main Menu")
        menu_msg_id = send_main_menu()
        if not menu_msg_id:
            print("[session] Không gửi được Main Menu. Thử lại sau 5 giây.")
            time.sleep(5)
            continue

        action = wait_main_menu_action(menu_msg_id)

        if action == "menu_write":
            pass  # Tiếp tục xuống bước chọn topic
        elif action == "timeout":
            print("[session] Main Menu timeout (24h). Reset.")
            continue
        else:
            print(f"[session] Action không xác định: {action}. Bỏ qua.")
            continue

        # ── BƯỚC 2: Chọn chủ đề ────────────────────────────────────────────
        print("\n[session] Chuyển sang chọn chủ đề...")
        selected_topic_id = select_topic_interactively()

        if selected_topic_id == "BACK_TO_MENU":
            print("[session] User về menu — quay lại Main Menu.")
            continue

        if selected_topic_id is None:
            print("[session] Timeout/lỗi chọn chủ đề — quay lại Main Menu.")
            send_message("⏰ <b>Hết thời gian chờ chọn chủ đề.</b> Quay về Main Menu.")
            continue

        # ── BƯỚC 3: Chạy LangGraph pipeline ────────────────────────────────
        print(f"\n[session] Bắt đầu viết bài cho topic #{selected_topic_id}...")

        initial_state: PostState = {
            "topic_id":             selected_topic_id,
            "topic_title":          "",
            "mode":                 "",
            "san_pham":             "",
            "media_folder_key":     "",
            "post_content":         "",
            "image_paths":          [],
            "image_raw_bytes":      [],
            "selected_page_ids":    [],
            "approval_status":      "",
            "telegram_message_id":  None,
            "facebook_post_id":     None,
            "error_message":        None,
        }

        final_state = app.invoke(initial_state)
        approval_status = final_state.get("approval_status", "")

        # ── BƯỚC 4: Xử lý kết quả pipeline ────────────────────────────────
        if final_state.get("facebook_post_id"):
            print(f"[session] ✅ Đăng thành công! Post ID: {final_state['facebook_post_id']}")
            send_message(f"✅ <b>Đã đăng bài thành công!</b>\n📌 Post ID: {final_state['facebook_post_id']}")
            # → quay lại Main Menu

        elif approval_status == "back_to_topic":
            # User muốn chọn lại topic → quay về BƯỚC 2 (không về menu)
            print("[session] User chọn lại topic — lặp lại bước chọn chủ đề.")
            # Dùng vòng lặp nhỏ để chọn lại topic mà không hiển thị Main Menu
            while True:
                selected_topic_id = select_topic_interactively()

                if selected_topic_id == "BACK_TO_MENU":
                    print("[session] User về menu từ màn hình chọn topic.")
                    break  # Thoát vòng lặp nhỏ → quay lại while True bên ngoài

                if selected_topic_id is None:
                    print("[session] Timeout chọn topic — quay về Main Menu.")
                    break

                # Chạy lại pipeline với topic mới
                initial_state["topic_id"] = selected_topic_id
                initial_state["approval_status"] = ""
                initial_state["post_content"] = ""
                initial_state["image_paths"] = []
                initial_state["image_raw_bytes"] = []
                final_state = app.invoke(initial_state)
                approval_status = final_state.get("approval_status", "")

                if final_state.get("facebook_post_id"):
                    send_message(f"✅ <b>Đã đăng bài thành công!</b>\n📌 Post ID: {final_state['facebook_post_id']}")
                    break  # Đăng xong → về Main Menu

                if approval_status != "back_to_topic":
                    break  # rejected / timeout → về Main Menu

        elif approval_status == "rejected":
            print("[session] Bài bị bỏ qua.")

        elif approval_status == "timeout":
            print("[session] Hết thời gian duyệt bài.")
            send_message("⏰ <b>Hết thời gian duyệt bài.</b> Quay về Main Menu.")

        elif final_state.get("error_message"):
            print(f"[session] ❌ Lỗi: {final_state['error_message']}")
            send_message(f"❌ <b>Có lỗi xảy ra:</b> {final_state['error_message']}")

        # Tất cả nhánh đều kết thúc → quay lại đầu while True → hiển thị Main Menu


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng chương trình (Ctrl+C).")


