import os
import shutil
import pandas as pd
import subprocess
from pathlib import Path

# Buộc child process dùng UTF-8 khi in output trên Windows
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw_reports"
PROCESSED_DIR = BASE_DIR / "data" / "processed_excel"
ARCHIVE_DIR = BASE_DIR / "data" / "archive_csv"
CONFIG_FILE = BASE_DIR / "config" / "keyword_rules.json"

SCRIPT_KEYWORDS = BASE_DIR / "scripts" / "analyze_keywords.py"
SCRIPT_SQOS = BASE_DIR / "scripts" / "analyze_sqos.py"

def setup_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

import unicodedata

def identify_report_type(file_path):
    """Đọc header CSV để nhận dạng loại báo cáo (Keywords hay SQOS)."""
    encodings = ['utf-8-sig', 'utf-16', 'utf-8']
    df = None

    for enc in encodings:
        try:
            sep = '\t' if enc == 'utf-16' else ','
            tmp = pd.read_csv(file_path, skiprows=2, encoding=enc, sep=sep, nrows=5)
            if len(tmp.columns) >= 3:
                df = tmp
                break
        except Exception:
            continue

    if df is None:
        print(f"   Không đọc được header: {file_path.name}")
        return None

    # Google Ads thường dùng Unicode tổ hợp (NFD) xuất file, cần gộp lại thành NFC
    cols_lower = [unicodedata.normalize('NFC', str(c).lower().strip()) for c in df.columns]

    # Dấu hiệu của báo cáo TỪ KHÓA: có cột Điểm Chất lượng / CPC Tối đa
    # (Loại đối sánh & Nhóm QC có ở cả 2 báo cáo, nên ta dùng dấu hiệu đặc trưng hơn)
    keyword_signals = ['điểm chất lượng', 'cpc tối đa', 'trạng thái từ khóa']
    keyword_hits = sum(1 for sig in keyword_signals if any(sig in c for c in cols_lower))

    # Dấu hiệu của báo cáo CỤM TỪ TÌM KIẾM: có cột Cụm từ tìm kiếm / Từ khóa đã thêm
    sqos_signals = ['cụm từ tìm kiếm', 'từ khóa đã thêm']
    sqos_hits = sum(1 for sig in sqos_signals if any(sig in c for c in cols_lower))

    if sqos_hits >= 1:
        return 'SQOS'
    elif keyword_hits >= 1:
        return 'KEYWORDS'
    else:
        # Fallback dựa vào tên file
        name_lower = unicodedata.normalize('NFC', file_path.name.lower())
        if 'cụm từ' in name_lower:
            return 'SQOS'
        return 'KEYWORDS'




def process_file(csv_file):
    print(f"\n[{csv_file.name}] Đang phân tích...")
    report_type = identify_report_type(csv_file)
    
    if not report_type:
        print(f"❌ Không thể nhận diện định dạng báo cáo cho file: {csv_file.name}")
        return False

    # Generate Output Name
    base_name = csv_file.stem.replace("Báo cáo", "Phân tích")
    
    if report_type == 'KEYWORDS':
        print(f"   ↳ Nhận diện: Báo Cáo Hiệu Suất Từ Khóa")
        out_file = PROCESSED_DIR / f"{base_name}_HieuSuat.xlsx"
        cmd = [
            "python", str(SCRIPT_KEYWORDS),
            "--input", str(csv_file),
            "--output", str(out_file)
        ]
    else:
        print(f"   ↳ Nhận diện: Báo Cáo Cụm Từ Tìm Kiếm (SQOS)")
        out_file = PROCESSED_DIR / f"{base_name}_SQOS.xlsx"
        cmd = [
            "python", str(SCRIPT_SQOS),
            "--input", str(csv_file),
            "--output", str(out_file),
            "--config", str(CONFIG_FILE)
        ]
        
    # Execute the analysis script
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            env=CHILD_ENV,
        )
        if result.returncode != 0:
            print(f"   ❌ Lỗi phân tích:\n{result.stdout}\n{result.stderr}")
            return False
        if "SUCCESS" in result.stdout:
            print(f"   ✅ Đã phân tích xong: {out_file.name}")
            return True
        else:
            print(f"   ❌ Lỗi phân tích:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Lỗi hệ thống khi chạy script: {e}")
        return False

def main():
    print("=" * 50)
    print("🚀 BỘ CÔNG CỤ PHÂN TÍCH GOOGLE ADS TỰ ĐỘNG")
    print("=" * 50)
    
    setup_dirs()
    
    csv_files = list(RAW_DIR.glob("*.csv"))
    
    if not csv_files:
        print(f"Không tìm thấy file .csv nào trong thư mục:\n{RAW_DIR}")
        print("Vui lòng copy báo cáo từ Google Ads vào đây và chạy lại.")
        return

    print(f"Tìm thấy {len(csv_files)} file cần xử lý.\n")
    
    success_count = 0
    for csv_file in csv_files:
        if process_file(csv_file):
            # Move to archive if successful
            archive_path = ARCHIVE_DIR / csv_file.name
            # If file already exists in archive, remove it first to overwrite
            if archive_path.exists():
                archive_path.unlink()
            shutil.move(str(csv_file), str(archive_path))
            print(f"   📂 Đã di chuyển file gốc vào: archive_csv/")
            success_count += 1

    print("\n" + "=" * 50)
    print(f"TỔNG KẾT: Hoàn thành {success_count}/{len(csv_files)} file.")
    print("=" * 50)

if __name__ == "__main__":
    main()
