# -*- coding: utf-8 -*-
"""
Khởi tạo 4 sheet + tiêu đề cột trên Google Sheets.

Chạy (sau khi đặt JSON vào .credentials/google-service-account.json
và đã chia sẻ spreadsheet cho service account):

  cd C:\\Users\\Administrator\\.cursor\\projects\\empty-window
  pip install gspread google-auth
  python init_sheets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

ROOT = Path(__file__).resolve().parent
SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1Ss-QAoyHbY81FMAeyT5m7_lcVZgTu5qi3RMgNoL3Ta4/edit"
)
CRED_PATHS = [
    ROOT / ".credentials" / "crypto-avenue-410700-f7e540ba2e49.json",
    ROOT / ".credentials" / "google-service-account.json",
    Path.home() / "Downloads" / "crypto-avenue-410700-f7e540ba2e49.json",
]

SHEET_HEADERS = {
    "Account": ["MaDTV", "MatKhau", "HoTen", "TrangThai"],
    "DanhSachĐTV": ["MaDTV", "HoTen", "TrangThai"],
    "DanhSachHo": ["Huyen", "Xa", "DiaBan", "HoSo", "TenChuHo", "MaDTV", "PhanLoai", "DiaChi"],
    "PhanCong": ["MaDTV", "HoSo", "Huyen", "Xa", "DiaBan", "TenChuHo", "NgayPhanCong"],
    "KetQua": [
        "MaDTV", "HoSo", "Huyen", "Xa", "DiaBan", "TenChuHo", "NhanKhauTT",
        "ThuLuong",
        "DT_TrongTrot", "CP_TrongTrot", "Thu_TrongTrot",
        "DT_ChanNuoi", "CP_ChanNuoi", "Thu_ChanNuoi",
        "DT_LamNghiep", "CP_LamNghiep", "Thu_LamNghiep",
        "DT_ThuySan", "CP_ThuySan", "Thu_ThuySan",
        "DT_SXKD", "CP_SXKD", "Thu_SXKD",
        "ThuKhac", "TongThuNhap", "ThuBQDauNguoi",
        "MaDiaBan", "DiaChi", "KhoangCachLech", "GhiChuViTri",
        "GPS_lat", "GPS_lng", "DoChinhXac", "Sai_so", "Do_cao", "Xac_Thuc_GPS",
        "IP", "MockGPS", "NgayNhap",
    ],
}

SAMPLE_NHAN_SU = [
    ["MaDTV", "HoTen", "TrangThai"],
    ["DTV01", "Điều tra viên 01", "Active"],
    ["DTV02", "Điều tra viên 02", "Active"],
]


def find_credentials() -> Path:
    for p in CRED_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Không tìm thấy google-service-account.json.\n"
        f"Đặt file vào: {CRED_PATHS[0]}"
    )


def main() -> int:
    cred_path = find_credentials()
    print(f"JSON: {cred_path}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(str(cred_path), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(SPREADSHEET_URL)

    print(f"\n✅ Kết nối: {sh.title}")
    print(f"📧 Chia sẻ spreadsheet (Editor) cho: {creds.service_account_email}\n")

    existing = {w.title for w in sh.worksheets()}
    for name, headers in SHEET_HEADERS.items():
        if name not in existing:
            print(f"+ Tạo sheet: {name}")
            sh.add_worksheet(title=name, rows=1000, cols=26)
        ws = sh.worksheet(name)
        row1 = ws.row_values(1)
        if not row1:
            if name == "DanhSachĐTV":
                ws.update(SAMPLE_NHAN_SU, "A1")
            else:
                ws.update([headers], "A1")
            print(f"  → Đã ghi tiêu đề cột [{name}]")
        else:
            print(f"  → [{name}] đã có hàng 1: {row1[:4]}...")

    print("\n✅ Hoàn tất: Account | DanhSachĐTV | DanhSachHo | PhanCong | KetQua")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\n❌ Lỗi: {e}", file=sys.stderr)
        print(
            "\nNếu lỗi quyền truy cập: mở Google Sheets → Chia sẻ → "
            "thêm email service account (Editor)."
        )
        sys.exit(1)
