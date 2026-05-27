# -*- coding: utf-8 -*-
"""
PMDTV.py — Phiếu hỏi điều tra thu nhập năm 2026 (Streamlit + Google Sheets).
Mã nguồn đã được Việt hóa toàn diện, tuân thủ chặt chẽ biểu mẫu và logic
của Quyết định 1099/QĐ-BKHĐT, đảm bảo tính trực quan và thân thiện với người dùng cuối.
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
    page_title="PMDTV — Phiếu Điều Tra Thu Nhập Hộ",
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
            height: 290px !important;
            width: 100% !important;
        }}
        
        .app-main-title {{
            color: #0d2137;
            font-weight: 800;
            margin-bottom: 0px;
            font-size: 22px;
            text-transform: uppercase;
            letter-spacing: -0.3px;
        }}

        .main-title-wrapper {{
            text-align: center;
            margin-top: -12px;
            margin-bottom: 15px;
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
        
        @media (max-width: 1200px) {{
            .sticky-header-spacer {{
                height: 265px !important;
            }}
        }}

        @media (max-width: 992px) {{
            .sticky-header-spacer {{
                height: 240px !important;
            }}
            .app-main-title {{
                font-size: 18px !important;
            }}
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
                height: 185px !important;
            }}
            .app-main-title {{
                font-size: 15px !important;
                letter-spacing: -0.5px !important;
                white-space: nowrap !important;
            }}
            .main-title-wrapper {{
                margin-top: -8px;
                margin-bottom: 8px;
            }}
            
            /* Thắt chặt khoảng cách và buộc các cột trong phần badge ở đầu trang không bị rớt dòng */
            div:has(#sticky-header) div[data-testid="stHorizontalBlock"] {{
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                gap: 6px !important;
                align-items: center !important;
            }}
            /* Cho phép cột chứa Badge co giãn và cột chứa Đăng xuất ôm khít */
            div:has(#sticky-header) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
                min-width: 0 !important;
                width: auto !important;
                flex: 1 1 auto !important;
            }}
            /* Riêng cột chứa nút Đăng xuất thì cho kích thước nhỏ gọn */
            div:has(#sticky-header) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
                flex: 0 0 100px !important;
                width: 100px !important;
            }}
            
            /* Tiết kiệm diện tích màn hình điện thoại cho Badge */
            .surveyor-badge-sub {{
                display: none !important;
            }}
            .surveyor-badge {{
                padding: 6px 10px !important;
                font-size: 10px !important;
                border-radius: 8px !important;
            }}
            .user-badge-card {{
                padding: 6px 10px !important;
                border-radius: 8px !important;
                gap: 6px !important;
            }}
            .user-title {{
                font-size: 11px !important;
            }}
            .user-role {{
                font-size: 8.5px !important;
                margin-top: 0px !important;
            }}
            .avatar-circle {{
                width: 28px !important;
                height: 28px !important;
                font-size: 12px !important;
            }}
            
            /* CSS thu nhỏ nút Đăng xuất Streamlit */
            div:has(#sticky-header) div[data-testid="stColumn"]:last-child div[data-testid="stButton"] button,
            div[data-testid="stButton"]:has(button[key="logout_btn"]) button {{
                padding: 4px 6px !important;
                min-height: unset !important;
                height: 36px !important;
            }}
            div:has(#sticky-header) div[data-testid="stColumn"]:last-child div[data-testid="stButton"] button p,
            div:has(#sticky-header) div[data-testid="stColumn"]:last-child div[data-testid="stButton"] button span,
            div[data-testid="stButton"]:has(button[key="logout_btn"]) button p,
            div[data-testid="stButton"]:has(button[key="logout_btn"]) button span {{
                font-size: 11px !important;
                font-weight: 700 !important;
            }}
        }}

        @media (max-width: 480px) {{
            .sticky-header-spacer {{
                height: 165px !important;
            }}
            .app-main-title {{
                font-size: 12.5px !important;
            }}
            div:has(#sticky-header) div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
                flex: 0 0 90px !important;
                width: 90px !important;
            }}
            div:has(#sticky-header) div[data-testid="stColumn"]:last-child div[data-testid="stButton"] button {{
                height: 32px !important;
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
        <div class="main-title-wrapper">
            <h2 class="app-main-title">HỆ THỐNG ĐIỀU TRA THU NHẬP HỘ</h2>
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

# Cấu trúc các mục thu nhập theo Quyết định 1099/QĐ-BKHĐT
PHIEU_THU_NHAP_CONFIG = [
    {"id": "thong_tin_chung", "ten": "Phần A: Thông tin chung", "loai": "thong_tin_chung"},
    {
        "id": "muc1", "ten": "Mục 1: Thu nhập từ tiền lương, tiền công", "loai": "luong",
        "cau_hoi": "Trong 12 tháng qua có ai trong hộ ông/bà đi làm để nhận tiền lương, tiền công và/hoặc nhận được lương hưu, trợ cấp thất nghiệp, thôi việc một lần không?"
    },
    {
        "id": "muc2", "ten": "Mục 2: Thu nhập từ trồng trọt", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động trồng trọt không?",
        "chi_phi_cols": ["Giống", "Phân bón, thuốc BVTV", "Chi khác"]
    },
    {
        "id": "muc3", "ten": "Mục 3: Thu nhập từ chăn nuôi", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động chăn nuôi hoặc từ sản bắt, đánh bẫy, thuần dưỡng chim, thú không?",
        "chi_phi_cols": ["Giống", "Thức ăn, thuốc phòng và chữa bệnh", "Chi khác"]
    },
    {
        "id": "muc4", "ten": "Mục 4: Thu nhập từ lâm nghiệp", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động lâm nghiệp (khai thác gỗ, khai thác và thu nhặt sản phẩm từ rừng và cây lâm nghiệp phân tán, ươm các loại giống cây lâm nghiệp, trồng/quản lý/bảo vệ/chăm sóc rừng, hoạt động dịch vụ lâm nghiệp,...) không?",
        "chi_phi_cols": ["Giống", "Phân bón, thuốc trừ sâu, diệt cỏ, bảo vệ thực vật", "Chi khác"]
    },
    {
        "id": "muc5", "ten": "Mục 5: Thu nhập từ thủy sản", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động thủy sản (nuôi trồng/đánh bắt thủy hải sản ở ao hồ, sông, suối, biển) không?",
        "chi_phi_cols": ["Giống", "Thức ăn, thuốc phòng và chữa bệnh", "Chi khác"]
    },
    {
        "id": "muc6", "ten": "Mục 6: Thu nhập từ hoạt động SXKD phi nông, lâm nghiệp, thủy sản", "loai": "sxkd",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động SXKD phi nông, lâm nghiệp, thủy sản của hộ không?",
        "chi_phi_cols": ["Nguyên vật liệu chính, phụ, thực liệu", "Năng lượng, nhiên liệu", "Chi khác"]
    },
    {
        "id": "muc7", "ten": "Mục 7: Thu nhập khác", "loai": "khac",
        "cau_hoi": "Xin ông/bà cho biết trong 12 tháng qua, hộ ông/bà có nhận được các nguồn thu nhập nào sau đây không?"
    }
]


# 7 nguồn thu nhập hiển thị chung
BAO_CAO_7_NGUON: list[tuple[str, str]] = [
    ("Muc1_ThuNhap", "1. Tiền lương, tiền công"),
    ("Muc2_ThuNhap", "2. Trồng trọt"),
    ("Muc3_ThuNhap", "3. Chăn nuôi"),
    ("Muc4_ThuNhap", "4. Lâm nghiệp"),
    ("Muc5_ThuNhap", "5. Thủy sản"),
    ("Muc6_ThuNhap", "6. SXKD phi nông nghiệp"),
    ("Muc7_ThuNhap", "7. Thu nhập khác"),
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
    "TongThuNhap": "Tổng thu nhập hộ (nghìn đồng/năm)",
    "GPS_lat": "Vĩ độ GPS", "GPS_lng": "Kinh độ GPS",
    "DoChinhXac": "Độ chính xác (m)", "Xac_Thuc_GPS": "Xác thực GPS",
    "Sai_so": "Sai số GPS (m)", "Do_cao": "Độ cao (m)",
    "IP": "Địa chỉ IP", "MockGPS": "Nghi ngờ vị trí giả",
    "NgayNhap": "Ngày nhập phiếu", "Tong": "Tổng số hộ",
    "Xong": "Đã hoàn thành", "PhanTram": "Tỷ lệ hoàn thành (%)",
    "SoPhieu": "Số phiếu", "NganhKT": "Ngành kinh tế",
    "MatKhau": "Mật khẩu", "NhanKhauTT": "Số nhân khẩu thường trú",
    "ThuBQDauNguoi": "Thu nhập bình quân đầu người (nghìn đồng/năm)",
    "DiaChi": "Địa chỉ", "KhoangCachLech": "Khoảng cách lệch (m)",
    "MaDiaBan": "Mã địa bàn", "GhiChuViTri": "Ghi chú vị trí lệch",
    "Muc1_ThuNhap": "Thu từ Tiền lương, công",
    "Muc2_ThuNhap": "Thu từ Trồng trọt",
    "Muc3_ThuNhap": "Thu từ Chăn nuôi",
    "Muc4_ThuNhap": "Thu từ Lâm nghiệp",
    "Muc5_ThuNhap": "Thu từ Thủy sản",
    "Muc6_ThuNhap": "Thu từ SXKD phi NLT",
    "Muc7_ThuNhap": "Thu nhập khác",
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
    "tongthunhap": "TongThuNhap",
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
            st.error(f"Lỗi đọc sheet '{name}' từ Google Sheets: {e}")
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
            st.error(f"Lỗi ghi sheet '{sheet_name}': {e}")
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

def hien_loi_validation(noi_dung: str) -> None:
    st.markdown(f'<p class="input-loi-do">{noi_dung}</p>', unsafe_allow_html=True)

def _key(muc_id: str, ho_so: str, form_ver: int, suffix: str | None = None) -> str:
    """Tạo session state key thống nhất cho từng mục."""
    base = f"{muc_id}_{ho_so}_{form_ver}"
    return f"{base}_{suffix}" if suffix else base

def hien_canh_bao_khong_tinh() -> None:
    st.caption(f"⚠️ Lưu ý: {CANH_BAO_KHONG_TINH}")


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
        return False, "Lỗi: Không tìm thấy dữ liệu tài khoản.", None
    row = df[df["MaDTV"].astype(str).str.strip() == ma]
    if row.empty:
        return False, f"Mã ĐTV '{ma}' không tồn tại.", None
    r = row.iloc[0]
    if str(r.get("MatKhau", "")).strip() != str(mat_khau).strip():
        return False, "Mật khẩu không đúng.", None
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
def nhap_thanh_vien_ho(ho_so: str, form_ver: int) -> list[dict[str, Any]]:
    key = f"ds_tv_{ho_so}_{form_ver}"
    if key not in st.session_state:
        st.session_state[key] = []
    
    st.markdown("<p style='font-weight: 600; color: #1e293b; margin-top: 10px; margin-bottom: -5px;'>➕ Thêm thành viên trong hộ (từ 6 tuổi trở lên):</p>", unsafe_allow_html=True)
    c1, _, c3 = st.columns([4, 1, 1])
    ten = c1.text_input("Họ và tên", key=_key("tv", ho_so, form_ver, "ten"), placeholder="VD: Nguyễn Văn A", label_visibility="collapsed")
    
    if c3.button("➕ Thêm", key=_key("tv", ho_so, form_ver, "them"), use_container_width=True, type="primary"):
        if ten.strip():
            ds = st.session_state[key]
            ds.append({"Họ tên": ten.strip().title(), "ma_tv": len(ds) + 1})
            st.session_state[key] = ds
            st.toast(f"Đã thêm: {ten.strip().title()}.", icon="✅")
            st.rerun()
            
    ds_hien = st.session_state[key]
    if ds_hien:
        st.markdown("<p style='font-weight: 700; color: #0f172a; margin-top: 15px; margin-bottom: 5px;'>👥 Danh sách thành viên:</p>", unsafe_allow_html=True)
        # Header
        cols_h = st.columns([1, 4, 1])
        cols_h[0].markdown("**Mã**")
        cols_h[1].markdown("**Họ và tên**")
        cols_h[2].markdown("**Xóa**")
        st.markdown("<hr style='margin: 5px 0 10px 0'>", unsafe_allow_html=True)
        
        for i, tv in enumerate(ds_hien):
            cols_r = st.columns([1, 4, 1])
            cols_r[0].write(f"**{tv['ma_tv']}**")
            cols_r[1].write(f"👤 {tv['Họ tên']}")
            if cols_r[2].button("🗑️", key=_key("tv", ho_so, form_ver, f"del_{i}"), help=f"Xóa thành viên {tv['Họ tên']}"):
                del st.session_state[key][i]
                st.rerun()
    return ds_hien

def nhap_muc_1_luong(ho_so: str, form_ver: int, thanh_vien: list[dict[str, Any]]):
    """Mục 1: Thu nhập từ tiền lương, tiền công."""
    key = _key("muc1", ho_so, form_ver, "data")
    if key not in st.session_state:
        st.session_state[key] = []

    if not thanh_vien:
        st.warning("Vui lòng nhập danh sách thành viên ở 'Phần A' trước khi kê khai mục này.")
        return

    # Header
    cols = st.columns([1, 3, 2, 2])
    cols[0].markdown("**Mã TV**")
    cols[1].markdown("**Họ và tên**")
    cols[2].markdown("**Tiền lương, tiền công**")
    cols[3].markdown("**Lương hưu / Trợ cấp**")

    total_luong = 0
    total_tro_cap = 0
    
    records = []
    for i, tv in enumerate(thanh_vien):
        cols_r = st.columns([1, 3, 2, 2])
        cols_r[0].write(f"**{tv['ma_tv']}**")
        cols_r[1].write(f"👤 {tv['Họ tên']}")
        
        luong = cols_r[2].number_input(
            "Lương (1.000đ/năm)", 
            min_value=0, 
            key=_key("muc1", ho_so, form_ver, f"luong_{i}"),
            label_visibility="collapsed"
        )
        tro_cap = cols_r[3].number_input(
            "Trợ cấp (1.000đ/năm)",
            min_value=0,
            key=_key("muc1", ho_so, form_ver, f"tro_cap_{i}"),
            label_visibility="collapsed"
        )
        total_luong += luong
        total_tro_cap += tro_cap
        records.append({"ma_tv": tv['ma_tv'], "luong": luong, "tro_cap": tro_cap})

    st.session_state[key] = records

    # Footer
    st.markdown("<hr style='margin: 10px 0'>", unsafe_allow_html=True)
    cols_f = st.columns([4, 2, 2])
    cols_f[1].metric("Tổng lương", f"{total_luong:,.0f}")
    cols_f[2].metric("Tổng trợ cấp", f"{total_tro_cap:,.0f}")

def nhap_muc_nong_nghiep_sxkd(muc_id: str, ten_muc: str, chi_phi_cols: list[str], ho_so: str, form_ver: int):
    """Template cho các mục 2, 3, 4, 5, 6."""
    key = _key(muc_id, ho_so, form_ver, "data")
    if key not in st.session_state:
        st.session_state[key] = []
    
    # Form thêm dòng mới
    st.markdown("---")
    st.markdown(f"**Thêm dòng mới**")
    cols = st.columns([2, 1, 1] + [1] * len(chi_phi_cols))
    
    nguon_thu = cols[0].text_input("Mô tả hoạt động / sản phẩm", key=_key(muc_id, ho_so, form_ver, "nguon_thu_new"), label_visibility="collapsed")
    c1 = cols[1].number_input("Trị giá bán/đổi/biếu tặng", min_value=0, key=_key(muc_id, ho_so, form_ver, "c1_new"), label_visibility="collapsed")
    c2 = cols[2].number_input("Trị giá hộ giữ lại dùng", min_value=0, key=_key(muc_id, ho_so, form_ver, "c2_new"), label_visibility="collapsed")

    cp_values = []
    for i, cp_label in enumerate(chi_phi_cols):
        val = cols[3+i].number_input(cp_label, min_value=0, key=_key(muc_id, ho_so, form_ver, f"cp_{i}_new"), label_visibility="collapsed")
        cp_values.append(val)

    if st.button(f"Thêm dòng", key=_key(muc_id, ho_so, form_ver, "add_btn"), type="primary"):
        tong_thu = c1 + c2
        tong_chi_phi = sum(cp_values)
        
        if tong_chi_phi > tong_thu:
            hien_loi_validation(f"Cảnh báo: Chi phí ({tong_chi_phi:,.0f}) > Tổng trị giá ({tong_thu:,.0f}) của '{nguon_thu}'.")
        
        if nguon_thu.strip():
            new_row = {"nguon_thu": nguon_thu, "c1": c1, "c2": c2}
            for i, val in enumerate(cp_values):
                new_row[f"cp_{i}"] = val
            st.session_state[key].append(new_row)
            st.rerun()

    # Bảng hiển thị dữ liệu đã nhập
    if st.session_state[key]:
        st.markdown(f"**Bảng chi tiết**")
        
        # Header động
        header_cols = ["Mô tả", "Bán/Đổi", "Tự dùng", "Tổng trị giá"] + chi_phi_cols + ["Tổng CP", "Thuần", "Xóa"]
        cols_h = st.columns([2, 1, 1, 1] + [1] * len(chi_phi_cols) + [1, 1, 0.5])
        for i, h in enumerate(header_cols):
             cols_h[i].markdown(f"**{h}**")

        st.markdown("<hr style='margin: 5px 0 10px 0'>", unsafe_allow_html=True)
        
        # Dữ liệu
        for i, row in enumerate(st.session_state[key]):
            tong_thu = row['c1'] + row['c2']
            cp_vals = [row.get(f'cp_{j}', 0) for j in range(len(chi_phi_cols))]
            tong_chi_phi = sum(cp_vals)
            thu_nhap = tong_thu - tong_chi_phi

            cols_r = st.columns([2, 1, 1, 1] + [1] * len(chi_phi_cols) + [1, 1, 0.5])
            cols_r[0].write(row['nguon_thu'])
            cols_r[1].write(f"{row['c1']:,}")
            cols_r[2].write(f"{row['c2']:,}")
            cols_r[3].write(f"**{tong_thu:,}**")
            for j, cp_val in enumerate(cp_vals):
                cols_r[4+j].write(f"{cp_val:,}")
            cols_r[4+len(cp_vals)].write(f"**{tong_chi_phi:,}**")
            cols_r[5+len(cp_vals)].write(f"**{thu_nhap:,}**")
            if cols_r[6+len(cp_vals)].button("🗑️", key=_key(muc_id, ho_so, form_ver, f"del_{i}"), help="Xóa dòng này"):
                del st.session_state[key][i]
                st.rerun()

def nhap_muc_7_khac(ho_so: str, form_ver: int):
    """Mục 7: Thu nhập khác."""
    key = _key("muc7", ho_so, form_ver, "data")
    if key not in st.session_state:
        st.session_state[key] = {
            "1.1": 0, "1.2": 0, "1.3": 0,
            "2.1": 0, "2.2": 0, "3.0": 0,
        }
    
    data = st.session_state[key]
    
    st.markdown("**1. THU NHẬP TỪ CHUYỂN NHƯỢNG**")
    data["1.1"] = st.number_input("1.1. Tiền, hiện vật do người ngoài cho/biếu/tặng", min_value=0, value=data["1.1"])
    data["1.2"] = st.number_input("1.2. Trợ cấp xã hội, Covid-19, thiên tai,...", min_value=0, value=data["1.2"])
    data["1.3"] = st.number_input("1.3. Học bổng, thưởng giáo dục, trợ cấp y tế", min_value=0, value=data["1.3"])
    
    st.markdown("**2. THU TỪ TÀI SẢN / ĐẦU TƯ**")
    data["2.1"] = st.number_input("2.1. Cho thuê tài sản, đất đai, nhà ở", min_value=0, value=data["2.1"])
    data["2.2"] = st.number_input("2.2. Lãi đầu tư, tín dụng (tiết kiệm, cổ phần, cho vay...)", min_value=0, value=data["2.2"])
    
    st.markdown("**3. THU NHẬP KHÁC**")
    data["3.0"] = st.number_input("3.1. Khoản khác (trúng số, vui chơi có thưởng,...)", min_value=0, value=data["3.0"])

    hien_canh_bao_khong_tinh()

def tong_hop_phieu(ho_so: str, form_ver: int) -> dict:
    """Tổng hợp toàn bộ dữ liệu từ các mục."""
    tong = {}
    
    # Mục 1
    muc1_data = st.session_state.get(_key("muc1", ho_so, form_ver, "data"), [])
    tong["Muc1_ThuNhap"] = sum(d['luong'] + d['tro_cap'] for d in muc1_data)
    
    # Mục 2-6
    for muc in PHIEU_THU_NHAP_CONFIG:
        if muc["loai"] in ["nong_nghiep", "sxkd"]:
            if st.session_state.get(_key(muc['id'], ho_so, form_ver, "co_ko")) == "1. Có":
                muc_data = st.session_state.get(_key(muc['id'], ho_so, form_ver, "data"), [])
                thu_nhap_muc = 0
                for row in muc_data:
                    tong_thu = row.get('c1', 0) + row.get('c2', 0)
                    cp_vals = [row.get(f'cp_{j}', 0) for j in range(len(muc["chi_phi_cols"]))]
                    tong_chi_phi = sum(cp_vals)
                    thu_nhap_muc += (tong_thu - tong_chi_phi)
                tong[f"{muc['id'].title()}_ThuNhap"] = thu_nhap_muc
            else:
                tong[f"{muc['id'].title()}_ThuNhap"] = 0

    # Mục 7
    if st.session_state.get(_key("muc7", ho_so, form_ver, "co_ko")) == "1. Có":
        muc7_data = st.session_state.get(_key("muc7", ho_so, form_ver, "data"), {})
        tong["Muc7_ThuNhap"] = sum(muc7_data.values())
    else:
        tong["Muc7_ThuNhap"] = 0

    tong["TongThuNhap"] = sum(tong.get(k, 0) for k, _ in BAO_CAO_7_NGUON)
    
    return tong

def kiem_tra_validation_phieu(ho_so: str, form_ver: int) -> tuple[bool, list[str]]:
    """Xác thực lỗi cấu trúc số liệu trước khi cho phép bấm nút Lưu phiếu."""
    errors = []
    for muc in PHIEU_THU_NHAP_CONFIG:
        if muc["loai"] in ["nong_nghiep", "sxkd"] and st.session_state.get(_key(muc['id'], ho_so, form_ver, "co_ko")) == "1. Có":
            muc_data = st.session_state.get(_key(muc['id'], ho_so, form_ver, "data"), [])
            for row in muc_data:
                tong_thu = row.get('c1', 0) + row.get('c2', 0)
                cp_vals = [row.get(f'cp_{j}', 0) for j in range(len(muc["chi_phi_cols"]))]
                tong_chi_phi = sum(cp_vals)
                if tong_chi_phi > tong_thu:
                    errors.append(f"{muc['ten']} - '{row['nguon_thu']}': Chi phí ({tong_chi_phi:,.0f}) > Tổng trị giá ({tong_thu:,.0f}).")
    return not errors, errors
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
    *, ma_dtv: str, ho: pd.Series, nhan_khau: int, 
    tong_hop: dict, loc: dict | None, gps: dict, geo: dict, ghi_chu_vi_tri: str
) -> dict[str, Any]:
    """Ghi nhận xuất bản file JSON phiếu của hộ tương thích biểu mẫu QĐ 1099 lưu trữ."""
    tong_thu_nhap_nam = tong_hop.get("TongThuNhap", 0)
    
    row = {
        "MaDTV": ma_dtv,
        "HoSo": str(ho.get("HoSo")),
        "MaTKCS": str(ho.get("Huyen")),
        "Xa": str(ho.get("Xa")),
        "DiaBan": str(ho.get("DiaBan")),
        "MaDiaBan": geo.get("ma_dia_ban"),
        "TenChuHo": str(ho.get("TenChuHo")),
        "NhanKhauTT": nhan_khau,
        "TongThuNhap": tong_thu_nhap_nam,
        "ThuBQDauNguoi": round(tong_thu_nhap_nam / max(1, nhan_khau), 2)
    }

    # Thêm thu nhập chi tiết từng mục
    for k, _ in BAO_CAO_7_NGUON:
        row[k] = tong_hop.get(k, 0)
        
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

    return row


# ---------------------------------------------------------------------------
# 10. GIAO DIỆN PHƯƠNG THỨC ADMIN (HỆ THỐNG / CHỌN MẪU)
# ---------------------------------------------------------------------------
def page_login():
    """Giao diện cửa đăng nhập vai trò."""
    hien_thi_banner()
    left, col2, right = st.columns([1, 2, 1])
    with col2:
        with card_container("ĐĂNG NHẬP HỆ THỐNG"):
            vt = st.radio("Chọn vai trò của bạn", ["Điều tra viên", "Quản trị viên"], horizontal=True)
            if vt == "Quản trị viên":
                mk = st.text_input("Mật khẩu quản trị", type="password")
                if st.button("Đăng nhập (Quản trị)", type="primary", use_container_width=True):
                    if mk.strip().upper() == ADMIN_MA:
                        st.session_state["user"] = {"ma": ADMIN_MA, "role": "admin", "ten": "Tổng quản trị"}
                        st.rerun()
                    else:
                        st.error("Mật khẩu quản trị không chính xác.")
            else:
                ma = st.text_input("Mã Điều tra viên")
                mk = st.text_input("Mật khẩu", type="password")
                if st.button("Đăng nhập (ĐTV)", type="primary", use_container_width=True):
                    ok, loi, r = xac_thuc_dang_nhap(ma, mk)
                    if ok:
                        st.session_state["user"] = {"ma": ma, "role": "dtv", "ten": r.get("HoTen", "ĐTV")}
                        st.rerun()
                    else:
                        st.error(loi)

def admin_he_thong():
    """Bảng điều khiển gán danh sách và chọn mốc mẫu r, k."""
    st.write("### ⚙️ Cấu hình hệ thống và phân mẫu")
    t1, t2 = st.tabs(["📤 Tải lên danh sách hộ", "🎯 Thực hiện chọn mẫu"])
    
    with t1:
        f = st.file_uploader("Tải lên tệp Excel danh sách hộ", type=["xlsx", "xls"])
        if f and st.button("Tải lên và cập nhật"):
            df, thieu = doc_excel_danh_sach_ho(f, can_madtv=True)
            if df is not None:
                df[COL_PHAN_LOAI] = PHAN_LOAI_NEN
                if write_sheet_replace(SHEETS["danh_sach_ho"], df):
                    dong_bo_account_tu_ma_dtv(df["MaDTV"].unique().tolist())
                    st.success("Tải lên thành công. Các tài khoản ĐTV đã được tạo hoặc cập nhật.")
            else:
                st.error(f"Tệp Excel thiếu các cột bắt buộc: {', '.join(thieu)}")
                
    with t2:
        df_ho = read_sheet(SHEETS["danh_sach_ho"])
        if not df_ho.empty:
            dtv_codes = df_ho["MaDTV"].unique().tolist()
            ma = st.selectbox("Chọn ĐTV để phân mẫu", dtv_codes)
            nen = lay_danh_sach_nen(df_ho, ma)
            
            st.write(f"Điều tra viên '{ma}' đang quản lý **{len(nen)}** hộ.")
            c1, c2 = st.columns(2)
            k = c1.number_input("Bước nhảy (k)", min_value=1, max_value=100, value=2)
            r = c2.number_input("Vị trí bắt đầu (r)", min_value=1, max_value=max(1, len(nen)), value=1)
            
            if st.button("Thực hiện chọn mẫu"):
                chi_so = chon_chi_so_mau_tu_nen(len(nen), int(k), int(r), so_luong_can_chon=SO_HO_MAU)
                if not chi_so:
                    st.error("Số lượng hộ không đủ để chọn mẫu.")
                else:
                    df_da_phan = gan_phan_loai_ho(nen, chi_so)
                    df_out = cap_nhat_danh_sach_ho_theo_dtv(df_ho, ma, df_da_phan)
                    if write_sheet_replace(SHEETS["danh_sach_ho"], df_out):
                        st.success(f"Đã chọn thành công {SO_HO_MAU} hộ mẫu cho ĐTV {ma}.")
                        hien_dataframe_an_toan(df_da_phan)


# ---------------------------------------------------------------------------
# 11. ĐIỀU TRA VIÊN: LUỒNG THỰC THI NHẬP PHIẾU
# ---------------------------------------------------------------------------
def dtv_nhap_phieu():
    user = st.session_state["user"]
    ma_dtv = user["ma"]
    ver = st.session_state.get("form_ver", 0)
    
    st.write(f"### 📝 Nhập phiếu điều tra - ĐTV: **{ma_dtv}**")
    
    df_ho = ho_mau_can_dieu_tra(lay_danh_sach_nen(read_sheet(SHEETS["danh_sach_ho"], silent=True), ma_dtv))
    if df_ho.empty:
        st.warning("Bạn chưa được phân công hộ mẫu nào. Vui lòng liên hệ quản trị viên.")
        return
        
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    done = set(df_kq[df_kq["MaDTV"].astype(str) == str(ma_dtv)]["HoSo"].astype(str)) if not df_kq.empty else set()
    pending = df_ho[~df_ho["HoSo"].astype(str).isin(done)]
    
    if pending.empty:
        st.success("🎉 Chúc mừng! Bạn đã hoàn thành 100% số hộ được giao.")
        return
        
    idx = st.selectbox("Chọn hộ để bắt đầu điều tra", range(len(pending)), format_func=lambda i: f"Hộ {pending.iloc[i]['HoSo']} - {pending.iloc[i]['TenChuHo']}")
    ho = pending.iloc[idx]
    ho_so = str(ho['HoSo'])
    
    # Quản lý trạng thái tab và làm mới khi đổi hộ
    if "prev_hoso" not in st.session_state or st.session_state.prev_hoso != ho_so:
        st.session_state.prev_hoso = ho_so
        st.session_state.form_ver = ver + 1
        st.rerun()

    ver = st.session_state.form_ver # Lấy lại version mới nhất
    
    tabs_options = ["Phần A: Thông tin chung", "Phần B: Thu nhập", "Phần C: Tổng hợp"]
    active_tab = st.radio("Điều hướng:", tabs_options, horizontal=True, key=_key("main_tabs", ho_so, ver))

    if active_tab == "Phần A: Thông tin chung":
        with card_container("PHẦN A: THÔNG TIN CHUNG"):
            st.info(f"Hộ số: {ho_so} | Tên chủ hộ: {ho['TenChuHo']} | Địa bàn: {ho['DiaBan']}, {ho['Xa']}")
            
            # Nhân khẩu
            st.number_input(
                "Tổng số nhân khẩu thực tế thường trú (ổn định >6 tháng/năm)",
                min_value=1, max_value=30, value=1,
                key=_key("chung", ho_so, ver, "nhan_khau_tt")
            )
            
            # Thành viên
            thanh_vien = nhap_thanh_vien_ho(ho_so, ver)
            st.session_state[_key("chung", ho_so, ver, "thanh_vien")] = thanh_vien

    elif active_tab == "Phần B: Thu nhập":
        st.info("Đơn vị tính: 1.000 đồng/năm")
        for muc in PHIEU_THU_NHAP_CONFIG:
            if muc["loai"] != "thong_tin_chung":
                with card_container(muc["ten"]):
                    co_ko = st.radio(muc["cau_hoi"], ["1. Có", "2. Không"], index=1, horizontal=True, key=_key(muc["id"], ho_so, ver, "co_ko"))
                    
                    if co_ko == "1. Có":
                        if muc["loai"] == "luong":
                            thanh_vien = st.session_state.get(_key("chung", ho_so, ver, "thanh_vien"), [])
                            nhap_muc_1_luong(ho_so, ver, thanh_vien)
                        elif muc["loai"] in ["nong_nghiep", "sxkd"]:
                            nhap_muc_nong_nghiep_sxkd(muc["id"], muc["ten"], muc["chi_phi_cols"], ho_so, ver)
                        elif muc["loai"] == "khac":
                            nhap_muc_7_khac(ho_so, ver)

    elif active_tab == "Phần C: Tổng hợp":
        with card_container("BIỂU TỔNG HỢP THU NHẬP CỦA HỘ NĂM"):
            tong_hop = tong_hop_phieu(ho_so, ver)
            
            # Bảng tổng hợp
            df_tong_hop = pd.DataFrame([
                {"Nguồn thu nhập": name, "Tổng thu nhập (1.000 đồng/năm)": f"{tong_hop.get(key, 0):,.0f}"}
                for key, name in BAO_CAO_7_NGUON
            ])
            st.dataframe(df_tong_hop, hide_index=True, use_container_width=True)
            
            st.metric("TỔNG THU NHẬP CỦA HỘ NĂM (1.000 đồng)", f"{tong_hop.get('TongThuNhap', 0):,.0f}")
            
            ok, errors = kiem_tra_validation_phieu(ho_so, ver)
            if not ok:
                for e in errors:
                    st.error(e)
            
            nhan_khau = st.session_state.get(_key("chung", ho_so, ver, "nhan_khau_tt"), 1)
            loc = streamlit_geolocation() if streamlit_geolocation else None

            if st.button("💾 Gửi kết quả điều tra", type="primary", use_container_width=True, disabled=not ok):
                gps = phan_tich_vi_tri_gps(loc)
                geo = phan_tich_geofence(ho, loc)
                row = tao_dong_ket_qua_qd1099(
                    ma_dtv=ma_dtv, ho=ho, nhan_khau=nhan_khau,
                    tong_hop=tong_hop, loc=loc, gps=gps, geo=geo, ghi_chu_vi_tri=""
                )
                if append_ket_qua(row):
                    st.success("Gửi phiếu điều tra thành công!")
                    st.session_state.form_ver = ver + 1 
                    st.rerun()

# ---------------------------------------------------------------------------
# 12. RUNTIME GRAPHICS & TIẾN ĐỘ THỐNG KÊ (DASHBOARD)
# ---------------------------------------------------------------------------
def check_or_get_ket_qua() -> pd.DataFrame:
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    if df_kq.empty or len(df_kq) == 0:
        st.session_state["using_mock_statistics"] = True
        return pd.DataFrame() 
        
    st.session_state["using_mock_statistics"] = False
    numeric_cols = [k for k, _ in BAO_CAO_7_NGUON] + ["TongThuNhap", "ThuBQDauNguoi", "NhanKhauTT"]
    for col in numeric_cols:
        if col in df_kq.columns:
            df_kq[col] = pd.to_numeric(df_kq[col], errors="coerce").fillna(0.0)
            
    return df_kq

def render_admin_dashboard():
    st.write("### 📊 Bảng điều khiển (Dashboard)")
    
    df_kq = check_or_get_ket_qua()
    df_ho = read_sheet(SHEETS["danh_sach_ho"], silent=True)
    
    if st.session_state.get("using_mock_statistics", False):
        st.info("Chưa có dữ liệu. Giao diện đang hiển thị ở chế độ minh họa.")
        total_samples, completed, ratio = 0, 0, 0
    else:
        total_samples = len(ho_mau_can_dieu_tra(df_ho)) if not df_ho.empty else 0
        completed = len(df_kq) if not df_kq.empty else 0
        ratio = round(completed / max(1, total_samples) * 100, 1) if total_samples > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng số hộ mẫu", f"{total_samples} hộ")
    c2.metric("Số phiếu đã nhập", f"{completed} phiếu")
    c3.metric("Tỷ lệ hoàn thành", f"{ratio}%")
    
    if completed > 0:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.write("#### Phân bố thu nhập bình quân")
            fig_hist = px.histogram(
                df_kq, x="ThuBQDauNguoi", nbins=15, 
                labels={"ThuBQDauNguoi": "Thu nhập BQ/người/năm (1.000đ)"}
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
        with col_g2:
            st.write("#### Tỷ trọng các nguồn thu nhập")
            sources_data = []
            for key, name in BAO_CAO_7_NGUON:
                val = df_kq.get(key, pd.Series([0.0])).mean()
                sources_data.append({"Nguồn thu": name, "Giá trị bình quân (1.000đ)": val})
            
            df_sources = pd.DataFrame(sources_data).query("`Giá trị bình quân (1.000đ)` > 0")
            fig_pie = px.pie(
                df_sources, values="Giá trị bình quân (1.000đ)", names="Nguồn thu",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_pie, use_container_width=True)

def admin_tien_do():
    st.write("### 📈 Thống kê tiến độ điều tra")
    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    df_kq = read_sheet(SHEETS["ket_qua"])
    
    if df_ho.empty:
        st.warning("Chưa có dữ liệu danh sách hộ.")
        return
        
    df_mau = ho_mau_can_dieu_tra(df_ho)
    if df_mau.empty:
        st.info("Chưa có hộ nào được chọn mẫu.")
        return
        
    total_mau = len(df_mau)
    completed = len(df_kq) if not df_kq.empty else 0
    ton_dong = max(0, total_mau - completed)
    ti_le = round(completed / max(1, total_mau) * 100, 1)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mẫu được giao", f"{total_mau} hộ")
    col2.metric("Đã điều tra", f"{completed} phiếu")
    col3.metric("Còn lại", f"{ton_dong} hộ")
    col4.metric("Tỷ lệ đạt", f"{ti_le}%")
    
    t_dtv, t_xa = st.tabs(["👨‍💻 Thống kê theo ĐTV", "🏡 Thống kê theo xã"])
    
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
        df_show.columns = ["Mã ĐTV", "Số hộ được giao", "Số hộ đã nhập", "Còn lại", "Tỷ lệ (%)"]
        hien_dataframe_an_toan(df_show)
        
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
        df_show_xa.columns = ["Xã", "Số hộ được giao", "Số hộ đã nhập", "Còn lại", "Tỷ lệ (%)"]
        hien_dataframe_an_toan(df_show_xa)

def admin_thong_ke_tong_hop():
    st.write("### 📋 Phân tích và thống kê thu nhập")
    
    df_kq = check_or_get_ket_qua()
    if df_kq.empty:
        st.warning("Chưa có dữ liệu điều tra để thống kê.")
        return
        
    phan_to = st.radio("Thống kê theo", ["Huyện/Thị xã/Thành phố", "Xã/Phường"], horizontal=True)
    group_by_col = "MaTKCS" if "Huyện" in phan_to else "Xa"

    df_agg = df_kq.groupby(group_by_col).agg(
        SoHo=("HoSo", "count"),
        TongNhanKhau=("NhanKhauTT", "sum"),
        ThuNhapBQ_Ho=("TongThuNhap", "mean"),
        ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
    ).reset_index()

    st.write(f"#### Bảng tổng hợp theo {phan_to}")
    hien_dataframe_an_toan(df_agg)

    fig = px.bar(
        df_agg,
        x=group_by_col,
        y=["ThuNhapBQ_Ho", "ThuNhapBQ_DauNguoi"],
        barmode="group",
        labels={"value": "Thu nhập bình quân (1.000 đồng/năm)", "variable": "Chỉ tiêu"},
        title=f"Biểu đồ so sánh thu nhập theo {phan_to}"
    )
    st.plotly_chart(fig, use_container_width=True)


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
        hien_thi_banner()
        
        cols = st.columns([2, 4.5, 1.2])
        with cols[0]:
            st.markdown(f"""
            <div class="user-badge-card">
                <div class="avatar-circle">{user['ten'][:1].upper()}</div>
                <div>
                    <div class="user-title">{user['ten']}</div>
                    <div class="user-role">Vai trò: {user['role'].upper()} | ID: {user['ma']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with cols[1]:
            if user["role"] == "admin":
                menu_options = ["Dashboard", "Cài đặt hệ thống", "Tiến độ điều tra", "Thống kê & Phân tích"]
                st.session_state.admin_menu = st.radio("Menu Admin:", menu_options, horizontal=True, key="admin_menu_radio")
            else:
                st.markdown(f"""
                <div class="surveyor-badge">
                    <span class="status-dot">●</span> 
                    <span style="font-weight:700;">CHẾ ĐỘ ĐIỀU TRA VIÊN</span>
                </div>
                """, unsafe_allow_html=True)
                
        with cols[2]:
            if st.button("🚪 Đăng xuất", key="logout_btn", use_container_width=True, type="secondary"):
                st.session_state.clear()
                st.rerun()
                
    st.markdown('<div class="sticky-header-spacer"></div>', unsafe_allow_html=True)
    
    if user["role"] == "admin":
        active_view = st.session_state.get("admin_menu", "Dashboard")
        if active_view == "Dashboard":
            render_admin_dashboard()
        elif active_view == "Cài đặt hệ thống":
            admin_he_thong()
        elif active_view == "Tiến độ điều tra":
            admin_tien_do()
        else:
            admin_thong_ke_tong_hop()
    else:
        dtv_nhap_phieu()

if __name__ == "__main__":
    main()
