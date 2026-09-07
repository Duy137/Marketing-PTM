"""
topic_service.py — Tầng xử lý dữ liệu chủ đề (topics.csv).

Nơi duy nhất thao tác đọc/ghi file CSV dữ liệu chủ đề.
Dùng thư viện csv thuần để đảm bảo tốc độ đọc/ghi nhanh (< 5ms).
"""

import csv
import random
from datetime import datetime
from config.settings import TOPICS_CSV

STATUS_CYCLE = {
    "chua_dang": "da_dang",
    "da_dang":   "tam_hoan",
    "tam_hoan":  "chua_dang",
}


def read_topics_csv(mode: str | None = None) -> list[dict]:
    """Đọc toàn bộ topics.csv thành danh sách dictionary (có thể lọc theo mode)."""
    with open(TOPICS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if mode:
        m_lower = mode.strip().lower()
        rows = [r for r in rows if r.get("mode", "").strip().lower() == m_lower]
    return rows


def write_topics_csv(rows: list[dict]) -> None:
    """Ghi lại danh sách dictionary vào file topics.csv."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(TOPICS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_topic_by_id(topic_id: int) -> dict | None:
    """Lấy thông tin 1 topic theo ID."""
    rows = read_topics_csv()
    return next((r for r in rows if int(r["id"]) == topic_id), None)


def toggle_topic_status(topic_id: int) -> str:
    """
    Toggle trạng thái topic theo vòng 3 chiều: chua_dang → da_dang → tam_hoan → chua_dang.
    Trả về trạng thái mới.
    """
    rows = read_topics_csv()
    new_status = "chua_dang"
    for row in rows:
        if int(row["id"]) == topic_id:
            current = row["trang_thai"]
            new_status = STATUS_CYCLE.get(current, "chua_dang")
            row["trang_thai"] = new_status
            break
    write_topics_csv(rows)
    return new_status


def reset_all_topics() -> None:
    """
    Reset tất cả chủ đề chua_dang/da_dang về chua_dang.
    Giữ nguyên tam_hoan (miễn nhiễm với reset).
    """
    rows = read_topics_csv()
    for row in rows:
        if row["trang_thai"] in ("chua_dang", "da_dang"):
            row["trang_thai"] = "chua_dang"
    write_topics_csv(rows)


def suggest_topic(exclude_ids: list[int] | None = None, mode: str | None = None) -> dict | None:
    """
    Gợi ý 1 chủ đề theo logic ưu tiên (có thể lọc theo mode):
    1. chua_dang (bỏ qua exclude_ids và tam_hoan)
    2. da_dang lâu nhất (bỏ qua exclude_ids và tam_hoan)
    """
    exclude_ids = exclude_ids or []
    rows = read_topics_csv(mode=mode)

    chua_dang = [
        r for r in rows
        if r["trang_thai"] == "chua_dang" and int(r["id"]) not in exclude_ids
    ]
    if chua_dang:
        return random.choice(chua_dang)

    da_dang = [
        r for r in rows
        if r["trang_thai"] == "da_dang" and int(r["id"]) not in exclude_ids
    ]
    if da_dang:
        da_dang_sorted = sorted(
            da_dang,
            key=lambda r: r["lan_cuoi_dang"] or "0000-00-00"
        )
        return da_dang_sorted[0]

    return None


def mark_topic_as_posted(topic_id: int) -> None:
    """Đánh dấu chủ đề thành da_dang và cập nhật ngày đăng hôm nay."""
    rows = read_topics_csv()
    today = datetime.now().strftime("%Y-%m-%d")
    for row in rows:
        if int(row["id"]) == topic_id:
            row["trang_thai"] = "da_dang"
            row["lan_cuoi_dang"] = today
            break
    write_topics_csv(rows)
    print(f"[topic_service] Đã cập nhật trạng thái topic {topic_id} → da_dang ({today})")
