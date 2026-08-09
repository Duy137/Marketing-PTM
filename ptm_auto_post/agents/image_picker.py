"""
image_picker.py — Node 3: Chọn ảnh ngẫu nhiên từ thư mục media.

Logic:
1. Đọc thư mục ảnh tương ứng với sản phẩm trong state
2. Nếu thư mục đó trống → fallback sang thư mục 'chung'
3. Chọn ngẫu nhiên N ảnh (N = IMAGES_PER_POST trong settings)
4. Nếu cả 'chung' cũng trống → trả về list rỗng (đăng bài không có ảnh)
"""

import random
from pathlib import Path

from config.settings import MEDIA_FOLDER_MAP, IMAGES_PER_POST
from agents.state import PostState

# Các đuôi file ảnh được chấp nhận
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _get_images_from_folder(folder: Path) -> list[Path]:
    """Lấy tất cả file ảnh trong một thư mục (không đệ quy)."""
    if not folder.exists():
        return []
    return [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]


def pick_images(state: PostState) -> PostState:
    """
    Chọn ảnh ngẫu nhiên từ thư mục phù hợp với sản phẩm.
    """
    folder_key = state.get("media_folder_key", "chung")
    print(f"[image_picker] Đang tìm ảnh trong thư mục: {folder_key}")

    # Bước 1: Thử thư mục chính của sản phẩm
    target_folder = MEDIA_FOLDER_MAP.get(folder_key, MEDIA_FOLDER_MAP["nep_inox"])
    images = _get_images_from_folder(target_folder)

    # Bước 2: Fallback sang thư mục 'nep_inox' nếu thư mục chính trống
    if not images and folder_key != "nep_inox":
        print(f"[image_picker] Thư mục '{folder_key}' trống, fallback sang 'nep_inox'")
        images = _get_images_from_folder(MEDIA_FOLDER_MAP["nep_inox"])

    # Bước 3: Nếu vẫn không có ảnh → đăng bài không kèm ảnh
    if not images:
        print("[image_picker] Không tìm thấy ảnh nào. Bài sẽ đăng không có ảnh.")
        return {**state, "image_paths": []}

    # Bước 4: Chọn ngẫu nhiên tối đa N ảnh
    count = min(IMAGES_PER_POST, len(images))
    selected = random.sample(images, count)
    selected_paths = [str(p) for p in selected]

    print(f"[image_picker] Đã chọn {len(selected_paths)} ảnh: {[Path(p).name for p in selected_paths]}")

    return {
        **state,
        "image_paths": selected_paths,
    }
