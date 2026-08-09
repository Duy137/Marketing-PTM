# PTM Auto Post — Hệ Thống Tự Động Đăng Bài Fanpage

Hệ thống tự động tạo và đăng bài viết cho các Fanpage PTM mỗi ngày.
Sử dụng **LangGraph + Telegram Bot + Facebook Graph API + Cloudflare Tunnel**.
Kiến trúc mô hình **Pragmatic MVC (Services - Views - Agents)**.

---

## Luồng hoạt động

```
Khởi động ➔ [Giai đoạn 1: Chọn chủ đề qua Telegram] ➔ [Giai đoạn 2: LangGraph Pipeline]
               ├── Gợi ý / Xem danh sách topic         ├── AI viết bài (LLM)
               ├── Toggle trạng thái (⬜/✅/⏸)           ├── Tự động lấy ảnh từ media/
               └── Chốt topic đăng                     ├── Gửi Telegram duyệt bài & ảnh
                                                       ├── Chọn Fanpage đăng
                                                       └── Đăng bài & Cập nhật CSV log
```

---

## Cấu trúc thư mục (MVC Architecture)

```
ptm_auto_post/
│
├── main.py                  # Điểm khởi chạy chính (Khởi động Webhook + Pre-pipeline + LangGraph)
│
├── services/                # ⚙️ TẦNG BACKEND & API (Services)
│   ├── telegram_service.py  # Quản lý toàn bộ cuộc gọi Telegram API (sendMessage, editMessage, sendMediaGroup...)
│   └── topic_service.py     # Thao tác đọc/ghi file data/topics.csv (Suggest, Toggle, Reset, Mark Posted)
│
├── views/                   # 🎨 TẦNG GIAO DIỆN TELEGRAM (Views)
│   └── telegram_views.py    # Format văn bản HTML & Inline Keyboards cho Telegram UI
│
├── agents/                  # 🎮 TẦNG ĐIỀU HƯỚNG WORKFLOW (Agents)
│   ├── topic_selector.py    # Controller Giai đoạn 1: Chọn chủ đề tương tác qua Telegram
│   ├── topic_picker.py      # LangGraph Node 1: Nạp dữ liệu chủ đề đã chọn vào State
│   ├── content_writer.py    # LangGraph Node 2: Gọi AI (LLM) viết bài theo Brand Voice
│   ├── image_picker.py      # LangGraph Node 3: Chọn ảnh ngẫu nhiên từ thư mục media/
│   ├── approver.py          # LangGraph Node 4: Gửi bài viết + album ảnh lên Telegram duyệt
│   ├── page_selector.py     # LangGraph Node: Chọn Fanpage Facebook muốn đăng
│   └── publisher.py         # LangGraph Node 5: Đăng bài lên Facebook & cập nhật trạng thái CSV
│
├── api/                     # 🌐 TẦNG WEBHOOK & QUEUE
│   ├── webhook_server.py    # FastAPI server nhận webhook từ Telegram (Fast response < 50ms)
│   └── pending_store.py     # Cầu nối Queue giữa Webhook và các Agent
│
├── config/
│   ├── settings.py          # Cấu hình chung (API keys, thông tin Fanpage, đường dẫn...)
│   └── .env                 # API keys (KHÔNG commit lên git)
│
├── data/
│   └── topics.csv           # Danh sách chủ đề + trạng thái + lịch sử đăng
│
├── prompts/
│   └── system_prompt.txt    # System prompt cho LLM (Brand Voice PTM)
│
├── media/                        # Thư mục ảnh minh họa theo loại sản phẩm
│   ├── nep_chu_t_inox/           # Nẹp chữ T inox
│   ├── nep_chu_u_inox/           # Nẹp chữ U inox
│   ├── nep_chu_v_inox/           # Nẹp chữ V inox (bo góc)
│   ├── nep_chong_tron_inox/      # Nẹp chống trơn cầu thang
│   ├── nep_len_chan_tuong_inox/  # Nẹp len chân tường inox
│   ├── hoc_am_tuong_inox/        # Hộc âm tường inox
│   ├── tu_bep_inox/              # Tủ bếp inox 304
│   ├── tam_inox_mau/             # Tấm inox màu mạ PVD
│   ├── do_kinh_inox/             # Đố kính inox
│   ├── gia_cong_cnc_inox/        # Gia công CNC, chấn gập, cắt laser
│   └── nep_inox/                 # Ảnh nẹp inox chung (fallback)
│
└── logs/
    └── post_history.log          # Log lịch sử đăng bài thành công
```

---

## Hướng dẫn cài đặt

```bash
# 1. Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# 2. Tạo file cấu hình môi trường
# Copy file config/.env.example thành config/.env
# Điền đầy đủ TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY, Facebook Page Access Tokens...

# 3. Chạy chương trình
python main.py
```

---

## Hướng dẫn sử dụng hàng ngày

### 🔹 Giai đoạn 1: Chọn chủ đề qua Telegram (Pre-pipeline, Không tốn AI)

Khi chạy `python main.py`, hệ thống sẽ kích hoạt Webhook và gửi tin nhắn đầu tiên lên Telegram:

#### 1. Màn hình Gợi ý chủ đề:
Bot hiển thị chủ đề được ưu tiên nhất kèm mode và thư mục ảnh:
* **`[✅ Viết bài này]`**: Chốt chủ đề này và bắt đầu để AI viết bài ngay.
* **`[🔄 Gợi ý khác]`**: Đổi sang chủ đề gợi ý tiếp theo.
* **`[📋 Xem tất cả]`**: Mở màn hình danh sách quản lý tất cả chủ đề.

#### 2. Màn hình Danh sách chủ đề (Phân trang 10 bài/trang):
* **Hàng nút Toggle (`⬜1` / `✅2` / `⏸10`)**: Bấm trực tiếp vào icon để đổi trạng thái theo vòng 3 chiều:
  * `⬜ chua_dang` ➔ `✅ da_dang` ➔ `⏸ tam_hoan` ➔ `⬜ chua_dang`
  * *(Thao tác toggle diễn ra tức thì < 50ms, phản hồi cực mượt)*
* **Hàng nút Chọn viết (`✍️1` / `✍️2`...)**: Bấm chọn viết ngay bài tương ứng trong danh sách.
* **Nút `[🔄 Reset tất cả]`**: Reset toàn bộ bài `da_dang` về `chua_dang` (các bài `⏸ tam_hoan` được giữ nguyên miễn nhiễm).

---

### 🔹 Giai đoạn 2: Duyệt bài & Đăng Fanpage (AI Pipeline)

Sau khi chốt chủ đề, AI sẽ tạo nội dung bài viết và chọn ảnh minh họa gửi lên Telegram:

| Nút | Hành động | Kết quả |
|:---|:---|:---|
| ✅ **Duyệt đăng** | Chấp nhận bài | Chuyển sang bước chọn Fanpage để đăng bài ngay |
| 🔄 **Cùng chủ đề** | Muốn viết lại | AI giữ nguyên chủ đề, tạo bài mới và gửi lại preview |
| 🎲 **Chủ đề khác** | Muốn đổi chủ đề | Quay về Giai đoạn 1 chọn chủ đề mới |
| 🖼️ **Gửi ảnh** | Muốn tự tải ảnh lên | Bật chế độ nhận ảnh từ chat (gửi 1-4 ảnh ➔ gõ `/xong`) |
| ❌ **Bỏ qua** | Hủy bài hôm nay | Kết thúc chương trình, không đăng bài |

#### 3. Màn hình Chọn Fanpage Facebook:
Hiển thị danh sách các Fanpage đã cấu hình:
* Bấm vào từng trang `[✅ Fanpage A]` / `[⬜ Fanpage B]` để chọn hoặc bỏ chọn.
* Bấm **`[🚀 Đăng bài ngay]`** để tiến hành đăng đồng thời (multi-page) lên các Fanpage đã chọn.

---

## Quản lý ảnh sản phẩm (`media/`)

Thêm ảnh sản phẩm thực tế vào đúng thư mục trong `media/`:
* Hệ thống tự động chọn ngẫu nhiên các ảnh trong thư mục tương ứng với sản phẩm của bài viết.
* Nếu thư mục sản phẩm đó trống, hệ thống tự động sử dụng ảnh từ thư mục chung `media/nep_inox/` (Fallback).

---

## Chạy tự động hàng ngày (Tùy chọn)

Để chạy tự động mỗi sáng lúc 08:00, cấu hình **Task Scheduler** trên Windows:
* **Program:** `python`
* **Arguments:** `main.py`
* **Start in:** `D:\Developer\Marketing PTM\ptm_auto_post`
* **Trigger:** Daily at 08:00 AM

Bot sẽ khởi động ➔ gửi gợi ý chủ đề lên Telegram ➔ chờ bạn tương tác ➔ đăng bài lên Facebook.
