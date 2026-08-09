"""
telegram_views.py — Tầng giao diện Telegram (HTML Texts & Inline Keyboards).

Nơi duy nhất định dạng văn bản HTML và tạo nút bấm cho giao diện Telegram:
- Màn hình Gợi ý chủ đề
- Màn hình Danh sách chủ đề (phân trang + toggle + chọn viết)
- Màn hình Duyệt bài đăng
- Màn hình Chọn Fanpage Facebook
"""

from datetime import datetime
from config.settings import FacebookPage

TOPICS_PER_PAGE = 10
STATUS_EMOJI = {
    "chua_dang": "⬜",
    "da_dang":   "✅",
    "tam_hoan":  "⏸",
}


# ==============================================
# VIEW: CHỌN CHỦ ĐỀ (TOPIC SELECTION)
# ==============================================

def render_suggestion_text(topic: dict) -> str:
    """Nội dung text màn hình Gợi ý chủ đề."""
    return (
        f"📌 <b>Gợi ý chủ đề hôm nay:</b>\n\n"
        f"💡 {topic['chu_de']}\n"
        f"🎯 Mode: {topic['mode']}\n"
        f"📁 Thư mục ảnh: {topic['thu_muc_anh']}"
    )


def render_suggestion_keyboard() -> dict:
    """Nút bấm màn hình Gợi ý chủ đề."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Viết bài này",  "callback_data": "tsc"},
                {"text": "🔄 Gợi ý khác",   "callback_data": "tsn"},
                {"text": "📋 Xem tất cả",   "callback_data": "tsl_1"},
            ]
        ]
    }


def render_list_text(page: int, page_topics: list[dict], all_topics: list[dict]) -> str:
    """Nội dung text màn hình Danh sách chủ đề."""
    total_pages = (len(all_topics) + TOPICS_PER_PAGE - 1) // TOPICS_PER_PAGE
    lines = [f"📋 <b>DANH SÁCH CHỦ ĐỀ</b> (Trang {page}/{total_pages})\n"]

    start_idx = (page - 1) * TOPICS_PER_PAGE
    for i, topic in enumerate(page_topics, start=1):
        emoji = STATUS_EMOJI.get(topic["trang_thai"], "⬜")
        title = topic["chu_de"]
        if len(title) > 50:
            title = title[:47] + "..."
        date_str = ""
        if topic["trang_thai"] == "da_dang" and topic.get("lan_cuoi_dang"):
            try:
                d = datetime.strptime(topic["lan_cuoi_dang"], "%Y-%m-%d")
                date_str = f"  [{d.strftime('%d/%m')}]"
            except Exception:
                pass
        lines.append(f"{i + start_idx}. {emoji} {title}{date_str}")

    return "\n".join(lines)


def render_list_keyboard(page: int, total_topics: int, page_topics: list[dict]) -> dict:
    """
    Bàn phím cho màn hình Danh sách chủ đề:
    Tách 10 chủ đề thành các hàng 5 nút để Telegram client không bị cắt bớt nút (Telegram giới hạn max 8 nút/hàng).
    - Hàng 1: Toggle status (bài 1 -> 5)
    - Hàng 2: Toggle status (bài 6 -> 10)
    - Hàng 3: Chọn viết bài (bài 1 -> 5)
    - Hàng 4: Chọn viết bài (bài 6 -> 10)
    - Hàng 5: Phân trang
    - Hàng 6: Actions (Reset + Quay lại)
    """
    total_pages = (total_topics + TOPICS_PER_PAGE - 1) // TOPICS_PER_PAGE

    toggle_row_1 = []
    toggle_row_2 = []
    write_row_1 = []
    write_row_2 = []

    for i, topic in enumerate(page_topics, start=1):
        emoji = STATUS_EMOJI.get(topic["trang_thai"], "⬜")
        tid = int(topic["id"])
        
        toggle_btn = {
            "text": f"{emoji}{i}",
            "callback_data": f"tsg_{tid}_{page}"
        }
        write_btn = {
            "text": f"✍️{topic['id']}",
            "callback_data": f"tsw_{tid}"
        }

        if i <= 5:
            toggle_row_1.append(toggle_btn)
            write_row_1.append(write_btn)
        else:
            toggle_row_2.append(toggle_btn)
            write_row_2.append(write_btn)

    # Phân trang
    nav_row = []
    if page > 1:
        nav_row.append({"text": "◀️ Trước", "callback_data": f"tsl_{page - 1}"})
    nav_row.append({"text": f"📄 {page}/{total_pages}", "callback_data": "tsl_1"})
    if page < total_pages:
        nav_row.append({"text": "Sau ▶️", "callback_data": f"tsl_{page + 1}"})

    # Actions
    action_row = [
        {"text": "🔄 Reset tất cả",   "callback_data": "tsr"},
        {"text": "◀️ Gợi ý chủ đề",  "callback_data": "tsb"},
    ]

    inline_keyboard = []
    if toggle_row_1:
        inline_keyboard.append(toggle_row_1)
    if toggle_row_2:
        inline_keyboard.append(toggle_row_2)
    if write_row_1:
        inline_keyboard.append(write_row_1)
    if write_row_2:
        inline_keyboard.append(write_row_2)
    inline_keyboard.append(nav_row)
    inline_keyboard.append(action_row)

    return {"inline_keyboard": inline_keyboard}


# ==============================================
# VIEW: DUYỆT BÀI ĐĂNG (APPROVER)
# ==============================================

def render_approval_text(state: dict) -> str:
    """Nội dung text xem trước bài viết để duyệt."""
    title = state.get("topic_title", "Không rõ")
    mode = state.get("mode", "Chưa xác định")
    content = state.get("post_content", "")
    images = state.get("image_paths", [])
    raw_bytes = state.get("image_raw_bytes", [])

    img_count = len(images) if images else len(raw_bytes)

    return (
        f"📝 <b>BÀI VIẾT MỚI CẦN DUYỆT</b>\n"
        f"📌 <b>Chủ đề:</b> {title}\n"
        f"🎯 <b>Mode:</b> {mode}\n"
        f"🖼️ <b>Số ảnh đính kèm:</b> {img_count}\n"
        f"=============================="
        f"\n\n{content}\n\n"
        f"==============================\n"
        f"Vui lòng chọn thao tác bên dưới 👇"
    )


def render_approval_keyboard() -> dict:
    """Nút bấm màn hình duyệt bài."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Duyệt đăng",    "callback_data": "approve"},
                {"text": "🔄 Cùng chủ đề",  "callback_data": "regen_same"},
            ],
            [
                {"text": "🎲 Chủ đề khác",  "callback_data": "regen_new"},
                {"text": "🖼️ Gửi ảnh",      "callback_data": "upload_img"},
            ],
            [
                {"text": "❌ Bỏ qua",       "callback_data": "reject"},
            ]
        ]
    }


# ==============================================
# VIEW: CHỌN FANPAGE (PAGE SELECTOR)
# ==============================================

def render_page_selection_text(content_preview: str) -> str:
    """Nội dung text màn hình chọn Fanpage đăng bài."""
    snippet = content_preview[:150] + "..." if len(content_preview) > 150 else content_preview
    return (
        f"📣 <b>CHỌN FANPAGE ĐỂ ĐĂNG BÀI</b>\n\n"
        f"📝 <i>Nội dung: {snippet}</i>\n\n"
        f"Bấm vào từng trang để chọn/bỏ chọn. Khi xong bấm <b>🚀 Đăng bài ngay</b>."
    )


def render_page_selection_keyboard(pages: list[FacebookPage], selected_ids: list[str]) -> dict:
    """Bàn phím chọn Fanpage (có icon tick ✅) sử dụng chuẩn FacebookPage Schema."""
    buttons = []
    for page in pages:
        pid = page["id"]
        pname = page["name"]
        icon = "✅" if pid in selected_ids else "⬜"
        buttons.append([{
            "text": f"{icon} {pname}",
            "callback_data": f"toggle_page_{pid}"
        }])

    # Nút bấm hành động
    buttons.append([
        {"text": "🚀 Đăng bài ngay", "callback_data": "publish_now"},
        {"text": "❌ Hủy",          "callback_data": "cancel_publish"}
    ])

    return {"inline_keyboard": buttons}
