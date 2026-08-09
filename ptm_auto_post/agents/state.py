"""
state.py — Định nghĩa trạng thái (State) dùng trong LangGraph.

State là "túi dữ liệu" được truyền từ node này sang node khác.
Mỗi node có thể đọc và ghi vào State.
"""

from typing import TypedDict, Optional
from pathlib import Path


class PostState(TypedDict):
    """
    Trạng thái của một luồng tạo bài đăng.
    Các trường này được cập nhật tuần tự qua từng bước của LangGraph.
    """

    # --- Thông tin chủ đề (được điền bởi topic_picker) ---
    topic_id: int               # ID dòng trong topics.csv
    topic_title: str            # Tiêu đề/mô tả chủ đề
    mode: str                   # Mode content (Product, Educational, Sales...)
    san_pham: str               # Tên sản phẩm (Nẹp chữ T, Tủ bếp inox...)
    media_folder_key: str       # Key thư mục ảnh (nep_chu_t, tu_bep_inox...)

    # --- Nội dung bài viết (được điền bởi content_writer) ---
    post_content: str           # Toàn bộ text bài viết đã viết xong

    # --- Hình ảnh (được điền bởi image_picker) ---
    image_paths: list[str]      # Danh sách đường dẫn ảnh từ thư mục media/
    image_raw_bytes: list       # list[bytes] — ảnh user tự gửi vào Telegram (lưu RAM, không qua disk)

    # --- Kết quả duyệt bài (được điền bởi approver) ---
    approval_status: str        # "approved" | "rejected" | "regenerate_same" | "regenerate_new" | "timeout"
    telegram_message_id: Optional[int]  # ID tin nhắn Telegram để xóa/cập nhật

    # --- Chọn page đăng (được điền bởi page_selector) ---
    selected_page_ids: list     # list[str] — danh sách page_id được chọn để đăng

    # --- Kết quả đăng bài (được điền bởi publisher) ---
    facebook_post_id: Optional[str]     # ID bài đăng trên Facebook (nếu thành công)
    error_message: Optional[str]        # Thông báo lỗi (nếu có)
