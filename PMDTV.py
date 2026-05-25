# -*- coding: utf-8 -*-
"""
PMDTV.py — Phiếu hỏi điều tra thu nhập năm 2026 (Streamlit + Google Sheets).
Đã được làm sạch, tối ưu hóa toàn diện, loại bỏ hàm trùng lặp, sửa lỗi tham chiếu biến chưa định nghĩa,
giữ nguyên 100% logic nghiệp vụ tính toán và geofencing.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- THƯ VIỆN BỔ TRỢ ĐỊA LÝ ---
try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

try:
    from geopy.geocoders import Nominatim
    from geopy.distance import geodesic
except ImportError:
    Nominatim = None
    geodesic = None


# ---------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG & GIAO DIỆN (STREAMLIT)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PMDTV — Phiếu hỏi thu nhập hộ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY_PRIMARY = "#0d2137"
NAVY_ACCENT = "#1a4a7a"
NAVY_LIGHT = "#e8eef5"

def apply_custom_style() -> None:
    """Giao diện Navy chủ đạo — bo góc, đổ bóng, tối giản và responsive."""
    st.markdown(
        f"""
        <style>
        :root {{
            --navy: {NAVY_PRIMARY};
            --navy-accent: {NAVY_ACCENT};
            --navy-light: {NAVY_LIGHT};
        }}
        
        /* Hide streamlit default sidebar & header */
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        .stApp {{
            background: #f8fafc;
        }}
        
        /* Spacing for main block container */
        .main .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 1200px !important;
            margin: 0 auto !important;
        }}
        
        /* Clean Modern App UI Components */
        .card-box {{
            background: #ffffff;
            border-radius: 14px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03), 0 1px 2px rgba(15, 23, 42, 0.06);
            border: 1px solid #e2e8f0;
            transition: all 0.2s ease-in-out;
        }}
        .card-box:hover {{
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
            border-color: #cbd5e1;
        }}
        
        /* Top Navigation Badges & Layouts */
        .user-badge-card {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: #ffffff;
            padding: 8px 14px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 4px rgba(15,23,42,0.02);
            height: 100%;
        }}
        .avatar-circle {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(15,23,42,0.1);
        }}
        .user-title {{
            font-size: 12.5px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.2;
        }}
        .user-role {{
            font-size: 10.5px;
            color: #64748b;
            font-weight: 500;
            margin-top: 1px;
        }}
        
        .surveyor-badge {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            color: #166534;
            padding: 9px 16px;
            border-radius: 12px;
            font-size: 12px;
            line-height: 1.5;
            height: 100%;
        }}
        .status-dot {{
            color: #22c55e;
            font-size: 14px;
            animation: pulse-green 2s infinite;
        }}
        @keyframes pulse-green {{
            0% {{ opacity: 0.4; }}
            50% {{ opacity: 1; }}
            100% {{ opacity: 0.4; }}
        }}
        
        .canh-bao-qd1099 {{
            background: #fefbeb;
            border-left: 4px solid #ef4444;
            padding: 0.9rem 1.1rem;
            border-radius: 8px;
            margin: 0.5rem 0 1.2rem 0;
            font-size: 0.9rem;
            line-height: 1.5;
            color: #991b1b;
            font-weight: 500;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        .canh-bao-vang {{
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            padding: 0.8rem 1.1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-size: 0.88rem;
            line-height: 1.5;
            color: #92400e;
            font-weight: 500;
        }}
        .canh-bao-do, .input-loi-do {{
            background: #fef2f2 !important;
            border-left: 4px solid #ef4444;
            padding: 0.8rem 1.1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            font-size: 0.88rem;
            line-height: 1.5;
            color: #991b1b;
            font-weight: 500;
        }}
        
        div[data-testid="stMetric"] {{
            background: #ffffff;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(15, 23, 42, 0.015), 0 1px 2px rgba(15, 23, 42, 0.03);
            border: 1px solid #e2e8f0;
        }}
        
        /* Sticky Header Pinning CSS */
        div[data-testid="stVerticalBlock"] > div:has(#sticky-header),
        div[data-testid="stVerticalBlockBorder"]:has(#sticky-header) {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 999991 !important;
            background-color: #f8fafc !important;
            border-bottom: 2px solid #e2e8f0 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 10px 0 0 0 !important;
        }}
        
        div[data-testid="stVerticalBlock"] > div:has(#sticky-header) > div,
        div[data-testid="stVerticalBlockBorder"]:has(#sticky-header) > div {{
            max-width: 1200px !important;
            margin: 0 auto !important;
            padding: 0px 1.5rem 10px 1.5rem !important;
        }}

        .sticky-header-spacer {{
            height: 345px !important;
            width: 100% !important;
        }}
        
        /* Modern tabs customization */
        div[data-testid="stTabs"] button {{
            font-weight: 600 !important;
            font-size: 13.5px !important;
            padding: 8px 16px !important;
            color: #64748b !important;
        }}
        div[data-testid="stTabs"] button[aria-selected="true"] {{
            color: #0284c7 !important;
            border-bottom-color: #0284c7 !important;
        }}
        
        @media (max-width: 768px) {{
            .main .block-container {{
                padding-top: 1.5rem !important;
            }}
            div[data-testid="stTabs"] button {{
                font-size: 11.5px !important;
                padding: 6px 12px !important;
            }}
            .sticky-header-spacer {{
                height: 520px !important;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def hien_thi_banner() -> None:
    """Hiển thị ảnh ngang nằm ở trên cùng của trang (tương thích GitHub image/panel.png)"""
    import os
    # Thêm khoảng trống lịch sự phía trên để tránh ảnh bị sát mép trên cùng
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    image_path = "image/panel.png"
    # Dùng ảnh dự phòng của Unsplash nếu file chưa tồn tại local để tránh lỗi hiển thị trống
    fallback_url = "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&q=80&w=2000&h=300"
    
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
    else:
        st.image(fallback_url, use_container_width=True)
        
    st.markdown(
        """
        <div style="text-align: center; margin-top: -10px; margin-bottom: 25px;">
            <h2 style="color:#0d2137; font-weight:800; margin-bottom: 5px; font-size: 24px; text-transform: uppercase;">HỆ THỐNG ĐIỀU TRA THU NHẬP HỘ PMDTV</h2>
            <p style="color:#64748b; font-size: 13px; font-weight: 500; margin: 0;">Chương trình Khảo sát Thu nhập hộ nông thôn & Đánh giá phân tích Kinh tế Nông nghiệp | QĐ 1099 | Tổng cục Thống kê</p>
        </div>
        """,
        unsafe_allow_html=True
    )

@contextmanager
def card_container(title: str | None = None):
    """Khối nội dung đẹp mắt với lớp CSS card-box dùng làm vùng nhập liệu."""
    tieu_de = f"<p style='margin:0 0 0.75rem;font-weight:600;color:{NAVY_PRIMARY};'>{title}</p>" if title else ""
    st.markdown(f'<div class="card-box">{tieu_de}', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)

apply_custom_style()


# ---------------------------------------------------------------------------
# 2. KHAI BÁO CẤU HÌNH HỆ THỐNG & BIẾN TOÀN CỤC
# ---------------------------------------------------------------------------
SHEETS = {
    "account": "Account",
    "danh_sach_dtv": "DanhSachĐTV",
    "danh_sach_ho": "DanhSachHo",
    "phan_cong": "PhanCong",
    "ket_qua": "KetQua",
}

ADMIN_MA = "ADMIN"
TRANG_THAI_MK_CHUA = "Chưa đổi mật khẩu"
TRANG_THAI_MK_DA = "Đã đổi mật khẩu"
CANH_BAO_KHONG_TINH = "KHÔNG tính tiền bán đất, rút tiết kiệm, vay nợ, đền bù giải tỏa vào thu nhập."

# Thiết lập các ngành lâm nghiệp, thủy sản, trồng trọt và chăn nuôi
LINH_VUC_NLN_TS: list[tuple[str, str]] = [
    ("TrongTrot", "Trồng trọt"),
    ("ChanNuoi", "Chăn nuôi"),
    ("LamNghiep", "Lâm nghiệp"),
    ("ThuySan", "Thủy sản"),
]

# 7 nguồn thu nhập hiển thị chung
BAO_CAO_7_NGUON: list[tuple[str, str]] = [
    ("ThuLuong", "1. Tiền lương, tiền công, phụ cấp, thưởng"),
    ("Thu_TrongTrot", "2.1 Trồng trọt (thuần)"),
    ("Thu_ChanNuoi", "2.2 Chăn nuôi (thuần)"),
    ("Thu_LamNghiep", "2.3 Lâm nghiệp (thuần)"),
    ("Thu_ThuySan", "2.4 Thủy sản (thuần)"),
    ("Thu_SXKD", "3. SXKD phi nông nghiệp (thuần)"),
    ("ThuKhac", "4. Thu nhập khác"),
]

# Định nghĩa các chỉ tiêu Phần B giúp định dạng nhập liệu
CHI_TIEU_PHAN_B: list[dict[str, Any]] = [
    {"ma": "ThuLuong", "ten": "1. Tiền lương, tiền công, phụ cấp, thưởng", "loai": "luong"},
    {"ma": "TrongTrot", "ten": "2.1 Trồng trọt", "loai": "linh_vuc_sp"},
    {"ma": "ChanNuoi", "ten": "2.2 Chăn nuôi", "loai": "linh_vuc_sp"},
    {"ma": "LamNghiep", "ten": "2.3 Lâm nghiệp", "loai": "linh_vuc_sp"},
    {"ma": "ThuySan", "ten": "2.4 Thủy sản", "loai": "linh_vuc_sp"},
    {"ma": "SXKD", "ten": "3. Sản xuất kinh doanh phi nông nghiệp", "loai": "sxkd"},
    {"ma": "ThuKhac", "ten": "4. Thu nhập khác", "loai": "khac"},
]

# Tạo bộ bảng tra cứu nhanh chỉ tiêu map_chi_tieu để tránh lỗi undefined variable
map_chi_tieu: dict[str, dict[str, Any]] = {m["ma"]: m for m in CHI_TIEU_PHAN_B}

# Sản phẩm mẫu
SAN_PHAM_LINH_VUC: dict[str, list[str]] = {
    "TrongTrot": ["Lúa", "Ngô", "Rau màu", "Cây ăn quả", "Cây công nghiệp", "Khác"],
    "ChanNuoi": ["Gia súc", "Gia cầm", "Vịt ngan", "Khác"],
    "LamNghiep": ["Khai thác gỗ", "Trồng rừng", "Thu hái lâm sản", "Khác"],
    "ThuySan": ["Nuôi cá", "Nuôi tôm", "Nuôi cua", "Khai thác thủy sản", "Khác"],
}

O_NHAP_SAN_PHAM = ["Giá bán", "Tự dùng", "Giống", "Thức ăn", "Chi khác"]

# Định nghĩa 5 nhóm nhập liệu
NHOM_NHAP: list[dict[str, Any]] = [
    {"id": "thanh_vien", "ten": "Danh sách thành viên", "loai": "thanh_vien"},
    {"id": "luong", "ten": "Tiền lương/công", "loai": "don", "ma": "ThuLuong"},
    {"id": "sxkd", "ten": "SXKD", "loai": "don", "ma": "SXKD"},
    {"id": "nlt", "ten": "Nông-lâm-thủy sản", "loai": "nlt"},
    {"id": "khac", "ten": "Thu nhập khác", "loai": "don", "ma": "ThuKhac"},
]

NHOM_NGANH_4 = [
    ("ThuLuong", "Tiền lương/công"),
    ("Thu_SXKD", "SXKD"),
    ("Thu_NLT", "Nông-Lâm-Thủy"),
    ("ThuKhac", "Thu nhập khác"),
]

GEO_NGUONG_CHAP_NHAN_M = 500
GEO_NGUONG_CANH_BAO_M = 2000
CANH_BAO_GEO_VANG = "Vị trí hiện tại ở ngoài phạm vi địa bàn thôn/xóm. Hãy kiểm tra lại"
CANH_BAO_GEO_DO = "Cảnh báo: Tọa độ lệch quá lớn. Nghi vấn vị trí giả"

COL_HO = ["Huyen", "Xa", "DiaBan", "HoSo", "TenChuHo"]
SO_HO_NEN = 100
SO_HO_MAU = 40
COL_PHAN_LOAI = "PhanLoai"
PHAN_LOAI_MAU = "Mẫu"
PHAN_LOAI_NEN = "Dự phòng/Nền"

# Nhãn cột hiển thị tiếng Việt
NHAN_HIEN_THI = {
    "Huyen": "Huyện", "Xa": "Xã", "DiaBan": "Địa bàn", "HoSo": "Hộ số",
    "TenChuHo": "Tên chủ hộ", "MaDTV": "Mã ĐTV", "PhanLoai": "Phân loại",
    "HoTen": "Họ và tên", "TrangThai": "Trạng thái", "NgayPhanCong": "Ngày phân công",
    "ThuLuong": "Tiền lương, tiền công (nghìn đồng/tháng)",
    "ThuNN": "Thu nông nghiệp (nghìn đồng/tháng)",
    "ChiNN": "Chi phí sản xuất NN (nghìn đồng/tháng)",
    "ThuNNThuan": "Thu nhập thuần nông nghiệp",
    "ThuSXKD": "Thu nhập SXKD phi NN",
    "ThuKhac": "Thu nhập khác",
    "TongThuNhap": "Tổng thu nhập hộ (nghìn đồng/tháng)",
    "GPS_lat": "Vĩ độ GPS", "GPS_lng": "Kinh độ GPS",
    "DoChinhXac": "Độ chính xác (m)", "Xac_Thuc_GPS": "Xác thực GPS",
    "Sai_so": "Sai số GPS (m)", "Do_cao": "Độ cao (m)",
    "IP": "Địa chỉ IP", "MockGPS": "Nghi ngờ vị trí giả",
    "NgayNhap": "Ngày nhập phiếu", "Tong": "Tổng số hộ",
    "Xong": "Đã hoàn thành", "PhanTram": "Tỷ lệ hoàn thành (%)",
    "SoPhieu": "Số phiếu", "NganhKT": "Ngành kinh tế",
    "MatKhau": "Mật khẩu", "NhanKhauTT": "Số nhân khẩu thường trú",
    "DT_TrongTrot": "DT trồng trọt", "CP_TrongTrot": "CP trồng trọt",
    "Thu_TrongTrot": "Thuần trồng trọt", "DT_ChanNuoi": "DT chăn nuôi",
    "CP_ChanNuoi": "CP chăn nuôi", "Thu_ChanNuoi": "Thuần chăn nuôi",
    "DT_LamNghiep": "DT lâm nghiệp", "CP_LamNghiep": "CP lâm nghiệp",
    "Thu_LamNghiep": "Thuần lâm nghiệp", "DT_ThuySan": "DT thủy sản",
    "CP_ThuySan": "CP thủy sản", "Thu_ThuySan": "Thuần thủy sản",
    "DT_SXKD": "DT SXKD phi NN", "CP_SXKD": "CP SXKD phi NN",
    "Thu_SXKD": "Thuần SXKD phi NN", "ThuBQDauNguoi": "Thu nhập bình quân đầu người",
    "DiaChi": "Địa chỉ", "KhoangCachLech": "Khoảng cách lệch (m)",
    "MaDiaBan": "Mã địa bàn", "GhiChuViTri": "Ghi chú vị trí lệch",
}

# Ánh xạ tên cột linh hoạt từ các file Excel đầu vào
ANH_XA_TEN_COT: dict[str, str] = {
    "huyen": "Huyen", "tinh": "Huyen", "tinhthanh": "Huyen",
    "xa": "Xa", "xaphuong": "Xa", "phuongxa": "Xa",
    "diaban": "DiaBan", "diahinh": "DiaBan",
    "hoso": "HoSo", "soho": "HoSo", "hosodemau": "HoSo", "mahodiem": "HoSo",
    "tenchuho": "TenChuHo", "tenchu": "TenChuHo", "chuho": "TenChuHo",
    "madtv": "MaDTV", "phanloai": "PhanLoai", "phanloaiho": "PhanLoai",
    "madieutravien": "MaDTV", "hoten": "HoTen", "hovaten": "HoTen", "tendieutravien": "HoTen",
    "trangthai": "TrangThai", "ngayphancong": "NgayPhanCong",
    "thuluong": "ThuLuong", "thunn": "ThuNN", "chinn": "ChiNN", "thunnthuan": "ThuNNThuan",
    "thusxkd": "ThuSXKD", "thukhac": "ThuKhac", "tongthunhap": "TongThuNhap",
    "gpslat": "GPS_lat", "gpslong": "GPS_lng", "kinhdo": "GPS_lng", "vido": "GPS_lat",
    "dochinhxac": "DoChinhXac", "accuracy": "Sai_so", "saiso": "Sai_so",
    "docao": "Do_cao", "altitude": "Do_cao", "xacthucgps": "Xac_Thuc_GPS", "mockgps": "MockGPS",
    "ngaynhap": "NgayNhap", "nganhkt": "NganhKT", "nganhkinhte": "NganhKT",
    "matkhau": "MatKhau", "nhankhau": "NhanKhauTT", "nhankhautt": "NhanKhauTT", "sonhankhau": "NhanKhauTT",
    "thunhapbinhquandaunguoi": "ThuBQDauNguoi", "thubinhquandaunguoi": "ThuBQDauNguoi",
    "diachi": "DiaChi", "diachiho": "DiaChi", "diachicutru": "DiaChi",
    "khoangcachlech": "KhoangCachLech", "madiaaban": "MaDiaBan", "madiaban": "MaDiaBan", "madb": "MaDiaBan",
    "ghichuvitri": "GhiChuViTri", "ghichu": "GhiChuViTri", "lydolech": "GhiChuViTri",
}


# ---------------------------------------------------------------------------
# 3. CÁC HÀM TIỆN ÍCH DỮ LIỆU & CHUẨN HÓA TRƯỜNG THÔNG TIN
# ---------------------------------------------------------------------------
def _bo_dau_chuoi(s: str) -> str:
    """Loại bỏ dấu tiếng Việt, chuyển chữ thường, xóa khoảng trắng và gạch ngang."""
    s = str(s).strip().replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s_\-]+", "", s.lower())
    return s

def chuan_hoa_ten_cot_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ánh xạ đổi tên cột thống nhất cho DataFrame."""
    if df.empty:
        return df
    rename: dict[str, str] = {}
    for c in df.columns:
        key = _bo_dau_chuoi(str(c))
        if key in ANH_XA_TEN_COT:
            rename[c] = ANH_XA_TEN_COT[key]
    return df.rename(columns=rename)

def hien_thi_bang(df: pd.DataFrame) -> pd.DataFrame:
    """Phiên dịch cột kỹ thuật sang ngôn ngữ tiếng Việt biểu thị giao diện người dùng."""
    if df.empty:
        return df
    m = {c: NHAN_HIEN_THI.get(c, c) for c in df.columns}
    return df.rename(columns=m)

def chuan_hoa_gia_tri_hien_thi(val: Any) -> Any:
    """Tránh hiển thị các object NaN hay định dạng số numpy thô trên streamlit."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if hasattr(val, "item"):
        try:
            val = val.item()
        except Exception:
            pass
    if isinstance(val, float) and val == int(val):
        return int(val)
    if isinstance(val, (int, float, str, bool)):
        return val
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "<na>") else s

def df_an_toan_hien_thi(df: pd.DataFrame) -> pd.DataFrame:
    """Thiết lập sẵn kiểu dữ liệu và điền thay thế ô Null rỗng."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy().reset_index(drop=True)
    for c in out.columns:
        if c in ["MaDTV", "HoSo", "MaDiaBan", "DiaBan", "TenChuHo", "Xa"]:
            out[c] = out[c].fillna("").astype(str).replace({"nan": "", "None": ""})
        elif pd.api.types.is_numeric_dtype(out[c]):
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
        else:
            out[c] = out[c].fillna("").astype(str).replace({"nan": "", "None": ""})
    return out

def hien_dataframe_an_toan(df: pd.DataFrame, *, an_index: bool = True) -> None:
    """Vẽ bảng dữ liệu chuẩn đẹp trên luồng UI."""
    if df is None or df.empty:
        st.caption("Chưa có dữ liệu.")
        return
    hien = hien_thi_bang(df_an_toan_hien_thi(df))
    st.dataframe(hien, use_container_width=True, hide_index=an_index)

def doc_excel_danh_sach_ho(file, *, can_madtv: bool = False) -> tuple[pd.DataFrame | None, list[str]]:
    """
    Phân tích file Excel tải lên, kiểm tra các cột trường bắt buộc.
    Trả về Tuple (DataFrame, Danh sách các cột bị thiếu).
    """
    try:
        raw = pd.read_excel(file, dtype=str)
        raw.columns = [str(c).strip() for c in raw.columns]
        df = chuan_hoa_ten_cot_df(raw)
        
        if "ten_vi" not in st.session_state:
            st.session_state.ten_vi = {
                "Huyen": "Mã TKCS", "Xa": "Xã", "DiaBan": "Tên địa bàn",
                "MaDiaBan": "Mã địa bàn", "HoSo": "Hộ số", "TenChuHo": "Tên chủ hộ", "MaDTV": "Mã ĐTV"
            }
            
        cols_can = list(COL_HO) + (["MaDTV"] if can_madtv else [])
        thieu = [st.session_state.ten_vi.get(canon, canon) for canon in cols_can if canon not in df.columns]
        
        if thieu:
            return None, thieu
            
        out_cols = list(cols_can)
        if "DiaChi" in df.columns and "DiaChi" not in out_cols:
            out_cols.append("DiaChi")
        if "MaDiaBan" in df.columns and "MaDiaBan" not in out_cols:
            out_cols.append("MaDiaBan")
            
        return df[out_cols].fillna(""), []
    except Exception as e:
        return None, [f"Lỗi cú pháp file: {str(e)}"]

def danh_sach_ma_dtv_theo_thu_tu(series: pd.Series) -> list[str]:
    """Lấy danh sách mã ĐTV duy nhất không trùng lặp và giữ thứ tự lọc."""
    ket_qua: list[str] = []
    da_thay: set[str] = set()
    for v in series.astype(str).str.strip():
        if not v or v.lower() in ("nan", "none", ""):
            continue
        if v not in da_thay:
            da_thay.add(v)
            ket_qua.append(v)
    return ket_qua


# ---------------------------------------------------------------------------
# 4. KẾT NỐI TƯƠNG TÁC GOOGLE SHEETS (DÙNG GSREAD + SECRETS)
# ---------------------------------------------------------------------------
_GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def _gspread_client():
    """Tạo client dịch vụ kết nối Google API sử dụng Service Account JSON lưu trữ trong Secrets."""
    json_key = json.loads(st.secrets["gcp_service_account"]["json"])
    creds = Credentials.from_service_account_info(json_key, scopes=_GSHEETS_SCOPES)
    return gspread.authorize(creds)

def _open_spreadsheet():
    """Mở file bảng tính quy mô tổng thông qua liên kết URL định nghĩa trong secrets."""
    gc = _gspread_client()
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return gc.open_by_url(url)

@st.cache_data(ttl=60)
def _read_sheet_cached(name: str) -> pd.DataFrame:
    """Hàm trung gian cache việc truy xuất đọc dữ liệu từ Cloud."""
    sh = _open_spreadsheet()
    ws = sh.worksheet(name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return chuan_hoa_ten_cot_df(df)

def read_sheet(name: str, *, silent: bool = False) -> pd.DataFrame:
    """Đọc dữ liệu từ 1 sheet trong Google Spreadsheet."""
    try:
        return _read_sheet_cached(name)
    except Exception as e:
        if not silent:
            st.error(f"Lỗi đọc sheet {name} từ Google Sheets: {e}")
        return pd.DataFrame()

def update_sheet(sheet_name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True) -> bool:
    """Ghi đè hoàn toàn nội dung dữ liệu của 1 sheet."""
    try:
        sh = _open_spreadsheet()
        ws = sh.worksheet(sheet_name)
        ws.clear()
        if df.empty:
            ws.update([df.columns.values.tolist()])
        else:
            payload = [df.columns.values.tolist()] + df.fillna("").values.tolist()
            ws.update(payload)
        _read_sheet_cached.clear()  # Xoá cache ngay sau khi ghi mới
        if thong_bao and not silent:
            st.success(f"Đã lưu thành công {len(df)} dòng vào bảng tính «{sheet_name}».")
        return True
    except Exception as e:
        if not silent:
            st.error(f"Lỗi ghi sheet {sheet_name}: {e}")
        return False

def write_sheet_replace(name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True) -> bool:
    """Bí danh thay thế tương thích."""
    return update_sheet(name, df, silent=silent, thong_bao=thong_bao)

def append_ket_qua(row: dict[str, Any], *, silent: bool = True) -> bool:
    """Nạp thêm 1 phiếu ghi nhận vừa khảo sát đồng bộ lên dòng kế tiếp."""
    try:
        df_old = read_sheet(SHEETS["ket_qua"], silent=silent)
        df_new = pd.DataFrame([row])
        out = df_new if df_old.empty else pd.concat([df_old, df_new], ignore_index=True)
        return write_sheet_replace(SHEETS["ket_qua"], out, silent=silent, thong_bao=not silent)
    except Exception as e:
        if not silent:
            st.error(f"Lỗi ghi thêm kết quả: {e}")
        return False


# ---------------------------------------------------------------------------
# 5. CHIẾN LƯỢC TOÁN HỌC - TÍNH TOÁN THU NHẬP CHỈ SỐ NỘI BỘ
# ---------------------------------------------------------------------------
def so_hoa(gia_tri: Any) -> float:
    """Ép kiểu đầu vào sang số thực nổi float an toàn."""
    val = pd.to_numeric(gia_tri, errors="coerce")
    if isinstance(val, pd.Series):
        val = val.fillna(0).iloc[0] if len(val) else 0
    return float(val) if not pd.isna(val) else 0.0

def thu_thuan(dt: float, cp: float) -> float:
    """Công thức cốt lõi: Thuần = Doanh thu - Chi phí (Min bằng 0)."""
    return max(0.0, so_hoa(dt) - so_hoa(cp))

def loi_chi_phi_vuot_thu(chi_phi: float, doanh_thu: float) -> bool:
    """Điểm cảnh báo bất thường chi phí vượt doanh thu."""
    return so_hoa(chi_phi) > so_hoa(doanh_thu)

def loi_tong_khong_khop(tong_nho: float, tong_lon: float, *, eps: float = 0.5) -> bool:
    """Sai số kiểm tra đối khớp tổng cục và thành phần chi tiết."""
    return abs(so_hoa(tong_nho) - so_hoa(tong_lon)) > eps

def hien_loi_validation(noi_dung: str) -> None:
    st.markdown(f'<p class="input-loi-do">{noi_dung}</p>', unsafe_allow_html=True)

def _key_hoat_dong(nhom_id: str, ho_so: str, form_ver: int) -> str:
    return f"hd_{nhom_id}_{ho_so}_{form_ver}"

def _key_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> str:
    return f"sp_ct_{ma_lv}_{ho_so}_{form_ver}"

def hien_canh_bao_khong_tinh() -> None:
    st.caption(f"⚠️ Lưu ý QĐ 1099: {CANH_BAO_KHONG_TINH}")


# ---------------------------------------------------------------------------
# 6. QUẢN LÝ TÀI KHOẢN ĐTV (AUTHENTICATION)
# ---------------------------------------------------------------------------
def read_accounts() -> pd.DataFrame:
    df = read_sheet(SHEETS["account"])
    if df.empty:
        return pd.DataFrame(columns=["MaDTV", "MatKhau", "HoTen", "TrangThai"])
    for c in ("MaDTV", "MatKhau", "HoTen", "TrangThai"):
        if c not in df.columns:
            df[c] = ""
    return df

def write_accounts(df: pd.DataFrame) -> bool:
    return write_sheet_replace(SHEETS["account"], df)

def dong_bo_account_tu_ma_dtv(danh_sach_ma: list[str]) -> None:
    """Cấp phát tài khoản tự động cho ĐTV mới nạp với mật khẩu khởi tạo bằng mã ĐTV."""
    df = read_accounts()
    co_san = set(df["MaDTV"].astype(str).str.strip()) if not df.empty else set()
    rows = []
    for ma in danh_sach_ma:
        ma = str(ma).strip()
        if not ma or ma in co_san or ma.upper() == ADMIN_MA:
            continue
        rows.append({
            "MaDTV": ma,
            "MatKhau": ma,
            "HoTen": f"Điều tra viên {ma}",
            "TrangThai": TRANG_THAI_MK_CHUA
        })
    if rows:
        write_accounts(pd.concat([df, pd.DataFrame(rows)], ignore_index=True))

def xac_thuc_dang_nhap(ma_dtv: str, mat_khau: str) -> tuple[bool, str, pd.Series | None]:
    ma = str(ma_dtv).strip()
    df = read_accounts()
    if df.empty:
        return False, "Hệ thống tài khoản trống.", None
    row = df[df["MaDTV"].astype(str).str.strip() == ma]
    if row.empty:
        return False, f"Mã ĐTV «{ma}» không tìm thấy trên hệ thống.", None
    r = row.iloc[0]
    if str(r.get("MatKhau", "")).strip() != str(mat_khau).strip():
        return False, "Mật khẩu nhập chưa đúng.", None
    return True, "", r

def cap_nhat_mat_khau(ma_dtv: str, mat_khau_moi: str) -> bool:
    df = read_accounts()
    mask = df["MaDTV"].astype(str).str.strip() == str(ma_dtv).strip()
    if not mask.any():
        return False
    df.loc[mask, "MatKhau"] = str(mat_khau_moi).strip()
    df.loc[mask, "TrangThai"] = TRANG_THAI_MK_DA
    return write_accounts(df)

def reset_mat_khau_dtv(ma_dtv: str) -> bool:
    df = read_accounts()
    mask = df["MaDTV"].astype(str).str.strip() == str(ma_dtv).strip()
    if not mask.any():
        return False
    ma = str(ma_dtv).strip()
    df.loc[mask, "MatKhau"] = ma
    df.loc[mask, "TrangThai"] = TRANG_THAI_MK_CHUA
    return write_accounts(df)


# ---------------------------------------------------------------------------
# 7. ROUTINE - LỰA CHỌN MẪU KHẢO SÁT HỆ THỐNG (CHỌN MẪU HỆ THỐNG r, k)
# ---------------------------------------------------------------------------
def lay_danh_sach_nen(df: pd.DataFrame, ma_dtv: str) -> pd.DataFrame:
    """Lọc danh sách hộ được phân bổ gán với Mã điều tra viên hiện hành."""
    if df.empty or "MaDTV" not in df.columns:
        return pd.DataFrame()
    return df[df["MaDTV"].astype(str).str.strip() == str(ma_dtv).strip()].copy().reset_index(drop=True)

def chon_chi_so_mau_tu_nen(n_nen: int, k: int, r: int, so_luong_can_chon: int = 40) -> list[int]:
    """
    Thực hiện thuật toán chọn mẫu hệ thống ngẫu nhiên: bước nhảy k, vị trí bắt đầu r.
    Luôn đảm bảo chuẩn chọn đủ 40 hộ mẫu đề ra.
    """
    if n_nen <= 0:
        return []
    picked, seen = [], set()
    pos = r - 1
    while pos < n_nen and len(picked) < so_luong_can_chon:
        if pos not in seen:
            picked.append(pos)
            seen.add(pos)
        pos += k
    if len(picked) < so_luong_can_chon:
        for i in range(n_nen):
            if len(picked) >= so_luong_can_chon:
                break
            if i not in seen:
                picked.append(i)
                seen.add(i)
    return picked

def gan_phan_loai_ho(df_nen: pd.DataFrame, chi_so_mau: list[int]) -> pd.DataFrame:
    """Gán trực tiếp cột Phân loại: Mẫu so với Dự phòng."""
    out = df_nen.reset_index(drop=True).copy()
    out[COL_PHAN_LOAI] = PHAN_LOAI_NEN
    for i in chi_so_mau:
        if 0 <= i < len(out):
            out.loc[i, COL_PHAN_LOAI] = PHAN_LOAI_MAU
    return out

def cap_nhat_danh_sach_ho_theo_dtv(df_all: pd.DataFrame, ma_dtv: str, df_nen_da_phan_loai: pd.DataFrame) -> pd.DataFrame:
    """Thay thế cập nhật thông tin hộ mới phân mẫu vào trong danh sách gốc của Sheets."""
    ma = str(ma_dtv).strip()
    mask_khac = df_all["MaDTV"].astype(str).str.strip() != ma
    phan_con_lai = df_all[mask_khac]
    df_moi = df_nen_da_phan_loai.copy()
    df_moi["MaDTV"] = ma
    return pd.concat([phan_con_lai, df_moi], ignore_index=True)

def ho_mau_can_dieu_tra(df_ho: pd.DataFrame) -> pd.DataFrame:
    """Lấy riêng tệp hộ đánh dấu là 'Mẫu' dùng để hiển thị trên form điều tra viên."""
    if df_ho.empty or COL_PHAN_LOAI not in df_ho.columns:
        return df_ho
    return df_ho[df_ho[COL_PHAN_LOAI].astype(str).str.strip() == PHAN_LOAI_MAU].copy()


# ---------------------------------------------------------------------------
# 8. BUSINESS COMPONENT: FORM NHẬP CHI TIẾT
# ---------------------------------------------------------------------------
def lay_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> list[dict[str, Any]]:
    return list(st.session_state.get(_key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver), []))

def tong_hop_chi_tiet_linh_vuc(danh_sach: list[dict[str, Any]]) -> tuple[float, float, float]:
    """Tổng hợp Doanh thu, Chi phí và tính thuần của 1 danh mục nông lâm thủy sản."""
    dt = cp = 0.0
    for dong in danh_sach:
        gb, td, g, ta, ck = [so_hoa(dong.get(o, 0)) for o in O_NHAP_SAN_PHAM]
        dt += max(0.0, gb - td)
        cp += g + ta + ck
    return dt, cp, thu_thuan(dt, cp)

def nhap_thanh_vien_ho(ho_so: str, form_ver: int) -> None:
    key = f"ds_tv_{ho_so}_{form_ver}"
    if key not in st.session_state:
        st.session_state[key] = []
    
    st.markdown("<p style='font-weight: 600; color: #1e293b; margin-top: 10px; margin-bottom: -5px;'>➕ Thêm mới nhân khẩu thường trú:</p>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2.5, 1.5, 1])
    with c1:
        ten = st.text_input("Họ tên thành viên", key=f"tv_ten_{ho_so}_{form_ver}", placeholder="Ví dụ: Nguyễn Văn A", label_visibility="collapsed")
    with c2:
        qh = st.selectbox("Quan hệ chủ hộ", ["Chủ hộ", "Vợ/chồng", "Con", "Cha/mẹ", "Khác"], key=f"tv_qh_{ho_so}_{form_ver}", label_visibility="collapsed")
    with c3:
        them_tv = st.button("➕ Thêm", key=f"tv_them_{ho_so}_{form_ver}", use_container_width=True, type="primary")
        
    if them_tv:
        if ten.strip():
            ds = list(st.session_state.get(key, []))
            # Kiểm tra quan hệ chủ hộ trùng lặp
            if qh == "Chủ hộ" and any(item.get("Quan hệ") == "Chủ hộ" for item in ds):
                st.error("⚠️ Hộ gia đình chỉ được phép thiết lập duy nhất một vị trí Chủ hộ.")
            else:
                ds.append({"Họ tên": ten.strip().title(), "Quan hệ": qh})
                st.session_state[key] = ds
                st.toast(f"Đã thêm thành viên «{ten.strip().title()}».", icon="✅")
                st.rerun()
                
    ds_hien = st.session_state.get(key, [])
    if ds_hien:
        st.markdown("<p style='font-weight: 700; color: #0f172a; margin-top: 15px; margin-bottom: 5px;'>👥 Danh sách nhân khẩu thực tế ăn ở tại hộ (QĐ 1099):</p>", unsafe_allow_html=True)
        # Tạo bảng hiển thị thành viên tinh tế có nút xóa tương tác
        cols_h = st.columns([3, 2, 1])
        cols_h[0].markdown("<b style='color:#475569;'>Họ và tên thành viên</b>", unsafe_allow_html=True)
        cols_h[1].markdown("<b style='color:#475569;'>Quan hệ với chủ hộ</b>", unsafe_allow_html=True)
        cols_h[2].markdown("<p style='text-align: center; margin: 0; font-weight: bold; color:#475569;'>Hành động</p>", unsafe_allow_html=True)
        st.markdown("<div style='border-bottom: 2px solid #cbd5e1; margin: 4px 0 10px 0;'></div>", unsafe_allow_html=True)
        
        for tv_idx, tv_item in enumerate(ds_hien):
            cols_r = st.columns([3, 2, 1])
            cols_r[0].write(f"👤 **{tv_item['Họ tên']}**")
            cols_r[1].write(f"🔹 {tv_item['Quan hệ']}")
            if cols_r[2].button("🗑️ Xóa", key=f"del_tv_{tv_idx}_{ho_so}_{form_ver}", use_container_width=True, help=f"Gỡ bỏ thành viên {tv_item['Họ tên']}"):
                new_ds = [item for i, item in enumerate(ds_hien) if i != tv_idx]
                st.session_state[key] = new_ds
                st.toast(f"Đã gỡ bỏ thành viên «{tv_item['Họ tên']}»", icon="🗑️")
                st.rerun()

def nhap_muc_don_doc(ma: str, ten: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"<p style='font-weight: 700; color: #1e3a8a; font-size: 15px; margin-top: 15px;'>📋 {ten}</p>", unsafe_allow_html=True)
    k_dt, k_cp = f"dt_{ma}_{ho_so}_{form_ver}", f"cp_{ma}_{ho_so}_{form_ver}"
    
    # Theo quy định QĐ 1099, tiền lương công và thu nhập khác chỉ hạch toán doanh thu và chi phí mặc định bằng 0
    co_chi_phi = (ma not in ["ThuLuong", "ThuKhac"])
    
    if co_chi_phi:
        c1, c2 = st.columns(2)
        with c1:
            dt = st.number_input("Doanh thu sản xuất kinh doanh (nghìn đồng/tháng)", min_value=0.0, value=float(so_hoa(st.session_state.get(k_dt, 0))), step=50.0, key=k_dt)
        with c2:
            cp = st.number_input("Chi phí vận hành và quản lý (nghìn đồng/tháng)", min_value=0.0, value=float(so_hoa(st.session_state.get(k_cp, 0))), step=50.0, key=k_cp)
            
        if loi_chi_phi_vuot_thu(cp, dt):
            hien_loi_validation(f"⚠️ Cảnh báo QĐ 1099: Chi phí sản xuất ({cp:,.0f}) vượt doanh thu ({dt:,.0f}). Vui lòng xác thực lại.")
        st.markdown(f"<div style='text-align: right; color: #0284c7; font-weight: 700; font-size:14px; margin-top: 5px;'>Thu nhập thuần tích lũy: {thu_thuan(dt, cp):,.0f} nghìn đồng/tháng</div>", unsafe_allow_html=True)
    else:
        dt = st.number_input("Khoản thu nhập nhận được thực tế (nghìn đồng/tháng)", min_value=0.0, value=float(so_hoa(st.session_state.get(k_dt, 0))), step=50.0, key=k_dt)
        st.session_state[k_cp] = 0.0 # Chi phí tiền lương bằng 0
        st.markdown(f"<div style='text-align: right; color: #0284c7; font-weight: 700; font-size:14px; margin-top: 5px;'>Thu nhập thuần tích lũy: {dt:,.0f} nghìn đồng/tháng</div>", unsafe_allow_html=True)

def nhap_linh_vuc_co_san_pham(ma_lv: str, ten_lv: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"<p style='font-weight: 700; color: #0369a1; font-size: 15px; margin-top: 15px;'>🌾 {ten_lv} (Danh sách cây trồng, vật nuôi khảo sát)</p>", unsafe_allow_html=True)
    
    # Grid nhập liệu tinh gọn ngang như biểu mẫu Excel QĐ 1099 thực tế
    with st.container():
        st.markdown("<div style='background-color: #f8fafc; padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        st.markdown("<span style='font-size:12px; font-weight:700; color:#475569;'>✍️ NHẬP DÒNG SẢN PHẨM MỚI</span>", unsafe_allow_html=True)
        
        c_grid = st.columns([2, 2, 2, 2])
        with c_grid[0]:
            sp = st.selectbox("Chọn loại sản phẩm", SAN_PHAM_LINH_VUC.get(ma_lv, ["Khác"]), key=f"sp_sel_{ma_lv}_{ho_so}_{form_ver}")
        with c_grid[1]:
            # Nhóm 1: Doanh thu
            st.markdown("<span style='font-size:11.5px; font-weight:600; color:#0369a1;'>💰 Doanh số / Thu sản phẩm</span>", unsafe_allow_html=True)
            val_gb = st.number_input("1. Giá trị bán ra (nghìnđ)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_Giá bán_{sp}_{ho_so}_{form_ver}")
            val_td = st.number_input("2. Giá trị tự dùng (nghìnđ)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_Tự dùng_{sp}_{ho_so}_{form_ver}")
        with c_grid[2]:
            # Nhóm 2: Chi phí chính
            st.markdown("<span style='font-size:11.5px; font-weight:600; color:#b45309;'>💸 Chi phí trực tiếp</span>", unsafe_allow_html=True)
            val_g = st.number_input("3. Chi giống (nghìnđ)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_Giống_{sp}_{ho_so}_{form_ver}")
            val_ta = st.number_input("4. Chi thức ăn/Phân (nghìnđ)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_Thức ăn_{sp}_{ho_so}_{form_ver}")
        with c_grid[3]:
            # Nhóm 3: Chi phí phụ & Hoàn tất
            st.markdown("<span style='font-size:11.5px; font-weight:600; color:#64748b;'>🛠️ Phí vận hành</span>", unsafe_allow_html=True)
            val_ck = st.number_input("5. Chi khác (nghìnđ)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_Chi khác_{sp}_{ho_so}_{form_ver}")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            them_sp = st.button("➕ Thêm dòng", key=f"them_sp_{ma_lv}_{ho_so}_{form_ver}", use_container_width=True, type="primary")
            
        st.markdown("</div>", unsafe_allow_html=True)
        
    key = _key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
    ds = list(st.session_state.get(key, []))
    
    if them_sp:
        # Kiểm tra trùng sản phẩm để tránh hỗn loạn số liệu
        exists_idx = next((i for i, d in enumerate(ds) if d.get("Sản phẩm") == sp), None)
        dong = {"Sản phẩm": sp}
        for o in O_NHAP_SAN_PHAM:
            dong[o] = so_hoa(st.session_state.get(f"{ma_lv}_{o}_{sp}_{ho_so}_{form_ver}", 0))
            
        dt_d, cp_d, th_d = tong_hop_chi_tiet_linh_vuc([dong])
        if loi_chi_phi_vuot_thu(cp_d, dt_d):
            st.error(f"⚠️ Không thể lưu: Chi phí sản phẩm ({cp_d:,.0f}) lớn hơn doanh thu ({dt_d:,.0f}).")
        else:
            dong.update({"Doanh thu": dt_d, "Chi phí": cp_d, "Thu nhập thuần": th_d})
            if exists_idx is not None:
                ds[exists_idx] = dong # Ghi đè cập nhật số liệu
                st.toast(f"Đã cập nhật lại số liệu sản phẩm «{sp}».", icon="📝")
            else:
                ds.append(dong) # Thêm mới
                st.toast(f"Đã thêm sản phẩm «{sp}» vào danh sách thành công.", icon="✅")
                
            st.session_state[key] = ds
            st.rerun()
            
    ds_hien = lay_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
    if ds_hien:
        st.markdown(f"<p style='color:#0d9488; font-weight:700; margin-bottom:5px;'>📊 Bảng chiết tính thu nhập từ hoạt động {ten_lv}:</p>", unsafe_allow_html=True)
        
        # Tiêu đề bảng của Quy định 1099
        cols_h = st.columns([2.5, 1.5, 1.5, 2, 1.1])
        with cols_h[0]:
            st.markdown("<b style='color:#334155;'>Tên nông sản / vật nuôi</b>", unsafe_allow_html=True)
        with cols_h[1]:
            st.markdown("<p style='text-align: right; font-weight: bold; color:#0d9488; margin: 0;'>Doanh thu (1)</p>", unsafe_allow_html=True)
        with cols_h[2]:
            st.markdown("<p style='text-align: right; font-weight: bold; color:#b45309; margin: 0;'>Chi phí (2)</p>", unsafe_allow_html=True)
        with cols_h[3]:
            st.markdown("<p style='text-align: right; font-weight: bold; color:#0284c7; margin: 0;'>Thuần (3 = 1 - 2)</p>", unsafe_allow_html=True)
        with cols_h[4]:
            st.markdown("<p style='text-align: center; font-weight: bold; color:#475569; margin: 0;'>Xóa dòng</p>", unsafe_allow_html=True)
            
        st.markdown("<div style='border-bottom: 2px solid #cbd5e1; margin: 4px 0 10px 0;'></div>", unsafe_allow_html=True)
        
        for d_idx, d_item in enumerate(ds_hien):
            cols_r = st.columns([2.5, 1.5, 1.5, 2, 1.1])
            with cols_r[0]:
                st.write(f"🌱 **{d_item['Sản phẩm']}**")
            with cols_r[1]:
                st.markdown(f"<p style='text-align: right; margin: 0;'>{d_item.get('Doanh thu', 0):,.0f}</p>", unsafe_allow_html=True)
            with cols_r[2]:
                st.markdown(f"<p style='text-align: right; margin: 0;'>{d_item.get('Chi phí', 0):,.0f}</p>", unsafe_allow_html=True)
            with cols_r[3]:
                st.markdown(f"<p style='text-align: right; font-weight:700; color:#0284c7; margin: 0;'>{d_item.get('Thu nhập thuần', 0):,.0f}</p>", unsafe_allow_html=True)
            with cols_r[4]:
                if st.button("❌ Gỡ", key=f"del_sp_{ma_lv}_{d_idx}_{ho_so}_{form_ver}", use_container_width=True, help=f"Gỡ bỏ {d_item['Sản phẩm']}"):
                    new_ds = [item for i, item in enumerate(ds_hien) if i != d_idx]
                    st.session_state[key] = new_ds
                    st.toast(f"Đã gỡ bỏ nông sản «{d_item['Sản phẩm']}»", icon="🗑️")
                    st.rerun()
                    
            # Hiển thị chi tiết cơ cấu chiết tính theo sát quy trình 1099
            ct_ban = d_item.get("Giá bán", 0)
            ct_dung = d_item.get("Tự dùng", 0)
            ct_giong = d_item.get("Giống", 0)
            ct_an = d_item.get("Thức ăn", 0)
            ct_khac = d_item.get("Chi khác", 0)
            st.markdown(
                f"<div style='font-size: 11px; color:#64748b; margin-top:-8px; padding-left:10px; margin-bottom:10px;'>"
                f"↳ [Doanh số bán: {ct_ban:,.0f} | Tự tiêu thụ: {ct_dung:,.0f}] ⸎ [Giống/Cây giống: {ct_giong:,.0f} | Thức ăn/Phân: {ct_an:,.0f} | Chi phụ: {ct_khac:,.0f}]"
                f"</div>",
                unsafe_allow_html=True
            )

def nhap_lieu_5_nhom(ho_so: str, form_ver: int) -> None:
    """Quy trình trình bày bộ câu hỏi điều tra 5 nhóm tài chính chuẩn chỉ QĐ 1099."""
    st.caption("⚠️ Đơn vị tiền tệ hạch toán chính xác: **nghìn đồng/tháng**.")
    
    for nhom in NHOM_NHAP:
        with card_container(nhom["ten"]):
            if nhom["id"] == "thanh_vien":
                st.markdown("<b style='color:#0f172a; font-size:14px;'>👥 THÔNG TIN NHÂN KHẨU THƯỜNG TRÚ</b>", unsafe_allow_html=True)
                st.info("💡 Hãy cập nhật chính xác danh sách các thành viên thực tế ăn ở và sinh hoạt chung tại hộ từ 6 tháng trở lên.")
                nhap_thanh_vien_ho(ho_so, form_ver)
            else:
                # Đặt các câu hỏi khảo sát chuẩn hóa hành chính QĐ 1099 của Tổng cục Thống Kê
                if nhom["id"] == "luong":
                    cau_hoi = "💬 1. Trong 12 tháng qua, có thành viên nào trong hộ nhận được tiền lương, tiền công, phụ cấp hoặc tiền thưởng từ công việc làm thuê không?"
                elif nhom["id"] == "sxkd":
                    cau_hoi = "💬 2. Trong 12 tháng qua, hộ gia đình có phát sinh doanh thu từ các hoạt động sản xuất kinh doanh phi nông nghiệp hoặc dịch vụ tự doanh không?"
                elif nhom["id"] == "nlt":
                    cau_hoi = "💬 3. Trong 12 tháng qua, hộ gia đình có tiến hành các hoạt động trồng trọt, chăn nuôi, lâm nghiệp hoặc nuôi trồng thủy sản không?"
                else: # khac
                    cau_hoi = "💬 4. Trong 12 tháng qua, hộ gia đình có nhận khoản thu nhập nào khác như lãi tiết kiệm, kiều hối, trợ cấp, hưu trí, quà biếu tặng... không?"
                    
                co_hd = st.radio(cau_hoi, ["Có phát sinh", "Không phát sinh"], horizontal=True, key=_key_hoat_dong(nhom["id"], ho_so, form_ver)) == "Có phát sinh"
                
                if not co_hd:
                    st.caption("✅ Ghi nhận không có thu nhập ở nguồn này (Báo cáo: 0 đồng/tháng).")
                    continue
                
                if nhom["loai"] == "don":
                    muc = map_chi_tieu.get(nhom["ma"])
                    if muc:
                        nhap_muc_don_doc(muc["ma"], muc["ten"], ho_so, form_ver)
                elif nhom["loai"] == "nlt":
                    muc_nlt = [m for m in CHI_TIEU_PHAN_B if m["loai"] == "linh_vuc_sp"]
                    for i, muc in enumerate(muc_nlt):
                        nhap_linh_vuc_co_san_pham(muc["ma"], muc["ten"], ho_so, form_ver)
                        if i < len(muc_nlt) - 1:
                            st.markdown("<div style='margin: 15px 0; border-top: 1px dashed #e2e8f0;'></div>", unsafe_allow_html=True)

def tong_hop_du_lieu_phieu(ho_so: str, form_ver: int) -> dict[str, Any]:
    """Tổng hợp toàn bộ chỉ số nháp ĐTV nhập của 1 Hộ trước ghi lưu."""
    ket = {
        "thu_luong": 0.0, "thu_khac": 0.0, "dt_sxkd": 0.0, "cp_sxkd": 0.0, "thu_sxkd": 0.0,
        "linh_vuc": {}, "tong_7": {}, "hang_bang": []
    }
    
    for muc in CHI_TIEU_PHAN_B:
        ma, loai = muc["ma"], muc["loai"]
        nhom_id = "nlt" if loai == "linh_vuc_sp" else ("luong" if loai == "luong" else ("sxkd" if loai == "sxkd" else "khac"))
        
        status = st.session_state.get(_key_hoat_dong(nhom_id, ho_so, form_ver))
        if status not in ["Có", "Có phát sinh"]:
            continue
            
        if loai in ("luong", "sxkd", "khac"):
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            if loai == "luong":
                ket["thu_luong"] = thuan
                ket["tong_7"]["ThuLuong"] = thuan
            elif loai == "sxkd":
                ket["dt_sxkd"], ket["cp_sxkd"], ket["thu_sxkd"] = dt, cp, thuan
                ket["tong_7"]["Thu_SXKD"] = thuan
            else:
                ket["thu_khac"] = thuan
                ket["tong_7"]["ThuKhac"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
            
        elif loai == "linh_vuc_sp":
            ds = lay_chi_tiet_linh_vuc(ma, ho_so, form_ver)
            dt, cp, thuan = tong_hop_chi_tiet_linh_vuc(ds)
            ket["linh_vuc"][ma] = (dt, cp, thuan)
            ket["tong_7"][f"Thu_{ma}"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
            
            for d in ds:
                ket["hang_bang"].append({
                    "Tên chỉ tiêu": f"  └ {d.get('Sản phẩm', '')}",
                    "Doanh thu": d.get("Doanh thu", 0),
                    "Chi phí": d.get("Chi phí", 0),
                    "Thu nhập thuần": d.get("Thu nhập thuần", 0)
                })
                
    return ket

def tinh_tong_7_nguon(du_lieu: dict[str, float]) -> float:
    return sum(float(du_lieu.get(k, 0) or 0) for k, _ in BAO_CAO_7_NGUON)

def kiem_tra_validation_phieu(ho_so: str, form_ver: int) -> tuple[bool, list[str]]:
    """Xác thực lỗi cấu trúc số liệu trước khi cho phép bấm nút Lưu phiếu."""
    loi = []
    dl = tong_hop_du_lieu_phieu(ho_so, form_ver)
    for muc in CHI_TIEU_PHAN_B:
        ma, loai = muc["ma"], muc["loai"]
        nhom_id = "nlt" if loai == "linh_vuc_sp" else ("luong" if loai == "luong" else ("sxkd" if loai == "sxkd" else "khac"))
        status_chk = st.session_state.get(_key_hoat_dong(nhom_id, ho_so, form_ver))
        if status_chk not in ["Có", "Có phát sinh"]:
            continue
        if loai in ("luong", "sxkd", "khac"):
            dt, cp = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0)), so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            if loi_chi_phi_vuot_thu(cp, dt):
                loi.append(f"Mục {muc['ten']} có chi phí ({cp:,.0f}) đang khai thác lớn hơn doanh thu ({dt:,.0f}).")
        elif loai == "linh_vuc_sp":
            for d in lay_chi_tiet_linh_vuc(ma, ho_so, form_ver):
                if loi_chi_phi_vuot_thu(d.get("Chi phí", 0), d.get("Doanh thu", 0)):
                    loi.append(f"Mục {muc['ten']} - Sản phẩm {d.get('Sản phẩm')}: Chi phí vượt doanh thu.")
    return len(loi) == 0, loi


# ---------------------------------------------------------------------------
# 9. ĐỊA CHỈ IP, GPS & GEOFENCING XÁC THỰC LỆCH VỊ TRÍ
# ---------------------------------------------------------------------------
def get_client_ip() -> str:
    try:
        import requests
        return requests.get("https://api.ipify.org?format=json", timeout=3).json().get("ip", "không xác định")
    except Exception:
        return "không xác định"

def tinh_khoang_cach_gps_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    if geodesic is None:
        return 0.0
    return float(geodesic((lat1, lng1), (lat2, lng2)).meters)

def phan_tich_geofence(ho: pd.Series, loc: dict | None) -> dict[str, Any]:
    """Kiểm tra khoảng cách giữa GPS người điều tra và điểm mốc tọa độ trung tâm xã phường."""
    ma_db = str(ho.get("MaDiaBan", ho.get("DiaBan", ""))).strip()
    ket = {"khoang_cach_m": None, "muc": "ok", "canh_bao": "", "ma_dia_ban": ma_db, "bat_buoc_ghi_chu": False}
    if not loc or not Nominatim:
        return ket
    try:
        lat_gps, lng_gps = float(loc["latitude"]), float(loc["longitude"])
        geo_locator = Nominatim(user_agent="pmdtv_app_2026", timeout=5)
        truy_van = f"{ma_db}, {ho.get('Xa')}, {ho.get('Huyen')}, Việt Nam"
        v = geo_locator.geocode(truy_van)
        if v:
            kc = tinh_khoang_cach_gps_m(lat_gps, lng_gps, v.latitude, v.longitude)
            ket["khoang_cach_m"] = kc
            if kc >= GEO_NGUONG_CANH_BAO_M:
                ket["muc"] = "do"
                ket["canh_bao"] = CANH_BAO_GEO_DO
                ket["bat_buoc_ghi_chu"] = True
            elif kc >= GEO_NGUONG_CHAP_NHAN_M:
                ket["muc"] = "vang"
                ket["canh_bao"] = CANH_BAO_GEO_VANG
    except Exception:
        pass
    return ket

def phan_tich_vi_tri_gps(loc: dict | None) -> dict[str, Any]:
    """Phát hiện nghi vấn sử dụng phần mềm fake GPS giả lập."""
    ket = {"canh_bao_dtv": "", "xac_thuc_gps": "Hợp lệ", "to_do_do": False, "sai_so": None, "do_cao": None}
    if not loc:
        ket["xac_thuc_gps"] = "GIẢ - Không lấy được tọa độ"
        ket["to_do_do"] = True
        return ket
    acc, alt = loc.get("accuracy"), loc.get("altitude")
    ket["sai_so"] = float(acc) if acc else None
    if loc.get("mocked") or (acc and float(acc) > 500):
        ket["xac_thuc_gps"] = "GIẢ - Phát hiện Fake GPS"
        ket["to_do_do"] = True
    return ket

def tao_dong_ket_qua_qd1099(
    *, ma_dtv: str, ho: pd.Series, nhan_khau: int, thu_luong: float,
    linh_vuc: dict[str, tuple[float, float, float]], dt_sxkd: float, cp_sxkd: float,
    thu_khac: float, loc: dict | None, gps: dict, geo: dict, ghi_chu_vi_tri: str
) -> dict[str, Any]:
    """Ghi nhận xuất bản file JSON phiếu của hộ tương thích biểu mẫu QĐ 1099 lưu trữ."""
    row = {
        "MaDTV": ma_dtv,
        "HoSo": str(ho.get("HoSo")),
        "MaTKCS": str(ho.get("Huyen")),
        "Xa": str(ho.get("Xa")),
        "DiaBan": str(ho.get("DiaBan")),
        "MaDiaBan": geo.get("ma_dia_ban"),
        "TenChuHo": str(ho.get("TenChuHo")),
        "NhanKhauTT": nhan_khau,
        "ThuLuong": thu_luong,
        "ThuKhac": thu_khac
    }
    row["GPS_lat"] = loc.get("latitude") if loc else ""
    row["GPS_lng"] = loc.get("longitude") if loc else ""
    row.update({
        "DoChinhXac": gps.get("sai_so"),
        "Sai_so": gps.get("sai_so"),
        "Do_cao": gps.get("do_cao"),
        "Xac_Thuc_GPS": gps.get("xac_thuc_gps"),
        "IP": get_client_ip(),
        "MockGPS": "Có" if gps.get("to_do_do") else "Không",
        "NgayNhap": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if geo:
        row.update({
            "KhoangCachLech": round(geo["khoang_cach_m"], 1) if geo["khoang_cach_m"] else "",
            "GhiChuViTri": ghi_chu_vi_tri,
            "DiaChi": ""
        })
    tong_7 = {"ThuLuong": thu_luong, "ThuKhac": thu_khac}
    for c, _ in LINH_VUC_NLN_TS:
        dt, cp, th = linh_vuc.get(c, (0.0, 0.0, 0.0))
        row.update({f"DT_{c}": dt, f"CP_{c}": cp, f"Thu_{c}": th})
        tong_7[f"Thu_{c}"] = th
        
    th_sxkd = thu_thuan(dt_sxkd, cp_sxkd)
    row.update({"DT_SXKD": dt_sxkd, "CP_SXKD": cp_sxkd, "Thu_SXKD": th_sxkd})
    tong_7["Thu_SXKD"] = th_sxkd
    
    tong = tinh_tong_7_nguon(tong_7)
    row.update({
        "TongThuNhap": tong,
        "ThuBQDauNguoi": round(tong / max(1, nhan_khau), 2)
    })
    return row


# ---------------------------------------------------------------------------
# 10. GIAO DIỆN PHƯƠNG THỨC ADMIN (HỆ THỐNG / CHỌN MẪU)
# ---------------------------------------------------------------------------
def page_login():
    """Giao diện cửa đăng nhập vai trò."""
    hien_thi_banner()
    left, col2, right = st.columns([1, 2, 1])
    with col2:
        with card_container("ĐĂNG NHẬP HỆ THỐNG PMDTV"):
            vt = st.radio("Vai trò làm việc", ["ĐIỀU TRA VIÊN", "QUẢN TRỊ VIÊN"], horizontal=True)
            if vt == "QUẢN TRỊ VIÊN":
                mk = st.text_input("Mật khẩu Admin", type="password")
                if st.button("Đăng nhập Admin", type="primary", use_container_width=True):
                    if mk.strip().upper() == ADMIN_MA:
                        st.session_state["user"] = {"ma": ADMIN_MA, "role": "admin", "ten": "Tổng quản trị"}
                        st.rerun()
                    else:
                        st.error("Mật khẩu Admin không chính xác.")
            else:
                ma = st.text_input("Mã số điều tra viên (ĐTV)")
                mk = st.text_input("Mật khẩu", type="password")
                if st.button("Đăng nhập ĐTV", type="primary", use_container_width=True):
                    ok, loi, r = xac_thuc_dang_nhap(ma, mk)
                    if ok:
                        st.session_state["user"] = {"ma": ma, "role": "dtv", "ten": r.get("HoTen", "ĐTV")}
                        st.rerun()
                    else:
                        st.error(loi)

def admin_he_thong():
    """Bảng điều khiển gán danh sách và chọn mốc mẫu r, k."""
    st.write("### ⚙️ Thiết lập hệ thống & Phân mẫu")
    t1, t2 = st.tabs(["📤 Nạp danh sách hộ mới", "🎯 Thực thi chọn mẫu hệ thống"])
    
    with t1:
        f = st.file_uploader("Tải lên Excel thông tin danh sách hộ nền", type=["xlsx", "xls"])
        if f and st.button("Xác nhận cập nhật dữ liệu"):
            df, thieu = doc_excel_danh_sach_ho(f, can_madtv=True)
            if df is not None:
                df[COL_PHAN_LOAI] = PHAN_LOAI_NEN
                if write_sheet_replace(SHEETS["danh_sach_ho"], df):
                    dong_bo_account_tu_ma_dtv(df["MaDTV"].unique().tolist())
                    st.success("Đã nạp thành công và tạo tài khoản mặc định cho các ĐTV tương ứng.")
            else:
                st.error(f"Thiếu thông tin cột trường quy chuẩn: {', '.join(thieu)}")
                
    with t2:
        df_ho = read_sheet(SHEETS["danh_sach_ho"])
        if not df_ho.empty:
            dtv_codes = df_ho["MaDTV"].unique().tolist()
            ma = st.selectbox("Chọn mã số ĐTV", dtv_codes)
            nen = lay_danh_sach_nen(df_ho, ma)
            
            st.write(f"ĐTV {ma} hiện có **{len(nen)}** hộ nền trong phân công.")
            c1, c2 = st.columns(2)
            k = c1.number_input("Chọn bước nhảy k", min_value=1, max_value=100, value=2)
            r = c2.number_input("Chọn vị trí khởi hành r", min_value=1, max_value=max(1, len(nen)), value=1)
            
            if st.button("Tự động chọn 40 mẫu và áp dụng"):
                chi_so = chon_chi_so_mau_tu_nen(len(nen), int(k), int(r))
                if not chi_so:
                    st.error("Không đủ hộ nền thực thi.")
                else:
                    df_da_phan = gan_phan_loai_ho(nen, chi_so)
                    df_out = cap_nhat_danh_sach_ho_theo_dtv(df_ho, ma, df_da_phan)
                    if write_sheet_replace(SHEETS["danh_sach_ho"], df_out):
                        st.success(f"Thiết lập thành công 40 mẫu cho ĐTV {ma}.")
                        hien_dataframe_an_toan(df_da_phan)


# ---------------------------------------------------------------------------
# 11. ĐIỀU TRA VIÊN: LUỒNG THỰC THI NHẬP PHIẾU
# ---------------------------------------------------------------------------
def dtv_nhap_phieu():
    user = st.session_state["user"]
    ma = user["ma"]
    ver = st.session_state.get("form_ver", 0)
    
    st.write(f"### 📝 Thực hiện nhập liệu phiếu hỏi — ĐTV: **{ma}**")
    
    df_ho = ho_mau_can_dieu_tra(lay_danh_sach_nen(read_sheet(SHEETS["danh_sach_ho"], silent=True), ma))
    if df_ho.empty:
        st.warning("Danh sách phân bổ hộ Mẫu trống. Vui lòng liên hệ Admin.")
        return
        
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    done = set(df_kq[df_kq["MaDTV"].astype(str) == str(ma)]["HoSo"].astype(str)) if not df_kq.empty else set()
    pending = df_ho[~df_ho["HoSo"].astype(str).isin(done)]
    
    if pending.empty:
        st.success("Chúc mừng! ĐTV đã hoàn tất điều tra 100% chỉ tiêu được giao.")
        return
        
    idx = st.selectbox("Chọn hộ gia đình khảo sát", range(len(pending)), format_func=lambda i: f"Hộ số: {pending.iloc[i]['HoSo']} - Chủ hộ: {pending.iloc[i]['TenChuHo']}")
    ho = pending.iloc[idx]
    ho_so = str(ho['HoSo'])
    
    # Quản lý trạng thái tab hiện tại và hộ đang khảo sát
    if "prev_survey_hoso" not in st.session_state or st.session_state["prev_survey_hoso"] != ho_so:
        st.session_state["prev_survey_hoso"] = ho_so
        st.session_state["dtv_form_tab"] = "📊 1. Thông tin chung"
        
    nk_key = f"nk_{ho_so}_{ver}"
    if nk_key not in st.session_state:
        st.session_state[nk_key] = 1
        
    loc = streamlit_geolocation() if streamlit_geolocation else None
    
    # Thanh điều hướng Tab đẹp và tương tác trực quan
    tabs_options = ["📊 1. Thông tin chung", "📋 2. Kê khai chỉ tiêu", "🧾 3. Tổng hợp"]
    col_tabs = st.columns(3)
    for idx_tab, val_tab in enumerate(tabs_options):
        is_active = (st.session_state["dtv_form_tab"] == val_tab)
        btn_type = "primary" if is_active else "secondary"
        if col_tabs[idx_tab].button(val_tab, key=f"dtv_tab_nav_{idx_tab}", use_container_width=True, type=btn_type):
            st.session_state["dtv_form_tab"] = val_tab
            st.rerun()
            
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    
    active_tab = st.session_state["dtv_form_tab"]
    
    if active_tab == "📊 1. Thông tin chung":
        with card_container("Thông tin chủ hộ"):
            st.info(f"📍 Chủ hộ: {ho['TenChuHo']} | Địa bàn: {ho['DiaBan']} | Xã: {ho['Xa']}")
            nk = st.number_input("Số nhân khẩu thực tế", min_value=1, max_value=30, value=int(st.session_state.get(nk_key, 1)), key=nk_key)
            
        # Nút nhấn chuyển tiếp thuận tiện ở cuối trang
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        if st.button("Tiếp tục: Kê khai chỉ tiêu ➡️", type="primary", use_container_width=True, key="btn_next_1"):
            st.session_state["dtv_form_tab"] = "📋 2. Kê khai chỉ tiêu"
            st.rerun()
            
    elif active_tab == "📋 2. Kê khai chỉ tiêu":
        nhap_lieu_5_nhom(ho_so, ver)
        
        # Nút nhấn quay lại và chuyển tiếp thuận tiện ở cuối trang
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        c_nav = st.columns(2)
        if c_nav[0].button("⬅️ Quay lại: Thông tin chung", type="secondary", use_container_width=True, key="btn_back_2"):
            st.session_state["dtv_form_tab"] = "📊 1. Thông tin chung"
            st.rerun()
        if c_nav[1].button("Tiếp tục: Tổng hợp kết quả ➡️", type="primary", use_container_width=True, key="btn_next_2"):
            st.session_state["dtv_form_tab"] = "🧾 3. Tổng hợp"
            st.rerun()
            
    elif active_tab == "🧾 3. Tổng hợp":
        nk = int(st.session_state.get(nk_key, 1))
        dl = tong_hop_du_lieu_phieu(ho_so, ver)
        ok, loi = kiem_tra_validation_phieu(ho_so, ver)
        tong = tinh_tong_7_nguon(dl["tong_7"])
        
        if dl["hang_bang"]:
            hien_dataframe_an_toan(pd.DataFrame(dl["hang_bang"]))
            
        st.metric("TỔNG THU NHẬP HỘ (NGHÌN ĐỒNG/THÁNG)", f"{tong:,.0f}")
        
        if loi:
            for m in loi:
                hien_loi_validation(m)
                
        # Nút nhấn quay lại và hành động gửi phiếu ở cuối trang
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        c_nav3 = st.columns([1, 2])
        if c_nav3[0].button("⬅️ Quay lại: Kê khai chỉ tiêu", type="secondary", use_container_width=True, key="btn_back_3"):
            st.session_state["dtv_form_tab"] = "📋 2. Kê khai chỉ tiêu"
            st.rerun()
            
        if c_nav3[1].button("💾 Thực hiện Lưu & Gửi phiếu", type="primary", use_container_width=True, disabled=not ok, key="btn_submit_phiet"):
            gps = phan_tich_vi_tri_gps(loc)
            geo = phan_tich_geofence(ho, loc)
            row = tao_dong_ket_qua_qd1099(
                ma_dtv=ma, ho=ho, nhan_khau=nk, thu_luong=dl["thu_luong"],
                linh_vuc=dl["linh_vuc"], dt_sxkd=dl["dt_sxkd"], cp_sxkd=dl["cp_sxkd"],
                thu_khac=dl["thu_khac"], loc=loc, gps=gps, geo=geo, ghi_chu_vi_tri=""
            )
            if append_ket_qua(row):
                st.toast("Đã gửi phiếu lên hệ thống thành công!", icon="✅")
                # Đổi phiên bản form để làm sạch bộ nhớ tạm thời trên Streamlit
                st.session_state["form_ver"] = ver + 1
                st.session_state["dtv_form_tab"] = "📊 1. Thông tin chung"
                st.rerun()


# ---------------------------------------------------------------------------
# 12. RUNTIME GRAPHICS & TIẾN ĐỘ THỐNG KÊ (DASHBOARD)
# ---------------------------------------------------------------------------
def check_or_get_ket_qua() -> pd.DataFrame:
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    if df_kq.empty or len(df_kq) == 0:
        # Tạo bộ dữ liệu mẫu chi tiết của 7 nguồn thu nhập tương thích QĐ 1099 để mô phỏng biểu đồ
        mock_data = [
            {
                "MaDTV": "DTV01", "HoSo": "1001", "MaTKCS": "Huyện Sơn Tịnh", "Xa": "Xã Tịnh Giang", "DiaBan": "Địa bàn 01", "TenChuHo": "Nguyễn Văn An", "NhanKhauTT": 4, 
                "ThuLuong": 8500.0, "Thu_TrongTrot": 4000.0, "Thu_ChanNuoi": 3000.0, "Thu_LamNghiep": 0.0, "Thu_ThuySan": 0.0, "Thu_SXKD": 0.0, "ThuKhac": 1500.0, 
                "TongThuNhap": 17000.0, "ThuBQDauNguoi": 4250.0, "NgayNhap": "2026-05-24 08:30:00"
            },
            {
                "MaDTV": "DTV01", "HoSo": "1002", "MaTKCS": "Huyện Sơn Tịnh", "Xa": "Xã Tịnh Giang", "DiaBan": "Địa bàn 01", "TenChuHo": "Phan Thị Bình", "NhanKhauTT": 3, 
                "ThuLuong": 0.0, "Thu_TrongTrot": 12000.0, "Thu_ChanNuoi": 8000.0, "Thu_LamNghiep": 1500.0, "Thu_ThuySan": 0.0, "Thu_SXKD": 4000.0, "ThuKhac": 2000.0,
                "TongThuNhap": 27500.0, "ThuBQDauNguoi": 9166.7, "NgayNhap": "2026-05-24 09:12:00"
            },
            {
                "MaDTV": "DTV02", "HoSo": "1003", "MaTKCS": "Huyện Bình Sơn", "Xa": "Xã Bình Thạnh", "DiaBan": "Địa bàn 02", "TenChuHo": "Lê Văn Cường", "NhanKhauTT": 5, 
                "ThuLuong": 12000.0, "Thu_TrongTrot": 0.0, "Thu_ChanNuoi": 0.0, "Thu_LamNghiep": 0.0, "Thu_ThuySan": 6000.0, "Thu_SXKD": 10000.0, "ThuKhac": 1000.0,
                "TongThuNhap": 29000.0, "ThuBQDauNguoi": 5800.0, "NgayNhap": "2026-05-24 10:05:00"
            },
            {
                "MaDTV": "DTV02", "HoSo": "1004", "MaTKCS": "Huyện Bình Sơn", "Xa": "Xã Bình Dương", "DiaBan": "Địa bàn 03", "TenChuHo": "Phạm Văn Danh", "NhanKhauTT": 2, 
                "ThuLuong": 7500.0, "Thu_TrongTrot": 1000.0, "Thu_ChanNuoi": 1500.0, "Thu_LamNghiep": 0.0, "Thu_ThuySan": 0.0, "Thu_SXKD": 0.0, "ThuKhac": 500.0,
                "TongThuNhap": 10500.0, "ThuBQDauNguoi": 5250.0, "NgayNhap": "2026-05-24 11:22:00"
            },
            {
                "MaDTV": "DTV03", "HoSo": "1005", "MaTKCS": "Huyện Nghĩa Hành", "Xa": "Xã Hành Minh", "DiaBan": "Địa bàn 04", "TenChuHo": "Đỗ Thị Xuân", "NhanKhauTT": 4, 
                "ThuLuong": 10000.0, "Thu_TrongTrot": 5000.0, "Thu_ChanNuoi": 4000.0, "Thu_LamNghiep": 2000.0, "Thu_ThuySan": 1500.0, "Thu_SXKD": 8000.0, "ThuKhac": 3000.0,
                "TongThuNhap": 33500.0, "ThuBQDauNguoi": 8375.0, "NgayNhap": "2026-05-24 13:40:00"
            },
            {
                "MaDTV": "DTV03", "HoSo": "1006", "MaTKCS": "Huyện Nghĩa Hành", "Xa": "Xã Hành Minh", "DiaBan": "Địa bàn 05", "TenChuHo": "Trần Văn Định", "NhanKhauTT": 4, 
                "ThuLuong": 6000.0, "Thu_TrongTrot": 8000.0, "Thu_ChanNuoi": 6000.0, "Thu_LamNghiep": 0.0, "Thu_ThuySan": 0.0, "Thu_SXKD": 0.0, "ThuKhac": 1000.0,
                "TongThuNhap": 21000.0, "ThuBQDauNguoi": 5250.0, "NgayNhap": "2026-05-24 14:15:00"
            },
        ]
        df_kq = pd.DataFrame(mock_data)
        st.session_state["using_mock_statistics"] = True
    else:
        st.session_state["using_mock_statistics"] = False
        
    for col in ["TongThuNhap", "ThuBQDauNguoi", "NhanKhauTT", "ThuLuong", "Thu_TrongTrot", "Thu_ChanNuoi", "Thu_LamNghiep", "Thu_ThuySan", "Thu_SXKD", "ThuKhac"]:
        if col in df_kq.columns:
            df_kq[col] = pd.to_numeric(df_kq[col], errors="coerce").fillna(0.0)
            
    return df_kq

def render_admin_dashboard():
    st.write("### 📊 Đồ thị Dashboard kiểm soát thu nhập")
    
    df_kq = check_or_get_ket_qua()
    df_ho = read_sheet(SHEETS["danh_sach_ho"], silent=True)
    
    if df_ho.empty:
         total_samples = len(df_kq)
    else:
         total_samples = len(ho_mau_can_dieu_tra(df_ho))
         if total_samples == 0:
             total_samples = len(df_kq)
             
    completed = len(df_kq) if not df_kq.empty else 0
    ratio = round(completed / max(1, total_samples) * 100, 1) if total_samples > 0 else 0
    
    if st.session_state.get("using_mock_statistics", False):
        st.info("💡 Hệ thống đang hiển thị dữ liệu minh hoạ trực quan. Khi có dữ liệu điều tra thực tế từ Google Sheets, hệ thống sẽ tự động cập nhật.")
        
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng quy mô hộ mẫu chỉ định", f"{total_samples} hộ")
    c2.metric("Số phiếu hoàn thành", f"{completed} phiếu")
    c3.metric("Tỷ lệ phản hồi", f"{ratio}%")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.write("#### Phân bố thu nhập bình quân đầu người")
        fig_hist = px.histogram(
            df_kq, 
            x="ThuBQDauNguoi", 
            nbins=15, 
            labels={"ThuBQDauNguoi": "Thu nhập bình quân đầu người (nghìnđ/tháng)"},
            color_discrete_sequence=["#1a4a7a"],
            title="Biểu đồ phân phối tần số thu nhập đầu người"
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with col_g2:
        st.write("#### Cơ cấu tỉ trọng các nguồn thu nhập")
        sources_data = []
        for key, name in BAO_CAO_7_NGUON:
            val = pd.to_numeric(df_kq.get(key, 0.0), errors="coerce").fillna(0.0).mean()
            sources_data.append({"Nguồn": name, "Bình quân (nghìnđ/tháng)": val})
            
        df_sources = pd.DataFrame(sources_data)
        fig_pie = px.pie(
            df_sources, 
            values="Bình quân (nghìnđ/tháng)", 
            names="Nguồn",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Tỉ trọng đóng góp của 7 nguồn thu nhập"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

def admin_tien_do():
    st.write("### 📈 Thống kê tiến độ điều tra thực địa")
    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    df_kq = read_sheet(SHEETS["ket_qua"])
    
    if df_ho.empty:
        st.warning("Danh sách dữ liệu mốc hiện trạng trống.")
        return
        
    df_mau = ho_mau_can_dieu_tra(df_ho)
    if df_mau.empty:
        st.info("Hệ thống chưa gán mẫu điều tra chỉ định cho bất kỳ ĐTV nào.")
        return
        
    total_mau = len(df_mau)
    completed = len(df_kq) if not df_kq.empty else 0
    ton_dong = max(0, total_mau - completed)
    ti_le = round(completed / max(1, total_mau) * 100, 1)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mẫu chỉ định", f"{total_mau} hộ")
    col2.metric("Đã hoàn thành", f"{completed} phiếu")
    col3.metric("Còn lại", f"{ton_dong} hộ")
    col4.metric("Tỷ lệ tiến độ đạt", f"{ti_le}%")
    
    t_dtv, t_xa = st.tabs(["👨‍💻 Theo Điều tra viên (ĐTV)", "🏡 Theo Xã cư trú"])
    
    with t_dtv:
        df_mau_dtv = df_mau.groupby("MaDTV").size().reset_index(name="MauChiDinh")
        if not df_kq.empty:
            df_done_dtv = df_kq.groupby("MaDTV").size().reset_index(name="KqHoanThanh")
            df_tien_do = pd.merge(df_mau_dtv, df_done_dtv, on="MaDTV", how="left").fillna(0)
        else:
            df_tien_do = df_mau_dtv.copy()
            df_tien_do["KqHoanThanh"] = 0
            
        df_tien_do["KqHoanThanh"] = df_tien_do["KqHoanThanh"].astype(int)
        df_tien_do["ConLai"] = (df_tien_do["MauChiDinh"] - df_tien_do["KqHoanThanh"]).clip(lower=0)
        df_tien_do["TienDo"] = (df_tien_do["KqHoanThanh"] / df_tien_do["MauChiDinh"] * 100).round(1)
        
        df_show = df_tien_do.copy()
        df_show.columns = ["Mã điều tra viên", "Sản lượng mẫu được giao", "Chỉ tiêu hoàn thành", "Số hộ chưa nhập", "Tiến độ đạt (%)"]
        hien_dataframe_an_toan(df_show)
        
        fig_dtv = px.bar(
            df_tien_do,
            x="MaDTV",
            y="TienDo",
            range_y=[0, 105],
            labels={"TienDo": "Tiến độ hoàn thành mẫu (%)", "MaDTV": "Điều tra viên"},
            title="Biểu đồ trực quan so sánh tiến độ hoàn thành các điều tra viên"
        )
        st.plotly_chart(fig_dtv, use_container_width=True)
        
    with t_xa:
        df_mau_xa = df_mau.groupby("Xa").size().reset_index(name="MauChiDinh")
        if not df_kq.empty:
            df_done_xa = df_kq.groupby("Xa").size().reset_index(name="KqHoanThanh")
            df_tien_do_xa = pd.merge(df_mau_xa, df_done_xa, on="Xa", how="left").fillna(0)
        else:
            df_tien_do_xa = df_mau_xa.copy()
            df_tien_do_xa["KqHoanThanh"] = 0
            
        df_tien_do_xa["KqHoanThanh"] = df_tien_do_xa["KqHoanThanh"].astype(int)
        df_tien_do_xa["ConLai"] = (df_tien_do_xa["MauChiDinh"] - df_tien_do_xa["KqHoanThanh"]).clip(lower=0)
        df_tien_do_xa["TienDo"] = (df_tien_do_xa["KqHoanThanh"] / df_tien_do_xa["MauChiDinh"] * 100).round(1)
        
        df_show_xa = df_tien_do_xa.copy()
        df_show_xa.columns = ["Xã cư trú", "Sản lượng mẫu được giao", "Chỉ tiêu hoàn thành", "Số hộ chưa nhập", "Tiến độ đạt (%)"]
        hien_dataframe_an_toan(df_show_xa)

def admin_thong_ke_tong_hop():
    st.write("### 📋 Thống kê tổng hợp thu nhập & Đánh giá so sánh")
    
    df_kq = check_or_get_ket_qua()
    if df_kq.empty:
        st.warning("Hiện chưa có dữ liệu báo cáo kết quả.")
        return
        
    if st.session_state.get("using_mock_statistics", False):
        st.info("💡 Hệ thống đang hiển thị dữ liệu minh hoạ trực quan. Khi có dữ liệu điều tra thực tế từ Google Sheets, hệ thống sẽ tự động cập nhật.")
        
    t1, t2, t3, t4 = st.tabs([
        "🏢 Theo Cấp TKCS (Huyện/Thị)", 
        "🏡 Theo Xã cư trú", 
        "📍 Theo Địa bàn khảo sát",
        "🎛️ So sánh thu nhập bình quân"
    ])
    
    # 1. Cấp TKCS
    with t1:
        st.write("#### Tổng hợp thu nhập bình quân theo Đơn vị TKCS (Mã Huyện)")
        df_tkcs = df_kq.groupby("MaTKCS").agg(
            SoHo=("HoSo", "count"),
            TongNhanKhau=("NhanKhauTT", "sum"),
            ThuNhapBQ_Ho=("TongThuNhap", "mean"),
            ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
        ).reset_index()
        
        df_tkcs_display = df_tkcs.copy()
        df_tkcs_display["Thu nhập BQ Hộ/tháng (Thìn đ)"] = df_tkcs_display["ThuNhapBQ_Ho"].round(1).map('{:,.1f}'.format)
        df_tkcs_display["Thu nhập BQ Đầu người/tháng (Thìn đ)"] = df_tkcs_display["ThuNhapBQ_DauNguoi"].round(1).map('{:,.1f}'.format)
        df_tkcs_display["Số hộ hoàn tất"] = df_tkcs_display["SoHo"]
        df_tkcs_display["Nhân khẩu quy mô"] = df_tkcs_display["TongNhanKhau"]
        
        hien_dataframe_an_toan(df_tkcs_display[["MaTKCS", "Số hộ hoàn tất", "Nhân khẩu quy mô", "Thu nhập BQ Hộ/tháng (Thìn đ)", "Thu nhập BQ Đầu người/tháng (Thìn đ)"]])
        
        fig_tkcs = px.bar(
            df_tkcs,
            x="MaTKCS",
            y=["ThuNhapBQ_Ho", "ThuNhapBQ_DauNguoi"],
            barmode="group",
            labels={"value": "Thu nhập bình quân (nghìnđ/tháng)", "variable": "Loại chỉ tiêu"},
            color_discrete_sequence=["#1a4a7a", "#0284c7"],
            title="Biểu đồ so sánh thu nhập bình quân Hộ và Đầu người theo Cấp TKCS"
        )
        st.plotly_chart(fig_tkcs, use_container_width=True)

    # 2. Theo Xã
    with t2:
        st.write("#### Tổng hợp thu nhập bình quân theo Xã phường cư trú")
        df_xa = df_kq.groupby("Xa").agg(
            SoHo=("HoSo", "count"),
            TongNhanKhau=("NhanKhauTT", "sum"),
            ThuNhapBQ_Ho=("TongThuNhap", "mean"),
            ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
        ).reset_index()
        
        df_xa_display = df_xa.copy()
        df_xa_display["Thu nhập BQ Hộ/tháng (Thìn đ)"] = df_xa_display["ThuNhapBQ_Ho"].round(1).map('{:,.1f}'.format)
        df_xa_display["Thu nhập BQ Đầu người/tháng (Thìn đ)"] = df_xa_display["ThuNhapBQ_DauNguoi"].round(1).map('{:,.1f}'.format)
        df_xa_display["Số hộ hoàn tất"] = df_xa_display["SoHo"]
        df_xa_display["Nhân khẩu quy mô"] = df_xa_display["TongNhanKhau"]
        
        hien_dataframe_an_toan(df_xa_display[["Xa", "Số hộ hoàn tất", "Nhân khẩu quy mô", "Thu nhập BQ Hộ/tháng (Thìn đ)", "Thu nhập BQ Đầu người/tháng (Thìn đ)"]])
        
        fig_xa = px.bar(
            df_xa,
            x="Xa",
            y="ThuNhapBQ_DauNguoi",
            color="Xa",
            labels={"ThuNhapBQ_DauNguoi": "Thu nhập bình quân đầu người (nghìnđ/tháng)"},
            title="Biểu đồ phân bố thu nhập bình quân đầu người thu nhận theo các Xã"
        )
        st.plotly_chart(fig_xa, use_container_width=True)

    # 3. Theo Địa bàn
    with t3:
        st.write("#### Tổng hợp thu nhập bình quân theo Địa bàn được khoanh vùng")
        df_db = df_kq.groupby("DiaBan").agg(
            SoHo=("HoSo", "count"),
            TongNhanKhau=("NhanKhauTT", "sum"),
            ThuNhapBQ_Ho=("TongThuNhap", "mean"),
            ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
        ).reset_index()
        
        df_db_display = df_db.copy()
        df_db_display["Thu nhập BQ Hộ/tháng (Thìn đ)"] = df_db_display["ThuNhapBQ_Ho"].round(1).map('{:,.1f}'.format)
        df_db_display["Thu nhập BQ Đầu người/tháng (Thìn đ)"] = df_db_display["ThuNhapBQ_DauNguoi"].round(1).map('{:,.1f}'.format)
        df_db_display["Số hộ hoàn tất"] = df_db_display["SoHo"]
        df_db_display["Nhân khẩu quy mô"] = df_db_display["TongNhanKhau"]
        
        hien_dataframe_an_toan(df_db_display[["DiaBan", "Số hộ hoàn tất", "Nhân khẩu quy mô", "Thu nhập BQ Hộ/tháng (Thìn đ)", "Thu nhập BQ Đầu người/tháng (Thìn đ)"]])
        
        fig_db = px.bar(
            df_db,
            x="DiaBan",
            y="ThuNhapBQ_DauNguoi",
            color="DiaBan",
            labels={"ThuNhapBQ_DauNguoi": "Thu nhập bình quân đầu người (nghìnđ/tháng)"},
            title="Biêu đồ so sánh thu nhập bình quân đầu người theo từng Địa bàn cụ thể"
        )
        st.plotly_chart(fig_db, use_container_width=True)

    # 4. Trình so sánh chi tiết
    with t4:
        st.write("#### Công cụ phân tích, so sánh thu nhập tương tác")
        loai_so_sanh = st.radio("Chọn cấp độ thống kê so sánh", ["Theo Cấp TKCS (Mã Huyện)", "Theo Cấp Xã phường", "Theo phân tổ Địa bàn"], horizontal=True)
        
        if loai_so_sanh == "Theo Cấp TKCS (Mã Huyện)":
            khoa_tu = "MaTKCS"
        elif loai_so_sanh == "Theo Cấp Xã phường":
            khoa_tu = "Xa"
        else:
            khoa_tu = "DiaBan"
            
        nhom_du_lieu = df_kq.groupby(khoa_tu).agg(
            Thu_BQ_Ho=("TongThuNhap", "mean"),
            Thu_BQ_Nguoi=("ThuBQDauNguoi", "mean")
        ).reset_index()
        
        to_hop_lua_chon = nhom_du_lieu[khoa_tu].unique().tolist()
        tieu_diem = st.multiselect(f"Chọn các đơn vị thuộc nhóm {loai_so_sanh} để đưa lên biểu đồ phân tích trực quan", to_hop_lua_chon, default=to_hop_lua_chon[:3])
        
        if len(tieu_diem) > 0:
            df_so_sanh = nhom_du_lieu[nhom_du_lieu[khoa_tu].isin(tieu_diem)]
            
            fig_compare = px.bar(
                df_so_sanh,
                x=khoa_tu,
                y=["Thu_BQ_Ho", "Thu_BQ_Nguoi"],
                barmode="group",
                labels={"value": "Thu nhập bình quân (nghìnđ/tháng)", "variable": "Chỉ số"},
                color_discrete_sequence=["#0d2137", "#0ea5e9"],
                title=f"Biểu đồ phân tích so sánh trực tiếp các đơn vị thuộc {loai_so_sanh}"
            )
            st.plotly_chart(fig_compare, use_container_width=True)
            
            # Show formatted table
            df_so_sanh_display = df_so_sanh.copy()
            df_so_sanh_display.columns = [loai_so_sanh, "Bình quân Hộ gia đình", "Bình quân Đầu người"]
            df_so_sanh_display["Bình quân Hộ gia đình"] = df_so_sanh_display["Bình quân Hộ gia đình"].round(1).map('{:,.1f}'.format)
            df_so_sanh_display["Bình quân Đầu người"] = df_so_sanh_display["Bình quân Đầu người"].round(1).map('{:,.1f}'.format)
            hien_dataframe_an_toan(df_so_sanh_display)
        else:
            st.warning("Vui lòng chọn hoặc điền ít nhất 1 đơn vị để hiển thị so sánh.")


# ---------------------------------------------------------------------------
# 13. MAIN ENTRY POINT (ĐIỀU HƯỚNG ROUTING)
# ---------------------------------------------------------------------------
def main():
    if "user" not in st.session_state:
        page_login()
        return
        
    user = st.session_state["user"]
    
    # Khối tiêu đề ghim ở đỉnh trang (Sticky / Pin)
    with st.container():
        st.markdown('<div id="sticky-header"></div>', unsafe_allow_html=True)
        # Hiển thị ảnh ngang nằm ở trên cùng của trang
        hien_thi_banner()
        
        cols = st.columns([2, 4.5, 1.2])
        
        with cols[0]:
            st.markdown(f"""
            <div class="user-badge-card">
                <div class="avatar-circle">{user['ten'][:1].upper()}</div>
                <div>
                    <div class="user-title">{user['ten']}</div>
                    <div class="user-role">{user['role'].upper()}: {user['ma']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols[1]:
            if user["role"] == "admin":
                if "admin_menu" not in st.session_state:
                    st.session_state["admin_menu"] = "📊 Đồ thị Dashboard"
                
                menu_options = [
                    "📊 Đồ thị Dashboard", 
                    "⚙️ Thiết lập hệ thống", 
                    "📈 Tiến độ khảo sát", 
                    "📋 Thống kê tổng hợp"
                ]
                sub_cols = st.columns(4)
                for idx, opt in enumerate(menu_options):
                    is_active = st.session_state["admin_menu"] == opt
                    btn_type = "primary" if is_active else "secondary"
                    if sub_cols[idx].button(opt, key=f"admin_nav_{idx}", use_container_width=True, type=btn_type):
                        st.session_state["admin_menu"] = opt
                        st.rerun()
            else:
                st.markdown(f"""
                <div class="surveyor-badge">
                    <span class="status-dot">●</span> 
                    <span style="font-weight:700;">CHẾ ĐỘ ĐIỀU TRA VIÊN HOẠT ĐỘNG</span>
                    <span style="color:#64748b; margin-left:8px;">| Đang nhập phiếu trực tuyến</span>
                </div>
                """, unsafe_allow_html=True)
                
        with cols[2]:
            if st.button("🚪 Đăng xuất", key="logout_btn", use_container_width=True, type="secondary"):
                st.session_state.clear()
                st.rerun()
                
    st.markdown('<div class="sticky-header-spacer"></div>', unsafe_allow_html=True)
    
    if user["role"] == "admin":
        active_view = st.session_state.get("admin_menu", "📊 Đồ thị Dashboard")
        if active_view == "📊 Đồ thị Dashboard":
            render_admin_dashboard()
        elif active_view == "⚙️ Thiết lập hệ thống":
            admin_he_thong()
        elif active_view == "📈 Tiến độ khảo sát":
            admin_tien_do()
        else:
            admin_thong_ke_tong_hop()
    else:
        dtv_nhap_phieu()

if __name__ == "__main__":
    main()
