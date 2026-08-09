# QUY TẮC CONTENT VIDEO AUTOCLIP CHO PTM
> **Mục đích:** File này là tài liệu tham khảo (context) bắt buộc cho AI và đội ngũ Content khi lên kịch bản video cho PTM. Nó giải quyết trực tiếp bài toán "Thiếu hụt hình ảnh/video thực tế tại xưởng" bằng cách tối ưu hóa kịch bản cho hệ thống AutoClip (AI tự động ghép stock footage).

---

## 1. THỰC TRẠNG & CHIẾN LƯỢC CỐT LÕI

- **Thực trạng:** PTM là xưởng sản xuất quy mô lớn (1.500m2) nhưng vốn tài nguyên truyền thông (hình ảnh, video thực tế) rất hạn chế.
- **Chiến lược Video:** Dùng hệ thống **AutoClip** làm công cụ sản xuất video chủ lực. 
- **Bí quyết bẻ lái (Pivot):** Thay vì cố tả cảnh xưởng sản xuất (thứ mà AutoClip khó tìm được stock chính xác), kịch bản sẽ tập trung vào **"Xu hướng thiết kế"**, **"Nỗi đau thi công"** và **"Vẻ đẹp công trình"**. AutoClip sẽ cực kỳ dễ tìm các đoạn video stock (từ Pexels/Pixabay) về nội thất sang trọng, biệt thự, hoặc thợ thi công chung chung để ghép vào. Cuối video mới "chốt sale" bằng năng lực xưởng PTM.

---

## 2. QUY TẮC VIẾT SCRIPT AUTOCLIP CHO PTM

Bởi vì video được tạo ra bằng AI dựa trên Text, kịch bản chữ cần tuân thủ tuyệt đối các quy tắc kỹ thuật sau:

### Về Kỹ thuật & Format
- **Chỉ dùng Text thuần:** Tuyệt đối không dùng emoji, không gạch đầu dòng, không ghi chú kiểu `[Chuyển cảnh]`, `[Hiển thị ảnh xưởng]`. 
- **Từ khóa thị giác (Visual Keywords):** Trong kịch bản phải chủ động dùng các từ tượng hình chung chung để hệ thống AutoClip dễ bốc đúng video stock. 
  - *Nên dùng:* "Biệt thự sang trọng", "phòng tắm hiện đại", "thợ mộc đang làm việc", "tia lửa cắt kim loại".
  - *Tránh dùng:* "Máy chấn gập màu xanh của PTM", "logo PTM ngoài cổng" (vì AI không có stock này).
- **Độ dài tối ưu:** Khoảng **900 - 1.160 ký tự** (bao gồm dấu cách) để tạo ra video dài 45 - 60 giây.
- **Ngắt nhịp tự nhiên:** Sử dụng dấu gạch ngang `—` để công cụ Text-to-Speech (TTS) ngắt nghỉ đúng chỗ.
- **Câu ngắn:** Mỗi câu không quá 25 - 30 từ, tránh câu ghép lồng ngoằng.

---

## 3. CẤU TRÚC KỊCH BẢN CHUẨN (5 PHẦN)

Mọi kịch bản video của PTM nên đi theo luồng tâm lý sau để dẫn dắt từ "cảm hứng" đến "chốt sale B2B":

1. **HOOK (1-2 câu):** Mở đầu bằng một xu hướng nội thất cực đẹp, hoặc đánh thẳng vào nỗi đau sai lầm trong thi công.
   - *Ví dụ:* "Chi hàng trăm triệu làm nội thất, nhưng lại bỏ qua chi tiết này — nhà bạn sẽ kém sang đi một nửa!"
2. **CONTEXT - Bối cảnh (2-3 câu):** Giải thích vấn đề đang xảy ra tại các công trình (dùng nẹp nhựa bị bong, cắt gạch cắt mòi bị mẻ, rãnh xẻ gỗ bị kích...).
3. **DETAIL - Giải pháp (3-4 câu):** Đưa sản phẩm nẹp inox mạ PVD / hộc âm tường nguyên khối vào như một giải pháp cứu cánh và xu hướng tất yếu. Tập trung vào vật liệu 304, công nghệ PVD, sự sắc nét.
4. **IMPACT - Năng lực PTM (2-3 câu):** Nhắc đến việc để có nẹp chuẩn kích thước lỡ cỡ hoặc giá tận gốc, cần một xưởng lớn. Giới thiệu khéo léo PTM (Quy mô 1500m2, gia công CNC mọi bản vẽ).
5. **CTA - Kêu gọi (1 câu):** Kêu gọi anh em thầu thợ, thiết kế bình luận hoặc liên hệ.

---

## 4. CÁC NHÓM CHỦ ĐỀ ƯU TIÊN (CONTENT THEMES)

Vì hạn chế hình ảnh thực tế, hãy ưu tiên chọn các chủ đề thuộc 2 nhóm sau (dựa trên *Danh sách chủ đề đăng fanpage.md*):

- **Nhóm 1 - Educational (Giáo dục thị trường & Cảnh báo):**
  - "Sai lầm khi chọn kích thước nẹp U"
  - "Phân biệt inox gương và inox xước"
  - "Vì sao nẹp rẻ tiền nhanh ố vàng?"
- **Nhóm 2 - Product Inspiration (Ứng dụng sản phẩm & Truyền cảm hứng):**
  - "3 vị trí trong nhà cứ ốp nẹp inox là tự động đắt tiền"
  - "Ứng dụng hộc âm tường trong phòng tắm siêu sang"
  - "Xu hướng thay thế phào chỉ truyền thống bằng nẹp PVD"

---

## 5. PROMPT MẪU CHO NHỮNG LẦN SAU

Khi bạn muốn AI viết một kịch bản video mới cho PTM, hãy copy dòng lệnh này:

> *"Dựa vào định hướng trong file @[Quy tắc Video AutoClip PTM.md], hãy viết cho tôi một kịch bản video AutoClip về chủ đề: [Tên chủ đề của bạn]. Nhớ tuân thủ giới hạn ký tự và tập trung vào cách kể chuyện để AI dễ bốc video stock nội thất/cơ khí."*
