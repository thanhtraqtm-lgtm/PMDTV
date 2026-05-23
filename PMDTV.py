# -*- coding: utf-8 -*-
"""
PMDTV.py — Phiếu hỏi điều tra thu nhập năm 2026 (Streamlit + Google Sheets).
Bản Full Code đầy đủ tất cả các tính năng nghiệp vụ và sửa lỗi hệ thống.
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

# --- THƯ VIỆN ĐỊA LÝ & GPS ---
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

# --- 1. CẤU HÌNH KẾT NỐI (DÙNG SECRETS) ---
_GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def _gspread_client():
    """Khởi tạo gspread client an toàn từ Streamlit Secrets."""
    json_key = json.loads(st.secrets["gcp_service_account"]["json"])
    creds = Credentials.from_service_account_info(json_key, scopes=_GSHEETS_SCOPES)
    return gspread.authorize(creds)

def _open_spreadsheet():
    """Mở file spreadsheet bằng URL từ Secrets."""
    gc = _gspread_client()
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return gc.open_by_url(url)

def _service_account_email() -> str:
    """Lấy email an toàn từ JSON trong Secrets."""
    json_data = st.secrets["gcp_service_account"]["json"]
    if isinstance(json_data, str):
        json_key = json.loads(json_data)
    else:
        json_key = json_data
    return str(json_key.get("client_email", "")).strip()

def _project_root() -> Path:
    return Path(__file__).resolve().parent

def _gsheets_cfg() -> dict:
    return dict(st.secrets["connections"]["gsheets"])

def _spreadsheet_url() -> str:
    root = _project_root()
    url_file = root / "gsheets_url.txt"
    if url_file.exists():
        for line in url_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    cfg = _gsheets_cfg()
    url = cfg.get("spreadsheet_url") or cfg.get("spreadsheet")
    if not url:
        raise KeyError("Thiếu link spreadsheet trong secrets.toml hoặc gsheets_url.txt.")
    url = str(url).strip()
    if "?" in url: url = url.split("?", 1)[0]
    if "#" in url: url = url.split("#", 1)[0]
    return url

# ---------------------------------------------------------------------------
# Cấu hình trang & giao diện CSS
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

def render_header(title=""):
    """
    Hiển thị ảnh panel sát đỉnh. 
    Phần dash-header đã được xóa bỏ để giao diện mỏng gọn hơn.
    """
    st.markdown('<div class="sticky-header">', unsafe_allow_html=True)
    try:
        st.image("image/panel.png", use_container_width=True)
    except:
        pass
    # XÓA HOẶC COMMENT ĐOẠN st.markdown f'''...''' CHỨA dash-header TẠI ĐÂY
    st.markdown('</div>', unsafe_allow_html=True)

def apply_custom_style() -> None:
    """Giao diện Navy tối giản — ép ảnh lên sát đỉnh và loại bỏ header dày."""
    st.markdown(
        f"""
        <style>
        /* 1. Ẩn thanh header/toolbar mặc định */
        [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
        
        /* 2. Loại bỏ khoảng cách đỉnh trang của Streamlit */
        .stAppViewContainer, .block-container {{ padding-top: 0px !important; }}
        
        /* 3. Cố định ảnh Panel ở đỉnh */
        .sticky-header {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            z-index: 99999 !important;
            background: #ffffff !important;
        }}

        /* 4. Đẩy nội dung xuống - CẬP NHẬT: tác động vào cả .main và .stMain */
        .main, .stMain, [data-testid="stAppViewContainer"] {{ padding-top: 70px !important; }}

        /* 5. ẨN HOÀN TOÀN dash-header (tiêu đề cũ) */
        .dash-header {{ display: none !important; }}
        
        /* Style các thành phần còn lại */
        :root {{ --navy: {NAVY_PRIMARY}; --navy-accent: {NAVY_ACCENT}; --navy-light: {NAVY_LIGHT}; }}
        .stApp {{ background: linear-gradient(165deg, #f4f7fb 0%, #ffffff 55%); }}
        [data-testid="stSidebar"] {{ background-color: {NAVY_LIGHT}; border-right: 1px solid #c5d0de; }}
        div[data-testid="stMetric"] {{ background: #fff; padding: 0.65rem 0.85rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(13, 33, 55, 0.06); border: 1px solid #e8edf3; }}
        .card-box {{ background: #ffffff; padding: 1.25rem; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.04); border: 1px solid #eef2f6; margin-bottom: 1rem; }}
        .input-loi-do {{ color: #c62828; font-size: 0.85rem; margin: 2px 0 0; font-weight: 500; }}
        .canh-bao-vang {{ background-color: #fff9c4; color: #f57f17; padding: 6px 10px; border-radius: 5px; font-size: 0.85rem; font-weight: 500; }}
        .canh-bao-do {{ background-color: #ffcdd2; color: #c62828; padding: 6px 10px; border-radius: 5px; font-size: 0.85rem; font-weight: 500; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

@contextmanager
def card_container(title: str | None = None):
    tieu_de = f"<p style='margin:0 0 0.75rem;font-weight:600;color:{NAVY_PRIMARY};'>{title}</p>" if title else ""
    st.markdown(f'<div class="card-box">{tieu_de}', unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)

apply_custom_style()

SHEETS = {
    "account": "Account",
    "danh_sach_dtv": "DanhSachĐTV",
    "danh_sach_ho": "DanhSachHo",
    "phan_cong": "PhanCong",
    "ket_qua": "KetQua",
}

# --- QĐ 1099 / Nghiệp vụ 7 Nguồn thu nhập ---
ADMIN_MA = "ADMIN"
TRANG_THAI_MK_CHUA = "Chưa đổi mật khẩu"
TRANG_THAI_MK_DA = "Đã đổi mật khẩu"
CANH_BAO_KHONG_TINH = "KHÔNG tính tiền bán đất, rút tiết kiệm, vay nợ, đền bù giải tỏa vào thu nhập."

LINH_VUC_NLN_TS: list[tuple[str, str]] = [
    ("TrongTrot", "Trồng trọt"),
    ("ChanNuoi", "Chăn nuôi"),
    ("LamNghiep", "Lâm nghiệp"),
    ("ThuySan", "Thủy sản"),
]

BAO_CAO_7_NGUON: list[tuple[str, str]] = [
    ("ThuLuong", "1. Tiền lương, tiền công, phụ cấp, thưởng"),
    ("Thu_TrongTrot", "2.1 Trồng trọt (thuần)"),
    ("Thu_ChanNuoi", "2.2 Chăn nuôi (thuần)"),
    ("Thu_LamNghiep", "2.3 Lâm nghiệp (thuần)"),
    ("Thu_ThuySan", "2.4 Thủy sản (thuần)"),
    ("Thu_SXKD", "3. SXKD phi nông nghiệp (thuần)"),
    ("ThuKhac", "4. Thu nhập khác"),
]

CHI_TIEU_PHAN_B: list[dict[str, Any]] = [
    {"ma": "ThuLuong", "ten": "1. Tiền lương, tiền công, phụ cấp, thưởng", "loai": "luong"},
    {"ma": "TrongTrot", "ten": "2.1 Trồng trọt", "loai": "linh_vuc_sp"},
    {"ma": "ChanNuoi", "ten": "2.2 Chăn nuôi", "loai": "linh_vuc_sp"},
    {"ma": "LamNghiep", "ten": "2.3 Lâm nghiệp", "loai": "linh_vuc_sp"},
    {"ma": "ThuySan", "ten": "2.4 Thủy sản", "loai": "linh_vuc_sp"},
    {"ma": "SXKD", "ten": "3. Sản xuất kinh doanh phi nông nghiệp", "loai": "sxkd"},
    {"ma": "ThuKhac", "ten": "4. Thu nhập khác", "loai": "khac"},
]

map_chi_tieu = {m["ma"]: m for m in CHI_TIEU_PHAN_B}

SAN_PHAM_LINH_VUC: dict[str, list[str]] = {
    "TrongTrot": ["Lúa", "Ngô", "Rau màu", "Cây ăn quả", "Cây công nghiệp", "Khác"],
    "ChanNuoi": ["Gia súc", "Gia cầm", "Vịt ngan", "Khác"],
    "LamNghiep": ["Khai thác gỗ", "Trồng rừng", "Thu hái lâm sản", "Khác"],
    "ThuySan": ["Nuôi cá", "Nuôi tôm", "Nuôi cua", "Khai thác thủy sản", "Khác"],
}

O_NHAP_SAN_PHAM = ["Giá bán", "Tự dùng", "Giống", "Thức ăn", "Chi khác"]

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

NHAN_HIEN_THI = {
    "Huyen": "Huyện", "Xa": "Xã", "DiaBan": "Địa bàn", "HoSo": "Hộ số", "TenChuHo": "Tên chủ hộ",
    "MaDTV": "Mã ĐTV", "PhanLoai": "Phân loại", "HoTen": "Họ và tên", "TrangThai": "Trạng thái",
    "NgayPhanCong": "Ngày phân công", "ThuLuong": "Tiền lương, tiền công (nghìn đồng/tháng)",
    "ThuNN": "Thu nông nghiệp (nghìn đồng/tháng)", "ChiNN": "Chi phí sản xuất NN (nghìn đồng/tháng)",
    "ThuNNThuan": "Thu nhập thuần nông nghiệp", "ThuSXKD": "Thu nhập SXKD phi NN", "ThuKhac": "Thu nhập khác",
    "TongThuNhap": "Tổng thu nhập hộ (nghìn đồng/tháng)", "GPS_lat": "Vĩ độ GPS", "GPS_lng": "Kinh độ GPS",
    "DoChinhXac": "Độ chính xác (m)", "Xac_Thuc_GPS": "Xác thực GPS", "Sai_so": "Sai số GPS (m)",
    "Do_cao": "Độ cao (m)", "IP": "Địa chỉ IP", "MockGPS": "Nghi ngờ vị trí giả", "NgayNhap": "Ngày nhập phiếu",
    "Tong": "Tổng số hộ", "Xong": "Đã hoàn thành", "PhanTram": "Tỷ lệ hoàn thành (%)", "SoPhieu": "Số phiếu",
    "NganhKT": "Ngành kinh tế", "MatKhau": "Mật khẩu", "NhanKhauTT": "Số nhân khẩu thường trú",
    "DT_TrongTrot": "DT trồng trọt", "CP_TrongTrot": "CP trồng trọt", "Thu_TrongTrot": "Thuần trồng trọt",
    "DT_ChanNuoi": "DT chăn nuôi", "CP_ChanNuoi": "CP chăn nuôi", "Thu_ChanNuoi": "Thuần chăn nuôi",
    "DT_LamNghiep": "DT lâm nghiệp", "CP_LamNghiep": "CP lâm nghiệp", "Thu_LamNghiep": "Thuần lâm nghiệp",
    "DT_ThuySan": "DT thủy sản", "CP_ThuySan": "CP thủy sản", "Thu_ThuySan": "Thuần thủy sản",
    "DT_SXKD": "DT SXKD phi NN", "CP_SXKD": "CP SXKD phi NN", "Thu_SXKD": "Thuần SXKD phi NN",
    "ThuBQDauNguoi": "Thu nhập bình quân đầu người", "DiaChi": "Địa chỉ", "KhoangCachLech": "Khoảng cách lệch (m)",
    "MaDiaBan": "Mã địa bàn", "GhiChuViTri": "Ghi chú vị trí lệch",
}

def _bo_dau_chuoi(s: str) -> str:
    s = str(s).strip().replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s_\-]+", "", s.lower())
    return s

ANH_XA_TEN_COT: dict[str, str] = {
    "huyen": "Huyen", "tinh": "Huyen", "tinhthanh": "Huyen", "xa": "Xa", "xaphuong": "Xa", "phuongxa": "Xa",
    "diaban": "DiaBan", "diahinh": "DiaBan", "hoso": "HoSo", "soho": "HoSo", "hosodemau": "HoSo", "mahodiem": "HoSo",
    "tenchuho": "TenChuHo", "tenchu": "TenChuHo", "chuho": "TenChuHo", "madtv": "MaDTV", "phanloai": "PhanLoai",
    "phanloaiho": "PhanLoai", "madieutravien": "MaDTV", "hoten": "HoTen", "hovaten": "HoTen", "tendieutravien": "HoTen",
    "trangthai": "TrangThai", "ngayphancong": "NgayPhanCong", "thuluong": "ThuLuong", "thunn": "ThuNN", "chinn": "ChiNN",
    "thunnthuan": "ThuNNThuan", "thusxkd": "ThuSXKD", "thukhac": "ThuKhac", "tongthunhap": "TongThuNhap",
    "gpslat": "GPS_lat", "gpslong": "GPS_lng", "kinhdo": "GPS_lng", "vido": "GPS_lat", "dochinhxac": "DoChinhXac",
    "accuracy": "Sai_so", "saiso": "Sai_so", "docao": "Do_cao", "altitude": "Do_cao", "xacthucgps": "Xac_Thuc_GPS",
    "mockgps": "MockGPS", "ngaynhap": "NgayNhap", "nganhkt": "NganhKT", "nganhkinhte": "NganhKT", "matkhau": "MatKhau",
    "nhankhau": "NhanKhauTT", "nhankhautt": "NhanKhauTT", "sonhankhau": "NhanKhauTT", "thunhapbinhquandaunguoi": "ThuBQDauNguoi",
    "thubinhquandaunguoi": "ThuBQDauNguoi", "diachi": "DiaChi", "diachiho": "DiaChi", "diachicutru": "DiaChi",
    "khoangcachlech": "KhoangCachLech", "madiaaban": "MaDiaBan", "madiaban": "MaDiaBan", "madb": "MaDiaBan",
    "ghichuvitri": "GhiChuViTri", "ghichu": "GhiChuViTri", "lydolech": "GhiChuViTri",
}

def chuan_hoa_ten_cot_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    rename: dict[str, str] = {}
    for c in df.columns:
        key = _bo_dau_chuoi(str(c))
        if key in ANH_XA_TEN_COT:
            rename[c] = ANH_XA_TEN_COT[key]
    return df.rename(columns=rename)

def hien_thi_bang(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    m = {c: NHAN_HIEN_THI.get(c, c) for c in df.columns}
    return df.rename(columns=m)

def chuan_hoa_gia_tri_hien_thi(val: Any) -> Any:
    if val is None or (isinstance(val, float) and pd.isna(val)): return ""
    if hasattr(val, "item"):
        try: val = val.item()
        except (ValueError, AttributeError): pass
    if isinstance(val, float) and val == int(val): return int(val)
    if isinstance(val, (int, float, str, bool)): return val
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "<na>") else s

def chuan_hoa_df_hien_thi(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(chuan_hoa_gia_tri_hien_thi)
    return out

def df_an_toan_hien_thi(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
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
    if df is None or df.empty:
        st.caption("Chưa có dữ liệu.")
        return
    hien = hien_thi_bang(df_an_toan_hien_thi(df))
    st.dataframe(hien, use_container_width=True, hide_index=an_index)

def hien_bang_ngang(df: pd.DataFrame) -> None:
    hien_dataframe_an_toan(df)

def doc_excel_danh_sach_ho(file, *, can_madtv: bool = False) -> tuple[pd.DataFrame | None, list[str]]:
    raw = pd.read_excel(file, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]
    df = chuan_hoa_ten_cot_df(raw)
    
    if "ten_vi" not in st.session_state:
        st.session_state.ten_vi = {
            "Huyen": "Mã TKCS", "Xa": "Xã", "DiaBan": "Tên địa bàn",
            "MaDiaBan": "Mã địa bàn", "HoSo": "Hộ số", "TenChuHo": "Tên chủ hộ", "MaDTV": "Mã ĐTV"
        }
    
    cols_can = list(COL_HO) + (["MaDTV"] if can_madtv else [])
    thieu: list[str] = []
    config_labels = st.session_state.ten_vi
    
    for canon in cols_can:
        if canon not in df.columns:
            thieu.append(config_labels.get(canon, canon))
            
    if thieu: return None, thieu
    
    out_cols = list(cols_can)
    if "DiaChi" in df.columns and "DiaChi" not in out_cols:
        out_cols.append("DiaChi")
        
    return df[out_cols].fillna(""), []

def danh_sach_ma_dtv_theo_thu_tu(series: pd.Series) -> list[str]:
    ket_qua: list[str] = []
    da_thay: set[str] = set()
    for gia_tri in series.astype(str).str.strip():
        if not gia_tri or gia_tri.lower() in ("nan", "none", ""): continue
        if gia_tri not in da_thay:
            da_thay.add(gia_tri)
            ket_qua.append(gia_tri)
    return ket_qua

def loc_mau_1000_ho(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if df.empty or "MaDTV" not in df.columns: return pd.DataFrame(), []
    work = df.copy()
    work["MaDTV"] = work["MaDTV"].astype(str).str.strip()
    tat_ca_dtv = danh_sach_ma_dtv_theo_thu_tu(work["MaDTV"])
    return work, tat_ca_dtv

def ho_theo_ma_dtv(df_ho: pd.DataFrame, ma_dtv: str) -> pd.DataFrame:
    if df_ho.empty or "MaDTV" not in df_ho.columns: return pd.DataFrame()
    ma = str(ma_dtv).strip()
    return df_ho[df_ho["MaDTV"].astype(str).str.strip() == ma].copy()

def lay_danh_sach_nen(df: pd.DataFrame, ma_dtv: str) -> pd.DataFrame:
    return ho_theo_ma_dtv(df, ma_dtv).reset_index(drop=True)

def chon_chi_so_mau_tu_nen(n_nen: int, k: int, r: int, so_luong_can_chon: int = 40) -> list[int]:
    if n_nen <= 0 or k < 1 or r < 1: return []
    picked: list[int] = []
    seen: set[int] = set()
    pos = r - 1
    while pos < n_nen and len(picked) < so_luong_can_chon:
        if pos not in seen:
            picked.append(pos)
            seen.add(pos)
        pos += k
    if len(picked) < so_luong_can_chon:
        for i in range(n_nen):
            if len(picked) >= so_luong_can_chon: break
            if i not in seen:
                picked.append(i)
                seen.add(i)
    return picked

def gan_phan_loai_ho(df_nen: pd.DataFrame, chi_so_mau: list[int]) -> pd.DataFrame:
    out = df_nen.reset_index(drop=True).copy()
    out[COL_PHAN_LOAI] = PHAN_LOAI_NEN
    for i in chi_so_mau:
        if 0 <= i < len(out):
            out.loc[i, COL_PHAN_LOAI] = PHAN_LOAI_MAU
    return out

def ap_dung_chon_mau_cho_dtv(df: pd.DataFrame, ma_dtv: str, k: int, r: int) -> pd.DataFrame:
    df_nen = lay_danh_sach_nen(df, ma_dtv)
    if df_nen.empty: return pd.DataFrame()
    chi_so = chon_chi_so_mau_tu_nen(len(df_nen), k, r)
    return gan_phan_loai_ho(df_nen, chi_so)

def ho_mau_can_dieu_tra(df_ho: pd.DataFrame) -> pd.DataFrame:
    if df_ho.empty or COL_PHAN_LOAI not in df_ho.columns: return df_ho
    return df_ho[df_ho[COL_PHAN_LOAI].astype(str).str.strip() == PHAN_LOAI_MAU].copy()

def cap_nhat_danh_sach_ho_theo_dtv(df_all: pd.DataFrame, ma_dtv: str, df_nen_da_phan_loai: pd.DataFrame) -> pd.DataFrame:
    if df_all.empty: return df_nen_da_phan_loai
    ma = str(ma_dtv).strip()
    mask_khac = df_all["MaDTV"].astype(str).str.strip() != ma
    phan_con_lai = df_all[mask_khac]
    df_moi = df_nen_da_phan_loai.copy()
    df_moi["MaDTV"] = ma
    return pd.concat([phan_con_lai, df_moi], ignore_index=True)

# ---------------------------------------------------------------------------
# Các hàm đồng bộ kết nối Google Sheets API
# ---------------------------------------------------------------------------
SHEET_DANH_SACH_HO = "DanhSachHo"
EXPECTED_SERVICE_EMAIL = "appthunhap@crypto-avenue-410700.iam.gserviceaccount.com"
EXPECTED_SPREADSHEET_TITLE = "Dieutrathunhaptest"

@st.cache_data(ttl=300)
def load_all_data_sync():
    return {
        "ho": read_sheet(SHEETS["danh_sach_ho"], silent=True),
        "kq": read_sheet(SHEETS["ket_qua"], silent=True),
        "dtv": read_sheet(SHEETS["danh_sach_dtv"], silent=True),
        "acc": read_sheet(SHEETS["account"], silent=True)
    }

def hien_thi_thong_tin_ket_noi_gsheets(*, truoc_khi_ghi: bool = False) -> bool:
    try:
        json_key = json.loads(st.secrets["gcp_service_account"]["json"])
        email = json_key.get("client_email", "Không xác định")
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except Exception as e:
        st.error(f"Lỗi đọc cấu hình từ Secrets: {e}")
        return False
    st.info(f"Đang dùng tài khoản **{email}** để ghi vào file [Google Sheets]({url})")
    if "EXPECTED_SERVICE_EMAIL" in globals() and email != EXPECTED_SERVICE_EMAIL:
        st.error(f"Sai tài khoản! Email là `{email}`, cần đúng `{EXPECTED_SERVICE_EMAIL}`.")
        return False
    if not truoc_khi_ghi: return True
    try:
        sh = _open_spreadsheet()
        st.success(f"Đã mở đúng file: **{sh.title}**")
        return True
    except Exception as e:
        st.error(f"Lỗi khi mở file: {e}")
        return False

def _loi_api_chua_bat(exc: Exception) -> str:
    return f"❌ **Lỗi kết nối Google API:** Vui lòng bật Google Sheets API & Drive API trên Google Cloud Console. Chi tiết: {exc}"

def _gsheets_error_message(exc: Exception, *, sheet_name: str, action: str) -> str:
    msg = str(exc).lower()
    if isinstance(exc, FileNotFoundError): return "❌ Không tìm thấy thông tin xác thực Service Account."
    if "sheets.googleapis.com" in msg or "api" in msg: return _loi_api_chua_bat(exc)
    return f"❌ Lỗi khi {action} sheet «{sheet_name}»: {exc}"

@st.cache_data(ttl=60)
def _read_sheet_cached(name: str) -> pd.DataFrame:
    sh = _open_spreadsheet()
    ws = sh.worksheet(name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty: return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return chuan_hoa_ten_cot_df(df)

def read_sheet(name: str, *, silent: bool = False) -> pd.DataFrame:
    try: return _read_sheet_cached(name)
    except Exception as e:
        if not silent: st.error(_gsheets_error_message(e, sheet_name=name, action="đọc"))
        return pd.DataFrame()

def clear_sheet_cache():
    _read_sheet_cached.clear()

def update_sheet(sheet_name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True) -> bool:
    if sheet_name == SHEETS["danh_sach_ho"]: sheet_name = SHEET_DANH_SACH_HO
    if not silent and not _kiem_tra_ket_noi_gsheets(): return False
    try:
        sh = _open_spreadsheet()
        ws = sh.worksheet(sheet_name)
        ws.clear()
        if df.empty:
            ws.update([df.columns.values.tolist()])
        else:
            payload = [df.columns.values.tolist()] + df.fillna("").values.tolist()
            ws.update(payload)
        clear_sheet_cache()
        if sheet_name == SHEETS["ket_qua"]: ap_dung_mau_do_hang_gia(ws)
        if thong_bao and not silent: st.success(f"Đã lưu dữ liệu vào sheet «{sheet_name}».")
        return True
    except Exception as e:
        if not silent: st.error(_gsheets_error_message(e, sheet_name=sheet_name, action="ghi"))
        return False

def _kiem_tra_ket_noi_gsheets() -> bool:
    try:      
        email = _service_account_email()
        if email != EXPECTED_SERVICE_EMAIL: return False
        _open_spreadsheet()
        return True
    except: return False

def ap_dung_mau_do_hang_gia(ws) -> None:
    from gspread.utils import rowcol_to_a1
    values = ws.get_all_values()
    if len(values) < 2: return
    headers = values[0]
    try: col_ix = headers.index("Xac_Thuc_GPS")
    except ValueError: return
    ncol = len(headers)
    fmt = {"backgroundColor": {"red": 0.96, "green": 0.78, "blue": 0.78}, "textFormat": {"foregroundColor": {"red": 0.72, "green": 0.0, "blue": 0.0}, "bold": True}}
    for row_num in range(2, len(values) + 1):
        row = values[row_num - 1]
        if len(row) <= col_ix: continue
        val = str(row[col_ix]).strip()
        if val.startswith("GIẢ") or "[CHECK_FAKE]" in str(row):
            end_cell = rowcol_to_a1(row_num, ncol)
            ws.format(f"A{row_num}:{end_cell}", fmt)

def write_sheet_replace(name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True) -> bool:
    return update_sheet(name, df, silent=silent, thong_bao=thong_bao)

def append_ket_qua(row: dict[str, Any], *, silent: bool = True) -> bool:
    try:
        df_old = read_sheet(SHEETS["ket_qua"], silent=silent)
        df_new = pd.DataFrame([row])
        out = df_new if df_old.empty else pd.concat([df_old, df_new], ignore_index=True)
        return write_sheet_replace(SHEETS["ket_qua"], out, silent=silent, thong_bao=not silent)
    except Exception as e:
        if not silent: st.error(f"Lỗi lưu phiếu: {e}")
        return False

# ---------------------------------------------------------------------------
# Logic tính toán & Validation nghiệp vụ
# ---------------------------------------------------------------------------
def so_hoa(gia_tri: Any) -> float:
    val = pd.to_numeric(gia_tri, errors="coerce")
    if isinstance(val, pd.Series): val = val.fillna(0).iloc[0] if len(val) else 0
    return float(val) if not pd.isna(val) else 0.0

def thu_thuan(dt: float, cp: float) -> float:
    return max(0.0, so_hoa(dt) - so_hoa(cp))

def loi_chi_phi_vuot_thu(chi_phi: float, doanh_thu: float) -> bool:
    return so_hoa(chi_phi) > so_hoa(doanh_thu)

def loi_tong_khong_khop(tong_nho: float, tong_lon: float, *, eps: float = 0.5) -> bool:
    return abs(so_hoa(tong_nho) - so_hoa(tong_lon)) > eps

def hien_loi_validation(noi_dung: str) -> None:
    st.markdown(f'<p class="input-loi-do">{noi_dung}</p>', unsafe_allow_html=True)

def _key_hoat_dong(nhom_id: str, ho_so: str, form_ver: int) -> str:
    return f"hd_{nhom_id}_{ho_so}_{form_ver}"

def read_accounts() -> pd.DataFrame:
    df = read_sheet(SHEETS["account"])
    if df.empty: return pd.DataFrame(columns=["MaDTV", "MatKhau", "HoTen", "TrangThai"])
    for c in ("MaDTV", "MatKhau", "HoTen", "TrangThai"):
        if c not in df.columns: df[c] = ""
    return df

def write_accounts(df: pd.DataFrame) -> bool:
    return write_sheet_replace(SHEETS["account"], df)

def dong_bo_account_tu_ma_dtv(danh_sach_ma: list[str]) -> None:
    df = read_accounts()
    co_san = set(df["MaDTV"].astype(str).str.strip()) if not df.empty else set()
    rows: list[dict[str, str]] = []
    for ma in danh_sach_ma:
        ma = str(ma).strip()
        if not ma or ma in co_san or normalize_ma(ma) == ADMIN_MA: continue
        rows.append({"MaDTV": ma, "MatKhau": ma, "HoTen": f"Điều tra viên {ma}", "TrangThai": TRANG_THAI_MK_CHUA})
    if rows: write_accounts(pd.concat([df, pd.DataFrame(rows)], ignore_index=True))

def xac_thuc_dang_nhap(ma_dtv: str, mat_khau: str) -> tuple[bool, str, pd.Series | None]:
    ma = str(ma_dtv).strip()
    df = read_accounts()
    if df.empty: return False, "Chưa có tài khoản hệ thống.", None
    row = df[df["MaDTV"].astype(str).str.strip() == ma]
    if row.empty: return False, f"Mã ĐTV «{ma}» không tồn tại.", None
    r = row.iloc[0]
    if str(r.get("MatKhau", "")).strip() != str(mat_khau).strip(): return False, "Mật khẩu nhập chưa đúng.", None
    return True, "", r

def cap_nhat_mat_khau(ma_dtv: str, mat_khau_moi: str) -> bool:
    df = read_accounts()
    if df.empty: return False
    mask = df["MaDTV"].astype(str).str.strip() == str(ma_dtv).strip()
    if not mask.any(): return False
    df.loc[mask, "MatKhau"] = str(mat_khau_moi).strip()
    df.loc[mask, "TrangThai"] = TRANG_THAI_MK_DA
    return write_accounts(df)

def reset_mat_khau_dtv(ma_dtv: str) -> bool:
    df = read_accounts()
    mask = df["MaDTV"].astype(str).str.strip() == str(ma_dtv).strip()
    if not mask.any(): return False
    df.loc[mask, "MatKhau"] = str(ma_dtv).strip()
    df.loc[mask, "TrangThai"] = TRANG_THAI_MK_CHUA
    return write_accounts(df)

def _key_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> str:
    return f"chi_tiet_{ma_lv}_{ho_so}_{form_ver}"

def lay_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> list[dict[str, Any]]:
    return list(st.session_state.get(_key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver), []))

def xoa_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> None:
    st.session_state[_key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)] = []

def tong_hop_chi_tiet_linh_vuc(danh_sach: list[dict[str, Any]]) -> tuple[float, float, float]:
    dt = cp = 0.0
    for dong in danh_sach:
        dt += max(0.0, so_hoa(dong.get("Giá bán", 0)) - so_hoa(dong.get("Tự dùng", 0)))
        cp += so_hoa(dong.get("Giống", 0)) + so_hoa(dong.get("Thức ăn", 0)) + so_hoa(dong.get("Chi khác", 0))
    return dt, cp, thu_thuan(dt, cp)

def _co_hoat_dong(nhom_id: str, ho_so: str, form_ver: int) -> bool:
    return st.session_state.get(_key_hoat_dong(nhom_id, ho_so, form_ver), "Có") == "Có"

def _dat_zero_nhom_don(ma: str, ho_so: str, form_ver: int) -> None:
    st.session_state[f"dt_{ma}_{ho_so}_{form_ver}"] = 0.0
    st.session_state[f"cp_{ma}_{ho_so}_{form_ver}"] = 0.0

def _dat_zero_nhom_nlt(ho_so: str, form_ver: int) -> None:
    for muc in CHI_TIEU_PHAN_B:
        if muc["loai"] == "linh_vuc_sp": xoa_chi_tiet_linh_vuc(muc["ma"], ho_so, form_ver)

# ---------------------------------------------------------------------------
# Các Form giao diện nhập liệu chi tiết
# ---------------------------------------------------------------------------
def nhap_thanh_vien_ho(ho_so: str, form_ver: int) -> None:
    key = f"ds_tv_{ho_so}_{form_ver}"
    if key not in st.session_state: st.session_state[key] = []
    ten = st.text_input("Họ tên thành viên", key=f"tv_ten_{ho_so}_{form_ver}")
    qh = st.selectbox("Quan hệ với chủ hộ", ["Chủ hộ", "Vợ/chồng", "Con", "Cha/mẹ", "Khác"], key=f"tv_qh_{ho_so}_{form_ver}")
    if st.button("Thêm thành viên", key=f"tv_them_{ho_so}_{form_ver}", use_container_width=True):
        if ten.strip():
            ds = list(st.session_state.get(key, []))
            ds.append({"Họ tên": ten.strip(), "Quan hệ": qh})
            st.session_state[key] = ds
            st.toast(f"Đã thêm «{ten.strip()}».", icon="✅")
        else: st.toast("Vui lòng nhập họ tên.", icon="⚠️")
    ds_hien = st.session_state.get(key, [])
    if ds_hien:
        with st.expander(f"Danh sách {len(ds_hien)} thành viên", expanded=False):
            hien_dataframe_an_toan(pd.DataFrame(ds_hien))

def nhap_muc_don_doc(ma: str, ten: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"**{ten}**")
    k_dt, k_cp = f"dt_{ma}_{ho_so}_{form_ver}", f"cp_{ma}_{ho_so}_{form_ver}"
    dt = st.number_input("Doanh thu (nghìn đồng/tháng)", min_value=0.0, value=float(so_hoa(st.session_state.get(k_dt, 0))), step=50.0, key=k_dt)
    cp = st.number_input("Chi phí (nghìn đồng/tháng)", min_value=0.0, value=float(so_hoa(st.session_state.get(k_cp, 0))), step=50.0, key=k_cp)
    if loi_chi_phi_vuot_thu(cp, dt): hien_loi_validation(f"⚠️ Chi phí vượt quá doanh thu.")
    st.caption(f"Thu nhập thuần mục này: **{thu_thuan(dt, cp):,.0f}**")

def nhap_linh_vuc_co_san_pham(ma_lv: str, ten_lv: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"**{ten_lv}**")
    san_pham = st.selectbox("Chọn sản phẩm / loại hình", SAN_PHAM_LINH_VUC.get(ma_lv, ["Khác"]), key=f"sp_sel_{ma_lv}_{ho_so}_{form_ver}")
    for o in O_NHAP_SAN_PHAM:
        st.number_input(f"{o} (nghìn đồng/tháng)", min_value=0.0, value=0.0, step=10.0, key=f"{ma_lv}_{o}_{san_pham}_{ho_so}_{form_ver}")
    if st.button("Thêm vào danh sách", key=f"them_sp_{ma_lv}_{ho_so}_{form_ver}", use_container_width=True):
        key = _key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
        ds = list(st.session_state.get(key, []))
        dong: dict[str, Any] = {"Sản phẩm": san_pham}
        for o in O_NHAP_SAN_PHAM:
            dong[o] = so_hoa(st.session_state.get(f"{ma_lv}_{o}_{san_pham}_{ho_so}_{form_ver}", 0))
        dt_d, cp_d, th_d = tong_hop_chi_tiet_linh_vuc([dong])
        if loi_chi_phi_vuot_thu(cp_d, dt_d):
            st.toast("Lỗi: Chi phí vượt doanh thu.", icon="⚠️")
            return
        dong["Doanh thu"] = dt_d
        dong["Chi phí"] = cp_d
        dong["Thu nhập thuần"] = th_d
        ds.append(dong)
        st.session_state[key] = ds
        st.toast(f"Đã thêm sản phẩm «{san_pham}».", icon="✅")
    ds_hien = lay_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
    if ds_hien:
        with st.expander(f"Đã nhập {len(ds_hien)} dòng sản phẩm — xem chi tiết", expanded=False):
            hien_dataframe_an_toan(pd.DataFrame(ds_hien))

def nhap_lieu_5_nhom(ho_so: str, form_ver: int) -> None:
    st.caption("Đơn vị tính toán: **nghìn đồng/tháng**.")
    for nhom in NHOM_NHAP:
        with card_container(nhom["ten"]):
            if nhom["id"] == "thanh_vien":
                nhap_thanh_vien_ho(ho_so, form_ver)
            else:
                cau_hoi = "Trong 12 tháng qua, hộ có thu nhập từ lương/công không?" if nhom["id"] == "luong" else f"Hộ có hoạt động {nhom['ten']} không?"
                co_hd = st.radio(cau_hoi, ["Có", "Không"], horizontal=True, key=_key_hoat_dong(nhom["id"], ho_so, form_ver)) == "Có"
                if not co_hd:
                    if nhom["loai"] == "don": _dat_zero_nhom_don(nhom["ma"], ho_so, form_ver)
                    elif nhom["loai"] == "nlt": _dat_zero_nhom_nlt(ho_so, form_ver)
                    st.caption("Đã mặc định ghi **0** cho nhóm này.")
                    continue
                if nhom["loai"] == "don":
                    muc = map_chi_tieu.get(nhom["ma"])
                    if muc: nhap_muc_don_doc(muc["ma"], muc["ten"], ho_so, form_ver)
                elif nhom["loai"] == "nlt":
                    muc_nlt = [m for m in CHI_TIEU_PHAN_B if m["loai"] == "linh_vuc_sp"]
                    for i, muc in enumerate(muc_nlt):
                        nhap_linh_vuc_co_san_pham(muc["ma"], muc["ten"], ho_so, form_ver)
                        if i < len(muc_nlt) - 1: st.divider()

# ---------------------------------------------------------------------------
# Xử lý tổng hợp dữ liệu phiếu & Bảng 7 nguồn thu nhập
# ---------------------------------------------------------------------------
def tong_hop_du_lieu_phieu(ho_so: str, form_ver: int) -> dict[str, Any]:
    ket: dict[str, Any] = {"thu_luong": 0.0, "thu_khac": 0.0, "dt_sxkd": 0.0, "cp_sxkd": 0.0, "thu_sxkd": 0.0, "linh_vuc": {}, "tong_7": {}, "hang_bang": []}
    for muc in CHI_TIEU_PHAN_B:
        ma, loai = muc["ma"], muc["loai"]
        if loai == "luong" and not _co_hoat_dong("luong", ho_so, form_ver): continue
        if loai == "sxkd" and not _co_hoat_dong("sxkd", ho_so, form_ver): continue
        if loai == "khac" and not _co_hoat_dong("khac", ho_so, form_ver): continue
        if loai == "linh_vuc_sp" and not _co_hoat_dong("nlt", ho_so, form_ver): continue

        if loai == "luong":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["thu_luong"] = thuan
            ket["tong_7"]["ThuLuong"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
        elif loai == "linh_vuc_sp":
            ds = lay_chi_tiet_linh_vuc(ma, ho_so, form_ver)
            dt, cp, thuan = tong_hop_chi_tiet_linh_vuc(ds)
            ket["linh_vuc"][ma] = (dt, cp, thuan)
            ket["tong_7"][f"Thu_{ma}"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
            for dong in ds:
                ket["hang_bang"].append({
                    "Tên chỉ tiêu": f"  └ {dong.get('Sản phẩm', '')}",
                    "Doanh thu": so_hoa(dong.get("Doanh thu", 0)),
                    "Chi phí": so_hoa(dong.get("Chi phí", 0)),
                    "Thu nhập thuần": so_hoa(dong.get("Thu nhập thuần", 0)),
                })
        elif loai == "sxkd":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["dt_sxkd"], ket["cp_sxkd"], ket["thu_sxkd"] = dt, cp, thuan
            ket["tong_7"]["Thu_SXKD"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
        elif loai == "khac":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["thu_khac"] = thuan
            ket["tong_7"]["ThuKhac"] = thuan
            ket["hang_bang"].append({"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan})
    return ket

def kiem_tra_validation_phieu(ho_so: str, form_ver: int) -> tuple[bool, list[str]]:
    loi: list[str] = []
    dl = tong_hop_du_lieu_phieu(ho_so, form_ver)
    for muc in CHI_TIEU_PHAN_B:
        ma, loai, ten = muc["ma"], muc["loai"], muc["ten"]
        if loai in ("luong", "sxkd", "khac"):
            nhom = {"luong": "luong", "sxkd": "sxkd", "khac": "khac"}[loai]
            if not _co_hoat_dong(nhom, ho_so, form_ver): continue
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            if loi_chi_phi_vuot_thu(cp, dt): loi.append(f"{ten}: Chi phí vượt doanh thu.")
    tong_nho = sum(so_hoa(r.get("Thu nhập thuần", 0)) for r in dl["hang_bang"] if not str(r.get("Tên chỉ tiêu", "")).startswith("  └"))
    tong_lon = tinh_tong_7_nguon(dl["tong_7"])
    if dl["hang_bang"] and loi_tong_khong_khop(tong_nho, tong_lon):
        loi.append(f"Lỗi logic: Tổng các nhóm không khớp tổng 7 nguồn.")
    return len(loi) == 0, loi

def tinh_tong_7_nguon(du_lieu: dict[str, float]) -> float:
    return sum(float(du_lieu.get(k, 0) or 0) for k, _ in BAO_CAO_7_NGUON)

# ---------------------------------------------------------------------------
# Hệ thống bảo mật & Xác thực chống gian lận GPS
# ---------------------------------------------------------------------------
def normalize_ma(ma: str) -> str:
    return ma.strip().upper()

def is_admin(ma: str) -> bool:
    return normalize_ma(ma) == ADMIN_MA

def danh_sach_ma_dtv_da_nap() -> list[str]:
    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    if df_ho.empty or "MaDTV" not in df_ho.columns: return []
    return danh_sach_ma_dtv_theo_thu_tu(df_ho["MaDTV"])

def get_client_ip() -> str:
    try:
        import requests
        return requests.get("https://api.ipify.org?format=json", timeout=3).json().get("ip", "không xác định")
    except: return "không xác định"

GPS_CANH_BAO_DTV = "Tọa độ có độ chính xác thấp, vui lòng bật GPS độ chính xác cao."
GPS_NGUONG_CANH_BAO_M = 100
GPS_NGUONG_GIA_M = 500
_geolocator: Any = None

def _lay_geolocator():
    global _geolocator
    if Nominatim is None: return None
    if _geolocator is None: _geolocator = Nominatim(user_agent="pmdtv_survey_v1", timeout=10)
    return _geolocator

@st.cache_data(ttl=86400, show_spinner=False)
def tra_cuu_toa_do_dia_chi(dia_chi: str) -> tuple[float, float] | None:
    dia_chi = str(dia_chi or "").strip()
    if not dia_chi or geodesic is None: return None
    geo = _lay_geolocator()
    if geo is None: return None
    try:
        vi_tri = geo.geocode(f"{dia_chi}, Việt Nam", language="vi")
        if vi_tri is None: vi_tri = geo.geocode(dia_chi, language="vi")
        return (float(vi_tri.latitude), float(vi_tri.longitude)) if vi_tri else None
    except: return None

def ma_dia_ban_ho(ho: pd.Series) -> str:
    for cot in ("MaDiaBan", "DiaBan"):
        ma = str(ho.get(cot, "") or "").strip()
        if ma and ma.lower() not in ("nan", "none"): return ma
    return ""

def dia_chi_ho_tu_dong(ho: pd.Series) -> str:
    ma_db = ma_dia_ban_ho(ho)
    parts = [ma_db, str(ho.get("Xa", "")).strip(), str(ho.get("Huyen", "")).strip(), "Việt Nam"]
    return ", ".join(p for p in parts if p and p.lower() not in ("nan", "none"))

@st.cache_data(ttl=86400, show_spinner=False)
def toa_do_neo_ma_dia_ban(ma_dia_ban: str, xa: str, huyen: str) -> tuple[float, float] | None:
    ma = str(ma_dia_ban or "").strip()
    if not ma: return None
    truy_van = ", ".join(p for p in (ma, str(xa).strip(), str(huyen).strip(), "Việt Nam") if p and p.lower() not in ("nan", "none"))
    return tra_cuu_toa_do_dia_chi(truy_van)

def tinh_khoang_cach_gps_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return float(geodesic((lat1, lng1), (lat2, lng2)).meters) if geodesic else 0.0

def phan_tich_geofence(ho: pd.Series, loc: dict | None) -> dict[str, Any]:
    ma_db = ma_dia_ban_ho(ho)
    ket: dict[str, Any] = {"khoang_cach_m": None, "muc": "ok", "canh_bao": "", "ma_dia_ban": ma_db, "dia_chi": dia_chi_ho_tu_dong(ho), "bat_buoc_ghi_chu": False}
    if not loc or loc.get("latitude") is None: return ket
    try:
        toa_do_neo = toa_do_neo_ma_dia_ban(ma_db, str(ho.get("Xa", "")), str(ho.get("Huyen", "")))
        if toa_do_neo:
            kc = tinh_khoang_cach_gps_m(float(loc["latitude"]), float(loc["longitude"]), toa_do_neo[0], toa_do_neo[1])
            ket["khoang_cach_m"] = kc
            if kc >= GEO_NGUONG_CHAP_NHAN_M:
                ket["muc"] = "vang" if kc < GEO_NGUONG_CANH_BAO_M else "do"
                ket["canh_bao"] = CANH_BAO_GEO_VANG if kc < GEO_NGUONG_CANH_BAO_M else CANH_BAO_GEO_DO
                if kc >= GEO_NGUONG_CANH_BAO_M: ket["bat_buoc_ghi_chu"] = True
    except: pass
    return ket

def hien_canh_bao_geofence_nhe(geo: dict[str, Any]) -> None:
    cb = geo.get("canh_bao")
    if not cb: return
    extra = f" (lệch {geo['khoang_cach_m']:.0f} m)" if geo.get("khoang_cach_m") else ""
    st.markdown(f'<p class="canh-bao-{geo["muc"]}">{cb}{extra}</p>', unsafe_allow_html=True)

def _ten_ung_dung_gps_gia(loc: dict) -> str:
    for key in ("mock_app", "mockApp", "provider", "app"):
        if loc.get(key): return str(loc[key]).strip()
    return "Mock Location App"

def phan_tich_vi_tri_gps(loc: dict | None) -> dict[str, Any]:
    ket: dict[str, Any] = {"canh_bao_dtv": "", "xac_thuc_gps": "Hợp lệ", "to_do_do": False, "sai_so": None, "do_cao": None}
    if not loc or loc.get("latitude") is None:
        return {"canh_bao_dtv": GPS_CANH_BAO_DTV, "xac_thuc_gps": "GIẢ - Không có GPS", "to_do_do": True, "sai_so": None, "do_cao": None}
    ket["sai_so"] = float(loc["accuracy"]) if loc.get("accuracy") is not None else None
    ket["do_cao"] = float(loc["altitude"]) if loc.get("altitude") is not None else None
    if bool(loc.get("mocked") or loc.get("is_mock")):
        ket["xac_thuc_gps"] = f"GIẢ - {_ten_ung_dung_gps_gia(loc)}"
        ket["canh_bao_dtv"] = GPS_CANH_BAO_DTV
        ket["to_do_do"] = True
    return ket

def dinh_dang_toa_do_gps(gia_tri: Any, *, fake: bool) -> str | None:
    if gia_tri is None: return None
    return f"{gia_tri} [CHECK_FAKE]" if fake else str(gia_tri)

def tao_dong_ket_qua_qd1099(*, ma_dtv: str, ho: pd.Series, nhan_khau: int, thu_luong: float, linh_vuc: dict[str, tuple[float, float, float]], dt_sxkd: float, cp_sxkd: float, thu_khac: float, loc: dict | None, gps: dict[str, Any], geo: dict[str, Any] | None = None, ghi_chu_vi_tri: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {
        "MaDTV": ma_dtv, "HoSo": str(ho.get("HoSo", "")), "MaTKCS": str(ho.get("MaTKCS", ho.get("Huyen", ""))),
        "Xa": str(ho.get("Xa", "")), "DiaBan": str(ho.get("DiaBan", "")), "MaDiaBan": str(geo.get("ma_dia_ban", ho.get("MaDiaBan", ""))),
        "TenChuHo": str(ho.get("TenChuHo", "")), "NhanKhauTT": nhan_khau, "ThuLuong": thu_luong, "ThuKhac": thu_khac,
    }
    co_mock = bool(loc and (loc.get("mocked") or loc.get("is_mock")))
    row["GPS_lat"] = dinh_dang_toa_do_gps(loc.get("latitude") if loc else None, fake=co_mock)
    row["GPS_lng"] = dinh_dang_toa_do_gps(loc.get("longitude") if loc else None, fake=co_mock)
    row["DoChinhXac"] = gps.get("sai_so")
    row["Sai_so"] = gps.get("sai_so")
    row["Do_cao"] = gps.get("do_cao")
    row["Xac_Thuc_GPS"] = f"GIẢ - {_ten_ung_dung_gps_gia(loc)}" if co_mock else gps.get("xac_thuc_gps", "Hợp lệ")
    row["IP"] = get_client_ip()
    row["MockGPS"] = "Có" if (co_mock or gps.get("to_do_do")) else "Không"
    row["NgayNhap"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if geo:
        row["KhoangCachLech"] = round(geo.get("khoang_cach_m", 0), 1) if geo.get("khoang_cach_m") is not None else ""
        row["GhiChuViTri"] = ghi_chu_vi_tri.strip()
        row["DiaChi"] = geo.get("dia_chi", "")

    tong_7: dict[str, float] = {"ThuLuong": thu_luong, "ThuKhac": thu_khac}
    for code, _ten in LINH_VUC_NLN_TS:
        dt, cp, thuan = linh_vuc.get(code, (0.0, 0.0, 0.0))
        row[f"DT_{code}"] = dt
        row[f"CP_{code}"] = cp
        row[f"Thu_{code}"] = thuan
        tong_7[f"Thu_{code}"] = thuan

    row["DT_SXKD"] = dt_sxkd
    row["CP_SXKD"] = cp_sxkd
    row["Thu_SXKD"] = thu_thuan(dt_sxkd, cp_sxkd)
    tong_7["Thu_SXKD"] = row["Thu_SXKD"]

    tong = tinh_tong_7_nguon(tong_7)
    row["TongThuNhap"] = tong
    row["ThuBQDauNguoi"] = round(tong / max(1, int(nhan_khau)), 2)
    return row

# ---------------------------------------------------------------------------
# UI: Hệ thống Quản trị & Điều hành Dashboard (Admin)
# ---------------------------------------------------------------------------
def page_login():
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        vai_tro = st.radio("Vai trò đăng nhập hệ thống", ["QUẢN TRỊ VIÊN", "ĐIỀU TRA VIÊN"], horizontal=True)
        if vai_tro == "QUẢN TRỊ VIÊN":
            mk = st.text_input("Mật khẩu Quản trị", type="password", key="login_admin_mk")
            if st.button("Đăng nhập Hệ thống", type="primary", use_container_width=True, key="btn_login_admin"):
                if normalize_ma(mk) == ADMIN_MA:
                    st.session_state["user"] = {"ma": ADMIN_MA, "role": "admin", "ten": "Quản trị viên"}
                    st.rerun()
                else: st.error("Mật khẩu truy cập không đúng.")
        else:
            ma = st.text_input("Mã số Điều tra viên (ĐTV)", key="login_ma_dtv_txt")
            mk = st.text_input("Mật khẩu tài khoản", type="password", key="login_mk_dtv")
            if st.button("Đăng nhập Hệ thống", type="primary", use_container_width=True, key="btn_login_dtv"):
                if not ma or not mk: st.warning("Nhập đầy đủ thông tin tài khoản.")
                else:
                    ok, loi, row = xac_thuc_dang_nhap(ma, mk)
                    if not ok: st.error(loi)
                    else:
                        st.session_state["user"] = {"ma": ma, "role": "dtv", "ten": row.get("HoTen", "ĐTV")}
                        st.rerun()

def page_doi_mat_khau():
    user = st.session_state["user"]
    render_header()
    mk1 = st.text_input("Mật khẩu mới", type="password")
    mk2 = st.text_input("Xác nhận mật khẩu mới", type="password")
    if st.button("Thay đổi mật khẩu", type="primary", use_container_width=True):
        if len(mk1) < 4: st.error("Mật khẩu bảo mật phải tối thiểu từ 4 ký tự.")
        elif mk1 != mk2: st.error("Xác nhận mật khẩu chưa trùng khớp.")
        elif cap_nhat_mat_khau(user["ma"], mk1):
            if "bat_doi_mk" in st.session_state: del st.session_state["bat_doi_mk"]
            st.success("Mật khẩu được đổi thành công.")
            st.rerun()

def xa_huyen_theo_dtv(df_ho: pd.DataFrame) -> dict[str, str]:
    ket: dict[str, str] = {}
    if df_ho.empty or "MaDTV" not in df_ho.columns: return ket
    for ma, g in df_ho.groupby("MaDTV"):
        r = g.iloc[0]
        ket[str(ma).strip()] = f"{str(r.get('Xa',''))} / {str(r.get('Huyen',''))}"
    return ket

def _df_mau_tien_do(df_ho: pd.DataFrame, df_kq: pd.DataFrame) -> pd.DataFrame:
    if df_ho.empty: return pd.DataFrame()
    df_mau = ho_mau_can_dieu_tra(df_ho) if COL_PHAN_LOAI in df_ho.columns else df_ho.copy()
    done_ho = set(df_kq["HoSo"].astype(str)) if not df_kq.empty and "HoSo" in df_kq.columns else set()
    work = df_mau.copy()
    work["HoanThanh"] = work["HoSo"].astype(str).isin(done_ho)
    return work

def _them_cot_nganh_4(df_kq: pd.DataFrame) -> pd.DataFrame:
    if df_kq.empty: return df_kq
    out = df_kq.copy()
    for c in ["ThuLuong", "Thu_SXKD", "ThuKhac", "TongThuNhap", "ThuBQDauNguoi"]:
        if c in out.columns: out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    cols_nlt = [f"Thu_{c}" for c, _ in LINH_VUC_NLN_TS if f"Thu_{c}" in out.columns]
    out["Thu_NLT"] = out[cols_nlt].sum(axis=1) if cols_nlt else 0.0
    return out

def _bang_tong_hop_thu_nhap(df_kq_xa: pd.DataFrame) -> pd.DataFrame:
    if df_kq_xa.empty: return pd.DataFrame()
    df = _them_cot_nganh_4(df_kq_xa)
    hang = [{"Nhóm thu nhập": ten, "Giá trị": float(df[col].sum()), "Số hộ": int((df[col] > 0).sum())} for col, ten in NHOM_NGANH_4 if col in df.columns]
    if not hang: return pd.DataFrame()
    bang = pd.DataFrame(hang)
    tong = bang["Giá trị"].sum()
    bang["Tỷ trọng (%)"] = (bang["Giá trị"] / tong * 100).round(1) if tong > 0 else 0.0
    return bang

def render_admin_dashboard(df_ho, df_kq) -> None:
    # ĐÃ XÓA KHỐI st.markdown("<style>...") ở đây!
    
    work = _df_mau_tien_do(df_ho, df_kq)
    tong_ho = len(work)
    da_xong = int(work["HoanThanh"].sum()) if "HoanThanh" in work.columns else 0
    ty_le = round(da_xong / tong_ho * 100, 1) if tong_ho else 0.0
    df_kq_num = _them_cot_nganh_4(df_kq)
    thu_bq = round(float(df_kq_num["ThuBQDauNguoi"].mean()), 1) if not df_kq_num.empty else 0.0

    with card_container("📊 Báo cáo Giám sát Tiến độ Hệ thống"):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng Hộ Mẫu", f"{tong_ho:,}")
        k2.metric("Tỷ Lệ Hoàn Thành", f"{ty_le}%")
        k3.metric("Thu Nhập Bình Quân", f"{thu_bq:,.0f} nghìn đ")
        k4.metric("Số Phiếu Hoàn Thành", f"{da_xong}/{tong_ho}")

    if work.empty:
        st.info("Hệ thống chưa ghi nhận danh sách hộ mẫu.")
    else:
        col_trai, col_phai = st.columns(2)
        with col_trai:
            with card_container("Biểu đồ: Thu nhập bình quân đầu người theo Xã"):
                if not df_kq_num.empty and "Xa" in df_kq_num.columns:
                    bx = df_kq_num.groupby("Xa", as_index=False)["ThuBQDauNguoi"].mean().rename(columns={"ThuBQDauNguoi": "ThuBQ"})
                    bx = bx.sort_values("ThuBQ").reset_index(drop=True)
                    bx["Mau"] = NAVY_ACCENT
                    fig = px.bar(bx, x="ThuBQ", y="Xa", orientation="h", title="Mức thu nhập BQ của từng Xã", color="Mau", color_discrete_map="identity")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.caption("Chưa có dữ liệu tính toán.")
        with col_phai:
            with card_container("Biểu đồ: Cơ cấu 4 nhóm ngành nghề"):
                ds_xa = sorted(work["Xa"].astype(str).unique().tolist())
                xa_sel = st.selectbox("Chọn địa bàn Xã theo dõi", ds_xa)
                df_xa = df_kq_num[df_kq_num["Xa"].astype(str) == xa_sel] if not df_kq_num.empty else pd.DataFrame()
                if not df_xa.empty:
                    stack_row = {ten: float(df_xa[col].sum()) for col, ten in NHOM_NGANH_4 if col in df_xa.columns}
                    fig2 = go.Figure(go.Bar(x=list(stack_row.keys()), y=list(stack_row.values()), marker_color="#1a4a7a"))
                    fig2.update_layout(title=f"Tổng thu nhập cơ cấu ngành nghề tại Xã {xa_sel}")
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.caption("Địa bàn này chưa phát sinh dữ liệu phiếu.")

    with st.expander("👥 Quản lý Danh sách Tài khoản & Khôi phục Mật khẩu ĐTV", expanded=False):
        df_acc = read_accounts()
        if not df_acc.empty:
            map_xh = xa_huyen_theo_dtv(df_ho)
            for _, row in df_acc.iterrows():
                ma = str(row.get("MaDTV")).strip()
                if not ma or ma == ADMIN_MA: continue
                c0, c1, c2, c3 = st.columns([1, 2, 2, 1])
                c0.write(f"**Mã ĐTV:** {ma}")
                c1.write(f"**Tên:** {str(row.get('HoTen'))}")
                c2.write(f"**Địa bàn:** {map_xh.get(ma, '—')}")
                if c3.button("Khôi phục MK", key=f"adm_reset_{ma}", use_container_width=True):
                    if reset_mat_khau_dtv(ma):
                        st.toast(f"Đã đưa mật khẩu tài khoản {ma} về mặc định.", icon="🔑")
                        st.rerun()

def admin_he_thong():
    render_header()
    tab1, tab2 = st.tabs(["📤 Bước 1: Nạp file Excel hộ nền", "🎯 Bước 2: Chọn mẫu hệ thống (k, r)"])
    with tab1:
        st.write("### Tải lên tệp danh sách Excel")
        f = st.file_uploader("Chọn tệp danh sách hộ khảo sát (.xlsx)", type=["xlsx"])
        if f and st.button("Nạp dữ liệu vào Google Sheets", type="primary", use_container_width=True):
            df_raw, thieu = doc_excel_danh_sach_ho(f, can_madtv=True)
            if df_raw is not None:
                df_loc, dtv_list = loc_mau_1000_ho(df_raw)
                df_ho_gs = df_loc[list(COL_HO) + ["MaDTV"]].copy()
                df_ho_gs[COL_PHAN_LOAI] = PHAN_LOAI_NEN
                if write_sheet_replace(SHEETS["danh_sach_ho"], df_ho_gs):
                    dong_bo_account_tu_ma_dtv(dtv_list)
                    st.success(f"Nạp dữ liệu thành công! Ghi nhận {len(df_ho_gs)} hộ nền.")
            else: st.error(f"File thiếu các cột cấu trúc: {thieu}")
    with tab2:
        df_ho = read_sheet(SHEETS["danh_sach_ho"])
        if not df_ho.empty:
            dtv_list = danh_sach_ma_dtv_theo_thu_tu(df_ho["MaDTV"])
            ma_dtv = st.selectbox("Lựa chọn Điều tra viên", dtv_list)
            c1, c2, c3 = st.columns(3)
            k = c1.number_input("Bước nhảy k", 1, 100, 2)
            r = c2.number_input("Vị trí ngẫu nhiên xuất phát r", 1, 100, 1)
            if c3.button("Thực hiện Bốc mẫu", type="primary", use_container_width=True):
                df_da_chon = ap_dung_chon_mau_cho_dtv(df_ho, ma_dtv, int(k), int(r))
                df_out = cap_nhat_danh_sach_ho_theo_dtv(df_ho, ma_dtv, df_da_chon)
                if write_sheet_replace(SHEETS["danh_sach_ho"], df_out):
                    st.success(f"Cấu hình bốc mẫu hoàn tất cho ĐTV {ma_dtv} (Chọn ra 40 hộ mẫu chính thức).")
                    hien_bang_ngang(df_da_chon)

def admin_thong_tin_ho(df_kq):
    render_header()
    if df_kq.empty:
        st.info("Chưa ghi nhận bản ghi kết quả nào từ ĐTV.")
        return
    sel = st.selectbox("Lựa chọn Mã Hộ cần kiểm tra", df_kq["HoSo"].astype(str).unique().tolist())
    row = df_kq[df_kq["HoSo"].astype(str) == sel].iloc[-1]
    
    with card_container(f"Dữ liệu phiếu hộ số {sel} — Chủ hộ: {row.get('TenChuHo')}"):
        hien_bang_ngang(pd.DataFrame([row]))
        
    # Tích hợp bản đồ GPS giám sát trực quan
    try:
        lat = float(str(row.get("GPS_lat")).split()[0])
        lng = float(str(row.get("GPS_lng")).split()[0])
        st.map(pd.DataFrame({"lat": [lat], "lon": [lng]}))
    except: pass

def admin_tong_hop(df_kq):
    render_header()
    if df_kq.empty:
        st.info("Hệ thống dữ liệu trống.")
        return
    hien_dataframe_an_toan(df_kq)

# ---------------------------------------------------------------------------
# UI: Màn hình nghiệp vụ Điều tra viên (ĐTV) nhập liệu trực địa
# ---------------------------------------------------------------------------
def dtv_nhap_phieu():
    user = st.session_state["user"]
    ma = user["ma"]
    form_ver = st.session_state.setdefault("form_ver", 0)
    render_header(f"📝 Giao diện Phiếu thu thập — Tài khoản ĐTV: {ma}")

    df_ho = ho_mau_can_dieu_tra(ho_theo_ma_dtv(read_sheet(SHEETS["danh_sach_ho"], silent=True), ma))
    if df_ho.empty:
        st.warning("Tài khoản chưa được cấu hình hoặc chưa bốc mẫu hộ chính thức.")
        return

    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    done = set(df_kq[df_kq["MaDTV"].astype(str) == str(ma)]["HoSo"].astype(str)) if not df_kq.empty else set()
    pending = df_ho[~df_ho["HoSo"].astype(str).isin(done)]

    c1, c2 = st.columns(2)
    c1.metric("Hộ mẫu chỉ tiêu được gán", len(df_ho))
    c2.metric("Hộ chưa hoàn thành", len(pending))

    if pending.empty:
        st.success("🎉 Xin chúc mừng! Bạn đã hoàn thành 100% khối lượng công việc điều tra.")
        return

    labels = pending.apply(lambda r: f"Hộ {r.get('HoSo')} — Chủ hộ: {r.get('TenChuHo')} (Xã {r.get('Xa')})", axis=1).tolist()
    idx = st.selectbox("Lựa chọn Hộ thực hiện điều tra thu nhập", range(len(labels)), format_func=lambda i: labels[i])
    ho = pending.iloc[idx]
    ho_so = str(ho.get("HoSo"))

    # Đọc định vị thực tế địa bàn trường điều tra
    loc = streamlit_geolocation() if streamlit_geolocation else None
    geo_hien_tai = phan_tich_geofence(ho, loc)
    hien_canh_bao_geofence_nhe(geo_hien_tai)
    
    ghi_chu_lech = ""
    if geo_hien_tai.get("bat_buoc_ghi_chu"):
        ghi_chu_lech = st.text_area("Giải trình lý do định vị lệch mục tiêu (>2km):", key=f"gc_vtr_{ho_so}_{form_ver}")

    hien_canh_bao_khong_tinh()

    tab_tt, tab_nhap, tab_tong = st.tabs(["📋 1. Thông tin Nhân khẩu", "🛠️ 2. Kê khai nguồn thu", "📊 3. Bảng tổng hợp phiếu"])
    with tab_tt:
        with card_container("Thông tin Hành chính định danh"):
            st.text_input("Chủ hộ", value=str(ho.get("TenChuHo")), disabled=True)
            st.text_input("Địa bàn thôn / xóm", value=str(ho.get("DiaBan")), disabled=True)
            st.number_input("Số nhân khẩu thường trú (Thành viên thực tế)", min_value=1, value=1, key=f"nk_{ho_so}_{form_ver}")
    with tab_nhap:
        nhap_lieu_5_nhom(ho_so, form_ver)
    with tab_tong:
        du_lieu_form = tong_hop_du_lieu_phieu(ho_so, form_ver)
        hop_le, ds_loi = kiem_tra_validation_phieu(ho_so, form_ver)
        
        if du_lieu_form["hang_bang"]:
            hien_dataframe_an_toan(pd.DataFrame(du_lieu_form["hang_bang"]))
        else: st.caption("Chưa có dữ liệu tính toán.")

        if ds_loi:
            st.error("Phiếu ghi nhận lỗi logic — Đề nghị ĐTV kiểm tra sửa đổi:")
            for e in ds_loi: st.write(f"- {e}")

        if st.button("💾 Hoàn thành & Lưu phiếu lên máy chủ", type="primary", use_container_width=True, disabled=not hop_le):
            gps = phan_tich_vi_tri_gps(loc)
            row = tao_dong_ket_qua_qd1099(
                ma_dtv=ma, ho=ho, nhan_khau=int(st.session_state[f"nk_{ho_so}_{form_ver}"]),
                thu_luong=du_lieu_form["thu_luong"], linh_vuc=du_lieu_form["linh_vuc"],
                dt_sxkd=du_lieu_form["dt_sxkd"], cp_sxkd=du_lieu_form["cp_sxkd"],
                thu_khac=du_lieu_form["thu_khac"], loc=loc, gps=gps, geo=geo_hien_tai,
                ghi_chu_vi_tri=str(ghi_chu_lech)
            )
            if append_ket_qua(row):
                st.toast("Lưu phiếu điều tra thành công!", icon="✅")
                st.rerun()

# ---------------------------------------------------------------------------
# Cổng điều hướng luồng chính hệ thống (Main Entry)
# ---------------------------------------------------------------------------
def main():
    data = load_all_data_sync()
    if "user" not in st.session_state:
        page_login()
        return

    user = st.session_state["user"]
    st.sidebar.markdown(f'<b>💻 BÀN LÀM VIỆC</b><br><small>Tài khoản: {user["ma"]}</small>', unsafe_allow_html=True)

    if user["role"] == "admin" and is_admin(str(user.get("ma", ""))):
        menu = st.sidebar.radio("Hệ thống quản trị", ["📊 Điều hành thống kê", "⚙️ Hệ thống", "🔍 Thông tin hộ", "📈 Tổng hợp"])
        if st.sidebar.button("Đăng xuất Hệ thống", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        # --- CÁCH SỬA: BỎ KHUNG DASH-HEADER DÀY ---
        # Thay vì truyền menu vào render_header(), ta để trống để nó chỉ hiển thị ảnh
        render_header() 
        
        # Hiển thị tên menu dạng chữ gọn gàng bên dưới ảnh panel
        st.markdown(f"### ➔ {menu}")
        
        # Sau đó giữ nguyên các lệnh if/elif bên dưới của bạn
        if menu == "📊 Điều hành thống kê": render_admin_dashboard(data["ho"], data["kq"])
        elif menu == "⚙️ Hệ thống": admin_he_thong()
        elif menu == "🔍 Thông tin hộ": admin_thong_tin_ho(data["kq"])
        elif menu == "📈 Tổng hợp": admin_tong_hop(data["kq"])
    else:
        if st.sidebar.button("Đăng xuất Khỏi hệ thống", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        dtv_nhap_phieu()

if __name__ == "__main__":
    main()