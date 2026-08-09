# Kiến trúc Kỹ thuật & Bối cảnh Hệ thống AutoClip

> **Vai trò Tài liệu:** Dành cho AI Assistant & Developer. 
> Đây là "bản đồ tư duy" (mental map) giải thích cách AutoClip hoạt động dưới nền tảng. Các AI Assistant làm nhiệm vụ tạo nội dung bắt buộc phải hiểu rõ giới hạn và quy trình này để sinh ra output phù hợp nhất.

---

## 1. Tổng quan Hệ thống (System Overview)

AutoClip là một công cụ AI Local tạo video ngắn dọc (9:16) tự động từ văn bản. Hệ thống được chia làm 3 phân hệ chính giao tiếp với nhau qua API:

1. **Backend (Python / FastAPI / LangGraph):** Não bộ của hệ thống. Chịu trách nhiệm tương tác với LLMs (để chia scene, sinh kịch bản), gọi API tìm kiếm media (Pexels), tạo âm thanh (TTS từ OpenAI, Edge-TTS, ElevenLabs, Gemini, Vbee), và quản lý tiến trình render qua pipeline dạng DAG.
2. **Frontend (React / Vite / Tailwind):** Giao diện Editor dạng Studio. Cho phép người dùng chỉnh sửa phân cảnh, thay đổi media, màu sắc và xem trước video (preview) ở thời gian thực.
3. **Render Engine (Remotion / React):** Động cơ kết xuất. Biến các thông số dữ liệu (VideoProps JSON) thành các frame hình ảnh và ghép lại thành file MP4 hoàn chỉnh chạy dưới background.

---

## 2. Luồng Dữ liệu Cốt lõi (Pipeline Xử lý Nội dung)

```text
Input Text → LLM Director Agent (chia scenes) → Content Parser → TTS Engine (đọc giọng) → Media Searcher (chọn video/ảnh) → Remotion Renderer → MP4
```

Toàn bộ pipeline này là **tự động hoàn toàn**. Trái tim của việc giao tiếp là file cấu hình dữ liệu dạng JSON (`videoProps`). Do đó, đầu vào từ người dùng hoặc từ AI Content Creator chỉ cần văn bản thô.

---

## 3. Ràng Buộc Kỹ Thuật Khi Tạo Nội Dung (QUAN TRỌNG)

Khi AI đóng vai trò là "Content Creator" để tạo kịch bản, **tuyệt đối tuân thủ** các ràng buộc kỹ thuật sau để pipeline của AutoClip không bị lỗi:

### Độ dài văn bản
| Thông số | Giá trị |
|----------|---------|
| Tối thiểu | 30 từ |
| Tối đa | 500 từ |
| **Khuyến nghị cho 1 phút video** | **~1,160 ký tự** (bao gồm dấu cách) |
| Tốc độ đọc (speed) | 1.4x |
| Thời lượng mục tiêu | 45-60 giây |

> ⚠️ **Lưu ý:** Script quá ngắn (<30 từ) sẽ bị pipeline reject. Giới hạn **1,160 ký tự** là mức khuyến nghị chung để tối ưu thời lượng TikTok. Tuy nhiên, **KHI CẦN THIẾT**, nếu bài báo có nhiều dữ liệu quan trọng (số liệu cụ thể, tên sự kiện, mốc thời gian) cần được đưa vào để làm nội dung đủ ý, rõ ràng và thuyết phục hơn, AI **ĐƯỢC PHÉP VƯỢT QUÁ** giới hạn 1,160 ký tự này (miễn là không vượt quá 500 từ). Không nên đánh đổi tính thuyết phục của kịch bản chỉ vì giới hạn ký tự.

### Ngôn ngữ & Giọng đọc (TTS)
- **Tiếng Việt** là ngôn ngữ chính.
- **Code-switching Việt-Anh** được hỗ trợ hoàn hảo (ví dụ: Bitcoin, blockchain, AI, NVIDIA, smart contract, stablecoin...). TTS engine sẽ tự nhận diện và phát âm chuẩn xác. Do đó, KHÔNG dịch các thuật ngữ chuyên ngành sang tiếng Việt ngô nghê.

### Những việc AutoClip "Tự Động Bao Thầu" (AI KHÔNG CẦN LÀM)
- ✅ Phân tích Text và tự chia thành 5-8 scenes.
- ✅ Tự động tìm hình ảnh/video stock (Pexels) dựa trên từ khóa của từng scene.
- ✅ Tự tạo subtitle word-by-word và highlight từ khóa.
- ✅ Tự chọn scene type phù hợp (title_card, media_showcase, info_card...).
- ✅ Tự thêm nhạc nền, hiệu ứng âm thanh (SFX) và transition.

**Do đó, khi viết script, AI cần nhớ:**
- ❌ **Không cần** đánh số scene.
- ❌ **Không cần** ghi chú đạo diễn như `[Hình ảnh: ...]`, `[Chuyển cảnh]`, `[Nhạc nền dồn dập]`.
- ❌ **Không cần** format đặc biệt (Markdown in đậm, in nghiêng...). **Chỉ cần trả về Text thuần (Plain Text).**
- ❌ **Không cần** thêm hashtag. (Hashtag là việc của quy trình đăng bài, không thuộc phạm vi kịch bản video).

### Quy tắc ngắt nhịp cho Parser
- Vì Parser sẽ phân tách scene dựa trên câu văn, hãy dùng dấu câu (chấm, phẩy, gạch ngang `—`) một cách hợp lý và rõ ràng. Một câu quá dài sẽ khiến 1 scene bị kéo dài lê thê và subtitle hiển thị xấu.
