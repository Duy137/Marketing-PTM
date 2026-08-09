"""
page_selector.py — Controller chọn Fanpage Facebook để đăng bài.

Chạy tương tác qua Telegram:
1. Đọc danh sách Fanpage cấu hình từ settings.py (chuẩn FacebookPage Schema)
2. Hiển thị bàn phím toggle chọn/bỏ chọn trang
3. Khi bấm "🚀 Đăng bài ngay" → trả về danh sách selected_page_ids trong State
"""

import queue
from config.settings import FACEBOOK_PAGES, FacebookPage
from agents.state import PostState
from api.pending_store import register_callback, unregister_callback
from views.telegram_views import (
    render_page_selection_text,
    render_page_selection_keyboard,
)
from services.telegram_service import (
    send_message,
    edit_message,
    answer_callback,
)

PAGE_SELECT_TIMEOUT = 1800  # 30 phút timeout


def select_pages_for_post(state: PostState) -> PostState:
    """Node chọn Fanpage trong LangGraph workflow."""
    if not FACEBOOK_PAGES:
        print("[page_selector] CẢNH BÁO: Chưa cấu hình FACEBOOK_PAGES trong config/settings.py!")
        return {**state, "selected_page_ids": []}

    # Nếu chỉ có 1 page cấu hình → tự chọn luôn không cần hỏi
    if len(FACEBOOK_PAGES) == 1:
        single_id = FACEBOOK_PAGES[0]["id"]
        print(f"[page_selector] Tự động chọn Fanpage duy nhất: {FACEBOOK_PAGES[0]['name']}")
        return {**state, "selected_page_ids": [single_id]}

    # Mặc định chọn tất cả các page
    selected_ids = [p["id"] for p in FACEBOOK_PAGES]

    content = state.get("post_content", "")
    text = render_page_selection_text(content)
    keyboard = render_page_selection_keyboard(FACEBOOK_PAGES, selected_ids)

    msg_id = send_message(text, keyboard)
    if not msg_id:
        return {**state, "selected_page_ids": selected_ids}

    callback_q = register_callback(msg_id)

    try:
        while True:
            try:
                callback = callback_q.get(timeout=PAGE_SELECT_TIMEOUT)
            except queue.Empty:
                print("[page_selector] Timeout chọn page — tự động chọn tất cả.")
                edit_message(msg_id, f"{text}\n\n⏰ <b>Hết thời gian chọn page</b> — Tự động chọn tất cả.", {"inline_keyboard": []})
                return {**state, "selected_page_ids": selected_ids}

            cb_id = callback["id"]
            action = callback.get("data", "")
            answer_callback(cb_id)

            if action.startswith("toggle_page_"):
                pid = action.replace("toggle_page_", "")
                if pid in selected_ids:
                    selected_ids.remove(pid)
                else:
                    selected_ids.append(pid)

                new_keyboard = render_page_selection_keyboard(FACEBOOK_PAGES, selected_ids)
                edit_message(msg_id, text, new_keyboard)

            elif action == "publish_now":
                if not selected_ids:
                    answer_callback(cb_id, "⚠️ Bạn phải chọn ít nhất 1 Fanpage!")
                    continue

                page_names = [p["name"] for p in FACEBOOK_PAGES if p["id"] in selected_ids]
                edit_message(msg_id, f"{text}\n\n✅ <b>ĐÃ CHỌN {len(selected_ids)} FANPAGE:</b>\n" + "\n".join(f"• {n}" for n in page_names), {"inline_keyboard": []})
                return {**state, "selected_page_ids": selected_ids}

            elif action == "cancel_publish":
                edit_message(msg_id, f"{text}\n\n❌ <b>ĐÃ HỦY ĐĂNG BÀI</b>", {"inline_keyboard": []})
                return {**state, "approval_status": "rejected", "selected_page_ids": []}

    finally:
        unregister_callback(msg_id)
