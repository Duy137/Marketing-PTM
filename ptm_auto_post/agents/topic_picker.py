"""
topic_picker.py — Node 1: Điền thông tin chủ đề vào State.

Sử dụng topic_service.py để truy vấn dữ liệu chủ đề.
Nạp thông tin chủ đề đã chọn ở bước pre-pipeline vào PostState,
hoặc bốc chủ đề mới khi người dùng bấm "Chủ đề khác" (regenerate_new).
"""

from agents.state import PostState
from services.topic_service import get_topic_by_id, suggest_topic, mark_topic_as_posted


def pick_topic(state: PostState) -> PostState:
    """
    Node 1: Điền thông tin chủ đề vào State.

    - Nếu state["approval_status"] == "regenerate_new": User vừa bấm nút "Chủ đề khác" trên Telegram.
      Xóa topic_id cũ và tự chọn ngẫu nhiên một chủ đề MỚI (loại trừ chủ đề vừa bị đổi).
    - Nếu state["topic_id"] != 0: Đọc thông tin topic từ topic_service theo ID đó (do topic_selector chọn).
    - Nếu state["topic_id"] == 0: Tự chọn theo logic ưu tiên (fallback).
    """
    print("[topic_picker] Đang nạp thông tin chủ đề...")

    approval_status = state.get("approval_status", "")
    old_topic_id = state.get("topic_id", 0)

    # --- TRƯỜNG HỢP 1: NẾU USER VỪA BẤM "CHỦ ĐỀ KHÁC" (REGENERATE_NEW) ---
    if approval_status == "regenerate_new":
        print(f"[topic_picker] Khách chọn ĐỔI CHỦ ĐỀ KHÁC (bỏ qua topic #{old_topic_id})...")
        topic_row = suggest_topic(exclude_ids=[old_topic_id])
        if not topic_row:
            # Fallback nếu không còn topic nào khác
            topic_row = suggest_topic()

        if not topic_row:
            raise ValueError("[topic_picker] Không còn chủ đề nào khả dụng!")

        print(f"[topic_picker] Đã bốc chủ đề mới: #{topic_row['id']} - {topic_row['chu_de']}")
        return {
            **state,
            "topic_id":         int(topic_row["id"]),
            "topic_title":      str(topic_row["chu_de"]),
            "mode":             str(topic_row["mode"]),
            "san_pham":         str(topic_row["san_pham"]),
            "media_folder_key": str(topic_row["thu_muc_anh"]),
            "approval_status":  "",  # Reset status sau khi đổi
        }

    # --- TRƯỜNG HỢP 2: NẠP TOPIC ĐÃ CHỌN HOẶC FALLBACK ---
    pre_selected_id = old_topic_id
    topic_row = None

    if pre_selected_id != 0:
        topic_row = get_topic_by_id(pre_selected_id)
        if topic_row:
            print(f"[topic_picker] Dùng chủ đề đã chọn sẵn: {topic_row['chu_de']}")
        else:
            print(f"[topic_picker] CẢNH BÁO: Không tìm thấy topic_id={pre_selected_id}. Chuyển sang tự chọn.")

    if not topic_row:
        topic_row = suggest_topic()
        if not topic_row:
            raise ValueError("[topic_picker] Không còn chủ đề nào khả dụng!")
        print(f"[topic_picker] Tự động chọn chủ đề: {topic_row['chu_de']}")

    return {
        **state,
        "topic_id":         int(topic_row["id"]),
        "topic_title":      str(topic_row["chu_de"]),
        "mode":             str(topic_row["mode"]),
        "san_pham":         str(topic_row["san_pham"]),
        "media_folder_key": str(topic_row["thu_muc_anh"]),
    }
