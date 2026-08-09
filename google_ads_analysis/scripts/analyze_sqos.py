import pandas as pd
import re
import os
import sys
import argparse
import json

def load_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Không thể đọc config: {e}. Sử dụng config mặc định.")
        return {
            "high_intent_words": ['xưởng', 'gia công', 'mạ pvd', 'báo giá', 'mua', 'hcm', 'hồ chí minh', 'sản xuất', 'chấn', 'gập', 'cắt', 'cnc'],
            "informational_words": ['kích thước', 'là gì', 'cách', 'hướng dẫn', 'mẫu', 'bảng', 'bao nhiêu'],
            "waste_words": ['nhựa', 'nẹp đồng', 'nẹp gỗ', 'ốp gỗ', 'chỉ gỗ', 'sắt', 'thanh lý', 'cũ', 'giáo trình', 'học', 'tự làm', 'trẻ mầm non', 'lớp']
        }

def main():
    parser = argparse.ArgumentParser(description="Phân tích Cụm từ tìm kiếm (SQOS) Google Ads")
    parser.add_argument("--input", required=True, help="Đường dẫn file CSV đầu vào")
    parser.add_argument("--output", required=True, help="Đường dẫn file Excel đầu ra")
    parser.add_argument("--config", help="Đường dẫn file keyword_rules.json", default=None)
    args = parser.parse_args()

    file_path = args.input
    out_path = args.output
    
    config = load_config(args.config) if args.config else load_config("keyword_rules.json")
    high_intent_words = config.get("high_intent_words", [])
    informational_words = config.get("informational_words", [])
    waste_words = config.get("waste_words", [])

    try:
        # Đọc CSV đa định dạng: thử utf-16 → utf-8-sig → utf-8
        df = None
        for enc, sep in [('utf-16', '\t'), ('utf-8-sig', ','), ('utf-8', ',')]:
            try:
                tmp = pd.read_csv(file_path, skiprows=2, encoding=enc, sep=sep)
                if len(tmp.columns) >= 5:
                    df = tmp
                    break
            except Exception:
                continue
        if df is None:
            raise ValueError("Không đọc được file CSV — thử kiểm tra định dạng file.")

        # Chuẩn hóa tên cột click: chỉ rename khi 'Số tương tác' chưa tồn tại
        if 'Lượt nhấp' in df.columns and 'Số tương tác' not in df.columns:
            df.rename(columns={'Lượt nhấp': 'Số tương tác'}, inplace=True)

        # KHÔNG rename 'Từ khóa' → 'Cụm từ tìm kiếm' (sẽ tạo 2 cột trùng tên)
        # Cột 'Từ khóa' được GIỮ LẠI trong output để người dùng biết từ khóa gốc nào kích hoạt cụm từ đó

        # Hàm xử lý định dạng số Việt Nam của Google Ads
        def _parse_vn_number(x):
            """
            - Dấu chấm (.) = phân cách hàng nghìn  (5.857 → 5857)
            - Dấu phẩy (,) = phân cách thập phân   (11,11 → 11.11)
            """
            if hasattr(x, 'iloc'):
                x = x.iloc[0]
            if pd.isna(x):
                return 0.0
            s = str(x).strip().replace('%', '').replace('<', '').strip()
            if s in ('--', '', 'nan'):
                return 0.0
            if ',' in s and '.' in s:
                s = s.replace('.', '').replace(',', '.')
            elif ',' in s:
                s = s.replace(',', '.')
            try:
                return float(s)
            except:
                return 0.0

        def clean_num(x):
            return _parse_vn_number(x)

        def clean_pct(x):
            """Giữ % dạng dễ đọc: 11.11 thay vì 0.1111"""
            return _parse_vn_number(x)

        for col in ['Chi phí', 'Lượt chuyển đổi', 'Số tương tác', 'Số lượt hiển thị']:
            if col in df.columns:
                df[col] = df[col].apply(clean_num)

        for col in ['Tỷ lệ chuyển đổi', 'CTR']:
            if col in df.columns:
                df[col] = df[col].apply(clean_pct)


        def classify_intent(query):
            query = str(query).lower()
            for w in waste_words:
                if w in query: return 'Noise (Rác - Cần phủ định)'
            for w in high_intent_words:
                if w in query: return 'High Intent (Mua/Gia công)'
            for w in informational_words:
                if w in query: return 'Informational (Tìm hiểu)'
            return 'Neutral (Bình thường)'

        df['Phân loại Intent'] = df['Cụm từ tìm kiếm'].apply(classify_intent)

        # SQOS Classification
        def _scalar(val):
            """Đảm bảo val luôn là scalar, tránh lỗi 'truth value of a Series is ambiguous'."""
            if hasattr(val, 'iloc'):   # là pandas Series (cột bị trùng tên)
                return val.iloc[0]
            return val

        def get_quadrant(row):
            cost = float(_scalar(row.get('Chi phí', 0)) or 0)
            conv = float(_scalar(row.get('Lượt chuyển đổi', 0)) or 0)
            intent = str(_scalar(row.get('Phân loại Intent', '')))

            if conv > 0:
                return 'Winners (Ra đơn/Tốt)'

            # Mốc chịu đựng nâng lên 50.000 và KHÔNG giết High Intent
            if cost > 50000 and conv == 0:
                if intent == 'High Intent (Mua/Gia công)':
                    return 'Investigate (High Intent tốn tiền)'
                else:
                    return 'Bleeders (Tốn tiền vô ích)'

            if cost <= 50000 and intent == 'High Intent (Mua/Gia công)':
                return 'Potential (Tiềm năng)'

            if intent == 'Noise (Rác - Cần phủ định)':
                return 'Noise (Cần phủ định)'

            return 'Other (Theo dõi thêm)'

        df['Nhóm SQOS'] = df.apply(get_quadrant, axis=1)

        # N-gram analysis (1-gram và 2-gram)
        words_cost = {}
        words_clicks = {}
        
        for idx, row in df.iterrows():
            q = str(row.get('Cụm từ tìm kiếm', '')).lower()
            cost = row.get('Chi phí', 0)
            clicks = row.get('Số tương tác', 0)
            
            # Tách từ đơn (1-gram)
            tokens = q.split()
            
            # Tạo 2-gram (cụm 2 từ liền kề)
            bigrams = [' '.join(tokens[i:i+2]) for i in range(len(tokens)-1)]
            
            # Gộp cả 1-gram và 2-gram
            all_grams = set(tokens + bigrams)
            
            for w in all_grams:
                words_cost[w] = words_cost.get(w, 0) + cost
                words_clicks[w] = words_clicks.get(w, 0) + clicks

        ngram_data = []
        for w in words_cost:
            ngram_data.append({
                'Cụm từ (1-gram & 2-gram)': w,
                'Tổng Chi Phí': words_cost[w],
                'Tổng Lượt Nhấp': words_clicks[w],
                'Gợi ý hành động': 'Nên Phủ Định' if any(waste == w for waste in waste_words) else ''
            })
            
        ngram_df = pd.DataFrame(ngram_data)
        ngram_df = ngram_df.sort_values(by='Tổng Chi Phí', ascending=False)

        # Write to Excel
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Toàn bộ dữ liệu', index=False)
            ngram_df.head(200).to_excel(writer, sheet_name='N-gram (Gốc từ tốn tiền)', index=False)
            df[df['Nhóm SQOS'] == 'Bleeders (Tốn tiền vô ích)'].sort_values('Chi phí', ascending=False).to_excel(writer, sheet_name='Bleeders (Kẻ cắp ngân sách)', index=False)
            df[df['Nhóm SQOS'] == 'Winners (Ra đơn/Tốt)'].sort_values('Lượt chuyển đổi', ascending=False).to_excel(writer, sheet_name='Winners (Từ khóa vàng)', index=False)
            df[df['Nhóm SQOS'] == 'Potential (Tiềm năng)'].sort_values('Số tương tác', ascending=False).to_excel(writer, sheet_name='Potential (Tiềm năng)', index=False)
            df[df['Nhóm SQOS'] == 'Investigate (High Intent tốn tiền)'].sort_values('Chi phí', ascending=False).to_excel(writer, sheet_name='Investigate (Cần kiểm tra)', index=False)
            df[df['Nhóm SQOS'] == 'Noise (Cần phủ định)'].sort_values('Chi phí', ascending=False).to_excel(writer, sheet_name='Noise (Nhiễu - Phủ định)', index=False)

        print(f"SUCCESS: {out_path}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
