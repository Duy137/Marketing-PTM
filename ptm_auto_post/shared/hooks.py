"""
hooks.py — Engine quản lý Plugin Hooks.

Đây là lớp keo duy nhất giữa core pipeline và các plugin tùy chọn.
File này KHÔNG BAO GIỜ cần sửa sau khi tạo.

Cách dùng trong core (main.py):
    from shared.hooks import fire
    fire("on_post_published", dict(final_state))

Cách dùng trong plugin:
    from shared.hooks import on
    on("on_post_published", my_handler_function)

Danh sách hooks đã định nghĩa:
    "on_session_start"    → gọi khi Main Menu được hiển thị
    "on_post_published"   → gọi sau khi đăng bài Facebook thành công
    "on_report_requested" → gọi khi user bấm nút Báo cáo trong Telegram
"""

from __future__ import annotations

_registry: dict[str, list] = {}


def on(event: str, handler) -> None:
    """
    Plugin gọi hàm này để đăng ký lắng nghe 1 event.
    Có thể đăng ký nhiều handler cho cùng 1 event.
    """
    # setdefault(event, []): Nếu sự kiện chưa có trong từ điển thì tạo danh sách rỗng mới [],
    # sau đó .append(handler): Nhét hàm xử lý này vào danh sách đó.
    _registry.setdefault(event, []).append(handler)


def fire(event: str, payload: dict | None = None) -> dict:
    """
    Kích hoạt một sự kiện (event) và gửi dữ liệu cho các plugin xử lý.

    - ĐẦU VÀO (Input):
        + event: Tên sự kiện xảy ra (ví dụ: 'on_post_published', 'on_session_start').
        + payload: Túi hồ sơ dữ liệu ban đầu gửi kèm (ví dụ: thông tin bài viết vừa đăng
                   gồm topic_id, san_pham, facebook_post_id...). Nếu không có thì để None.

    - CÁCH XỬ LÝ:
        + Lần lượt chuyển túi hồ sơ này qua từng plugin đã đăng ký sự kiện đó.
        + Plugin có thể chỉ đọc dữ liệu (để ghi log, gửi tin nhắn), HOẶC có thể trả về
          dữ liệu mới để bổ sung thêm vào túi hồ sơ này.

    - ĐẦU RA (Output):
        + Trả về chính túi hồ sơ đó sau khi đã được các plugin bổ sung thêm dữ liệu (nếu có).
          Khác với đầu vào ở chỗ: nó có thể có thêm các trường thông tin mới do plugin đính kèm.
    """
    payload = dict(payload) if payload else {}
    handlers = _registry.get(event, [])

    if handlers:
        print(f"[hooks] Event '{event}' → {len(handlers)} handler(s)")

    for handler in handlers:
        try:
            result = handler(payload)
            if isinstance(result, dict):
                payload.update(result)
        except Exception as exc:
            print(f"[hooks] ⚠️  Handler '{handler.__name__}' lỗi khi xử lý '{event}': {exc}")

    return payload
