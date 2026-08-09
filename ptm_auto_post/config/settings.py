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
# CÀI ĐẶT LLM
# ==============================================
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

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
}


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
