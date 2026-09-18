"""
approver.py — Controller duyệt bài viết qua Telegram.

1. Gửi preview (album ảnh + bài viết + nút bấm) qua telegram_service
2. Đăng ký nhận callback qua pending_store
3. Nếu user bấm "🖼️ Gửi ảnh" → chuyển sang mode chờ nhận ảnh
4. Trả về approval_status trong PostState
"""

import queue
from pathlib import Path
from agents.state import PostState
from api.pending_store import (
    register_callback,
    unregister_callback,
    activate_message_queue,
    deactivate_message_queue,
)
from views.telegram_views import (
    render_approval_text,
    render_approval_keyboard,
)
from services.telegram_service import (
    send_message,
    edit_message,
    delete_message,
    answer_callback,
    send_media_group_paths,
    send_media_group_bytes,
)

APPROVAL_TIMEOUT = 3600  # 1 giờ timeout


def _download_telegram_file(file_id: str) -> bytes | None:
    """Tải file từ Telegram API dạng raw bytes."""
    import requests
    from config.settings import TELEGRAM_BOT_TOKEN
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=10,
        )
        file_path = r.json().get("result", {}).get("file_path")
        if not file_path:
            return None
        r_file = requests.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}",
            timeout=30,
        )
        return r_file.content
    except Exception as e:
        print(f"[approver] Lỗi tải ảnh: {e}")
        return None


def _handle_image_upload(preview_msg_id: int) -> list[bytes]:
    """Chế độ chờ nhận ảnh từ user cho đến khi gõ /xong."""
    msg_q = activate_message_queue()
    prompt_msg_id = send_message(
        "📸 <b>ĐÃ BẬT CHẾ ĐỘ NHẬN ẢNH</b>\n\n"
        "Hãy gửi từ 1-4 ảnh vào chat này.\n"
        "Khi gửi xong, gõ <b>/xong</b> để hoàn tất."
    )

    received_bytes: list[bytes] = []

    try:
        while True:
            try:
                msg = msg_q.get(timeout=600)
            except queue.Empty:
                print("[approver] Timeout chờ nhận ảnh.")
                break

            text = msg.get("text", "").strip()
            if text == "/xong":
                break

            photos = msg.get("photo")
            if photos:
                best_photo = photos[-1]
                file_id = best_photo.get("file_id")
                if file_id:
                    img_data = _download_telegram_file(file_id)
                    if img_data:
                        received_bytes.append(img_data)
                        count = len(received_bytes)
                        send_message(f"✅ Đã nhận ảnh {count}/4.")
                        if count >= 4:
                            break
    finally:
        deactivate_message_queue()
        delete_message(prompt_msg_id)

    return received_bytes


def send_for_approval(state: PostState) -> PostState:
    """Node duyệt bài trong LangGraph workflow."""
    print("[approver] Đang gửi bài viết lên Telegram để duyệt...")

    # Gửi album ảnh nếu có
    if state.get("image_raw_bytes"):
        send_media_group_bytes(state["image_raw_bytes"])
    elif state.get("image_paths"):
        send_media_group_paths(state["image_paths"])

    # Dựng giao diện preview bài viết
    text = render_approval_text(state)
    keyboard = render_approval_keyboard()
    msg_id = send_message(text, keyboard)

    if not msg_id:
        print("[approver] CẢNH BÁO: Không gửi được tin nhắn preview!")
        return {**state, "approval_status": "rejected"}

    # Đăng ký chờ callback cho message_id này
    callback_q = register_callback(msg_id)

    try:
        while True:
            try:
                callback = callback_q.get(timeout=APPROVAL_TIMEOUT)
            except queue.Empty:
                print("[approver] Hết thời gian chờ duyệt bài (Timeout).")
                current_text = render_approval_text(state)
                edit_message(msg_id, f"{current_text}\n\n⏰ <b>HẾT THỜI GIAN DUYỆT BÀI</b>", {"inline_keyboard": []})
                return {**state, "approval_status": "timeout"}

            cb_id = callback["id"]
            action = callback.get("data", "")
            answer_callback(cb_id)

            if action == "approve":
                current_text = render_approval_text(state)
                edit_message(msg_id, f"{current_text}\n\n✅ <b>BÀI VIẾT ĐÃ ĐƯỢC DUYỆT</b>\nĐang chuyển sang chọn Fanpage...", {"inline_keyboard": []})
                print("[approver] User bấm: DUYỆT ĐĂNG")
                return {**state, "approval_status": "approved", "telegram_message_id": msg_id}

            elif action == "regen_same":
                current_text = render_approval_text(state)
                edit_message(msg_id, f"{current_text}\n\n🔄 <b>VIẾT LẠI BÀI (CÙNG CHỦ ĐỀ)</b>", {"inline_keyboard": []})
                print("[approver] User bấm: CÙNG CHỦ ĐỀ")
                return {**state, "approval_status": "regenerate_same"}

            elif action == "back_to_topic":
                current_text = render_approval_text(state)
                edit_message(msg_id, f"{current_text}\n\n⬅️ <b>QUAY LẠI CHỌN CHỦ ĐỀ</b>", {"inline_keyboard": []})
                print("[approver] User bấm: CHỌN LẠI TOPIC")
                return {**state, "approval_status": "back_to_topic"}

            elif action == "upload_img":
                print("[approver] User bấm: GỬI ẢNH")
                new_bytes = _handle_image_upload(msg_id)

                if new_bytes:
                    updated_state = {
                        **state,
                        "image_raw_bytes": new_bytes,
                        "image_paths": [],
                    }
                    send_media_group_bytes(new_bytes)
                    
                    # Xóa tin nhắn preview cũ đang bị kẹt ở tít trên lịch sử chat
                    delete_message(msg_id)
                    unregister_callback(msg_id)
                    
                    # Gửi lại tin nhắn preview (text cũ) kèm nút bấm xuống dưới cùng chat
                    new_text = render_approval_text(updated_state)
                    msg_id = send_message(new_text, keyboard)
                    callback_q = register_callback(msg_id)
                    
                    state = updated_state
                else:
                    send_message("⚠️ Không có ảnh nào mới được tải lên.")

            elif action == "reject":
                current_text = render_approval_text(state)
                edit_message(msg_id, f"{current_text}\n\n❌ <b>BÀI VIẾT ĐÃ BỊ BỎ QUA</b>", {"inline_keyboard": []})
                print("[approver] User bấm: BỎ QUA")
                return {**state, "approval_status": "rejected"}

    finally:
        unregister_callback(msg_id)
