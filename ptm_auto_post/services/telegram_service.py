"""
telegram_service.py — Tầng giao tiếp HTTP với Telegram API.

Nơi duy nhất trong hệ thống gọi requests.post đến Telegram API.
Tất cả các agent và controller đều sử dụng service này.
"""

import io
import json
import time
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_message(text: str, keyboard: dict | None = None, parse_mode: str = "HTML") -> int:
    """
    Gửi tin nhắn văn bản mới lên Telegram.
    Trả về message_id của tin nhắn vừa gửi.
    """
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
    }
    if keyboard:
        payload["reply_markup"] = keyboard

    try:
        resp = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return resp.json().get("result", {}).get("message_id", 0)
    except Exception as e:
        print(f"[telegram_service] Lỗi send_message: {e}")
        return 0


def edit_message(message_id: int, text: str, keyboard: dict | None = None, parse_mode: str = "HTML") -> None:
    """Edit nội dung và bàn phím của một tin nhắn hiện có."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if keyboard is not None:
        payload["reply_markup"] = keyboard

    try:
        requests.post(f"{TELEGRAM_API}/editMessageText", json=payload, timeout=10)
    except Exception as e:
        print(f"[telegram_service] Lỗi edit_message #{message_id}: {e}")


def delete_message(message_id: int) -> None:
    """Xóa một tin nhắn khỏi chat."""
    try:
        requests.post(
            f"{TELEGRAM_API}/deleteMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id},
            timeout=5,
        )
    except Exception as e:
        print(f"[telegram_service] Lỗi delete_message #{message_id}: {e}")


def answer_callback(callback_id: str, text: str = "") -> None:
    """
    Phản hồi callback query ngay lập tức để tắt spinner (loading indicator)
    trên nút bấm Telegram của người dùng.
    """
    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=5,
        )
    except Exception as e:
        print(f"[telegram_service] Lỗi answer_callback: {e}")


def send_media_group_paths(image_paths: list[str]) -> None:
    """Gửi album ảnh từ danh sách đường dẫn file trên ổ đĩa."""
    if not image_paths:
        return

    for attempt in range(3):
        media = []
        files = {}
        opened_files = []

        try:
            for i, path_str in enumerate(image_paths[:4]):
                key = f"photo_{i}"
                f = open(path_str, "rb")
                opened_files.append(f)
                media.append({"type": "photo", "media": f"attach://{key}"})
                files[key] = (f"photo_{i}.jpg", f, "image/jpeg")

            requests.post(
                f"{TELEGRAM_API}/sendMediaGroup",
                data={"chat_id": TELEGRAM_CHAT_ID, "media": json.dumps(media)},
                files=files,
                timeout=120,
            )
            break
        except Exception as e:
            print(f"[telegram_service] Lỗi sendMediaGroup paths (lần {attempt+1}/3): {e}")
            time.sleep(3)
        finally:
            for f in opened_files:
                f.close()


def send_media_group_bytes(raw_bytes_list: list[bytes]) -> None:
    """Gửi album ảnh từ danh sách raw bytes (ảnh user upload)."""
    if not raw_bytes_list:
        return

    for attempt in range(3):
        media = []
        files = {}

        for i, raw in enumerate(raw_bytes_list[:4]):
            key = f"photo_{i}"
            media.append({"type": "photo", "media": f"attach://{key}"})
            files[key] = (f"photo_{i}.jpg", io.BytesIO(raw), "image/jpeg")

        try:
            requests.post(
                f"{TELEGRAM_API}/sendMediaGroup",
                data={"chat_id": TELEGRAM_CHAT_ID, "media": json.dumps(media)},
                files=files,
                timeout=120,
            )
            break
        except Exception as e:
            print(f"[telegram_service] Lỗi sendMediaGroup bytes (lần {attempt+1}/3): {e}")
            time.sleep(3)
