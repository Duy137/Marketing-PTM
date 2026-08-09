# Tài Liệu Nguyên Lý Hoạt Động: Hệ Thống Phân Tích Từ Khóa Google Ads — PTM

> **Đối tượng:** Nhà quản trị Marketing, Nhà phân tích chiến lược
> **Mục tiêu:** Hiểu đủ sâu để ra quyết định tối ưu và đánh giá nên nâng cấp gì
> **Nguyên tắc đọc:** Không cần biết lập trình. Chỉ cần hiểu logic. Đọc tóm gọn tự viết ở cuối

---

## PHẦN I — BỨC TRANH TỔNG QUÁT

### Hệ thống này giải quyết vấn đề gì?

Khi chạy Google Ads, bạn chi tiền cho 2 thứ rất khác nhau:

1. **Từ khóa bạn đặt mua** (Keywords) — bạn chủ động chọn, ví dụ: "nẹp inox", "gia công inox".
2. **Cụm từ người dùng thực sự gõ** (Search Terms) — Google tự khớp dựa trên từ khóa bạn đặt, có thể là "nẹp inox giá rẻ nhất hcm" hoặc... "nẹp nhựa giả inox".

Vấn đề nằm ở chỗ: **Google không phân biệt được mua hàng và tham khảo**. Một người gõ "nẹp inox là gì" và một người gõ "báo giá nẹp inox hcm" đều có thể kích hoạt cùng quảng cáo của bạn — nhưng chỉ người thứ hai có khả năng mua hàng.

Hệ thống phân tích này được xây dựng để **phân loại, phán xét và ưu tiên hoá** dữ liệu từ 2 nguồn trên, giúp bạn biết chính xác:
- Đang đốt tiền ở đâu?
- Tiền đang nằm ở những từ khóa nào có tiềm năng nhưng chưa được khai thác?
- Cần chặn (phủ định) những gì để ngăn ngân sách chảy vào rác?

---

## PHẦN II — HAI LOẠI BÁO CÁO VÀ SỰ KHÁC BIỆT CỐT LÕI

Đây là điểm mà nhiều người nhầm lẫn nhất. Hai loại báo cáo nhìn gần giống nhau nhưng trả lời **hai câu hỏi hoàn toàn khác nhau**.

### Báo Cáo 1: Từ Khóa Tìm Kiếm (Search Keywords Report)
**Câu hỏi nó trả lời:** *"Hiệu suất của những từ khóa TÔI đã đặt mua ra sao?"*

Đây là danh sách **từ khóa do chính bạn tạo ra** trong tài khoản Google Ads. Ví dụ: bạn đã chọn mua từ khóa `nẹp inox` — báo cáo này cho bạn biết trong tháng qua, từ khóa đó tốn bao nhiêu tiền, ra bao nhiêu đơn, có điểm chất lượng bao nhiêu.

**Đặc trưng nhận dạng:** Cột chính là "Từ khóa", có cột "Điểm Chất Lượng" (Quality Score — Google chấm điểm 1-10 cho từ khóa của bạn).

**Công cụ xử lý:** `analyze_keywords.py` → xuất file `_HieuSuat.xlsx`

---

### Báo Cáo 2: Cụm Từ Tìm Kiếm (Search Terms Report / SQOS)
**Câu hỏi nó trả lời:** *"Người dùng thực sự gõ GÌ trước khi click vào quảng cáo của tôi?"*

Đây là nhật ký thực tế của hành vi người dùng. Từ khóa bạn đặt chỉ là "lưới bẫy" — báo cáo này cho biết con nào đã bị bắt. Bạn đặt bẫy `nẹp inox` nhưng có thể đang bắt được cả người tìm `nẹp nhựa giả inox`.

**Đặc trưng nhận dạng:** Cột chính là "Cụm từ tìm kiếm", **không có** cột "Điểm Chất Lượng".

**Công cụ xử lý:** `analyze_sqos.py` → xuất file `_SQOS.xlsx`

---

> [!IMPORTANT]
> **Quy tắc vàng:** Hai báo cáo này bổ sung cho nhau, không thay thế nhau. Báo cáo Từ khóa cho biết "từ nào của bạn hoạt động tốt". Báo cáo Cụm từ cho biết "ai đang tiêu tiền của bạn và họ thực sự muốn gì".

---

## PHẦN III — NGUYÊN LÝ HOẠT ĐỘNG CHI TIẾT

### 3.1 — Phân Tích Từ Khóa: Ma Trận 6 Nhóm Hiệu Suất

Khi phân tích báo cáo Từ khóa, hệ thống **không phán xét ý định** (vì bạn đã chủ động chọn những từ đó). Thay vào đó, nó chỉ nhìn vào **bằng chứng hiệu suất thực tế** theo thứ tự ưu tiên:

#### Sơ đồ phán xét (theo thứ tự):

```
Từ khóa X
    │
    ├─ Có chuyển đổi (đơn hàng)?
    │       ├─ CPA ≤ 100,000đ  → [Nhóm 1] TOP PERFORMERS ✅ Tăng bid
    │       └─ CPA > 100,000đ  → [Nhóm 2] COSTLY CONVERTING 🟡 Cân nhắc tối ưu
    │
    ├─ Không có đơn + Tốn ≥ 50,000đ → [Nhóm 3] BLEEDERS 🔴 Giảm bid/Tạm dừng
    │
    ├─ Điểm Chất Lượng 1-4 (Google phạt thấp) → [Nhóm 4] LOW QS 🔴 Sửa ad/landing page
    │
    ├─ Hiển thị ≥ 100 lần + CTR < 3% → [Nhóm 5] LOW CTR 🟡 Viết lại ad copy
    │
    ├─ Điểm CL ≥ 7 + CTR ≥ 10% + Hiển thị < 100 → [Nhóm 6] SLEEPING GIANTS 💎 Tăng bid mạnh
    │
    └─ Còn lại → [Nhóm 7] OTHER — Tiếp tục theo dõi
```

**Tại sao thứ tự quan trọng?**
Một từ khóa có thể đáp ứng nhiều tiêu chí cùng lúc. Ví dụ: tốn 80,000đ nhưng ra 1 đơn với CPA = 80,000đ — nó **không bị** xếp vào Bleeder dù tốn tiền, vì tiêu chí "có chuyển đổi" được kiểm tra *trước*. Đây là thiết kế có chủ ý để tránh xóa nhầm từ khóa đang ra đơn.

**Điểm Chất Lượng (QS) — tại sao quan trọng?**
Google dùng QS để tính giá thầu thực tế. QS = 5 là trung bình. QS = 3 nghĩa là Google đang **phạt** bạn: bạn phải trả nhiều tiền hơn đối thủ để xuất hiện ở cùng vị trí. Nhóm Low QS cần được ưu tiên xử lý vì nó ảnh hưởng đến toàn bộ cấu trúc chi phí.

---

### 3.2 — Phân Tích Cụm Từ Tìm Kiếm: Bộ Lọc 3 Tầng

Đây là phần phức tạp hơn và cũng quan trọng hơn. Hệ thống cần giải một bài toán khó: **Từ hàng trăm/nghìn cụm từ người dùng gõ, cái nào là vàng, cái nào là rác?**

#### Tầng 1 — Phân Loại Ý Định (Intent Classification)

Mỗi cụm từ được đọc và đối chiếu với 3 danh sách từ khóa trong file cấu hình (`keyword_rules.json`):

| Danh sách | Ví dụ từ | Ý nghĩa |
|-----------|----------|---------|
| **Từ rác** (waste_words) | nhựa, nẹp gỗ, thanh lý, học, tự làm | Người dùng không phải khách hàng B2B của PTM |
| **Ý định mua** (high_intent_words) | xưởng, gia công, báo giá, hcm, mạ pvd | Người dùng có nhu cầu thực sự |
| **Ý định tìm hiểu** (informational_words) | là gì, kích thước, hướng dẫn, bao nhiêu | Nghiên cứu thị trường, chưa sẵn sàng mua |

**Thứ tự ưu tiên xét:** Từ rác → Ý định mua → Ý định tìm hiểu → Trung tính

Điều này có nghĩa là: nếu một cụm từ vừa chứa "học" (rác) vừa chứa "báo giá" (mua), nó sẽ bị xếp vào **rác** trước — bởi vì cụm từ kiểu "học cách báo giá gia công" có khả năng thấp ra đơn hàng.

#### Tầng 2 — Phân Nhóm SQOS (Dựa Trên Chi Phí + Intent)

Sau khi có Intent, hệ thống kết hợp với dữ liệu thực tế (tốn bao nhiêu, ra bao nhiêu đơn):

```
Cụm từ X
    │
    ├─ Đã ra đơn? → [WINNERS] ✅ Đây là từ khóa vàng — cân nhắc thêm vào danh sách từ khóa chính
    │
    ├─ Tốn > 50,000đ, không ra đơn:
    │       ├─ Intent = Mua → [INVESTIGATE] 🟡 Đắt nhưng đúng đối tượng — theo dõi thêm
    │       └─ Intent khác → [BLEEDERS] 🔴 Đốt tiền vô ích — phủ định ngay
    │
    ├─ Tốn ≤ 50,000đ + Intent = Mua → [POTENTIAL] 💎 Tiềm năng — để thêm data
    │
    ├─ Intent = Rác → [NOISE] ⛔ Phủ định ngay dù chưa tốn nhiều
    │
    └─ Còn lại → [OTHER] — Tiếp tục quan sát
```

**Thiết kế then chốt — Tại sao có nhóm INVESTIGATE?**

Nếu hệ thống chỉ nhìn vào chi phí, nó sẽ đề nghị xóa cả những cụm từ như "báo giá nẹp inox hcm" chỉ vì tháng này chưa ra đơn nhưng đã tốn 80,000đ. Đây là sai lầm nguy hiểm — chu kỳ bán hàng B2B có thể dài 2-4 tuần. Nhóm INVESTIGATE được tạo ra chính xác để bảo vệ những từ khóa đúng đối tượng nhưng cần thêm thời gian.

#### Tầng 3 — Phân Tích N-gram (Gốc Từ Gây Tốn Tiền)

Đây là tính năng phân tích sâu nhất. Hệ thống "băm nhỏ" tất cả cụm từ tìm kiếm và đếm xem **mỗi chữ/cụm 2 chữ đang tiêu hao bao nhiêu ngân sách** khi cộng dồn trên tất cả truy vấn.

**Ví dụ minh họa:**
Giả sử có 50 truy vấn khác nhau đều chứa chữ "nhựa" (nẹp nhựa, nhựa giả inox, nẹp ốp nhựa, v.v.), tổng cộng đã tốn 500,000đ cho nhóm này. Phân tích N-gram sẽ "nổi bong bóng" chữ "nhựa" lên đầu danh sách, cho bạn thấy rằng **một gốc từ duy nhất này đang đốt 500k/tháng** — dù không một truy vấn đơn lẻ nào trong đó tốn đủ để bị flag là Bleeder.

Đây là lý do N-gram quan trọng hơn việc chỉ xem từng dòng riêng lẻ.

---

## PHẦN IV — HỆ THỐNG LỌC TỐT GÌ VÀ BỎ SÓT GÌ

### ✅ Hệ Thống Lọc Tốt Ở Những Trường Hợp Này:

**1. Từ rác rõ ràng về chất liệu/ngành khác**
Các từ như `nhựa`, `nẹp gỗ`, `ốp gỗ` bị chặn rất sớm và chính xác vì đây là từ đặc thù của ngành vật liệu hoàn toàn khác.

**2. Từ khóa mang tín hiệu mua hàng B2B rõ ràng**
`gia công`, `xưởng`, `báo giá`, `hcm` — đây là những từ ngữ đặc thù của người mua sỉ/doanh nghiệp. Hệ thống nhận diện và bảo vệ tốt nhóm này.

**3. Từ có volume đủ lớn để đánh giá**
Khi một từ khóa đã hiển thị ≥ 100 lần, hệ thống có đủ data thống kê để kết luận CTR thấp là thực chất, không phải ngẫu nhiên.

**4. Phát hiện gốc từ độc hại ẩn trong nhiều query**
Tính năng N-gram phát hiện những "tội phạm ẩn danh" — các gốc từ tiêu ngân sách ẩn trong nhiều query nhỏ mà nhìn từng dòng không thấy.

---

### ⚠️ Những Gì Hệ Thống Có Thể Bỏ Sót Hoặc Phán Xét Sai:

**1. Từ khóa chưa đủ data (dưới 100 lần hiển thị)**
Một từ khóa tốt nhưng mới đặt chạy 2 tuần, chưa có đủ 100 lần hiển thị sẽ rơi vào nhóm "Other" — không được nổi bật để tăng bid. Hệ thống không có cơ chế xét tới yếu tố thời gian chạy của từ khóa.

**2. Từ có nghĩa đa tầng**
Từ `học` trong danh sách rác sẽ bắt cả cụm từ "khóa học phong thủy" — đúng. Nhưng nếu có ai gõ "học hỏi kỹ thuật mạ pvd" thì từ "học" sẽ khiến nó bị xếp vào rác trước, dù cụm từ này thực ra chứa "mạ pvd" là tín hiệu mua hàng mạnh. Hệ thống ưu tiên rác trước mua hàng — đây là lựa chọn thiết kế **thận trọng nhưng có thể bỏ sót**.

**3. Mùa vụ và biến động ngân sách**
Các ngưỡng phán xét (`50,000đ` cho Bleeder, `100,000đ` cho CPA tốt) được đặt cố định. Khi ngân sách tháng tăng gấp đôi hoặc vào mùa cao điểm, cùng một từ khóa có thể bị phán xét khác nhau chỉ vì tổng chi phí thay đổi — không phải vì hiệu suất thực sự thay đổi.

**4. Không có trí nhớ tháng trước**
Mỗi lần chạy, hệ thống phân tích độc lập từng tháng. Nó không biết rằng từ khóa A tháng này là Bleeder nhưng tháng trước là Top Performer. Không có cảnh báo xu hướng xấu đi hay cải thiện.

**5. Độ chính xác của N-gram với tiếng Việt**
Tiếng Việt có đặc điểm là mỗi "từ" thực chất gồm nhiều âm tiết (`gia công` = 2 âm tiết không thể tách rời). Hệ thống hiện tại băm theo khoảng trắng, dẫn đến việc "gia" và "công" bị đếm riêng lẻ. Phân tích N-gram tiếng Việt vì vậy **chỉ chuẩn ở mức ước lượng**, không hoàn toàn chính xác về ngữ nghĩa.

---

## PHẦN V — HƯỚNG DẪN SỬ DỤNG (QUY TRÌNH THỰC CHIẾN)

Để sử dụng hệ thống này đạt hiệu quả cao nhất, bạn cần hiểu nguyên lý **"Cái rổ và những quả táo"** và đối mặt với **Lỗ hổng đo lường ngoại tuyến (Offline Conversion Gap)** thường gặp trong B2B.

### Tư duy Chiến lược Cốt lõi

1. **Từ khóa gốc là "Cái rổ" (Báo cáo Từ Khóa):** Một từ khóa mở rộng/cụm từ (ví dụ: `"hộc âm tường"`) là một cái rổ gom rất nhiều cụm từ tìm kiếm nhỏ bên trong. Đừng vội vã đập vỡ cái rổ (giảm giá thầu/tắt) chỉ vì thấy tổng chuyển đổi bằng 0, bởi vì có thể khách hàng lướt web rồi bốc máy gọi điện trực tiếp nên hệ thống đo lường không ghi nhận được (Offline Conversion Gap). Giảm giá thầu ở đây sẽ bóp nghẹt toàn bộ lượng truy cập tiềm năng.
2. **Cụm từ tìm kiếm là "Quả táo" (Báo cáo SQOS):** Hãy soi từng quả táo. Quả nào thối (ví dụ: *tự làm hộc âm tường*, hoặc chữ cụt lủn tốn tiền không ra đơn), hãy nhặt riêng nó ra vứt đi bằng cách dùng **Từ khóa phủ định chính xác `[ ]`**.
3. **Sức mạnh của Phủ định chính xác:** Việc thêm `[hộc âm tường]` vào danh sách phủ định đóng vai trò như một "con dao mổ" — nó chỉ chặn đứng đúng truy vấn cụt lủn đốt tiền đó, nhưng vẫn bảo vệ an toàn cho các truy vấn dài sinh lời (như *báo giá hộc âm tường hcm*).

### Quy Trình Tối Ưu Hàng Tuần

> [!TIP]
> **Bước 1 — Nhổ cỏ (Xử lý Báo cáo Cụm từ tìm kiếm - SQOS trước):**
> 1. Tải báo cáo "Cụm từ tìm kiếm" → Thả vào `raw_reports` → Chạy `RUN_ANALYSIS.bat`
> 2. Mở sheet `Bleeders` và `Noise`:
>    - Nếu thấy từ khóa rác (sai tệp khách, ý định kém): Đưa vào **Từ khóa phủ định cụm từ `" "`**.
>    - Nếu thấy từ khóa ngắn, chung chung đốt tiền: Đưa vào **Từ khóa phủ định chính xác `[ ]`**.
> 
> **Bước 2 — Gieo hạt (Tìm từ khóa ra đơn từ SQOS):**
> Mở sheet `Exact Matches / Winners` (các từ đã ra đơn): Lấy chính xác các từ này thêm vào tài khoản chạy Ads dưới dạng **Từ khóa chính xác `[ ]`** và bơm ngân sách/giá thầu thật cao để luôn đứng Top 1.
>
> **Bước 3 — Điều hướng chiến lược (Xử lý Báo cáo Từ khóa - Keywords sau):**
> 1. Tải báo cáo "Từ khóa tìm kiếm" → Chạy tương tự
> 2. Mở sheet `Top Performers` + `Sleeping Giants` → Tăng bid nhẹ 15-20% để duy trì lợi thế. 
> 3. Mở sheet `Bleeders` → Nếu một từ khóa tốn một số tiền khổng lồ (gấp 3-5 lần CPA) mà bạn đã check đối chiếu qua Bước 1 thấy toàn từ khóa chuẩn nhưng khách vẫn không gọi, lúc đó mới ra quyết định **Giảm giá thầu 30%** hoặc Tạm dừng. Không giảm giá thầu vội vàng.

### Cách Cập Nhật Danh Sách Từ Khóa Rác / Từ Khóa Tiềm Năng

Mở file `config/keyword_rules.json`. Thêm hoặc xóa từ trong 3 danh sách:
- **`waste_words`**: Thêm khi phát hiện cụm từ rác mới xuất hiện liên tục trong báo cáo SQOS.
- **`high_intent_words`**: Thêm khi bạn phát hiện từ nào đó dù không có trong danh sách vẫn hay ra đơn.
- **`informational_words`**: Thêm khi muốn phân loại nhóm "đang tìm hiểu" rõ hơn.

> [!WARNING]
> Không nên thêm từ quá ngắn (1 chữ như "gỗ", "sắt") vào `waste_words` vì có thể khớp nhầm với nhiều cụm từ vô tội. Ưu tiên dùng cụm 2 từ như "nẹp gỗ", "khung sắt" để tránh chặn nhầm.

---

## PHẦN VI — CẤU TRÚC THƯ MỤC THAM CHIẾU NHANH

```
google_ads_analysis/
│
├── 🚀 RUN_ANALYSIS.bat          ← Bấm đúp để chạy toàn bộ
│
├── config/
│   └── keyword_rules.json       ← Danh sách từ rác / từ tiềm năng — chỉnh ở đây
│
├── data/
│   ├── raw_reports/             ← Thả file CSV mới tải từ Google Ads vào đây
│   ├── processed_excel/         ← File Excel phân tích đầu ra
│   └── archive_csv/             ← File CSV gốc sau khi xử lý (lưu tham chiếu)
│
└── scripts/                     ← Không cần đụng vào
```

---

## PHẦN VII — BẢNG TRA CỨU NHANH ĐẦU RA

### File `_HieuSuat.xlsx` (Từ Khóa)

| Sheet | Nội Dung | Hành Động Gợi Ý |
|-------|----------|----------------|
| Toàn bộ Từ Khóa | Tất cả dữ liệu | Tham chiếu tổng quan |
| 1. Top Performers | CPA tốt, đang ra đơn | Tăng bid 15-20% |
| 2. Costly Converting | Đắt nhưng có đơn | Tối ưu landing page, thử giảm bid nhẹ |
| 3. Bleeders | Tốn tiền, không đơn | Giảm bid 30% hoặc Tạm dừng |
| 4. Low Quality Score | Google phạt | Viết lại ad copy hoặc cải thiện landing page |
| 5. Low CTR | Hiển thị nhiều nhưng ít click | Viết lại tiêu đề quảng cáo |
| 6. Sleeping Giants | QS cao, CTR cao nhưng ít ngân sách | Tăng bid mạnh để lấy volume |

### File `_SQOS.xlsx` (Cụm Từ Tìm Kiếm)

| Sheet | Nội Dung | Hành Động Gợi Ý |
|-------|----------|----------------|
| Toàn bộ dữ liệu | Tất cả cụm từ + phân loại Intent | Tham chiếu tổng quan |
| N-gram | Gốc từ tốn tiền nhất | Phủ định gốc từ → chặn nhiều query cùng lúc |
| Bleeders | Tốn > 50k, không đơn, không phải High Intent | Phủ định ngay |
| Winners | Đã ra đơn | Cân nhắc thêm thành từ khóa chính |
| Potential | High Intent, chưa tốn nhiều | Để thêm data, không làm gì vội |
| Investigate | High Intent nhưng tốn tiền chưa ra đơn | Theo dõi thêm 2-4 tuần trước khi quyết định |
| Noise | Đã xác định rác | Phủ định ngay, ưu tiên cao |

## PHẦN VIII — TỰ TỔNG HỢP

### Các Bảng
Bảng Báo cáo Cụm từ tìm kiếm (SQOS) -> Cụm từ Người dùng thực sự search -> Thường dùng hơn -> Phân tích SQOS
Bảng Báo cáo Từ khóa tìm kiếm -> Những từ khóa đang sử dụng -> Ít dùng hơn -> Phân tích Từ khóa

### Quy trình
1. Xem phân tích SQOS trước -> Lấy từ khóa hoạt động tốt người dùng thực sự search; Phủ định các từ rác
- Nhìn vào sheet Bleeders (tốn >50k, không chuyển đổi) và Noise (không chuyển đổi, đã xác định rác) -> Phủ định các từ rác
- Nhìn vào sheet Winners (đã ra đơn) -> Cân nhắc thêm thành từ khóa chính (sử dụng khớp chính xác `[ ]`)
- Nhìn vào sheet Potential (High Intent nhưng tốn ít tiền) và Investigate (High Intent nhưng tốn nhiều tiền) -> Theo dõi thêm

2. Từ báo cáo Từ khóa tìm kiếm
- Nhìn vào sheet Top Performers (CPA tốt, đang ra đơn) -> Tăng bid 15-20%
- Nhìn vào sheet Bleeders (tốn tiền, không đơn) -> Giảm bid 30% hoặc Tạm dừng. Cách thông minh hơn là so sánh với Phân tích Cụm từ tìm kiếm (Có thể mở Toàn bộ dữ liệu và lọc theo keywords, sort chi phí từ cao tới thấp) để phủ định các cụm từ liên quan đến các từ khóa trong Bleeders (Từ khóa tìm kiếm)
- Nhìn vào sheet Costly Converting (đắt nhưng có đơn) -> Cân nhắc tối ưu landing page hoặc giảm bid nhẹ

