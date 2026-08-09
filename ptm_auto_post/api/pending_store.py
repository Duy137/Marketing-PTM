"""
pending_store.py — Cầu nối giữa Telegram Webhook và các agent LangGraph.

Cách hoạt động:
  1. Agent gửi tin nhắn Telegram → đăng ký message_id vào store
  2. User bấm nút → Webhook nhận callback → dispatch vào Queue đúng message_id
  3. Agent đang chờ (queue.get) → nhận kết quả ngay lập tức

Không còn polling getUpdates — phản hồi < 0.5s thay vì 0-30s.
"""

import threading
from queue import Queue
from typing import Optional


# ==============================================
# CALLBACK STORE — cho button presses (inline keyboard)
# ==============================================

_callback_store: dict[int, Queue] = {}
_callback_lock = threading.Lock()


def register_callback(message_id: int) -> Queue:
    """
    Đăng ký chờ callback cho message_id.
    Trả về Queue — agent gọi queue.get(timeout=...) để chờ.
    """
    q: Queue = Queue()
    with _callback_lock:
        _callback_store[message_id] = q
    return q


def dispatch_callback(message_id: int, data: dict) -> bool:
    """
    Webhook gọi hàm này khi nhận callback cho message_id.
    Đặt data vào Queue → agent đang chờ sẽ nhận ngay.
    """
    with _callback_lock:
        q = _callback_store.get(message_id)
    if q is not None:
        q.put(data)
        return True
    return False


def unregister_callback(message_id: int) -> None:
    """Dọn dẹp sau khi agent không còn chờ callback nữa."""
    with _callback_lock:
        _callback_store.pop(message_id, None)


# ==============================================
# MESSAGE QUEUE — cho ảnh và text commands (/xong)
# ==============================================

_message_queue: Optional[Queue] = None
_message_lock = threading.Lock()


def activate_message_queue() -> Queue:
    """
    Bật chế độ nhận messages từ user (dùng khi thu thập ảnh).
    Trả về Queue — agent gọi queue.get(timeout=...) để chờ.
    """
    global _message_queue
    q: Queue = Queue()
    with _message_lock:
        _message_queue = q
    return q


def dispatch_message(message: dict) -> bool:
    """
    Webhook gọi hàm này khi nhận tin nhắn thường (ảnh, /xong).
    Chỉ có hiệu lực khi message queue đang được activate.
    """
    with _message_lock:
        q = _message_queue
    if q is not None:
        q.put(message)
        return True
    return False


def deactivate_message_queue() -> None:
    """Tắt chế độ nhận messages sau khi thu thập xong ảnh."""
    global _message_queue
    with _message_lock:
        _message_queue = None


# ==============================================
# TOPIC SELECTION QUEUE
# ==============================================

_topic_selection_queue = None
_topic_selection_lock = __import__('threading').Lock()


def register_topic_selection_queue():
    global _topic_selection_queue
    from queue import Queue
    q = Queue()
    with _topic_selection_lock:
        _topic_selection_queue = q
    return q


def dispatch_topic_selection(data):
    with _topic_selection_lock:
        q = _topic_selection_queue
    if q is not None:
        q.put(data)
        return True
    return False


def unregister_topic_selection_queue():
    global _topic_selection_queue
    with _topic_selection_lock:
        _topic_selection_queue = None

