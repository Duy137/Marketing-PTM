"""
topic_selector.py — Controller chọn chủ đề PRE-PIPELINE (không dùng LLM).

Luồng:
1. Lấy dữ liệu topic từ topic_service.py
2. Dựng giao diện text & keyboard từ views/telegram_views.py
3. Giao tiếp Telegram qua services/telegram_service.py
4. Chờ nhận phản hồi từ user qua pending_store.py
"""

import queue
from api.pending_store import (
    register_topic_selection_queue,
    unregister_topic_selection_queue,
)
from services.topic_service import (
    suggest_topic,
    read_topics_csv,
    toggle_topic_status,
    reset_all_topics,
    get_topic_by_id,
)
from views.telegram_views import (
    render_suggestion_text,
    render_suggestion_keyboard,
    render_mode_picker_text,
    render_mode_picker_keyboard,
    render_list_text,
    render_list_keyboard,
    TOPICS_PER_PAGE,
)
from services.telegram_service import (
    send_message,
    edit_message,
    delete_message,
    answer_callback,
)

SELECTION_TIMEOUT = 3600  # 1 giờ timeout


def select_topic_interactively() -> int | None:
    """
    Giao tiếp với user qua Telegram để chọn chủ đề (hỗ trợ lọc theo Mode).
    Trả về topic_id đã được user xác nhận, hoặc None nếu timeout/lỗi.
    """
    q = register_topic_selection_queue()

    try:
        active_mode: str | None = None
        excluded_ids: list[int] = []
        current_topic = suggest_topic(exclude_ids=excluded_ids, mode=active_mode)

        if not current_topic:
            print("[topic_selector] Không còn chủ đề nào khả dụng!")
            return None

        # Gửi tin nhắn gợi ý đầu tiên
        text = render_suggestion_text(current_topic, active_mode=active_mode)
        keyboard = render_suggestion_keyboard()
        msg_id = send_message(text, keyboard)
        print(f"[topic_selector] Đã gửi gợi ý chủ đề: {current_topic['chu_de']}")

        current_page = 1

        while True:
            try:
                callback = q.get(timeout=SELECTION_TIMEOUT)
            except queue.Empty:
                print("[topic_selector] Timeout — không có phản hồi từ user.")
                delete_message(msg_id)
                return None

            cb_id = callback["id"]
            cb_data = callback.get("data", "")

            # Tắt spinner NGAY (< 50ms)
            answer_callback(cb_id)

            # --- [✅ Viết bài này] ---
            if cb_data == "tsc":
                topic_id = int(current_topic["id"])
                edit_message(msg_id, f"✅ <b>Đã chọn chủ đề:</b> {current_topic['chu_de']} <i>({current_topic.get('mode', '')})</i>", {"inline_keyboard": []})
                print(f"[topic_selector] User xác nhận topic #{topic_id}: {current_topic['chu_de']}")
                return topic_id

            # --- [🔄 Gợi ý khác] ---
            elif cb_data == "tsn":
                if current_topic:
                    excluded_ids.append(int(current_topic["id"]))
                current_topic = suggest_topic(exclude_ids=excluded_ids, mode=active_mode)
                if not current_topic:
                    excluded_ids = []
                    current_topic = suggest_topic(mode=active_mode)
                    if not current_topic:
                        edit_message(msg_id, f"❌ Không còn chủ đề nào khả dụng cho mode <b>{active_mode}</b>!", render_suggestion_keyboard())
                        continue
                text = render_suggestion_text(current_topic, active_mode=active_mode)
                keyboard = render_suggestion_keyboard()
                edit_message(msg_id, text, keyboard)

            # --- [🎯 Đổi Mode từ Gợi ý] ---
            elif cb_data == "tsm_sug":
                text = render_mode_picker_text(active_mode=active_mode)
                keyboard = render_mode_picker_keyboard(source="sug")
                edit_message(msg_id, text, keyboard)

            # --- [🏷️ Đổi Mode từ Danh sách] ---
            elif cb_data == "tsm_list":
                text = render_mode_picker_text(active_mode=active_mode)
                keyboard = render_mode_picker_keyboard(source="list")
                edit_message(msg_id, text, keyboard)

            # --- [Xác nhận chọn Mode: tsm_set_{mode_code}_{source}] ---
            elif cb_data.startswith("tsm_set_"):
                # Dạng: tsm_set_Product_sug hoặc tsm_set_all_list hoặc tsm_set_Social Proof_sug
                parts = cb_data[len("tsm_set_"):].rsplit("_", 1)
                selected_mode_code = parts[0]
                source = parts[1] if len(parts) > 1 else "sug"

                active_mode = None if selected_mode_code == "all" else selected_mode_code
                print(f"[topic_selector] Đã chuyển mode lọc thành: {active_mode or 'Tất cả'}")

                if source == "sug":
                    excluded_ids = []
                    current_topic = suggest_topic(exclude_ids=excluded_ids, mode=active_mode)
                    if not current_topic:
                        # Fallback nếu không có topic nào cho mode này
                        all_topics = read_topics_csv(mode=active_mode)
                        if all_topics:
                            current_topic = all_topics[0]
                        else:
                            edit_message(
                                msg_id,
                                f"❌ Không tìm thấy chủ đề nào thuộc mode <b>{active_mode}</b>!",
                                render_mode_picker_keyboard(source="sug")
                            )
                            continue
                    text = render_suggestion_text(current_topic, active_mode=active_mode)
                    keyboard = render_suggestion_keyboard()
                    edit_message(msg_id, text, keyboard)
                else:
                    # Quay lại danh sách
                    current_page = 1
                    all_topics = read_topics_csv(mode=active_mode)
                    start = (current_page - 1) * TOPICS_PER_PAGE
                    page_topics = all_topics[start:start + TOPICS_PER_PAGE]
                    text = render_list_text(current_page, page_topics, all_topics, active_mode=active_mode)
                    keyboard = render_list_keyboard(current_page, len(all_topics), page_topics, active_mode=active_mode)
                    edit_message(msg_id, text, keyboard)

            # --- [◀️ Quay lại từ menu chọn Mode: tsm_back_{source}] ---
            elif cb_data.startswith("tsm_back_"):
                source = cb_data.split("_")[-1]
                if source == "sug":
                    if not current_topic:
                        current_topic = suggest_topic(mode=active_mode)
                    text = render_suggestion_text(current_topic, active_mode=active_mode)
                    keyboard = render_suggestion_keyboard()
                    edit_message(msg_id, text, keyboard)
                else:
                    all_topics = read_topics_csv(mode=active_mode)
                    start = (current_page - 1) * TOPICS_PER_PAGE
                    page_topics = all_topics[start:start + TOPICS_PER_PAGE]
                    text = render_list_text(current_page, page_topics, all_topics, active_mode=active_mode)
                    keyboard = render_list_keyboard(current_page, len(all_topics), page_topics, active_mode=active_mode)
                    edit_message(msg_id, text, keyboard)

            # --- [📋 Xem tất cả / tsl_{page}] ---
            elif cb_data.startswith("tsl_"):
                current_page = int(cb_data.split("_")[1])
                all_topics = read_topics_csv(mode=active_mode)
                start = (current_page - 1) * TOPICS_PER_PAGE
                page_topics = all_topics[start:start + TOPICS_PER_PAGE]
                text = render_list_text(current_page, page_topics, all_topics, active_mode=active_mode)
                keyboard = render_list_keyboard(current_page, len(all_topics), page_topics, active_mode=active_mode)
                edit_message(msg_id, text, keyboard)

            # --- [Toggle ⬜/✅/⏸] — tsg_{topic_id}_{page} ---
            elif cb_data.startswith("tsg_"):
                parts = cb_data.split("_")
                tid = int(parts[1])
                page = int(parts[2])
                toggle_topic_status(tid)
                all_topics = read_topics_csv(mode=active_mode)
                start = (page - 1) * TOPICS_PER_PAGE
                page_topics = all_topics[start:start + TOPICS_PER_PAGE]
                text = render_list_text(page, page_topics, all_topics, active_mode=active_mode)
                keyboard = render_list_keyboard(page, len(all_topics), page_topics, active_mode=active_mode)
                edit_message(msg_id, text, keyboard)

            # --- [✍️ Viết bài này] từ danh sách — tsw_{topic_id} ---
            elif cb_data.startswith("tsw_"):
                tid = int(cb_data.split("_")[1])
                chosen = get_topic_by_id(tid)
                if chosen:
                    edit_message(msg_id, f"✅ <b>Đã chọn chủ đề:</b> {chosen['chu_de']} <i>({chosen.get('mode', '')})</i>", {"inline_keyboard": []})
                    print(f"[topic_selector] User chọn topic #{tid} từ danh sách: {chosen['chu_de']}")
                    return tid

            # --- [🔄 Reset tất cả] ---
            elif cb_data == "tsr":
                reset_all_topics()
                all_topics = read_topics_csv(mode=active_mode)
                start = (current_page - 1) * TOPICS_PER_PAGE
                page_topics = all_topics[start:start + TOPICS_PER_PAGE]
                text = render_list_text(current_page, page_topics, all_topics, active_mode=active_mode)
                keyboard = render_list_keyboard(current_page, len(all_topics), page_topics, active_mode=active_mode)
                edit_message(msg_id, text, keyboard)

            # --- [◀️ Gợi ý chủ đề] — tsb ---
            elif cb_data == "tsb":
                if not current_topic or (active_mode and current_topic.get("mode", "").strip().lower() != active_mode.strip().lower()):
                    current_topic = suggest_topic(mode=active_mode)
                text = render_suggestion_text(current_topic, active_mode=active_mode)
                keyboard = render_suggestion_keyboard()
                edit_message(msg_id, text, keyboard)

    finally:
        unregister_topic_selection_queue()
