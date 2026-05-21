# -*- coding: utf-8 -*-
"""
Cấu hình tự động kết nối Google Sheets -> .streamlit/secrets.toml

Cách dùng nhanh:
  1. Tải file JSON Service Account từ Google Cloud, đặt vào:
     .credentials/google-service-account.json
  2. Tạo file gsheets_url.txt chứa link Google Spreadsheet (1 dòng)
  3. Chạy: python setup_gsheets.py

Hoặc:
  python setup_gsheets.py --json "đường_dẫn\key.json" --url "https://docs.google.com/..."
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CRED_DIR = ROOT / ".credentials"
DEFAULT_JSON = CRED_DIR / "google-service-account.json"
URL_FILE = ROOT / "gsheets_url.txt"
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"

REQUIRED_SHEETS = ["DanhSachĐTV", "DanhSachHo", "PhanCong", "KetQua"]

SHEET_HEADERS = {
    "DanhSachĐTV": ["MaDTV", "HoTen", "TrangThai"],
    "DanhSachHo": ["Huyen", "Xa", "DiaBan", "HoSo", "TenChuHo"],
    "PhanCong": ["MaDTV", "HoSo", "Huyen", "Xa", "DiaBan", "TenChuHo", "NgayPhanCong"],
    "KetQua": [
        "MaDTV", "HoSo", "Huyen", "Xa", "TenChuHo",
        "ThuLuong", "ThuNN", "ChiNN", "ThuNNThuan", "ThuSXKD", "ThuKhac",
        "TongThuNhap", "GPS_lat", "GPS_lng", "DoChinhXac",
        "Xac_Thuc_GPS", "Sai_so", "Do_cao",
        "IP", "MockGPS", "NgayNhap",
    ],
}


def escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_secrets_toml(spreadsheet_url: str, cred_rel_path: str) -> str:
    rel = cred_rel_path.replace("\\", "/")
    url = escape_toml_string(spreadsheet_url)
    return f'''# Tự động tạo bởi setup_gsheets.py
# Chia sẻ Google Spreadsheet cho client_email trong file JSON (quyền Editor)

[connections.gsheets]
spreadsheet_url = "{url}"
spreadsheet = "{url}"
credentials_file = "{escape_toml_string(rel)}"
'''


def normalize_spreadsheet_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("Link spreadsheet trống.")
    if "/d/" in url:
        return url
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", url):
        return f"https://docs.google.com/spreadsheets/d/{url}/edit"
    return url


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file JSON: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if data.get("type") != "service_account":
        raise ValueError("File JSON không phải Service Account (thiếu type=service_account).")
    return data


def read_url_from_file() -> str | None:
    if URL_FILE.exists():
        text = URL_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text.splitlines()[0].strip()
    return None


def test_and_init_sheets(spreadsheet_url: str, json_path: Path) -> None:
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(str(json_path), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(normalize_spreadsheet_url(spreadsheet_url))

    print(f"\n✅ Kết nối OK: {sh.title}")
    print(f"   Service account: {creds.service_account_email}")
    print("   → Hãy chia sẻ spreadsheet cho email trên (quyền Editor).\n")

    existing = {ws.title for ws in sh.worksheets()}
    for name in REQUIRED_SHEETS:
        if name not in existing:
            print(f"   + Tạo sheet: {name}")
            sh.add_worksheet(title=name, rows=1000, cols=26)
        ws = sh.worksheet(name)
        row1 = ws.row_values(1)
        headers = SHEET_HEADERS[name]
        if not row1:
            ws.update([headers], "A1")
            print(f"   + Ghi tiêu đề cột cho [{name}]")
        elif row1 != headers:
            print(f"   ⚠ Sheet [{name}] đã có tiêu đề khác — giữ nguyên.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cấu hình Google Sheets cho PMDTV")
    parser.add_argument("--json", type=str, help="Đường dẫn file Service Account JSON")
    parser.add_argument("--url", type=str, help="Link Google Spreadsheet")
    parser.add_argument("--no-test", action="store_true", help="Chỉ ghi secrets, không test kết nối")
    parser.add_argument("--init-sheets", action="store_true", help="Tạo sheet & tiêu đề cột nếu thiếu")
    args = parser.parse_args()

    json_path = Path(args.json) if args.json else DEFAULT_JSON
    if not json_path.is_absolute():
        json_path = ROOT / json_path

    spreadsheet_url = args.url or read_url_from_file()
    if not spreadsheet_url:
        print("\n📋 Cấu hình Google Sheets cho PMDTV\n")
        print(f"Đặt file JSON vào: {DEFAULT_JSON}")
        print(f"Hoặc nhập đường dẫn file JSON:")
        p = input("> ").strip().strip('"')
        if p:
            json_path = Path(p)

        print("\nDán link Google Spreadsheet (hoặc chỉ SPREADSHEET_ID):")
        spreadsheet_url = input("> ").strip()

    try:
        cred = load_json(json_path)
        spreadsheet_url = normalize_spreadsheet_url(spreadsheet_url)
    except Exception as e:
        print(f"\n❌ Lỗi: {e}", file=sys.stderr)
        return 1

    try:
        rel = json_path.relative_to(ROOT).as_posix()
    except ValueError:
        rel = json_path.as_posix()

    SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SECRETS_PATH.write_text(build_secrets_toml(spreadsheet_url, rel), encoding="utf-8")
    print(f"\n✅ Đã ghi: {SECRETS_PATH}")

    # Lưu URL để lần sau chạy lại không cần nhập
    URL_FILE.write_text(spreadsheet_url + "\n", encoding="utf-8")
    print(f"✅ Đã lưu link: {URL_FILE}")

    if not args.no_test:
        try:
            if args.init_sheets:
                test_and_init_sheets(spreadsheet_url, json_path)
            else:
                import gspread
                from google.oauth2.service_account import Credentials

                scopes = [
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
                creds = Credentials.from_service_account_file(str(json_path), scopes=scopes)
                gc = gspread.authorize(creds)
                sh = gc.open_by_url(spreadsheet_url)
                print(f"\n✅ Kết nối thử OK: {sh.title}")
                print(f"   Email cần chia sẻ sheet: {creds.service_account_email}")
        except Exception as e:
            print(f"\n⚠ Ghi secrets xong nhưng test kết nối thất bại: {e}")
            print("   Kiểm tra: đã chia sẻ spreadsheet cho service account chưa?")
            return 2

    print("\n▶ Chạy app: streamlit run PMDTV.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
