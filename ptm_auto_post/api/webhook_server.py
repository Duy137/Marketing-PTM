"""
webhook_server.py — FastAPI server nhận webhook từ Telegram.

Chạy ở background thread của main.py. Nhận request và đẩy vào pending_store
để các agent xử lý lập tức.

Routing logic:
- Callback có prefix "ts" → dispatch_topic_selection (giai đoạn chọn chủ đề)
- Callback thông thường   → dispatch_callback theo message_id (approver, page_selector...)
- Message thường/ảnh      → dispatch_message (thu thập ảnh)
"""

from fastapi import FastAPI, Request
from api.pending_store import dispatch_callback, dispatch_message, dispatch_topic_selection
import requests
from config.settings import TELEGRAM_BOT_TOKEN

app = FastAPI()

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint nhận update từ Telegram.
    Trả về {"ok": True} ngay lập tức để Telegram không retry.
    """
    data = await request.json()

    # 1. Xử lý Callback Query (bấm nút inline)
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback.get("data", "")
        message_id = callback.get("message", {}).get("message_id")

        # --- Route: Topic Selection callbacks (prefix "ts") ---
        if callback_data.startswith("ts"):
            dispatched = dispatch_topic_selection(callback)
            # Nếu không có topic selector đang chờ, tắt spinner ngay
            if not dispatched:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback["id"]},
                    timeout=5,
                )

        # --- Route: Standard callbacks (approver, page_selector...) ---
        elif message_id:
            dispatched = dispatch_callback(message_id, callback)
            if not dispatched:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback["id"]},
                    timeout=5,
                )

    # 2. Xử lý Message (text hoặc ảnh)
    elif "message" in data:
        message = data["message"]
        dispatch_message(message)

    return {"ok": True}
