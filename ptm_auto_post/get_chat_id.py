"""
get_chat_id.py — Script lấy Telegram Chat ID.

Cách dùng:
1. Mở Telegram, tìm bot của bạn và nhắn bất kỳ tin nhắn gì (VD: "hello")
2. Chạy script này: python get_chat_id.py
3. Script sẽ in ra Chat ID của bạn
"""

import requests

# Dán Bot Token của bạn vào đây
BOT_TOKEN = "8727295207:AAGkXaJVVgKyOEBUDVDxJNg6E1xxSVFV9u4"

def get_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url, timeout=10)
    data = response.json()

    if not data.get("ok"):
        print(f"Lỗi: {data}")
        return

    updates = data.get("result", [])
    if not updates:
        print("Chưa có tin nhắn nào!")
        print("→ Hãy mở Telegram, tìm bot của bạn và nhắn 1 tin nhắn bất kỳ, rồi chạy lại script này.")
        return

    # Lấy tin nhắn mới nhất
    last = updates[-1]
    message = last.get("message", {})
    chat = message.get("chat", {})

    chat_id = chat.get("id")
    chat_name = chat.get("first_name") or chat.get("title") or "N/A"

    print(f"\n✅ Chat ID của bạn là: {chat_id}")
    print(f"   Tên: {chat_name}")
    print(f"\n→ Hãy điền vào .env:")
    print(f"   TELEGRAM_CHAT_ID={chat_id}")

if __name__ == "__main__":
    get_chat_id()
