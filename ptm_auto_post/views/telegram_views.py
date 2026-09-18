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


AVAILABLE_MODES = [
    {"code": "Product",       "name": "Product",       "emoji": "📦"},
    {"code": "Sales",         "name": "Sales",         "emoji": "💰"},
    {"code": "Social Proof",  "name": "Social Proof",  "emoji": "🚚"},
    {"code": "Educational",   "name": "Educational",   "emoji": "🎓"},
    {"code": "Pain & Relief", "name": "Pain & Relief", "emoji": "🛡️"},
    {"code": "Authority",     "name": "Authority",     "emoji": "🏭"},
    {"code": "Lifestyle",     "name": "Lifestyle",     "emoji": "✨"},
]


# ==============================================
# VIEW: MAIN MENU
# ==============================================

def render_main_menu_text() -> str:
    """Nội dung text màn hình Main Menu."""
    return (
        "🏠 <b>PTM AUTO POST — MENU CHÍNH</b>\n\n"
        "Chọn thao tác bên dưới 👇"
    )


def render_main_menu_keyboard() -> dict:
    """Nút bấm màn hình Main Menu."""
    return {
        "inline_keyboard": [
            [
                {"text": "✍️ Viết bài", "callback_data": "menu_write"},
            ]
        ]
    }


# ==============================================
# VIEW: CHỌN CHỦ ĐỀ (TOPIC SELECTION)
# ==============================================

def render_suggestion_text(topic: dict, active_mode: str | None = None) -> str:
    """Nội dung text màn hình Gợi ý chủ đề."""
    filter_tag = f" [Lọc: 🏷️ <b>{active_mode}</b>]" if active_mode else ""
    return (
        f"📌 <b>Gợi ý chủ đề hôm nay{filter_tag}:</b>\n\n"
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
            ],
            [
                {"text": "🎯 Đổi Mode",     "callback_data": "tsm_sug"},
                {"text": "📋 Xem danh sách", "callback_data": "tsl_1"},
            ],
            [
                {"text": "🏠 Về menu",      "callback_data": "menu_home"},
            ]
        ]
    }


def render_mode_picker_text(active_mode: str | None = None) -> str:
    """Nội dung text màn hình Chọn Mode."""
    curr = active_mode if active_mode else "Tất cả"
    return (
        f"🎯 <b>CHỌN MODE NỘI DUNG MONG MUỐN</b>\n"
        f"<i>(Hiện tại đang lọc: <b>{curr}</b>)</i>\n\n"
        f"Vui lòng chọn 1 Mode bên dưới để lọc danh sách/gợi ý 👇"
    )


def render_mode_picker_keyboard(source: str = "sug") -> dict:
    """
    Bàn phím chọn Mode:
    - Hàng 1: Tất cả các Mode
    - Hàng 2: Product & Sales
    - Hàng 3: Social Proof & Educational
    - Hàng 4: Pain & Relief & Authority
    - Hàng 5: Lifestyle
    - Hàng 6: Quay lại
    """
    return {
        "inline_keyboard": [
            [
                {"text": "🌐 Tất cả các Mode", "callback_data": f"tsm_set_all_{source}"},
            ],
            [
                {"text": "📦 Product",      "callback_data": f"tsm_set_Product_{source}"},
                {"text": "💰 Sales",        "callback_data": f"tsm_set_Sales_{source}"},
            ],
            [
                {"text": "🚚 Social Proof", "callback_data": f"tsm_set_Social Proof_{source}"},
                {"text": "🎓 Educational",  "callback_data": f"tsm_set_Educational_{source}"},
            ],
            [
                {"text": "🛡️ Pain & Relief", "callback_data": f"tsm_set_Pain & Relief_{source}"},
                {"text": "🏭 Authority",     "callback_data": f"tsm_set_Authority_{source}"},
            ],
            [
                {"text": "✨ Lifestyle",     "callback_data": f"tsm_set_Lifestyle_{source}"},
            ],
            [
                {"text": "◀️ Quay lại",      "callback_data": f"tsm_back_{source}"},
            ]
        ]
    }


def render_list_text(page: int, page_topics: list[dict], all_topics: list[dict], active_mode: str | None = None) -> str:
    """Nội dung text màn hình Danh sách chủ đề."""
    total_pages = max(1, (len(all_topics) + TOPICS_PER_PAGE - 1) // TOPICS_PER_PAGE)
    mode_str = f" [Mode: <b>{active_mode}</b>]" if active_mode else " [Tất cả Mode]"
    lines = [f"📋 <b>DANH SÁCH CHỦ ĐỀ</b>{mode_str} (Trang {page}/{total_pages} - {len(all_topics)} chủ đề)\n"]

    if not page_topics:
        lines.append("<i>(Không có chủ đề nào trong danh mục này)</i>")
        return "\n".join(lines)

    start_idx = (page - 1) * TOPICS_PER_PAGE
    for i, topic in enumerate(page_topics, start=1):
        emoji = STATUS_EMOJI.get(topic["trang_thai"], "⬜")
        title = topic["chu_de"]
        if len(title) > 42:
            title = title[:39] + "..."
        date_str = ""
        if topic["trang_thai"] == "da_dang" and topic.get("lan_cuoi_dang"):
            try:
                d = datetime.strptime(topic["lan_cuoi_dang"], "%Y-%m-%d")
                date_str = f" [{d.strftime('%d/%m')}]"
            except Exception:
                pass
        mode_tag = f" <i>({topic.get('mode', '')})</i>" if not active_mode else ""
        lines.append(f"{i + start_idx}. {emoji} {title}{mode_tag}{date_str}")

    return "\n".join(lines)


def render_list_keyboard(page: int, total_topics: int, page_topics: list[dict], active_mode: str | None = None) -> dict:
    """
    Bàn phím cho màn hình Danh sách chủ đề:
    - Hàng 1 & 2: Toggle status
    - Hàng 3 & 4: Chọn viết bài
    - Hàng 5: Phân trang
    - Hàng 6: Actions (Đổi Mode + Reset + Gợi ý)
    """
    total_pages = max(1, (total_topics + TOPICS_PER_PAGE - 1) // TOPICS_PER_PAGE)

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
    nav_row.append({"text": f"📄 {page}/{total_pages}", "callback_data": f"tsl_{page}"})
    if page < total_pages:
        nav_row.append({"text": "Sau ▶️", "callback_data": f"tsl_{page + 1}"})

    # Actions (Có thêm nút Đổi Mode)
    action_row = [
        {"text": "🏷️ Đổi Mode",      "callback_data": "tsm_list"},
        {"text": "🔄 Reset",         "callback_data": "tsr"},
        {"text": "◀️ Gợi ý",         "callback_data": "tsb"},
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
    if nav_row:
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
                {"text": "✅ Duyệt đăng",       "callback_data": "approve"},
                {"text": "🔄 Cùng chủ đề",     "callback_data": "regen_same"},
            ],
            [
                {"text": "⬅️ Chọn lại topic",   "callback_data": "back_to_topic"},
                {"text": "🖼️ Gửi ảnh",         "callback_data": "upload_img"},
            ],
            [
                {"text": "❌ Bỏ qua",           "callback_data": "reject"},
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
