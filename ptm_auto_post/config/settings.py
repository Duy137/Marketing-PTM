"""
settings.py — Cấu hình trung tâm của hệ thống PTM Auto Post.
Tất cả API keys và đường dẫn đều đọc từ file .env.
"""

import os
from pathlib import Path
from typing import TypedDict
from dotenv import load_dotenv

# --- Đường dẫn gốc của project ---
BASE_DIR = Path(__file__).resolve().parent.parent  # thư mục ptm_auto_post/

# Load file .env từ thư mục config/
load_dotenv(BASE_DIR / "config" / ".env")

# ==============================================
# API KEYS
# ==============================================
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

# --- Facebook pages ---
FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "")
FACEBOOK_ACCESS_TOKEN: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")


class FacebookPage(TypedDict):
    """Hợp đồng dữ liệu chuẩn duy nhất cho một Facebook Fanpage trong hệ thống."""
    id: str           # ID của Fanpage (ví dụ: "123456789")
    name: str         # Tên hiển thị Fanpage (ví dụ: "PTM Nẹp Inox")
    access_token: str # Access Token để đăng bài qua Facebook Graph API


def load_facebook_pages() -> list[FacebookPage]:
    """
    Tải danh sách Facebook Pages từ biến môi trường theo chuẩn FacebookPage Schema.
    """
    pages: list[FacebookPage] = []
    n = 1
    while True:
        page_id = os.getenv(f"FACEBOOK_PAGE_{n}_ID", "")
        if not page_id:          # Hết page
            break
        pages.append({
            "id":           page_id,
            "name":         os.getenv(f"FACEBOOK_PAGE_{n}_NAME", f"Page {n}"),
            "access_token": os.getenv(f"FACEBOOK_PAGE_{n}_TOKEN", ""),
        })
        n += 1

    # Fallback sang format cũ nếu không có format mới
    if not pages and FACEBOOK_PAGE_ID:
        pages.append({
            "id":           FACEBOOK_PAGE_ID,
            "name":         "PTM Fanpage",
            "access_token": FACEBOOK_ACCESS_TOKEN,
        })

    return pages


FACEBOOK_PAGES: list[FacebookPage] = load_facebook_pages()

# ==============================================
# CÀI ĐẶT LLM — GLOBAL DEFAULT
# ==============================================
# Dùng làm fallback cho tất cả các task không có cấu hình riêng.
# Nên chọn model tốt nhất, vì đây là default cho Content Writer.
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL:    str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

# ==============================================
# CÀI ĐẶT LLM — PER-TASK PROFILES
# ==============================================
# Mỗi task LLM có profile riêng: provider + model + temperature.
# Nếu biến môi trường không được set → tự động fallback về global default.
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │ HƯỚNG DẪN THÊM TASK MỚI:                                               │
# │ 1. Thêm 3 dòng os.getenv bên dưới theo đúng pattern                    │
# │ 2. Thêm biến tương ứng vào file .env                                   │
# │ 3. Trong agent, gọi: llm = create_llm_for_task("ten_task")             │
# │    → hàm create_llm_for_task() được định nghĩa trong llm_factory.py    │
# └─────────────────────────────────────────────────────────────────────────┘
#
# Lưu ý về nhiệt độ (temperature):
#   0.0 = Hoàn toàn deterministc, lý tưởng cho classification / structured output
#   0.7 = Cân bằng, lý tưởng cho viết nội dung sáng tạo
#   1.0 = Rất sáng tạo, không ổn định — ít dùng trong production

# --- Task: CONTENT_WRITER (viết bài fanpage) ---
# Cần model mạnh nhất để đảm bảo chất lượng content.
# Gợi ý: gpt-4o | gemini-2.0-flash | claude-3-5-sonnet-20241022
LLM_CONTENT_WRITER_PROVIDER: str = os.getenv("LLM_CONTENT_WRITER_PROVIDER", LLM_PROVIDER)
LLM_CONTENT_WRITER_MODEL:    str = os.getenv("LLM_CONTENT_WRITER_MODEL",    LLM_MODEL)
LLM_CONTENT_WRITER_TEMP:    float = float(os.getenv("LLM_CONTENT_WRITER_TEMP", "0.7"))

# --- Task: IMAGE_PICKER (chọn loại ảnh phù hợp nội dung bài) ---
# Chỉ cần phân loại đơn giản → dùng model rẻ nhất.
# Gợi ý: gpt-4o-mini | gemini-2.0-flash-lite | claude-3-haiku-20240307
LLM_IMAGE_PICKER_PROVIDER: str = os.getenv("LLM_IMAGE_PICKER_PROVIDER", LLM_PROVIDER)
LLM_IMAGE_PICKER_MODEL:    str = os.getenv("LLM_IMAGE_PICKER_MODEL",    LLM_MODEL)
LLM_IMAGE_PICKER_TEMP:    float = float(os.getenv("LLM_IMAGE_PICKER_TEMP", "0.0"))

# ==============================================
# CÀI ĐẶT HÌNH ẢNH
# ==============================================
IMAGES_PER_POST: int = int(os.getenv("IMAGES_PER_POST", "3"))

# ==============================================
# ĐƯỜNG DẪN FILES QUAN TRỌNG
# ==============================================
TOPICS_CSV: Path = BASE_DIR / "data" / "topics.csv"
SYSTEM_PROMPT_FILE: Path = BASE_DIR / "prompts" / "system_prompt.txt"
MEDIA_DIR: Path = BASE_DIR / "media"
LOGS_DIR: Path = BASE_DIR / "logs"
POST_HISTORY_LOG: Path = LOGS_DIR / "post_history.log"

# ==============================================
# ÁNH XẠ: Thư mục ảnh theo từng loại sản phẩm
# Key = giá trị trong cột 'thu_muc_anh' của topics.csv
# ==============================================
MEDIA_FOLDER_MAP: dict[str, Path] = {
    "nep_chu_t_inox":           MEDIA_DIR / "nep_chu_t_inox",
    "nep_chu_u_inox":           MEDIA_DIR / "nep_chu_u_inox",
    "nep_chu_v_inox":           MEDIA_DIR / "nep_chu_v_inox",
    "nep_chong_tron_inox":      MEDIA_DIR / "nep_chong_tron_inox",
    "nep_len_chan_tuong_inox":  MEDIA_DIR / "nep_len_chan_tuong_inox",
    "hoc_am_tuong_inox":        MEDIA_DIR / "hoc_am_tuong_inox",
    "tu_bep_inox":              MEDIA_DIR / "tu_bep_inox",
    "tam_inox_mau":             MEDIA_DIR / "tam_inox_mau",
    "do_kinh_inox":             MEDIA_DIR / "do_kinh_inox",
    "gia_cong_cnc_inox":        MEDIA_DIR / "gia_cong_cnc_inox",
    "nep_inox":                 MEDIA_DIR / "nep_inox",
    "giao_hang":               MEDIA_DIR / "giao_hang",
}

# ==============================================
# PHÂN LOẠI ẢNH THEO NỘI DUNG (IMAGE TAGS)
# ==============================================
# Hệ thống nhận diện loại ảnh dựa trên TÊN FILE.
# Quy tắc đặt tên: nếu tên file chứa một trong các từ khoá dưới đây
# → ảnh đó được phân vào loại tương ứng.
# Ảnh không chứa bất kỳ từ khoá nào → mặc định là ảnh sản phẩm hoàn thiện (studio/catalogue).
#
# Các loại ảnh hiện tại:
#
#   [KHÔNG TAG]   — Ảnh sản phẩm hoàn thiện (chụp đẹp, background trắng/studio)
#                   Phù hợp: Product, Lifestyle, Sales, Pain & Relief
#
#   tai_xuong     — Không gian xưởng, máy móc, thợ làm việc, kho nguyên liệu
#                   Phù hợp: Authority, Behind the Scenes
#
#   gia_cong      — Quá trình gia công đang diễn ra (cắt, chấn, hàn, phay...)
#                   Phù hợp: Authority, Educational
#
#   thi_cong      — Sản phẩm đang được lắp đặt tại công trình
#                   Phù hợp: Case Study, Educational
#
#   ung_dung      — Sản phẩm đã hoàn thiện trong bối cảnh thực tế (thấy cả không gian/công trình)
#                   Phù hợp: Case Study, Product, Pain & Relief
#
#   van_chuyen    — Đóng gói, xe tải, giao hàng, kho thành phẩm
#                   Phù hợp: Social Proof
#
# Cách đặt tên file: dùng "_" phân cách, đặt tag ở đầu tên.
# Ví dụ: "tai_xuong_01.jpg", "gia_cong_phay_ranh.jpg", "ung_dung_phong_bep.jpg"
# Ảnh sản phẩm studio giữ nguyên tên random: "IMG_20240315_102233.jpg"
IMAGE_TAGS: list[str] = ["tai_xuong", "gia_cong", "thi_cong", "ung_dung", "van_chuyen"]

# ==============================================
# FEATURE FLAGS — BẬT / TẮT CÁC TÍNH NĂNG AI
# ==============================================
# Tất cả tính năng dùng LLM được kiểm soát tập trung tại đây.
# Đổi True ↔ False để bật/tắt — không cần sửa code ở chỗ khác.

# LLM_CHOOSE_IMAGE_TYPE
# ─────────────────────
# True  → LLM đọc nội dung bài vừa viết, tự quyết định nên dùng bao nhiêu ảnh
#          của từng loại (hoàn thiện / tai_xuong / gia_cong / thi_cong / ung_dung / van_chuyen).
#          Chuẩn xác nhất vì LLM hiểu ngữ cảnh thực của bài.
#          Chi phí: thêm ~1 lần gọi LLM nhỏ (gọi structured output, rất nhanh).
#
# False → Chọn ngẫu nhiên (random) toàn bộ pool ảnh của sản phẩm, bất kể loại.
#          Nhanh hơn, không tốn thêm token.
#          Phù hợp khi kho ảnh chưa được đặt tên theo tag hệ thống.
LLM_CHOOSE_IMAGE_TYPE: bool = True


def validate_settings() -> list[str]:
    """Kiểm tra xem các API keys quan trọng có bị thiếu không."""
    missing = []

    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY (cần thiết khi dùng LLM_PROVIDER=gemini)")
    elif LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY (cần thiết khi dùng LLM_PROVIDER=openai)")
    elif LLM_PROVIDER == "claude" and not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY (cần thiết khi dùng LLM_PROVIDER=claude)")

    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if not FACEBOOK_PAGES:
        missing.append("FACEBOOK_PAGE_ID & FACEBOOK_ACCESS_TOKEN (hoặc FACEBOOK_PAGE_1_...)")

    return missing
