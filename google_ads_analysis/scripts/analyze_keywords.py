import pandas as pd
import sys
import argparse
import traceback

def main():
    parser = argparse.ArgumentParser(description="Phân tích hiệu suất từ khóa Google Ads")
    parser.add_argument("--input", required=True, help="Đường dẫn file CSV đầu vào")
    parser.add_argument("--output", required=True, help="Đường dẫn file Excel đầu ra")
    args = parser.parse_args()

    file_path = args.input
    out_path = args.output

    try:
        # 1. Đọc CSV — thử lần lượt các encoding Google Ads hay dùng
        df = None
        for enc, sep in [('utf-8-sig', ','), ('utf-16', '\t'), ('utf-8', ',')]:
            try:
                tmp = pd.read_csv(file_path, skiprows=2, encoding=enc, sep=sep)
                if len(tmp.columns) >= 5:
                    df = tmp
                    break
            except Exception:
                continue

        if df is None:
            print("ERROR: Không đọc được file CSV. Kiểm tra encoding và định dạng.")
            sys.exit(1)


        # 2. Làm sạch dữ liệu số
        def _parse_vn_number(x):
            """
            Xử lý định dạng số Google Ads Việt Nam:
            - Dấu chấm (.)  = phân cách hàng nghìn  (ví dụ: 5.857 = 5857)
            - Dấu phẩy (,) = phân cách thập phân    (ví dụ: 11,11 = 11.11)
            - Nếu có cả hai: xóa dấu chấm rồi thay phẩy bằng chấm
            - Nếu chỉ có phẩy: thay phẩy bằng chấm (thập phân)
            - Nếu chỉ có chấm: giữ nguyên (thập phân chuẩn)
            """
            if hasattr(x, 'iloc'):
                x = x.iloc[0]
            if pd.isna(x):
                return 0.0
            s = str(x).strip().replace('%', '').replace('<', '').strip()
            if s in ('--', '', 'nan'):
                return 0.0
            if ',' in s and '.' in s:
                # Cả hai: dấu chấm là phân cách nghìn, dấu phẩy là thập phân
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                # Chỉ phẩy: đây là dấu thập phân
                s = s.replace(',', '.')
            # Chỉ chấm: giữ nguyên (đã đúng chuẩn float)
            try:
                return float(s)
            except:
                return 0.0

        def clean_num(x):
            """Trả về số nguyên/thập phân thực tế."""
            return _parse_vn_number(x)

        def clean_pct(x):
            """
            Trả về giá trị % dạng dễ đọc (ví dụ: 11.11 thay vì 0.1111).
            Excel sẽ hiển thị 11.11 và người dùng biết đây là 11.11%.
            """
            return _parse_vn_number(x)  # giữ nguyên, không chia 100

        # Đổi tên cột trước khi xử lý để tránh nhầm lẫn tên tương tự
        # Chỉ rename nếu 'Số tương tác' chưa tồn tại — tránh tạo 2 cột trùng tên
        if 'Lượt nhấp' in df.columns and 'Số tương tác' not in df.columns:
            df.rename(columns={'Lượt nhấp': 'Số tương tác'}, inplace=True)

        # Dùng exact match: lấy cột đúng tên, tránh trường hợp pandas
        # trả về DataFrame khi có nhiều cột tên gần giống ('Chi phí' vs 'Chi phí tr.bình')
        def get_col_exact(dataframe, name):
            """Trả về Series đúng tên cột, tránh nhầm cột tên tương tự."""
            matching = [c for c in dataframe.columns if c == name]
            if matching:
                return dataframe[matching[0]]
            return None

        num_cols = ['Chi phí', 'Lượt chuyển đổi', 'Số tương tác', 'Số lượt hiển thị', 'Điểm Chất lượng',
                     'CPC Tối đa', 'Chi phí/lượt chuyển đổi']
        pct_cols = ['Tỷ lệ chuyển đổi', 'CTR', 'Tỷ lệ tương tác']

        for col in num_cols:
            series = get_col_exact(df, col)
            if series is not None:
                df[col] = series.apply(clean_num)

        for col in pct_cols:
            series = get_col_exact(df, col)
            if series is not None:
                df[col] = series.apply(clean_pct)


        # 3. Phân loại theo Ma trận Hiệu suất
        def classify_keyword(row):
            conv = row.get('Lượt chuyển đổi', 0)
            cost = row.get('Chi phí', 0)
            cpa = cost / conv if conv > 0 else 0
            qs = row.get('Điểm Chất lượng', 0)
            ctr = row.get('CTR', 0)
            imps = row.get('Số lượt hiển thị', 0)
            
            # Nhóm 1 & 2: Có chuyển đổi
            if conv > 0:
                if cpa <= 100000:
                    return 'Top Performers (Tốt)'
                else:
                    return 'Costly but Converting (Đắt)'
                    
            # Nhóm 3: Đốt tiền vô ích
            if cost >= 50000:
                return 'Bleeders (Tốn tiền)'
                
            # Nhóm 4: Điểm chất lượng thấp (Google phạt)
            if 0 < qs < 5:
                return 'Low Quality Score (Phạt)'
                
            # Nhóm 5: Thiếu hấp dẫn
            if imps >= 100 and ctr < 0.03:
                return 'Low CTR (Chán)'
                
            # Nhóm 6: Tiềm năng chưa được khai thác
            if qs >= 7 and ctr >= 0.1 and imps < 100:
                return 'Sleeping Giants (Tiềm năng)'
                
            return 'Other (Theo dõi)'

        df['Nhóm Hiệu Suất'] = df.apply(classify_keyword, axis=1)

        # 4. Xuất file Excel
        def safe_sort(subset_df, col, ascending=True):
            """Sort nếu cột tồn tại, không thì trả về nguyên df."""
            if col in subset_df.columns:
                return subset_df.sort_values(col, ascending=ascending)
            return subset_df

        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Toàn bộ Từ Khóa', index=False)

            top = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Top Performers (Tốt)'], 'Lượt chuyển đổi', ascending=False)
            if not top.empty: top.to_excel(writer, sheet_name='1. Top Performers', index=False)

            costly = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Costly but Converting (Đắt)'], 'Chi phí', ascending=False)
            if not costly.empty: costly.to_excel(writer, sheet_name='2. Costly but Converting', index=False)

            bleeders = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Bleeders (Tốn tiền)'], 'Chi phí', ascending=False)
            if not bleeders.empty: bleeders.to_excel(writer, sheet_name='3. Bleeders', index=False)

            low_qs = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Low Quality Score (Phạt)'], 'Điểm Chất lượng', ascending=True)
            if not low_qs.empty: low_qs.to_excel(writer, sheet_name='4. Low Quality Score', index=False)

            low_ctr = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Low CTR (Chán)'], 'CTR', ascending=True)
            if not low_ctr.empty: low_ctr.to_excel(writer, sheet_name='5. Low CTR', index=False)

            giants = safe_sort(df[df['Nhóm Hiệu Suất'] == 'Sleeping Giants (Tiềm năng)'], 'CTR', ascending=False)
            if not giants.empty: giants.to_excel(writer, sheet_name='6. Sleeping Giants', index=False)


        print(f"SUCCESS: {out_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
