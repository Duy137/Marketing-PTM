"""
post_log_service.py — Dịch vụ ghi và đọc lịch sử bài đăng.

Lưu trữ metadata nội bộ (mode, sản phẩm, loại ảnh) kèm facebook_post_id
để sau này có thể JOIN với Facebook Insights API.

File log: logs/post_log.csv
Schema:
    facebook_post_id | published_at | topic_id | topic_title | san_pham | mode | image_types | page_ids
"""

import csv
from datetime import datetime, timezone
from pathlib import Path

from config.settings import LOGS_DIR

POST_LOG_FILE = Path(LOGS_DIR) / "post_log.csv"

_FIELDNAMES = [
    "facebook_post_id",
    "published_at",
    "topic_id",
    "topic_title",
    "san_pham",
    "mode",
    "image_types",   # pipe-separated: "tai_xuong|thuong"
    "page_ids",      # pipe-separated: "page_id_1|page_id_2"
]

# Tags nhận biết từ tên file ảnh (từ image_picker.py)
_KNOWN_TAGS = {"tai_xuong", "gia_cong", "thi_cong", "ung_dung", "van_chuyen"}


def _extract_image_types(image_paths: list[str]) -> str:
    """Trích xuất loại ảnh từ tên file. Ảnh không có tag → 'thuong'."""
    tags = set()
    for path in image_paths:
        stem = Path(path).stem.lower()
        found = False
        for tag in _KNOWN_TAGS:
            if tag in stem:
                tags.add(tag)
                found = True
                break
        if not found:
            tags.add("thuong")
    return "|".join(sorted(tags)) if tags else "thuong"


def _ensure_file() -> None:
    """Tạo file với header nếu chưa tồn tại."""
    POST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not POST_LOG_FILE.exists():
        with open(POST_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=_FIELDNAMES).writeheader()


def log_published_post(state: dict) -> None:
    """
    Ghi 1 dòng vào post_log.csv sau khi đăng bài thành công.
    Gọi từ plugin on_post_published — không gọi trực tiếp từ core.
    """
    _ensure_file()

    row = {
        "facebook_post_id": state.get("facebook_post_id", ""),
        "published_at":     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "topic_id":         state.get("topic_id", ""),
        "topic_title":      state.get("topic_title", ""),
        "san_pham":         state.get("san_pham", ""),
        "mode":             state.get("mode", ""),
        "image_types":      _extract_image_types(state.get("image_paths", [])),
        "page_ids":         "|".join(state.get("selected_page_ids", [])),
    }

    with open(POST_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writerow(row)

    print(f"[post_log] ✅ Ghi log: {row['facebook_post_id']} | {row['san_pham']} | {row['mode']}")


def read_post_log(days: int = 30) -> list[dict]:
    """
    Đọc lịch sử bài đăng trong N ngày gần nhất.
    Trả về list of dict, mỗi dict là 1 bài đã đăng.
    """
    _ensure_file()
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = []
    with open(POST_LOG_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                dt = datetime.strptime(row["published_at"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    rows.append(row)
            except (ValueError, KeyError):
                continue
    return rows
