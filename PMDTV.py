# -*- coding: utf-8 -*-
"""
PMDTV.py — Phiếu hỏi điều tra thu nhập năm 2026 (Streamlit + Google Sheets).
Đã được tái cấu trúc giao diện sang dạng sidebar, dashboard hiện đại và
tuân thủ chặt chẽ Quyết định 1099/QĐ-BKHĐT.
"""
from __future__ import annotations

import io
import json
import re
import base64
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

NAVY_PRIMARY = "#0a2351"
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
        
        /* Custom CSS to fix layout issues */
        #MainMenu {{visibility: hidden !important;}}
        footer {{visibility: hidden !important;}}

        /* Ẩn header mặc định của Streamlit */
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        .stApp {{
            background: #f0f2f5;
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {NAVY_PRIMARY};
            padding: 1rem;
        }}
        [data-testid="stSidebar"] .stButton > button {{
             background-color: {NAVY_ACCENT};
             color: white;
             border-radius: 8px;
             width: 100%;
        }}
         [data-testid="stSidebar"] .stRadio > label {{
             font-size: 1.1rem;
             font-weight: 700;
             color: white;
             margin-bottom: 1rem;
        }}
        [data-testid="stSidebar"] .stRadio > div > label p {{
            color: white;
            font-size: 1.05rem;
            padding: 0.5rem 0;
        }}

        /* Default main content container */
        .main .block-container {{
            padding-top: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 95% !important;
            margin: 0 auto !important;
        }}
        
        /* Các thành phần UI */
        .card-box {{
            background: #ffffff;
            border-radius: 12px;
            padding: 1.35rem 1.6rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }}

        .user-badge-card {{
            display: flex;
            align-items: center;
            gap: 12px;
            background: {NAVY_ACCENT};
            padding: 12px 14px;
            border-radius: 10px;
            margin-bottom: 2rem;
        }}
        .avatar-circle {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: {NAVY_PRIMARY};
            background-color: white;
            font-weight: 700;
            font-size: 16px;
        }}
        .user-title {{
            font-size: 1rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
        }}
        .user-role {{
            font-size: 0.8rem;
            color: #d1d5db; /* Light gray for role */
            font-weight: 500;
            margin-top: 2px;
        }}
        
        div[data-testid="stMetric"] {{
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}
        div[data-testid="stMetric"] > div:nth-child(2) > div {{
            font-size: 2rem;
            font-weight: 700;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def hien_thi_banner() -> None:
    """Hiển thị ảnh banner của ứng dụng (ảnh này đã chứa sẵn tiêu đề)."""
    import os

    # CSS để xóa khoảng trắng phía trên, giúp banner nằm sát lề
    st.markdown("<style>.main .block-container { padding-top: 0rem !important; }</style>", unsafe_allow_html=True)

    image_path = "image/panel.png"
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
        # Thêm khoảng trống bên dưới banner để tách biệt với nội dung
        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)
    else:
        # Nếu không có ảnh, hiển thị tiêu đề dạng chữ và giữ lại khoảng trắng mặc định
        st.markdown("<style>.main .block-container { padding-top: 2rem !important; }</style>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center; color: {NAVY_PRIMARY}; font-weight: 700;'>HỆ THỐNG ĐIỀU TRA THU NHẬP HỘ</h2>", unsafe_allow_html=True)

@contextmanager
def card_container(title: str | None = None):
    """Khối nội dung trong thẻ card-box."""
    tieu_de = f"<h3 style='margin-bottom: 1rem; color: {NAVY_PRIMARY};'>{title}</h3>" if title else ""
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
        "chi_phi_cols": ["CP Giống", "CP Phân bón, BVTV", "CP Khác"]
    },
    {
        "id": "muc3", "ten": "Mục 3: Thu nhập từ chăn nuôi", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động chăn nuôi hoặc từ sản bắt, đánh bẫy, thuần dưỡng chim, thú không?",
        "chi_phi_cols": ["CP Giống", "CP Thức ăn, thuốc", "CP Khác"]
    },
    {
        "id": "muc4", "ten": "Mục 4: Thu nhập từ lâm nghiệp", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động lâm nghiệp không?",
        "chi_phi_cols": ["CP Giống", "CP Phân bón, BVTV", "CP Khác"]
    },
    {
        "id": "muc5", "ten": "Mục 5: Thu nhập từ thủy sản", "loai": "nong_nghiep",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động thủy sản không?",
        "chi_phi_cols": ["CP Giống", "CP Thức ăn, thuốc", "CP Khác"]
    },
    {
        "id": "muc6", "ten": "Mục 6: Thu nhập từ hoạt động SXKD phi nông, lâm nghiệp, thủy sản", "loai": "sxkd",
        "cau_hoi": "Trong 12 tháng qua hộ ông/bà có phát sinh thu nhập - chi phí từ hoạt động SXKD phi nông, lâm nghiệp, thủy sản của hộ không?",
        "chi_phi_cols": ["CP Nguyên vật liệu", "CP Năng lượng", "CP Khác"]
    },
    {
        "id": "muc7", "ten": "Mục 7: Thu nhập khác", "loai": "khac",
        "cau_hoi": "Trong 12 tháng qua, hộ ông/bà có nhận được các nguồn thu nhập nào khác không?"
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
CANH_BAO_GEO_VANG = "Vị trí hiện tại ở ngoài phạm vi địa bàn thôn/xóm. Hãy kiểm tra lại."
CANH_BAO_GEO_DO = "Cảnh báo: Tọa độ lệch quá lớn. Nghi vấn vị trí giả."

COL_HO = ["Huyen", "Xa", "DiaBan", "HoSo", "TenChuHo"]
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
    "huyen": "Huyen", "tinh": "Huyen", "tinhthanh": "Huyen", "matkcs": "MaTKCS",
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
@st.cache_data
def tai_danh_muc_san_pham():
    """Đọc và cache danh mục sản phẩm từ file JSON."""
    # Xác định thư mục chứa file PMDTV.py hiện tại
    base_dir = Path(__file__).resolve().parent
    # Tạo đường dẫn đầy đủ tới file json
    file_path = base_dir / "danh_muc_san_pham.json"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Lỗi: Không tìm thấy tệp tại: {file_path}")
        return {}
    except json.JSONDecodeError:
        st.error("Lỗi: Tệp 'danh_muc_san_pham.json' có định dạng không hợp lệ.")
        return {}
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
        if "MaTKCS" in df.columns and "MaTKCS" not in out_cols:
             out_cols.append("MaTKCS")
            
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

def nhap_muc_nong_nghiep_sxkd(muc: dict, ho_so: str, form_ver: int, danh_muc: dict):
    """Template cho các mục 2, 3, 4, 5, 6."""
    muc_id = muc["id"]
    chi_phi_cols = muc["chi_phi_cols"]
    key = _key(muc_id, ho_so, form_ver, "data")

    if key not in st.session_state:
        st.session_state[key] = []

    # Form thêm dòng mới
    st.markdown("---<br>**Thêm sản phẩm/hoạt động mới**", unsafe_allow_html=True)
    
    danh_muc_options = danh_muc.get(muc_id, []) + ["Khác"]
    lua_chon_sp = st.selectbox("Chọn từ danh mục", options=danh_muc_options, key=_key(muc_id, ho_so, form_ver, "sp_select"))
    nguon_thu_final = st.text_input("Hoặc nhập tên khác", key=_key(muc_id, ho_so, form_ver, "sp_khac")) if lua_chon_sp == "Khác" else lua_chon_sp

    st.markdown("**Nhập giá trị & chi phí tương ứng:**")
    cols = st.columns(2 + len(chi_phi_cols))
    c1 = cols[0].number_input("Giá trị bán/đổi", min_value=0, key=_key(muc_id, ho_so, form_ver, "c1_new"))
    c2 = cols[1].number_input("Giá trị tự dùng", min_value=0, key=_key(muc_id, ho_so, form_ver, "c2_new"))

    cp_values = []
    for i, cp_label in enumerate(chi_phi_cols):
        val = cols[2+i].number_input(cp_label, min_value=0, key=_key(muc_id, ho_so, form_ver, f"cp_{i}_new"))
        cp_values.append(val)

    if st.button(f"Lưu sản phẩm", key=_key(muc_id, ho_so, form_ver, "add_btn")):
        tong_thu = c1 + c2
        tong_chi_phi = sum(cp_values)
        
        if tong_chi_phi > tong_thu:
            hien_loi_validation(f"Cảnh báo: Chi phí ({tong_chi_phi:,.0f}) > Tổng trị giá ({tong_thu:,.0f}) của '{nguon_thu_final}'.")
        
        if nguon_thu_final.strip():
            new_row = {"nguon_thu": nguon_thu_final, "c1": c1, "c2": c2}
            for i, val in enumerate(cp_values):
                new_row[f"cp_{i}"] = val
            st.session_state[key].append(new_row)
            st.rerun()

    # Bảng hiển thị dữ liệu đã nhập
    if st.session_state[key]:
        st.markdown("---<br>**Bảng chi tiết các khoản thu đã nhập**", unsafe_allow_html=True)
        df_data = []
        for i, row in enumerate(st.session_state[key]):
            tong_thu = row['c1'] + row['c2']
            cp_vals = [row.get(f'cp_{j}', 0) for j in range(len(chi_phi_cols))]
            tong_chi_phi = sum(cp_vals)
            thu_nhap = tong_thu - tong_chi_phi
            
            display_row = {"Sản phẩm/Hoạt động": row['nguon_thu'], "Giá bán/đổi": row['c1'], "Giá tự dùng": row['c2'], "Tổng trị giá": tong_thu}
            for j, label in enumerate(chi_phi_cols):
                display_row[label] = cp_vals[j]
            display_row["Tổng chi phí"] = tong_chi_phi
            display_row["Thu nhập thuần"] = thu_nhap
            display_row["xoa"] = i # Index để xóa
            df_data.append(display_row)

        df_display = pd.DataFrame(df_data)
        st.data_editor(
            df_display,
            column_config={
                "xoa": st.column_config.ButtonColumn("Xóa", help="Xóa dòng này")
            },
            disabled=df_display.columns.drop("xoa"),
            hide_index=True,
            key=_key(muc_id, ho_so, form_ver, "editor")
        )

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
    if st.session_state.get(_key("muc1", ho_so, form_ver, "co_ko")) == "1. Có":
        muc1_data = st.session_state.get(_key("muc1", ho_so, form_ver, "data"), [])
        tong["Muc1_ThuNhap"] = sum(d['luong'] + d['tro_cap'] for d in muc1_data)
    else:
        tong["Muc1_ThuNhap"] = 0
    
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
# 10. GIAO DIỆN CÁC TRANG
# ---------------------------------------------------------------------------
def page_login():
    """Giao diện trang đăng nhập đã được đơn giản hóa."""
    # Xóa khoảng trắng trên cùng cho trang đăng nhập
    st.markdown("<style>.block-container { padding-top: 2rem !important; }</style>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: {NAVY_PRIMARY};'>HỆ THỐNG ĐIỀU TRA THU NHẬP HỘ</h1>", unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        with card_container("Đăng nhập"):
            vt = st.radio("Vai trò", ["Điều tra viên", "Quản trị viên"], horizontal=True, label_visibility="collapsed")
            if vt == "Quản trị viên":
                mk = st.text_input("Mật khẩu quản trị", type="password")
                if st.button("Đăng nhập Quản trị", type="primary", use_container_width=True):
                    if mk.strip().upper() == ADMIN_MA:
                        st.session_state["user"] = {"ma": ADMIN_MA, "role": "admin", "ten": "Quản trị viên"}
                        st.rerun()
                    else:
                        st.error("Mật khẩu không đúng.")
            else:
                ma = st.text_input("Mã Điều tra viên (ĐTV)")
                mk = st.text_input("Mật khẩu ĐTV", type="password")
                if st.button("Đăng nhập ĐTV", type="primary", use_container_width=True):
                    ok, loi, r = xac_thuc_dang_nhap(ma, mk)
                    if ok:
                        st.session_state["user"] = {"ma": ma, "role": "dtv", "ten": r.get("HoTen", f"ĐTV {ma}")}
                        st.rerun()
                    else:
                        st.error(loi)

def admin_dashboard():
    """Trang Dashboard chính của Admin."""
    hien_thi_banner()
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    df_ho = read_sheet(SHEETS["danh_sach_ho"], silent=True)

    total_mau = len(ho_mau_can_dieu_tra(df_ho)) if not df_ho.empty else 0
    completed = len(df_kq) if not df_kq.empty else 0
    pending = total_mau - completed
    ratio = round(completed / max(1, total_mau) * 100, 1) if total_mau > 0 else 0
    avg_income = df_kq['TongThuNhap'].mean() if completed > 0 else 0

    st.markdown("### Tổng quan tiến độ")
    cols = st.columns(4)
    cols[0].metric("Hộ đã điều tra", f"{completed}")
    cols[1].metric("Hộ chưa làm", f"{pending}")
    cols[2].metric("Thu nhập TB/Hộ", f"{avg_income:,.0f}")
    cols[3].metric("Tỷ lệ hoàn thành", f"{ratio}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Phân tích nhanh")
    if completed > 0:
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Phân bố thu nhập BQ/người**")
            fig_hist = px.histogram(df_kq, x="ThuBQDauNguoi", nbins=15, labels={"ThuBQDauNguoi": "Thu nhập (nghìn đ/năm)"})
            st.plotly_chart(fig_hist, use_container_width=True)
        with col2:
            st.write("**Cơ cấu các nguồn thu nhập**")
            sources_data = [{
                "Nguồn": name.split('. ')[1],
                "Giá trị TB": df_kq.get(key, pd.Series([0.0])).mean()
            } for key, name in BAO_CAO_7_NGUON]
            df_sources = pd.DataFrame(sources_data).query("`Giá trị TB` > 0")
            fig_pie = px.pie(df_sources, values="Giá trị TB", names="Nguồn")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu để hiển thị biểu đồ.")

def admin_he_thong():
    """Bảng điều khiển gán danh sách và chọn mốc mẫu r, k."""
    st.markdown("### ⚙️ Cấu hình hệ thống và phân mẫu")
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
            dtv_codes = [c for c in df_ho["MaDTV"].unique().tolist() if c]
            ma = st.selectbox("Chọn ĐTV để phân mẫu", dtv_codes)
            if ma:
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

def admin_tien_do():
    """Trang thống kê tiến độ và kết quả chi tiết."""
    st.markdown("### 📈 Thống kê & Phân tích chi tiết")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Tiến độ hoàn thành", "📋 Thông tin chi tiết hộ", "🏡 Tổng hợp theo xã", "🏢 Tổng hợp theo TKCS"])

    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    df_kq = read_sheet(SHEETS["ket_qua"])
    
    with tab1:
        st.subheader("Tiến độ hoàn thành theo ĐTV và Xã")
        if df_ho.empty:
            st.warning("Chưa có dữ liệu danh sách hộ.")
        else:
            df_mau = ho_mau_can_dieu_tra(df_ho)
            if df_mau.empty:
                st.info("Chưa có hộ nào được chọn mẫu.")
            else:
                t_dtv, t_xa = st.tabs(["👨‍💻 Theo Điều tra viên (ĐTV)", "🏡 Theo Xã"])
                with t_dtv:
                    df_mau_dtv = df_mau.groupby("MaDTV").size().reset_index(name="Giao")
                    df_done_dtv = df_kq.groupby("MaDTV").size().reset_index(name="Hoàn thành") if not df_kq.empty else pd.DataFrame(columns=["MaDTV", "Hoàn thành"])
                    df_tien_do = pd.merge(df_mau_dtv, df_done_dtv, on="MaDTV", how="left").fillna(0)
                    df_tien_do["Hoàn thành"] = df_tien_do["Hoàn thành"].astype(int)
                    df_tien_do["Còn lại"] = (df_tien_do["Giao"] - df_tien_do["Hoàn thành"]).clip(lower=0).astype(int)
                    df_tien_do["Tỷ lệ (%)"] = (df_tien_do["Hoàn thành"] / df_tien_do["Giao"] * 100).round(1)
                    st.dataframe(df_tien_do, use_container_width=True, hide_index=True)
                with t_xa:
                    df_mau_xa = df_mau.groupby("Xa").size().reset_index(name="Giao")
                    df_done_xa = df_kq.groupby("Xa").size().reset_index(name="Hoàn thành") if not df_kq.empty else pd.DataFrame(columns=["Xa", "Hoàn thành"])
                    df_tien_do_xa = pd.merge(df_mau_xa, df_done_xa, on="Xa", how="left").fillna(0)
                    df_tien_do_xa["Hoàn thành"] = df_tien_do_xa["Hoàn thành"].astype(int)
                    df_tien_do_xa["Còn lại"] = (df_tien_do_xa["Giao"] - df_tien_do_xa["Hoàn thành"]).clip(lower=0).astype(int)
                    df_tien_do_xa["Tỷ lệ (%)"] = (df_tien_do_xa["Hoàn thành"] / df_tien_do_xa["Giao"] * 100).round(1)
                    st.dataframe(df_tien_do_xa, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Bảng chi tiết kết quả điều tra")
        if df_kq.empty:
            st.info("Chưa có phiếu nào được ghi nhận.")
        else:
            col1, col2 = st.columns(2)
            xa_filter = col1.multiselect("Lọc theo Xã", df_kq['Xa'].unique())
            dtv_filter = col2.multiselect("Lọc theo ĐTV", df_kq['MaDTV'].unique())
            
            df_filtered = df_kq.copy()
            if xa_filter:
                df_filtered = df_filtered[df_filtered['Xa'].isin(xa_filter)]
            if dtv_filter:
                df_filtered = df_filtered[df_filtered['MaDTV'].isin(dtv_filter)]
                
            hien_dataframe_an_toan(df_filtered)

    with tab3:
        st.subheader("Tổng hợp thu nhập bình quân theo Xã")
        if not df_kq.empty:
            df_kq['TongThuNhap'] = pd.to_numeric(df_kq['TongThuNhap'], errors='coerce').fillna(0)
            df_kq['ThuBQDauNguoi'] = pd.to_numeric(df_kq['ThuBQDauNguoi'], errors='coerce').fillna(0)
            df_agg = df_kq.groupby("Xa").agg(
                SoHo=("HoSo", "count"),
                ThuNhapBQ_Ho=("TongThuNhap", "mean"),
                ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
            ).reset_index()
            hien_dataframe_an_toan(df_agg)
            fig = px.bar(df_agg, x="Xa", y=["ThuNhapBQ_Ho", "ThuNhapBQ_DauNguoi"], barmode="group", title="So sánh thu nhập bình quân theo Xã")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu để tổng hợp.")

    with tab4:
        st.subheader("Tổng hợp thu nhập bình quân theo Tỉnh/Huyện (TKCS)")
        if not df_kq.empty:
            df_kq['TongThuNhap'] = pd.to_numeric(df_kq['TongThuNhap'], errors='coerce').fillna(0)
            df_kq['ThuBQDauNguoi'] = pd.to_numeric(df_kq['ThuBQDauNguoi'], errors='coerce').fillna(0)
            df_agg = df_kq.groupby("MaTKCS").agg(
                SoHo=("HoSo", "count"),
                ThuNhapBQ_Ho=("TongThuNhap", "mean"),
                ThuNhapBQ_DauNguoi=("ThuBQDauNguoi", "mean")
            ).reset_index()
            hien_dataframe_an_toan(df_agg)
            fig = px.bar(df_agg, x="MaTKCS", y=["ThuNhapBQ_Ho", "ThuNhapBQ_DauNguoi"], barmode="group", title="So sánh thu nhập bình quân theo TKCS")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu để tổng hợp.")

def dtv_nhap_phieu():
    """Trang nhập liệu cho Điều tra viên."""
    st.markdown(f"### 📝 Nhập phiếu điều tra")
    user = st.session_state["user"]
    ma_dtv = user["ma"]
    form_ver = st.session_state.get("form_ver", 0)
    
    df_ho = ho_mau_can_dieu_tra(lay_danh_sach_nen(read_sheet(SHEETS["danh_sach_ho"], silent=True), ma_dtv))
    if df_ho.empty:
        st.warning("Bạn chưa được phân công hộ mẫu nào."); return
        
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    done_hoso = set(df_kq[df_kq["MaDTV"].astype(str) == str(ma_dtv)]["HoSo"].astype(str)) if not df_kq.empty else set()
    pending_ho = df_ho[~df_ho["HoSo"].astype(str).isin(done_hoso)]
    
    if pending_ho.empty:
        st.success("🎉 Chúc mừng! Bạn đã hoàn thành 100% số hộ được giao."); return
        
    idx = st.selectbox("Chọn hộ để điều tra", range(len(pending_ho)), format_func=lambda i: f"Hộ {pending_ho.iloc[i]['HoSo']} - {pending_ho.iloc[i]['TenChuHo']}")
    ho = pending_ho.iloc[idx]
    ho_so = str(ho['HoSo'])
    
    if st.session_state.get("current_hoso") != ho_so:
        st.session_state.current_hoso = ho_so
        st.session_state.form_ver = form_ver + 1
        st.session_state.active_section_index = 0
        st.rerun()

    form_ver = st.session_state.form_ver 
    danh_muc = tai_danh_muc_san_pham()
    section_index = st.session_state.get('active_section_index', 0)

    # ---- Render UI ----
    with card_container("Phần A: Thông tin chung"):
        st.info(f"Hộ số: {ho_so} | Chủ hộ: {ho['TenChuHo']} | Địa bàn: {ho['DiaBan']}, {ho['Xa']}")
        st.number_input("Tổng số nhân khẩu thực tế thường trú", min_value=1, value=1, key=_key("A", ho_so, form_ver, "nhan_khau"))
        thanh_vien = nhap_thanh_vien_ho(ho_so, form_ver)
        st.session_state[_key("A", ho_so, form_ver, "thanh_vien")] = thanh_vien
        if st.button("Lưu và tiếp tục sang Phần B", type="primary"):
            st.session_state.active_section_index = 1
            st.rerun()
    
    if section_index > 0:
        st.header("Phần B: Thu nhập (Đơn vị: 1.000 đồng/năm)")
        for i, muc in enumerate(PHIEU_THU_NHAP_CONFIG[1:], 1):
            with st.expander(muc["ten"], expanded=(section_index == i)):
                co_ko = st.radio(muc["cau_hoi"], ["1. Có", "2. Không"], index=1, horizontal=True, key=_key(muc["id"], ho_so, form_ver, "co_ko"))
                if co_ko == "1. Có":
                    if muc["loai"] == "luong": nhap_muc_1_luong(ho_so, form_ver, thanh_vien)
                    elif muc["loai"] in ["nong_nghiep", "sxkd"]: nhap_muc_nong_nghiep_sxkd(muc, ho_so, form_ver, danh_muc)
                    elif muc["loai"] == "khac": nhap_muc_7_khac(ho_so, form_ver)
                
                nav_cols = st.columns([1,1,1])
                if i > 1 and nav_cols[0].button(f"⬅️ Quay lại", key=f"back_{i}"):
                    st.session_state.active_section_index = i - 1; st.rerun()
                if i < len(PHIEU_THU_NHAP_CONFIG) - 1 and nav_cols[2].button(f"Tiếp theo ➡️", key=f"next_{i}"):
                    st.session_state.active_section_index = i + 1; st.rerun()
                elif i == len(PHIEU_THU_NHAP_CONFIG) - 1 and nav_cols[2].button(f"➡️ Tới Phần C: Tổng hợp", key=f"next_{i}", type="primary"):
                    st.session_state.active_section_index = -1; st.rerun()

    if section_index == -1:
        st.header("Phần C: Tổng hợp & Gửi phiếu")
        with card_container():
            tong_hop = tong_hop_phieu(ho_so, form_ver)
            st.dataframe(pd.DataFrame([{"Nguồn thu nhập": n, "Tổng (1.000đ/năm)": f"{tong_hop.get(k, 0):,.0f}"} for k, n in BAO_CAO_7_NGUON]), hide_index=True)
            st.metric("TỔNG THU NHẬP CỦA HỘ (1.000đ/năm)", f"{tong_hop.get('TongThuNhap', 0):,.0f}")

            ok, errors = kiem_tra_validation_phieu(ho_so, form_ver)
            if not ok: [st.error(e) for e in errors]

            if st.button("💾 Gửi kết quả", type="primary", use_container_width=True, disabled=not ok):
                loc = streamlit_geolocation() if streamlit_geolocation else None
                gps = phan_tich_vi_tri_gps(loc); geo = phan_tich_geofence(ho, loc)
                row = tao_dong_ket_qua_qd1099(ma_dtv=ma_dtv, ho=ho, nhan_khau=st.session_state.get(_key("A", ho_so, form_ver, "nhan_khau"), 1), tong_hop=tong_hop, loc=loc, gps=gps, geo=geo, ghi_chu_vi_tri="")
                if append_ket_qua(row):
                    st.success("Gửi phiếu thành công!")
                    st.session_state.form_ver += 1; st.session_state.active_section_index = 0; st.rerun()


# ---------------------------------------------------------------------------
# 11. MAIN ENTRY POINT (ĐIỀU HƯỚNG ROUTING)
# ---------------------------------------------------------------------------
def main():
    if "user" not in st.session_state:
        page_login()
        return
        
    user = st.session_state["user"]

    with st.sidebar:
        st.markdown(f"""
        <div class="user-badge-card">
            <div class="avatar-circle">{user['ten'][:1].upper()}</div>
            <div>
                <div class="user-title">{user['ten']}</div>
                <div class="user-role">{user['role'].upper()}: {user['ma']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if user["role"] == "admin":
            menu_options = {
                "🏠 Dashboard": admin_dashboard,
                "📈 Tiến độ & Thống kê": admin_tien_do,
                "⚙️ Hệ thống": admin_he_thong,
            }
        else:
            menu_options = {
                "📝 Nhập phiếu": dtv_nhap_phieu,
            }
        
        selected_page = st.radio("Menu chính", menu_options.keys())

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất"):
            st.session_state.clear()
            st.rerun()

    # Render the selected page
    page_function = menu_options[selected_page]
    page_function()


if __name__ == "__main__":
    main()
