"""
image_picker.py — Node 3: Chọn ảnh phù hợp từ thư mục media.

Hỗ trợ 2 chế độ, cấu hình qua settings.py:

    LLM_CHOOSE_IMAGE_TYPE = True
        → LLM đọc nội dung bài vừa viết, quyết định phân bổ số lượng ảnh
          theo từng loại (hoàn thiện / tai_xuong / gia_cong / thi_cong / ung_dung / van_chuyen).
          LLM trả về JSON: {"thuong": 1, "tai_xuong": 0, "gia_cong": 1, ...}

    LLM_CHOOSE_IMAGE_TYPE = False
        → Chọn ngẫu nhiên toàn bộ pool ảnh của sản phẩm, bất kể loại.

Cấu trúc tên file ảnh:
    - Ảnh có tag: "tai_xuong_01.jpg", "gia_cong_phay_ranh.jpg", "ung_dung_phong_bep.jpg"
    - Ảnh studio (không tag): "IMG_20240315_102233.jpg", "product_nep_t.jpg"
"""

import json
import random
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import (
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    LLM_PROVIDER, LLM_MODEL,
    MEDIA_FOLDER_MAP, IMAGES_PER_POST,
    IMAGE_TAGS, LLM_CHOOSE_IMAGE_TYPE,
)
from agents.state import PostState

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


# ==============================================
# HELPERS
# ==============================================

def _get_images_from_folder(folder: Path) -> list[Path]:
    """Lấy tất cả file ảnh trong một thư mục (không đệ quy)."""
    if not folder.exists():
        return []
    return [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]


def _classify_images(images: list[Path]) -> dict[str, list[Path]]:
    """
    Phân loại danh sách ảnh theo tag trong tên file.
    Trả về dict: {"thuong": [...], "tai_xuong": [...], "gia_cong": [...], ...}
    "thuong" = ảnh sản phẩm hoàn thiện (không có tag nào trong tên file).
    """
    buckets: dict[str, list[Path]] = {"thuong": []}
    for tag in IMAGE_TAGS:
        buckets[tag] = []

    for img in images:
        stem = img.stem.lower()
        matched = False
        for tag in IMAGE_TAGS:
            if tag in stem:
                buckets[tag].append(img)
                matched = True
                break  # Mỗi ảnh chỉ thuộc 1 loại (loại đầu tiên khớp)
        if not matched:
            buckets["thuong"].append(img)

    return buckets


def _pick_from_buckets(
    buckets: dict[str, list[Path]],
    allocation: dict[str, int],
) -> list[Path]:
    """
    Chọn ảnh từ từng bucket theo số lượng yêu cầu trong allocation.
    Nếu bucket không đủ ảnh → lấy hết những gì có.
    """
    selected: list[Path] = []
    for tag, count in allocation.items():
        if count <= 0:
            continue
        pool = buckets.get(tag, [])
        take = min(count, len(pool))
        if take > 0:
            selected.extend(random.sample(pool, take))
    return selected


def _fill_remaining(
    selected: list[Path],
    buckets: dict[str, list[Path]],
    target: int,
) -> list[Path]:
    """
    Nếu tổng ảnh đã chọn chưa đủ target → bổ sung từ toàn bộ pool còn lại.
    Tránh chọn trùng ảnh đã có.
    """
    if len(selected) >= target:
        return selected

    already_selected = set(selected)
    remaining_pool: list[Path] = []
    for pool in buckets.values():
        for img in pool:
            if img not in already_selected:
                remaining_pool.append(img)

    need = target - len(selected)
    take = min(need, len(remaining_pool))
    if take > 0:
        selected.extend(random.sample(remaining_pool, take))

    return selected


# ==============================================
# LLM-BASED IMAGE TYPE SELECTION
# ==============================================

def _ask_llm_for_allocation(
    post_content: str,
    buckets: dict[str, list[Path]],
    total: int,
) -> dict[str, int]:
    """
    Gọi LLM nhỏ để phân bổ số lượng ảnh theo loại dựa trên nội dung bài.
    Trả về dict allocation, ví dụ: {"thuong": 2, "tai_xuong": 0, "gia_cong": 1, ...}
    """
    # Tóm tắt kho ảnh có sẵn để LLM biết và không yêu cầu loại trống
    available_summary = {
        tag: len(pool)
        for tag, pool in buckets.items()
        if len(pool) > 0
    }

    prompt = f"""Bạn là hệ thống chọn ảnh cho bài đăng Facebook.

Bài đăng vừa được viết:
\"\"\"
{post_content}
\"\"\"

Kho ảnh hiện có (tên loại: số lượng ảnh):
{json.dumps(available_summary, ensure_ascii=False, indent=2)}

Giải thích các loại ảnh:
- "thuong": Ảnh sản phẩm hoàn thiện, chụp đẹp (studio/catalogue)
- "tai_xuong": Không gian xưởng, máy móc, thợ làm việc
- "gia_cong": Quá trình gia công (cắt, chấn, hàn, phay...)
- "thi_cong": Sản phẩm đang lắp đặt tại công trình
- "ung_dung": Sản phẩm hoàn thiện trong bối cảnh thực tế (có không gian công trình)
- "van_chuyen": Đóng gói, giao hàng, kho hàng

Nhiệm vụ: Chọn tổng cộng {total} ảnh. Phân bổ số lượng ảnh từng loại sao cho phù hợp nhất với nội dung và cảm xúc của bài.
- Chỉ phân bổ từ các loại có sẵn trong kho ảnh (số lượng > 0).
- Tổng phân bổ phải đúng bằng {total}.
- Nếu kho không đủ, có thể phân bổ ít hơn.

Trả về JSON duy nhất (không giải thích gì thêm):
{{"thuong": <số>, "tai_xuong": <số>, "gia_cong": <số>, "thi_cong": <số>, "ung_dung": <số>, "van_chuyen": <số>}}"""

    # Tạo LLM nhỏ (dùng cùng provider để tránh phải cấu hình thêm)
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0,
        )
    elif LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0)
    elif LLM_PROVIDER == "claude":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0)
    else:
        raise ValueError(f"LLM_PROVIDER không hợp lệ: '{LLM_PROVIDER}'")

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        # Trích xuất JSON từ response (đề phòng LLM thêm text thừa)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        allocation = json.loads(raw[start:end])
        # Đảm bảo tất cả keys đều tồn tại
        for tag in list(buckets.keys()):
            allocation.setdefault(tag, 0)
        print(f"[image_picker] LLM phân bổ ảnh: {allocation}")
        return allocation
    except Exception as e:
        print(f"[image_picker] LLM chọn ảnh lỗi ({e}), fallback random.")
        return {}  # Trả về rỗng → caller sẽ fallback random


# ==============================================
# NODE FUNCTION
# ==============================================

def pick_images(state: PostState) -> PostState:
    """
    Chọn ảnh phù hợp với nội dung bài đăng.
    Chế độ được điều khiển bởi LLM_CHOOSE_IMAGE_TYPE trong settings.py.
    """
    folder_key = state.get("media_folder_key", "chung")
    print(f"[image_picker] Đang tìm ảnh trong thư mục: {folder_key}")

    # Bước 1: Lấy pool ảnh từ thư mục sản phẩm
    target_folder = MEDIA_FOLDER_MAP.get(folder_key, MEDIA_FOLDER_MAP["nep_inox"])
    images = _get_images_from_folder(target_folder)

    # Bước 2: Fallback sang thư mục 'nep_inox' nếu thư mục chính trống
    if not images and folder_key != "nep_inox":
        print(f"[image_picker] Thư mục '{folder_key}' trống, fallback sang 'nep_inox'")
        images = _get_images_from_folder(MEDIA_FOLDER_MAP["nep_inox"])

    # Bước 3: Không có ảnh nào → đăng bài không kèm ảnh
    if not images:
        print("[image_picker] Không tìm thấy ảnh nào. Bài sẽ đăng không có ảnh.")
        return {**state, "image_paths": []}

    total = min(IMAGES_PER_POST, len(images))

    # Bước 4: Chọn ảnh theo chế độ cấu hình
    if LLM_CHOOSE_IMAGE_TYPE:
        print("[image_picker] Chế độ: LLM chọn loại ảnh theo nội dung bài")
        buckets = _classify_images(images)
        post_content = state.get("post_content", "")

        allocation = _ask_llm_for_allocation(post_content, buckets, total)

        if allocation:
            selected = _pick_from_buckets(buckets, allocation)
            # Nếu LLM phân bổ thiếu → bổ sung bằng random từ pool còn lại
            selected = _fill_remaining(selected, buckets, total)
        else:
            # Fallback random nếu LLM gặp lỗi
            print("[image_picker] Fallback: random toàn bộ pool")
            selected = random.sample(images, total)
    else:
        print("[image_picker] Chế độ: Random toàn bộ pool")
        selected = random.sample(images, total)

    selected_paths = [str(p) for p in selected]
    print(f"[image_picker] Đã chọn {len(selected_paths)} ảnh: {[Path(p).name for p in selected_paths]}")

    return {
        **state,
        "image_paths": selected_paths,
    }
