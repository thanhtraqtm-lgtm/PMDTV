# -*- coding: utf-8 -*-
"""
PMDTV.py — Phiếu hỏi điều tra thu nhập năm 2026 (Streamlit + Google Sheets).
Phân quyền: ADMIN | ĐTV (sheet Account + DanhSachHo).
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

# Ẩn main-header trong sidebar để tránh trùng lặp
st.markdown("""
<style>
    .main-header {
        display: none !important;
    }`
</style>
""", unsafe_allow_html=True)

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None

try:
    from geopy.distance import geodesic
    from geopy.geocoders import Nominatim
except ImportError:
    geodesic = None
    Nominatim = None

# ---------------------------------------------------------------------------
# Cấu hình trang & giao diện
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
    # Sử dụng session_state để đánh dấu đã vẽ banner chưa
    if "header_rendered" not in st.session_state:
        # Lấy thông tin user
        user = st.session_state.get("user", {})
        is_admin = user.get("role") == 'admin'
        
        # Vẽ banner và CSS - CHỈ CHẠY LẦN ĐẦU TIÊN
        st.markdown(f"""
        <style>
            .header-main {{ background-color: #0d2137; padding: 15px; border-radius: 8px; }}
            .header-title {{ font-weight:bold; font-size: 1.1em; color: white; text-align: center; }}
            .banner-nongthon {{ width: 100%; height: auto; border-radius: 8px; margin-bottom: 10px; }}
            .subtitle-bar {{ background-color: #f0f2f6; padding: 10px; font-weight: bold; margin-top: 10px; }}
        </style>
        <div class="header-main">
            <img src="https://www.gso.gov.vn/wp-content/uploads/logo-gso.png" class="banner-nongthon">
            <div class="header-title">PHẦN MỀM ĐIỀU TRA THU NHẬP</div>
        </div>
        """, unsafe_allow_html=True)
        
        if is_admin:
            st.markdown("""
                <img src="https://images.unsplash.com/photo-1523348837708-15d4a09cfacb?auto=format&fit=crop&q=80&w=600&h=150" class="banner-nongthon">
            """, unsafe_allow_html=True)
            
        # Đánh dấu đã vẽ xong banner
        st.session_state.header_rendered = True

    # TIÊU ĐỀ TRANG: Luôn hiện mỗi khi gọi hàm để biết đang ở trang nào
    st.markdown(f'<div class="subtitle-bar">{title}</div>', unsafe_allow_html=True)
        
def apply_custom_style() -> None:
    """Giao diện Navy chủ đạo — bo góc, đổ bóng, tối giản."""
    st.markdown(
        f"""
        <style>
        :root {{
            --navy: {NAVY_PRIMARY};
            --navy-accent: {NAVY_ACCENT};
            --navy-light: {NAVY_LIGHT};
        }}
        .stApp {{
            background: linear-gradient(165deg, #f4f7fb 0%, #ffffff 55%);
        }}
        [data-testid="stSidebar"] {{
            background-color: {NAVY_LIGHT};
            border-right: 1px solid #c5d0de;
        }}
        .main-header, .dash-header {{
            background: linear-gradient(135deg, {NAVY_PRIMARY}, {NAVY_ACCENT});
            color: #fff;
            padding: 1.1rem 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            box-shadow: 0 4px 14px rgba(13, 33, 55, 0.18);
        }}
        .dash-header h1 {{
            margin: 0;
            font-size: 1.45rem;
            letter-spacing: 0.04em;
            font-weight: 700;
        }}
        .card-box {{
            background: #ffffff;
            border-radius: 10px;
            padding: 1rem 1.15rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 12px rgba(13, 33, 55, 0.08);
            border: 1px solid #e2e8f0;
        }}
        .canh-bao-qd1099 {{
            background: #fff8e1;
            border-left: 4px solid #f9a825;
            padding: 0.75rem 1rem;
            border-radius: 10px;
            margin: 0.5rem 0 1rem 0;
            font-size: 0.92rem;
        }}
        .canh-bao-vang {{
            background: #fff8e1;
            border-left: 4px solid #f9a825;
            padding: 0.65rem 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            font-size: 0.92rem;
        }}
        .canh-bao-do, .input-loi-do {{
            background: #ffebee !important;
            border-left: 4px solid #c62828;
            padding: 0.65rem 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            font-size: 0.92rem;
            color: #b71c1c;
        }}
        div[data-testid="stMetric"] {{
            background: #fff;
            padding: 0.65rem 0.85rem;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(13, 33, 55, 0.06);
            border: 1px solid #e8edf3;
        }}
        @media (max-width: 768px) {{
            .main-header, .dash-header {{ font-size: 1rem; padding: 0.85rem; }}
            [data-testid="stTabs"] button {{ font-size: 0.85rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def card_container(title: str | None = None):
    """Khối nội dung bo góc 10px + đổ bóng."""
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

# --- QĐ 1099 / Phần B: 7 nguồn thu nhập ---
ADMIN_MA = "ADMIN"
TRANG_THAI_MK_CHUA = "Chưa đổi mật khẩu"
TRANG_THAI_MK_DA = "Đã đổi mật khẩu"
CANH_BAO_KHONG_TINH = (
    "KHÔNG tính tiền bán đất, rút tiết kiệm, vay nợ, đền bù giải tỏa vào thu nhập."
)

# Lĩnh vực nông, lâm, thủy sản (mỗi mục: Doanh thu - Chi phí = Thuần)
LINH_VUC_NLN_TS: list[tuple[str, str]] = [
    ("TrongTrot", "Trồng trọt"),
    ("ChanNuoi", "Chăn nuôi"),
    ("LamNghiep", "Lâm nghiệp"),
    ("ThuySan", "Thủy sản"),
]

# 7 nguồn thu nhập hiển thị bảng tổng hợp
BAO_CAO_7_NGUON: list[tuple[str, str]] = [
    ("ThuLuong", "1. Tiền lương, tiền công, phụ cấp, thưởng"),
    ("Thu_TrongTrot", "2.1 Trồng trọt (thuần)"),
    ("Thu_ChanNuoi", "2.2 Chăn nuôi (thuần)"),
    ("Thu_LamNghiep", "2.3 Lâm nghiệp (thuần)"),
    ("Thu_ThuySan", "2.4 Thủy sản (thuần)"),
    ("Thu_SXKD", "3. SXKD phi nông nghiệp (thuần)"),
    ("ThuKhac", "4. Thu nhập khác"),
]

# Phần B — nhãn khớp biểu mẫu QĐ 1099
CHI_TIEU_PHAN_B: list[dict[str, Any]] = [
    {"ma": "ThuLuong", "ten": "1. Tiền lương, tiền công, phụ cấp, thưởng", "loai": "luong"},
    {"ma": "TrongTrot", "ten": "2.1 Trồng trọt", "loai": "linh_vuc_sp"},
    {"ma": "ChanNuoi", "ten": "2.2 Chăn nuôi", "loai": "linh_vuc_sp"},
    {"ma": "LamNghiep", "ten": "2.3 Lâm nghiệp", "loai": "linh_vuc_sp"},
    {"ma": "ThuySan", "ten": "2.4 Thủy sản", "loai": "linh_vuc_sp"},
    {"ma": "SXKD", "ten": "3. Sản xuất kinh doanh phi nông nghiệp", "loai": "sxkd"},
    {"ma": "ThuKhac", "ten": "4. Thu nhập khác", "loai": "khac"},
]

# Sản phẩm theo lĩnh vực (chọn bằng selectbox — không bảng ngang)
SAN_PHAM_LINH_VUC: dict[str, list[str]] = {
    "TrongTrot": ["Lúa", "Ngô", "Rau màu", "Cây ăn quả", "Cây công nghiệp", "Khác"],
    "ChanNuoi": ["Gia súc", "Gia cầm", "Vịt ngan", "Khác"],
    "LamNghiep": ["Khai thác gỗ", "Trồng rừng", "Thu hái lâm sản", "Khác"],
    "ThuySan": ["Nuôi cá", "Nuôi tôm", "Nuôi cua", "Khai thác thủy sản", "Khác"],
}

O_NHAP_SAN_PHAM = ["Giá bán", "Tự dùng", "Giống", "Thức ăn", "Chi khác"]

# 5 nhóm luồng nhập liệu độc lập
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
CANH_BAO_GEO_VANG = (
    "Vị trí hiện tại ở ngoài phạm vi địa bàn thôn/xóm. Hãy kiểm tra lại"
)
CANH_BAO_GEO_DO = "Cảnh báo: Tọa độ lệch quá lớn. Nghi vấn vị trí giả"

# Cột chuẩn trong hệ thống (không dùng cột Nhân khẩu)
COL_HO = ["Huyen", "Xa", "DiaBan", "HoSo", "TenChuHo"]
SO_HO_NEN = 100
SO_HO_MAU = 40
COL_PHAN_LOAI = "PhanLoai"
PHAN_LOAI_MAU = "Mẫu"
PHAN_LOAI_NEN = "Dự phòng/Nền"

# Hiển thị tiếng Việt có dấu (tên cột kỹ thuật -> nhãn giao diện)
NHAN_HIEN_THI = {
    "Huyen": "Huyện",
    "Xa": "Xã",
    "DiaBan": "Địa bàn",
    "HoSo": "Hộ số",
    "TenChuHo": "Tên chủ hộ",
    "MaDTV": "Mã ĐTV",
    "PhanLoai": "Phân loại",
    "HoTen": "Họ và tên",
    "TrangThai": "Trạng thái",
    "NgayPhanCong": "Ngày phân công",
    "ThuLuong": "Tiền lương, tiền công (nghìn đồng/tháng)",
    "ThuNN": "Thu nông nghiệp (nghìn đồng/tháng)",
    "ChiNN": "Chi phí sản xuất NN (nghìn đồng/tháng)",
    "ThuNNThuan": "Thu nhập thuần nông nghiệp",
    "ThuSXKD": "Thu nhập SXKD phi NN",
    "ThuKhac": "Thu nhập khác",
    "TongThuNhap": "Tổng thu nhập hộ (nghìn đồng/tháng)",
    "GPS_lat": "Vĩ độ GPS",
    "GPS_lng": "Kinh độ GPS",
    "DoChinhXac": "Độ chính xác (m)",
    "Xac_Thuc_GPS": "Xác thực GPS",
    "Sai_so": "Sai số GPS (m)",
    "Do_cao": "Độ cao (m)",
    "IP": "Địa chỉ IP",
    "MockGPS": "Nghi ngờ vị trí giả",
    "NgayNhap": "Ngày nhập phiếu",
    "Tong": "Tổng số hộ",
    "Xong": "Đã hoàn thành",
    "PhanTram": "Tỷ lệ hoàn thành (%)",
    "SoPhieu": "Số phiếu",
    "NganhKT": "Ngành kinh tế",
    "MatKhau": "Mật khẩu",
    "NhanKhauTT": "Số nhân khẩu thường trú",
    "DT_TrongTrot": "DT trồng trọt",
    "CP_TrongTrot": "CP trồng trọt",
    "Thu_TrongTrot": "Thuần trồng trọt",
    "DT_ChanNuoi": "DT chăn nuôi",
    "CP_ChanNuoi": "CP chăn nuôi",
    "Thu_ChanNuoi": "Thuần chăn nuôi",
    "DT_LamNghiep": "DT lâm nghiệp",
    "CP_LamNghiep": "CP lâm nghiệp",
    "Thu_LamNghiep": "Thuần lâm nghiệp",
    "DT_ThuySan": "DT thủy sản",
    "CP_ThuySan": "CP thủy sản",
    "Thu_ThuySan": "Thuần thủy sản",
    "DT_SXKD": "DT SXKD phi NN",
    "CP_SXKD": "CP SXKD phi NN",
    "Thu_SXKD": "Thuần SXKD phi NN",
    "ThuBQDauNguoi": "Thu nhập bình quân đầu người",
    "DiaChi": "Địa chỉ",
    "KhoangCachLech": "Khoảng cách lệch (m)",
    "MaDiaBan": "Mã địa bàn",
    "GhiChuViTri": "Ghi chú vị trí lệch",
}


def _bo_dau_chuoi(s: str) -> str:
    """Chuẩn hóa tên cột: bỏ dấu, chữ thường, bỏ khoảng trắng và gạch dưới."""
    s = str(s).strip().replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s_\-]+", "", s.lower())
    return s


# Khóa đã chuẩn hóa (Excel / Google Sheet có dấu hoặc không dấu) -> tên cột nội bộ
ANH_XA_TEN_COT: dict[str, str] = {
    "huyen": "Huyen",
    "tinh": "Huyen",
    "tinhthanh": "Huyen",
    "xa": "Xa",
    "xaphuong": "Xa",
    "phuongxa": "Xa",
    "diaban": "DiaBan",
    "diahinh": "DiaBan",
    "hoso": "HoSo",
    "soho": "HoSo",
    "hosodemau": "HoSo",
    "mahodiem": "HoSo",
    "tenchuho": "TenChuHo",
    "tenchu": "TenChuHo",
    "chuho": "TenChuHo",
    "madtv": "MaDTV",
    "phanloai": "PhanLoai",
    "phanloaiho": "PhanLoai",
    "madieutravien": "MaDTV",
    "hoten": "HoTen",
    "hovaten": "HoTen",
    "tendieutravien": "HoTen",
    "trangthai": "TrangThai",
    "ngayphancong": "NgayPhanCong",
    "thuluong": "ThuLuong",
    "thunn": "ThuNN",
    "chinn": "ChiNN",
    "thunnthuan": "ThuNNThuan",
    "thusxkd": "ThuSXKD",
    "thukhac": "ThuKhac",
    "tongthunhap": "TongThuNhap",
    "gpslat": "GPS_lat",
    "gpslong": "GPS_lng",
    "kinhdo": "GPS_lng",
    "vido": "GPS_lat",
    "dochinhxac": "DoChinhXac",
    "accuracy": "Sai_so",
    "saiso": "Sai_so",
    "docao": "Do_cao",
    "altitude": "Do_cao",
    "xacthucgps": "Xac_Thuc_GPS",
    "mockgps": "MockGPS",
    "ngaynhap": "NgayNhap",
    "nganhkt": "NganhKT",
    "nganhkinhte": "NganhKT",
    "matkhau": "MatKhau",
    "nhankhau": "NhanKhauTT",
    "nhankhautt": "NhanKhauTT",
    "sonhankhau": "NhanKhauTT",
    "thunhapbinhquandaunguoi": "ThuBQDauNguoi",
    "thubinhquandaunguoi": "ThuBQDauNguoi",
    "diachi": "DiaChi",
    "diachiho": "DiaChi",
    "diachicutru": "DiaChi",
    "khoangcachlech": "KhoangCachLech",
    "madiaaban": "MaDiaBan",
    "madiaban": "MaDiaBan",
    "madb": "MaDiaBan",
    "ghichuvitri": "GhiChuViTri",
    "ghichu": "GhiChuViTri",
    "lydolech": "GhiChuViTri",
}


def chuan_hoa_ten_cot_df(df: pd.DataFrame) -> pd.DataFrame:
    """Đổi tên cột từ tiếng Việt có/không dấu hoặc ASCII sang tên nội bộ thống nhất."""
    if df.empty:
        return df
    rename: dict[str, str] = {}
    for c in df.columns:
        key = _bo_dau_chuoi(str(c))
        if key in ANH_XA_TEN_COT:
            rename[c] = ANH_XA_TEN_COT[key]
    return df.rename(columns=rename)


def hien_thi_bang(df: pd.DataFrame) -> pd.DataFrame:
    """Đổi tên cột để hiển thị trên giao diện (tiếng Việt có dấu)."""
    if df.empty:
        return df
    m = {c: NHAN_HIEN_THI.get(c, c) for c in df.columns}
    return df.rename(columns=m)


def chuan_hoa_gia_tri_hien_thi(val: Any) -> Any:
    """Chuyển giá trị pandas/numpy sang kiểu Python thuần (tránh np.int64 trên UI)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if hasattr(val, "item"):
        try:
            val = val.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(val, float) and val == int(val):
        return int(val)
    if isinstance(val, (int, float, str, bool)):
        return val
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "<na>") else s


def chuan_hoa_df_hien_thi(df: pd.DataFrame) -> pd.DataFrame:
    """DataFrame sạch cho st.dataframe — hàng ngang, không kiểu kỹ thuật."""
    if df.empty:
        return df
    out = df.copy()
    for c in out.columns:
        out[c] = out[c].map(chuan_hoa_gia_tri_hien_thi)
    return out


def df_an_toan_hien_thi(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa DataFrame trước hiển thị — tránh np.int64, None, InvalidIndexError."""
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy().reset_index(drop=True)
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
        else:
            out[c] = out[c].fillna("").astype(str).replace({"nan": "", "None": "<NA>"})
    return out


def hien_dataframe_an_toan(df: pd.DataFrame, *, an_index: bool = True) -> None:
    """Hiển thị bảng an toàn trên mobile/desktop — không dùng height."""
    if df is None or df.empty:
        st.caption("Chưa có dữ liệu.")
        return
    hien = hien_thi_bang(df_an_toan_hien_thi(df))
    st.dataframe(hien, use_container_width=True, hide_index=an_index)


def hien_bang_ngang(df: pd.DataFrame) -> None:
    """Hiển thị bảng dữ liệu (mỗi bản ghi = một hàng)."""
    hien_dataframe_an_toan(df)


def doc_excel_danh_sach_ho(
    file, *, can_madtv: bool = False
) -> tuple[pd.DataFrame | None, list[str]]:
    """
    Đọc Excel danh sách hộ, khớp cột linh hoạt (có dấu / không dấu).
    Trả về (DataFrame các cột chuẩn, danh sách tên cột thiếu bằng tiếng Việt).
    can_madtv=True: bắt buộc có cột Mã ĐTV (dùng cho nạp thông minh 1.000 hộ).
    """
    raw = pd.read_excel(file, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]
    df = chuan_hoa_ten_cot_df(raw)
    thieu: list[str] = []
    ten_vi = {
        "Huyen": "Huyện",
        "Xa": "Xã",
        "DiaBan": "Địa bàn",
        "HoSo": "Hộ số",
        "TenChuHo": "Tên chủ hộ",
        "MaDTV": "Mã ĐTV",
    }
    cols_can = list(COL_HO) + (["MaDTV"] if can_madtv else [])
    for canon in cols_can:
        if canon not in df.columns:
            thieu.append(ten_vi.get(canon, canon))
    if thieu:
        return None, thieu
    out_cols = list(cols_can)
    if "DiaChi" in df.columns and "DiaChi" not in out_cols:
        out_cols.append("DiaChi")
    return df[out_cols].fillna(""), []


def danh_sach_ma_dtv_theo_thu_tu(series: pd.Series) -> list[str]:
    """Lấy danh sách Mã ĐTV duy nhất, giữ nguyên giá trị gốc và thứ tự xuất hiện trong file."""
    ket_qua: list[str] = []
    da_thay: set[str] = set()
    for gia_tri in series.astype(str).str.strip():
        if not gia_tri or gia_tri.lower() in ("nan", "none", ""):
            continue
        if gia_tri not in da_thay:
            da_thay.add(gia_tri)
            ket_qua.append(gia_tri)
    return ket_qua


def loc_mau_1000_ho(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Bước 1 — Danh sách nền: 10 Mã ĐTV đầu tiên trong file Excel;
    mỗi mã lấy đúng 100 hộ đầu tiên (giữ thứ tự gốc), tối đa 1.000 hộ.
    """
    if df.empty or "MaDTV" not in df.columns:
        return pd.DataFrame(), []

    work = df.copy()
    work["MaDTV"] = work["MaDTV"].astype(str).str.strip()

    tat_ca_dtv = danh_sach_ma_dtv_theo_thu_tu(work["MaDTV"])
    dtv_10 = tat_ca_dtv[:10]
    cac_phan: list[pd.DataFrame] = []
    for ma in dtv_10:
        cac_phan.append(work[work["MaDTV"] == ma].head(100))

    if not cac_phan:
        return pd.DataFrame(), []
    return pd.concat(cac_phan, ignore_index=True), dtv_10


def ho_theo_ma_dtv(df_ho: pd.DataFrame, ma_dtv: str) -> pd.DataFrame:
    """Lọc danh sách hộ theo đúng Mã ĐTV (khớp chính xác sau khi strip)."""
    if df_ho.empty or "MaDTV" not in df_ho.columns:
        return pd.DataFrame()
    ma = str(ma_dtv).strip()
    return df_ho[df_ho["MaDTV"].astype(str).str.strip() == ma].copy()


def lay_danh_sach_nen(df: pd.DataFrame, ma_dtv: str) -> pd.DataFrame:
    """Bước 1: đúng 100 hộ đầu tiên của Mã ĐTV trong file/sheet (thứ tự gốc)."""
    return ho_theo_ma_dtv(df, ma_dtv).head(SO_HO_NEN).reset_index(drop=True)


def chon_chi_so_mau_tu_nen(n_nen: int, k: int, r: int) -> list[int]:
    """
    Bước 2: từ n hộ nền, chọn đủ SO_HO_MAU chỉ số.
    Lấy mẫu hệ thống bước nhảy k từ vị trí r; nếu chưa đủ thì bổ sung tuần tự các hộ còn lại.
    """
    if n_nen <= 0 or k < 1 or r < 1:
        return []

    picked: list[int] = []
    seen: set[int] = set()
    pos = r - 1
    while pos < n_nen and len(picked) < SO_HO_MAU:
        if pos not in seen:
            picked.append(pos)
            seen.add(pos)
        pos += k

    for i in range(n_nen):
        if len(picked) >= SO_HO_MAU:
            break
        if i not in seen:
            picked.append(i)
            seen.add(i)

    return picked[:SO_HO_MAU]


def gan_phan_loai_ho(df_nen: pd.DataFrame, chi_so_mau: list[int]) -> pd.DataFrame:
    """Gán cột Phân loại: Mẫu (40) / Dự phòng/Nền (còn lại trong 100 hộ nền)."""
    out = df_nen.reset_index(drop=True).copy()
    out[COL_PHAN_LOAI] = PHAN_LOAI_NEN
    for i in chi_so_mau:
        if 0 <= i < len(out):
            out.loc[out.index[i], COL_PHAN_LOAI] = PHAN_LOAI_MAU
    return out


def ap_dung_chon_mau_cho_dtv(df: pd.DataFrame, ma_dtv: str, k: int, r: int) -> pd.DataFrame:
    """Bước 1 + 2: lấy 100 hộ nền rồi chọn 40 hộ mẫu trong đó."""
    df_nen = lay_danh_sach_nen(df, ma_dtv)
    if df_nen.empty:
        return pd.DataFrame()
    chi_so = chon_chi_so_mau_tu_nen(len(df_nen), k, r)
    return gan_phan_loai_ho(df_nen, chi_so)


def ho_mau_can_dieu_tra(df_ho: pd.DataFrame) -> pd.DataFrame:
    """Chỉ các hộ được đánh dấu «Mẫu» — ĐTV nhập liệu trên danh sách này."""
    if df_ho.empty:
        return df_ho
    if COL_PHAN_LOAI not in df_ho.columns:
        return df_ho
    return df_ho[df_ho[COL_PHAN_LOAI].astype(str).str.strip() == PHAN_LOAI_MAU].copy()


def cap_nhat_danh_sach_ho_theo_dtv(
    df_all: pd.DataFrame, ma_dtv: str, df_nen_da_phan_loai: pd.DataFrame
) -> pd.DataFrame:
    """Thay 100 hộ của một Mã ĐTV trong sheet DanhSachHo, giữ nguyên các ĐTV khác."""
    if df_all.empty:
        return df_nen_da_phan_loai
    ma = str(ma_dtv).strip()
    mask_khac = df_all["MaDTV"].astype(str).str.strip() != ma
    phan_con_lai = df_all[mask_khac]
    return pd.concat([phan_con_lai, df_nen_da_phan_loai], ignore_index=True)


# ---------------------------------------------------------------------------
# Google Sheets — gspread + Service Account JSON (google-auth)
# ---------------------------------------------------------------------------
SHEET_DANH_SACH_HO = "DanhSachHo"
EXPECTED_SERVICE_EMAIL = "appthunhap@crypto-avenue-410700.iam.gserviceaccount.com"
EXPECTED_SPREADSHEET_TITLE = "Dieutrathunhaptest"

_GSHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _gsheets_cfg() -> dict:
    return dict(st.secrets["connections"]["gsheets"])


def _spreadsheet_url() -> str:
    """
    Ưu tiên gsheets_url.txt (dán link file Dieutrathunhaptest), sau đó secrets.toml.
    """
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
        raise KeyError(
            "Thiếu link spreadsheet. Dán URL file Dieutrathunhaptest vào "
            "gsheets_url.txt (dòng đầu, không có #) hoặc spreadsheet_url trong secrets.toml."
        )
    url = str(url).strip()
    # Bỏ ?gid=... và #gid=... — gspread chỉ cần link /edit
    if "?" in url:
        url = url.split("?", 1)[0]
    if "#" in url:
        url = url.split("#", 1)[0]
    return url


def _credentials_json_path() -> Path:
    """Chỉ dùng đúng file JSON khai báo trong secrets — không đoán file khác."""
    root = _project_root()
    cfg = _gsheets_cfg()
    cred_file = cfg.get("credentials_file")
    if not cred_file:
        raise FileNotFoundError(
            "Thiếu credentials_file trong [connections.gsheets] "
            "(ví dụ: .credentials/crypto-avenue-410700-f7e540ba2e49.json)"
        )
    path = Path(cred_file)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file JSON: {path}")
    return path


def _service_account_email() -> str:
    _, data = _load_credentials_json()
    return str(data.get("client_email", "")).strip()


def _load_credentials_json() -> tuple[Path, dict]:
    path = _credentials_json_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") != "service_account":
        raise ValueError(f"File JSON không phải Service Account: {path}")
    return path, data


@st.cache_resource
@st.cache_resource
def _gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials
    import json

    # Đọc trực tiếp nội dung JSON từ "két sắt" Secrets
    json_key = json.loads(st.secrets["gcp_service_account"]["json"])
    
    # Kết nối
    creds = Credentials.from_service_account_info(json_key, scopes=_GSHEETS_SCOPES)
    return gspread.authorize(creds)

def _open_spreadsheet():
    # Gọi hàm kết nối đã sửa ở trên
    gc = _gspread_client()
    # Lấy URL từ Secrets
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return gc.open_by_url(url)

def hien_thi_thong_tin_ket_noi_gsheets(*, truoc_khi_ghi: bool = False) -> bool:
    """In ra email và link đang dùng để kiểm tra cấu hình."""
    try:
        import json
        json_key = json.loads(st.secrets["gcp_service_account"]["json"])
        email = json_key.get("client_email", "Không xác định")
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    except Exception as e:
        st.error(f"Lỗi đọc cấu hình từ Secrets: {e}")
        return False

    st.info(f"Đang dùng tài khoản **{email}** để ghi vào file [Google Sheets]({url})")

    # Kiểm tra email khớp hay không
    if "EXPECTED_SERVICE_EMAIL" in globals() and email != EXPECTED_SERVICE_EMAIL:
        st.error(f"Sai tài khoản! Email là `{email}`, cần đúng `{EXPECTED_SERVICE_EMAIL}`.")
        return False

    if not truoc_khi_ghi:
        return True

    try:
        sh = _open_spreadsheet()
        st.success(f"Đã mở đúng file: **{sh.title}**")
        return True
    except Exception as e:
        st.error(f"Lỗi khi mở file: {e}")
        return False


def _loi_api_chua_bat(exc: Exception) -> str:
    """Google Cloud project chưa bật Google Sheets API (thường bị gói thành PermissionError)."""
    try:
        _, data = _load_credentials_json()
        project_id = data.get("project_id", "")
    except Exception:
        project_id = ""
    link = (
        f"https://console.developers.google.com/apis/api/sheets.googleapis.com/overview"
        f"?project={project_id}"
        if project_id
        else "https://console.cloud.google.com/apis/library/sheets.googleapis.com"
    )
    return (
        f"❌ **Google Sheets API chưa được bật** trên project Google Cloud của file JSON.\n\n"
        f"Đây là lý do chính gây PermissionError dù đã chia sẻ Editor đúng email.\n\n"
        f"**Cách sửa:**\n"
        f"1. Mở: {link}\n"
        f"2. Bấm **Enable** (Bật) Google Sheets API\n"
        f"3. (Khuyến nghị) Bật thêm **Google Drive API** trên cùng project\n"
        f"4. Đợi 1–2 phút rồi chạy lại app\n\n"
        f"Chi tiết kỹ thuật: {exc}"
    )


def _gsheets_error_message(exc: Exception, *, sheet_name: str, action: str) -> str:
    import gspread

    msg = str(exc).lower()
    email = ""
    try:
        email = _service_account_email()
    except Exception:
        pass

    if isinstance(exc, FileNotFoundError):
        return (
            f"❌ Không tìm thấy file JSON chìa khóa Service Account.\n\n"
            f"Chi tiết: {exc}\n\n"
            f"→ Kiểm tra `credentials_file` trong `.streamlit/secrets.toml`."
        )
    if isinstance(exc, PermissionError):
        if "sheets.googleapis.com" in msg or "google sheets api" in msg:
            return _loi_api_chua_bat(exc)
        return (
            f"❌ PermissionError — `{email or EXPECTED_SERVICE_EMAIL}` "
            f"không có quyền trên link:\n`{_spreadsheet_url()}`\n\n"
            f"→ Chia sẻ file **{EXPECTED_SPREADSHEET_TITLE}** cho email trên (quyền **Editor**)."
        )
    if isinstance(exc, gspread.exceptions.SpreadsheetNotFound):
        return (
            f"❌ Sai link Google Sheets — không mở được spreadsheet.\n\n"
            f"URL: `{_spreadsheet_url()}`\nChi tiết: {exc}"
        )
    if isinstance(exc, gspread.exceptions.WorksheetNotFound):
        return (
            f"❌ Không tìm thấy sheet «{sheet_name}».\n\n"
            f"→ Tạo tab «{SHEET_DANH_SACH_HO}» (viết liền, không dấu)."
        )
    if isinstance(exc, gspread.exceptions.APIError):
        if "sheets api has not been used" in msg or "sheets.googleapis.com" in msg:
            return _loi_api_chua_bat(exc)
        if "drive api has not been used" in msg or "drive.googleapis.com" in msg:
            return (
                f"❌ **Google Drive API chưa được bật** trên project Google Cloud.\n\n"
                f"Bật tại Google Cloud Console → APIs → Google Drive API → Enable.\n\n"
                f"Chi tiết: {exc}"
            )
        if "403" in msg or "permission" in msg or "forbidden" in msg:
            return (
                f"❌ Sai quyền — `{email}` chưa được chia sẻ Editor trên file này.\n\n"
                f"URL: `{_spreadsheet_url()}`\nChi tiết: {exc}"
            )
        return f"❌ Lỗi API khi {action} sheet «{sheet_name}»: {exc}"
    return f"❌ Lỗi khi {action} sheet «{sheet_name}»: {type(exc).__name__}: {exc}"


@st.cache_data(ttl=60)
def _read_sheet_cached(name: str) -> pd.DataFrame:
    sh = _open_spreadsheet()
    ws = sh.worksheet(name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return chuan_hoa_ten_cot_df(df)


def read_sheet(name: str, *, silent: bool = False) -> pd.DataFrame:
    try:
        return _read_sheet_cached(name)
    except Exception as e:
        if not silent:
            st.error(_gsheets_error_message(e, sheet_name=name, action="đọc"))
        return pd.DataFrame()


def clear_sheet_cache():
    _read_sheet_cached.clear()


def update_sheet(
    sheet_name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True
) -> bool:
    """Ghi đè sheet: clear() rồi update header + dữ liệu."""
    if sheet_name == SHEETS["danh_sach_ho"]:
        sheet_name = SHEET_DANH_SACH_HO

    if not silent and not _kiem_tra_ket_noi_gsheets():
        return False

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
        if sheet_name == SHEETS["ket_qua"]:
            ap_dung_mau_do_hang_gia(ws)
        if thong_bao and not silent:
            st.success(f"Đã lưu dữ liệu vào sheet «{sheet_name}».")
        return True
    except Exception as e:
        if not silent:
            st.error(_gsheets_error_message(e, sheet_name=sheet_name, action="ghi"))
        return False


def _kiem_tra_ket_noi_gsheets() -> bool:
    """Kiểm tra JSON + quyền mở spreadsheet (không hiện đường dẫn file kỹ thuật)."""
    try:
        cred_path, _ = _load_credentials_json()
        email = _service_account_email()
        if email != EXPECTED_SERVICE_EMAIL:
            st.error(
                f"Sai tài khoản dịch vụ Google Sheets. Cần dùng `{EXPECTED_SERVICE_EMAIL}`."
            )
            return False
        _open_spreadsheet()
        return True
    except ValueError as e:
        st.error(str(e))
        return False
    except Exception as e:
        st.error(_gsheets_error_message(e, sheet_name=SHEET_DANH_SACH_HO, action="mở file"))
        return False


def ap_dung_mau_do_hang_gia(ws) -> None:
    """Tô đỏ toàn dòng KetQua khi Xac_Thuc_GPS bắt đầu bằng «GIẢ» (quản lý từ xa)."""
    from gspread.utils import rowcol_to_a1

    values = ws.get_all_values()
    if len(values) < 2:
        return
    headers = values[0]
    try:
        col_ix = headers.index("Xac_Thuc_GPS")
    except ValueError:
        return

    ncol = len(headers)
    fmt = {
        "backgroundColor": {"red": 0.96, "green": 0.78, "blue": 0.78},
        "textFormat": {
            "foregroundColor": {"red": 0.72, "green": 0.0, "blue": 0.0},
            "bold": True,
        },
    }
    for row_num in range(2, len(values) + 1):
        row = values[row_num - 1]
        if len(row) <= col_ix:
            continue
        val = str(row[col_ix]).strip()
        if val.startswith("GIẢ") or "[CHECK_FAKE]" in str(row):
            end_cell = rowcol_to_a1(row_num, ncol)
            ws.format(f"A{row_num}:{end_cell}", fmt)


def write_sheet_replace(
    name: str, df: pd.DataFrame, *, silent: bool = False, thong_bao: bool = True
) -> bool:
    return update_sheet(name, df, silent=silent, thong_bao=thong_bao)


def append_ket_qua(row: dict[str, Any], *, silent: bool = True) -> bool:
    try:
        df_old = read_sheet(SHEETS["ket_qua"], silent=silent)
        df_new = pd.DataFrame([row])
        out = df_new if df_old.empty else pd.concat([df_old, df_new], ignore_index=True)
        return write_sheet_replace(
            SHEETS["ket_qua"], out, silent=silent, thong_bao=not silent
        )
    except Exception as e:
        if not silent:
            st.error(f"Lỗi lưu phiếu: {e}")
        return False


# ---------------------------------------------------------------------------
# Sheet Account & tính toán thu nhập QĐ 1099
# ---------------------------------------------------------------------------
def so_hoa(gia_tri: Any) -> float:
    """Ép kiểu số an toàn — tránh TypeError từ ô nhập."""
    val = pd.to_numeric(gia_tri, errors="coerce")
    if isinstance(val, pd.Series):
        val = val.fillna(0).iloc[0] if len(val) else 0
    if pd.isna(val):
        return 0.0
    return float(val)


def thu_thuan(dt: float, cp: float) -> float:
    """Thu nhập thuần = Doanh thu - Chi phí (không âm)."""
    return max(0.0, so_hoa(dt) - so_hoa(cp))


def loi_chi_phi_vuot_thu(chi_phi: float, doanh_thu: float) -> bool:
    """Chi phí > Doanh thu / Thu nhập → lỗi đỏ."""
    return so_hoa(chi_phi) > so_hoa(doanh_thu)


def loi_tong_khong_khop(tong_nho: float, tong_lon: float, *, eps: float = 0.5) -> bool:
    """Tổng chi tiết ≠ tổng nhóm."""
    return abs(so_hoa(tong_nho) - so_hoa(tong_lon)) > eps


def hien_loi_validation(noi_dung: str) -> None:
    st.markdown(f'<p class="input-loi-do">{noi_dung}</p>', unsafe_allow_html=True)


def _key_hoat_dong(nhom_id: str, ho_so: str, form_ver: int) -> str:
    return f"hd_{nhom_id}_{ho_so}_{form_ver}"


def hoi_co_hoat_dong(nhom: dict[str, Any], ho_so: str, form_ver: int) -> bool:
    """Hộ có hoạt động [nhóm] không?"""
    key = _key_hoat_dong(nhom["id"], ho_so, form_ver)
    return st.radio(
        f"Hộ có hoạt động **{nhom['ten']}** không?",
        ["Có", "Không"],
        horizontal=True,
        key=key,
    ) == "Có"


def hien_canh_bao_khong_tinh() -> None:
    st.caption(f"⚠️ Lưu ý QĐ 1099: {CANH_BAO_KHONG_TINH}")


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
    """Tạo tài khoản ĐTV mới: mật khẩu mặc định = Mã ĐTV."""
    df = read_accounts()
    co_san = set(df["MaDTV"].astype(str).str.strip()) if not df.empty else set()
    rows: list[dict[str, str]] = []
    for ma in danh_sach_ma:
        ma = str(ma).strip()
        if not ma or ma in co_san or normalize_ma(ma) == ADMIN_MA:
            continue
        rows.append(
            {
                "MaDTV": ma,
                "MatKhau": ma,
                "HoTen": f"Điều tra viên {ma}",
                "TrangThai": TRANG_THAI_MK_CHUA,
            }
        )
    if rows:
        write_accounts(pd.concat([df, pd.DataFrame(rows)], ignore_index=True))


def xac_thuc_dang_nhap(ma_dtv: str, mat_khau: str) -> tuple[bool, str, pd.Series | None]:
    ma = str(ma_dtv).strip()
    df = read_accounts()
    if df.empty:
        return False, "Chưa có tài khoản trên sheet Account.", None
    row = df[df["MaDTV"].astype(str).str.strip() == ma]
    if row.empty:
        return False, f"Mã ĐTV «{ma}» không tồn tại.", None
    r = row.iloc[0]
    if str(r.get("MatKhau", "")).strip() != str(mat_khau).strip():
        return False, "Mật khẩu không đúng.", None
    return True, "", r


def can_doi_mat_khau(mat_khau: str, ma_dtv: str) -> bool:
    return str(mat_khau).strip() == str(ma_dtv).strip()


def cap_nhat_mat_khau(ma_dtv: str, mat_khau_moi: str) -> bool:
    df = read_accounts()
    if df.empty:
        return False
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


def _key_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> str:
    return f"chi_tiet_{ma_lv}_{ho_so}_{form_ver}"


def lay_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> list[dict[str, Any]]:
    return list(st.session_state.get(_key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver), []))


def xoa_chi_tiet_linh_vuc(ma_lv: str, ho_so: str, form_ver: int) -> None:
    st.session_state[_key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)] = []


def tong_hop_chi_tiet_linh_vuc(danh_sach: list[dict[str, Any]]) -> tuple[float, float, float]:
    dt = cp = 0.0
    for dong in danh_sach:
        gia_ban = so_hoa(dong.get("Giá bán", 0))
        tu_dung = so_hoa(dong.get("Tự dùng", 0))
        giong = so_hoa(dong.get("Giống", 0))
        thuc_an = so_hoa(dong.get("Thức ăn", 0))
        chi_khac = so_hoa(dong.get("Chi khác", 0))
        dt += max(0.0, gia_ban - tu_dung)
        cp += giong + thuc_an + chi_khac
    return dt, cp, thu_thuan(dt, cp)


def _co_hoat_dong(nhom_id: str, ho_so: str, form_ver: int) -> bool:
    return st.session_state.get(_key_hoat_dong(nhom_id, ho_so, form_ver), "Có") == "Có"


def _dat_zero_nhom_don(ma: str, ho_so: str, form_ver: int) -> None:
    st.session_state[f"dt_{ma}_{ho_so}_{form_ver}"] = 0.0
    st.session_state[f"cp_{ma}_{ho_so}_{form_ver}"] = 0.0


def _dat_zero_nhom_nlt(ho_so: str, form_ver: int) -> None:
    for muc in CHI_TIEU_PHAN_B:
        if muc["loai"] == "linh_vuc_sp":
            xoa_chi_tiet_linh_vuc(muc["ma"], ho_so, form_ver)


def nhap_thanh_vien_ho(ho_so: str, form_ver: int) -> None:
    key = f"ds_tv_{ho_so}_{form_ver}"
    if key not in st.session_state:
        st.session_state[key] = []
    ten = st.text_input("Họ tên thành viên", key=f"tv_ten_{ho_so}_{form_ver}")
    qh = st.selectbox(
        "Quan hệ với chủ hộ",
        ["Chủ hộ", "Vợ/chồng", "Con", "Cha/mẹ", "Khác"],
        key=f"tv_qh_{ho_so}_{form_ver}",
    )
    if st.button("Thêm thành viên", key=f"tv_them_{ho_so}_{form_ver}", use_container_width=True):
        if ten.strip():
            ds = list(st.session_state.get(key, []))
            ds.append({"Họ tên": ten.strip(), "Quan hệ": qh})
            st.session_state[key] = ds
            st.toast(f"Đã thêm «{ten.strip()}».", icon="✅")
        else:
            st.toast("Nhập họ tên thành viên.", icon="⚠️")
    ds_hien = st.session_state.get(key, [])
    if ds_hien:
        with st.expander(f"Danh sách {len(ds_hien)} thành viên", expanded=False):
            hien_dataframe_an_toan(pd.DataFrame(ds_hien))


def nhap_muc_don_doc(ma: str, ten: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"**{ten}**")
    k_dt, k_cp = f"dt_{ma}_{ho_so}_{form_ver}", f"cp_{ma}_{ho_so}_{form_ver}"
    dt = st.number_input(
        "Doanh thu (nghìn đồng/tháng)",
        min_value=0.0,
        value=float(so_hoa(st.session_state.get(k_dt, 0))),
        step=50.0,
        key=k_dt,
    )
    cp = st.number_input(
        "Chi phí (nghìn đồng/tháng)",
        min_value=0.0,
        value=float(so_hoa(st.session_state.get(k_cp, 0))),
        step=50.0,
        key=k_cp,
    )
    dt_n, cp_n = so_hoa(dt), so_hoa(cp)
    if loi_chi_phi_vuot_thu(cp_n, dt_n):
        hien_loi_validation(f"⚠️ Chi phí ({cp_n:,.0f}) lớn hơn doanh thu ({dt_n:,.0f}) — cần điều chỉnh.")
    st.caption(f"Thu nhập thuần: **{thu_thuan(dt_n, cp_n):,.0f}** nghìn đồng/tháng")


def nhap_linh_vuc_co_san_pham(ma_lv: str, ten_lv: str, ho_so: str, form_ver: int) -> None:
    st.markdown(f"**{ten_lv}**")
    san_pham = st.selectbox(
        "Chọn sản phẩm / loại hình",
        SAN_PHAM_LINH_VUC.get(ma_lv, ["Khác"]),
        key=f"sp_sel_{ma_lv}_{ho_so}_{form_ver}",
    )
    for o in O_NHAP_SAN_PHAM:
        st.number_input(
            f"{o} (nghìn đồng/tháng)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{ma_lv}_{o}_{san_pham}_{ho_so}_{form_ver}",
        )
    if st.button(
        "Thêm vào danh sách",
        key=f"them_sp_{ma_lv}_{ho_so}_{form_ver}",
        use_container_width=True,
    ):
        key = _key_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
        ds = list(st.session_state.get(key, []))
        dong: dict[str, Any] = {"Sản phẩm": san_pham}
        for o in O_NHAP_SAN_PHAM:
            dong[o] = so_hoa(
                st.session_state.get(f"{ma_lv}_{o}_{san_pham}_{ho_so}_{form_ver}", 0)
            )
        dt_d, cp_d, th_d = tong_hop_chi_tiet_linh_vuc([dong])
        if loi_chi_phi_vuot_thu(cp_d, dt_d):
            st.toast("Chi phí dòng sản phẩm vượt doanh thu — kiểm tra lại.", icon="⚠️")
            return
        dong["Doanh thu"] = dt_d
        dong["Chi phí"] = cp_d
        dong["Thu nhập thuần"] = th_d
        ds.append(dong)
        st.session_state[key] = ds
        st.toast(f"Đã thêm «{san_pham}».", icon="✅")
    ds_hien = lay_chi_tiet_linh_vuc(ma_lv, ho_so, form_ver)
    if ds_hien:
        with st.expander(f"Đã nhập {len(ds_hien)} dòng — bấm để xem", expanded=False):
            hien_dataframe_an_toan(pd.DataFrame(ds_hien))


def tong_hop_du_lieu_phieu(ho_so: str, form_ver: int) -> dict[str, Any]:
    ket: dict[str, Any] = {
        "thu_luong": 0.0,
        "thu_khac": 0.0,
        "dt_sxkd": 0.0,
        "cp_sxkd": 0.0,
        "thu_sxkd": 0.0,
        "linh_vuc": {},
        "tong_7": {},
        "hang_bang": [],
    }
    for muc in CHI_TIEU_PHAN_B:
        ma, loai = muc["ma"], muc["loai"]
        if loai == "luong" and not _co_hoat_dong("luong", ho_so, form_ver):
            continue
        if loai == "sxkd" and not _co_hoat_dong("sxkd", ho_so, form_ver):
            continue
        if loai == "khac" and not _co_hoat_dong("khac", ho_so, form_ver):
            continue
        if loai == "linh_vuc_sp" and not _co_hoat_dong("nlt", ho_so, form_ver):
            continue

        if loai == "luong":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["thu_luong"] = thuan
            ket["tong_7"]["ThuLuong"] = thuan
            ket["hang_bang"].append(
                {"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan}
            )
        elif loai == "linh_vuc_sp":
            ds = lay_chi_tiet_linh_vuc(ma, ho_so, form_ver)
            dt, cp, thuan = tong_hop_chi_tiet_linh_vuc(ds)
            ket["linh_vuc"][ma] = (dt, cp, thuan)
            ket["tong_7"][f"Thu_{ma}"] = thuan
            ket["hang_bang"].append(
                {"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan}
            )
            tong_dong = 0.0
            for dong in ds:
                th_d = so_hoa(dong.get("Thu nhập thuần", 0))
                tong_dong += th_d
                ket["hang_bang"].append(
                    {
                        "Tên chỉ tiêu": f"  └ {dong.get('Sản phẩm', '')}",
                        "Doanh thu": so_hoa(dong.get("Doanh thu", 0)),
                        "Chi phí": so_hoa(dong.get("Chi phí", 0)),
                        "Thu nhập thuần": th_d,
                    }
                )
            if ds and loi_tong_khong_khop(tong_dong, thuan):
                ket.setdefault("loi_tong", []).append(
                    f"{muc['ten']}: tổng dòng ({tong_dong:,.0f}) ≠ tổng lĩnh vực ({thuan:,.0f})"
                )
        elif loai == "sxkd":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["dt_sxkd"], ket["cp_sxkd"], ket["thu_sxkd"] = dt, cp, thuan
            ket["tong_7"]["Thu_SXKD"] = thuan
            ket["hang_bang"].append(
                {"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan}
            )
        elif loai == "khac":
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            thuan = thu_thuan(dt, cp)
            ket["thu_khac"] = thuan
            ket["tong_7"]["ThuKhac"] = thuan
            ket["hang_bang"].append(
                {"Tên chỉ tiêu": muc["ten"], "Doanh thu": dt, "Chi phí": cp, "Thu nhập thuần": thuan}
            )
    return ket


def kiem_tra_validation_phieu(ho_so: str, form_ver: int) -> tuple[bool, list[str]]:
    """Trả về (hợp lệ, danh sách lỗi)."""
    loi: list[str] = []
    dl = tong_hop_du_lieu_phieu(ho_so, form_ver)
    loi.extend(dl.get("loi_tong", []))

    for muc in CHI_TIEU_PHAN_B:
        ma, loai, ten = muc["ma"], muc["loai"], muc["ten"]
        if loai in ("luong", "sxkd", "khac"):
            nhom = {"luong": "luong", "sxkd": "sxkd", "khac": "khac"}[loai]
            if not _co_hoat_dong(nhom, ho_so, form_ver):
                continue
            dt = so_hoa(st.session_state.get(f"dt_{ma}_{ho_so}_{form_ver}", 0))
            cp = so_hoa(st.session_state.get(f"cp_{ma}_{ho_so}_{form_ver}", 0))
            if loi_chi_phi_vuot_thu(cp, dt):
                loi.append(f"{ten}: chi phí ({cp:,.0f}) > doanh thu ({dt:,.0f})")
        elif loai == "linh_vuc_sp" and _co_hoat_dong("nlt", ho_so, form_ver):
            for dong in lay_chi_tiet_linh_vuc(ma, ho_so, form_ver):
                dt_d = so_hoa(dong.get("Doanh thu", 0))
                cp_d = so_hoa(dong.get("Chi phí", 0))
                sp = dong.get("Sản phẩm", "")
                if loi_chi_phi_vuot_thu(cp_d, dt_d):
                    loi.append(f"{ten} — {sp}: chi phí > doanh thu")

    tong_nho = sum(so_hoa(r.get("Thu nhập thuần", 0)) for r in dl["hang_bang"] if not str(r.get("Tên chỉ tiêu", "")).startswith("  └"))
    tong_lon = tinh_tong_7_nguon(dl["tong_7"])
    if dl["hang_bang"] and loi_tong_khong_khop(tong_nho, tong_lon):
        loi.append(f"Tổng nhóm ({tong_nho:,.0f}) ≠ tổng 7 nguồn ({tong_lon:,.0f})")

    st.session_state[f"phieu_hop_le_{ho_so}_{form_ver}"] = len(loi) == 0
    return len(loi) == 0, loi


def reset_du_lieu_phieu_ho(ho_so: str, form_ver: int) -> None:
    for muc in CHI_TIEU_PHAN_B:
        if muc["loai"] == "linh_vuc_sp":
            xoa_chi_tiet_linh_vuc(muc["ma"], ho_so, form_ver)
    st.session_state.pop(f"ds_tv_{ho_so}_{form_ver}", None)
    for nhom in NHOM_NHAP:
        st.session_state.pop(_key_hoat_dong(nhom["id"], ho_so, form_ver), None)


def nhap_lieu_5_nhom(ho_so: str, form_ver: int) -> None:
    """Tab 2 — 5 nhóm luồng nhập liệu độc lập."""
    st.caption("Đơn vị: **nghìn đồng/tháng**. Mỗi nhóm hỏi trước — chọn **Không** sẽ ghi 0 và chuyển nhóm tiếp theo.")

    for nhom in NHOM_NHAP:
        with card_container(nhom["ten"]):
            co_hd = hoi_co_hoat_dong(nhom, ho_so, form_ver)
            if not co_hd:
                if nhom["loai"] == "thanh_vien":
                    st.session_state[f"ds_tv_{ho_so}_{form_ver}"] = []
                elif nhom["loai"] == "don":
                    _dat_zero_nhom_don(nhom["ma"], ho_so, form_ver)
                elif nhom["loai"] == "nlt":
                    _dat_zero_nhom_nlt(ho_so, form_ver)
                st.caption("Đã ghi **0** — chuyển sang nhóm kế tiếp.")
                continue

            if nhom["loai"] == "thanh_vien":
                nhap_thanh_vien_ho(ho_so, form_ver)
            elif nhom["loai"] == "don":
                muc = next((m for m in CHI_TIEU_PHAN_B if m["ma"] == nhom["ma"]), None)
                if muc:
                    nhap_muc_don_doc(muc["ma"], muc["ten"], ho_so, form_ver)
            elif nhom["loai"] == "nlt":
                for muc in CHI_TIEU_PHAN_B:
                    if muc["loai"] == "linh_vuc_sp":
                        nhap_linh_vuc_co_san_pham(muc["ma"], muc["ten"], ho_so, form_ver)
                        st.divider()


def tab_nhap_lieu_mobile(ho_so: str, form_ver: int) -> None:
    """Alias — dùng luồng 5 nhóm."""
    nhap_lieu_5_nhom(ho_so, form_ver)


def tinh_tong_7_nguon(du_lieu: dict[str, float]) -> float:
    return sum(float(du_lieu.get(k, 0) or 0) for k, _ in BAO_CAO_7_NGUON)


def tao_ban_tong_hop_7_nguon(du_lieu: dict[str, float]) -> pd.DataFrame:
    rows = [{"Nguồn thu nhập": ten, "Giá trị (nghìn đ/tháng)": du_lieu.get(key, 0)} for key, ten in BAO_CAO_7_NGUON]
    return pd.DataFrame(rows)


def dinh_dang_toa_do_gps(gia_tri: Any, *, fake: bool) -> str | None:
    if gia_tri is None:
        return None
    s = str(gia_tri)
    if fake:
        return f"{s} [CHECK_FAKE]"
    return s


def tao_dong_ket_qua_qd1099(
    *,
    ma_dtv: str,
    ho: pd.Series,
    nhan_khau: int,
    thu_luong: float,
    linh_vuc: dict[str, tuple[float, float, float]],
    dt_sxkd: float,
    cp_sxkd: float,
    thu_khac: float,
    loc: dict | None,
    gps: dict[str, Any],
    geo: dict[str, Any] | None = None,
    ghi_chu_vi_tri: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "MaDTV": ma_dtv,
        "HoSo": str(ho.get("HoSo", "")),
        "Huyen": str(ho.get("Huyen", "")),
        "Xa": str(ho.get("Xa", "")),
        "DiaBan": str(ho.get("DiaBan", "")),
        "TenChuHo": str(ho.get("TenChuHo", "")),
        "NhanKhauTT": nhan_khau,
        "ThuLuong": thu_luong,
        "ThuKhac": thu_khac,
    }
    tong_7: dict[str, float] = {"ThuLuong": thu_luong, "ThuKhac": thu_khac}
    for code, _ten in LINH_VUC_NLN_TS:
        dt, cp, thuan = linh_vuc.get(code, (0.0, 0.0, 0.0))
        row[f"DT_{code}"] = dt
        row[f"CP_{code}"] = cp
        row[f"Thu_{code}"] = thuan
        tong_7[f"Thu_{code}"] = thuan

    thu_sxkd = thu_thuan(dt_sxkd, cp_sxkd)
    row["DT_SXKD"] = dt_sxkd
    row["CP_SXKD"] = cp_sxkd
    row["Thu_SXKD"] = thu_sxkd
    tong_7["Thu_SXKD"] = thu_sxkd

    tong = tinh_tong_7_nguon(tong_7)
    nk = max(1, int(nhan_khau or 1))
    row["TongThuNhap"] = tong
    row["ThuBQDauNguoi"] = round(tong / nk, 2)

    co_mock = bool(loc and (loc.get("mocked") or loc.get("is_mock")))
    lat = loc.get("latitude") if loc else None
    lng = loc.get("longitude") if loc else None
    row["GPS_lat"] = dinh_dang_toa_do_gps(lat, fake=co_mock)
    row["GPS_lng"] = dinh_dang_toa_do_gps(lng, fake=co_mock)
    sai_so = gps.get("sai_so")
    row["DoChinhXac"] = sai_so
    row["Sai_so"] = sai_so
    row["Do_cao"] = gps.get("do_cao")
    if co_mock:
        row["Xac_Thuc_GPS"] = f"GIẢ - {_ten_ung_dung_gps_gia(loc)}"
    else:
        row["Xac_Thuc_GPS"] = gps.get("xac_thuc_gps", "Hợp lệ")
    row["IP"] = get_client_ip()
    row["MockGPS"] = "Có" if (co_mock or gps.get("to_do_do")) else "Không"
    row["NgayNhap"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if geo:
        kc = geo.get("khoang_cach_m")
        row["KhoangCachLech"] = round(kc, 1) if kc is not None else ""
        row["MaDiaBan"] = geo.get("ma_dia_ban", "")
        row["GhiChuViTri"] = ghi_chu_vi_tri.strip()
        row["DiaChi"] = geo.get("dia_chi", "")
    return row


# ---------------------------------------------------------------------------
# Xác thực & phân quyền
# ---------------------------------------------------------------------------
def normalize_ma(ma: str) -> str:
    return ma.strip().upper()


def is_admin(ma: str) -> bool:
    return normalize_ma(ma) == ADMIN_MA


def danh_sach_ma_dtv_da_nap() -> list[str]:
    """Danh sách Mã ĐTV đã nạp trên Google Sheets (từ cột Mã ĐTV trong DanhSachHo)."""
    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    if df_ho.empty or "MaDTV" not in df_ho.columns:
        return []
    return danh_sach_ma_dtv_theo_thu_tu(df_ho["MaDTV"])


def get_client_ip() -> str:
    try:
        import requests

        r = requests.get("https://api.ipify.org?format=json", timeout=3)
        return r.json().get("ip", "không xác định")
    except Exception:
        return "không xác định"


GPS_CANH_BAO_DTV = "Tọa độ có độ chính xác thấp, vui lòng kiểm tra lại GPS"
GPS_NGUONG_CANH_BAO_M = 100
GPS_NGUONG_GIA_M = 500

_geolocator: Any = None


def _lay_geolocator():
    global _geolocator
    if Nominatim is None:
        return None
    if _geolocator is None:
        _geolocator = Nominatim(user_agent="pmdtv_survey_v1", timeout=10)
    return _geolocator


@st.cache_data(ttl=86400, show_spinner=False)
def tra_cuu_toa_do_dia_chi(dia_chi: str) -> tuple[float, float] | None:
    """Geocode địa chỉ hộ (geopy + Nominatim), có cache theo chuỗi địa chỉ."""
    dia_chi = str(dia_chi or "").strip()
    if not dia_chi or geodesic is None:
        return None
    geo = _lay_geolocator()
    if geo is None:
        return None
    try:
        vi_tri = geo.geocode(f"{dia_chi}, Việt Nam", language="vi")
        if vi_tri is None:
            vi_tri = geo.geocode(dia_chi, language="vi")
        if vi_tri is None:
            return None
        return float(vi_tri.latitude), float(vi_tri.longitude)
    except Exception:
        return None


def ma_dia_ban_ho(ho: pd.Series) -> str:
    """Mã địa bàn làm điểm neo geofencing (ưu tiên cột MaDiaBan, sau đó Địa bàn)."""
    for cot in ("MaDiaBan", "DiaBan"):
        ma = str(ho.get(cot, "") or "").strip()
        if ma and ma.lower() not in ("nan", "none"):
            return ma
    return ""


def dia_chi_ho_tu_dong(ho: pd.Series) -> str:
    """Chuỗi địa chỉ phục vụ geocode điểm neo theo mã địa bàn."""
    ma_db = ma_dia_ban_ho(ho)
    dc = str(ho.get("DiaChi", "") or "").strip()
    if dc and dc.lower() not in ("nan", "none"):
        return dc
    parts = [
        ma_db,
        str(ho.get("Xa", "") or "").strip(),
        str(ho.get("Huyen", "") or "").strip(),
        "Việt Nam",
    ]
    return ", ".join(p for p in parts if p and p.lower() not in ("nan", "none"))


@st.cache_data(ttl=86400, show_spinner=False)
def toa_do_neo_ma_dia_ban(ma_dia_ban: str, xa: str, huyen: str) -> tuple[float, float] | None:
    """Tọa độ trung tâm theo Mã địa bàn (cache theo mã)."""
    ma = str(ma_dia_ban or "").strip()
    if not ma:
        return None
    truy_van = ", ".join(
        p
        for p in (ma, str(xa or "").strip(), str(huyen or "").strip(), "Việt Nam")
        if p and p.lower() not in ("nan", "none")
    )
    return tra_cuu_toa_do_dia_chi(truy_van)


def tinh_khoang_cach_gps_m(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    if geodesic is None:
        return 0.0
    return float(geodesic((lat1, lng1), (lat2, lng2)).meters)


def phan_tich_geofence(ho: pd.Series, loc: dict | None) -> dict[str, Any]:
    """
    So sánh GPS với điểm neo Mã địa bàn (geopy).
    <500m: OK; 500m–2km: cảnh báo vàng; >2km: cảnh báo đỏ + bắt buộc ghi chú.
    """
    ma_db = ma_dia_ban_ho(ho)
    ket: dict[str, Any] = {
        "khoang_cach_m": None,
        "muc": "ok",
        "canh_bao": "",
        "ma_dia_ban": ma_db,
        "dia_chi": dia_chi_ho_tu_dong(ho),
        "bat_buoc_ghi_chu": False,
    }
    if not loc or loc.get("latitude") is None or loc.get("longitude") is None:
        return ket

    try:
        lat_gps = float(loc["latitude"])
        lng_gps = float(loc["longitude"])
    except (TypeError, ValueError):
        return ket

    toa_do_neo = toa_do_neo_ma_dia_ban(
        ma_db, str(ho.get("Xa", "")), str(ho.get("Huyen", ""))
    )
    if toa_do_neo is None:
        return ket

    lat_neo, lng_neo = toa_do_neo
    kc = tinh_khoang_cach_gps_m(lat_gps, lng_gps, lat_neo, lng_neo)
    ket["khoang_cach_m"] = kc

    if kc < GEO_NGUONG_CHAP_NHAN_M:
        ket["muc"] = "ok"
    elif kc < GEO_NGUONG_CANH_BAO_M:
        ket["muc"] = "vang"
        ket["canh_bao"] = CANH_BAO_GEO_VANG
    else:
        ket["muc"] = "do"
        ket["canh_bao"] = CANH_BAO_GEO_DO
        ket["bat_buoc_ghi_chu"] = True

    return ket


def hien_canh_bao_geofence_nhe(geo: dict[str, Any]) -> None:
    """Cảnh báo vị trí nhẹ nhàng — không chiếm không gian form."""
    cb = geo.get("canh_bao", "")
    if not cb:
        return
    muc = geo.get("muc", "ok")
    kc = geo.get("khoang_cach_m")
    extra = f" (lệch {kc:.0f} m)" if kc is not None else ""
    if muc == "vang":
        st.markdown(
            f'<p class="canh-bao-vang">{cb}{extra}</p>',
            unsafe_allow_html=True,
        )
    elif muc == "do":
        st.markdown(
            f'<p class="canh-bao-do">{cb}{extra}. Vui lòng ghi chú lý do bên dưới.</p>',
            unsafe_allow_html=True,
        )


def _ten_ung_dung_gps_gia(loc: dict) -> str:
    """Lấy tên app fake nếu trình duyệt/thiết bị cung cấp (nếu không có thì mô tả ngắn)."""
    for key in (
        "mock_app",
        "mockApp",
        "provider",
        "source",
        "application",
        "app",
        "mock_provider",
    ):
        val = loc.get(key)
        if val:
            return str(val).strip()
    if loc.get("mocked") or loc.get("is_mock"):
        return "Mock Location"
    return "GPS giả lập / sai số cao"


def phan_tich_vi_tri_gps(loc: dict | None) -> dict[str, Any]:
    """Phân tích GPS: ĐTV chỉ nhận cảnh báo nhẹ; admin xem Xac_Thuc_GPS trên Sheets."""
    ket: dict[str, Any] = {
        "canh_bao_dtv": "",
        "xac_thuc_gps": "Hợp lệ",
        "to_do_do": False,
        "sai_so": None,
        "do_cao": None,
    }
    if not loc or loc.get("latitude") is None or loc.get("longitude") is None:
        ket["xac_thuc_gps"] = "GIẢ - Không có tọa độ"
        ket["canh_bao_dtv"] = GPS_CANH_BAO_DTV
        ket["to_do_do"] = True
        return ket

    acc_raw = loc.get("accuracy")
    alt_raw = loc.get("altitude")
    try:
        ket["sai_so"] = float(acc_raw) if acc_raw is not None else None
    except (TypeError, ValueError):
        ket["sai_so"] = None
    try:
        ket["do_cao"] = float(alt_raw) if alt_raw is not None else None
    except (TypeError, ValueError):
        ket["do_cao"] = None

    co_mock = bool(loc.get("mocked") or loc.get("is_mock"))
    acc = ket["sai_so"]
    nghi_gia = co_mock or (acc is not None and acc > GPS_NGUONG_GIA_M)
    nghi_thap = (acc is not None and acc > GPS_NGUONG_CANH_BAO_M) or acc is None

    if nghi_gia:
        ly_do = _ten_ung_dung_gps_gia(loc)
        if acc is not None and not co_mock:
            ly_do = f"{ly_do} (sai số {acc:.0f}m)"
        ket["xac_thuc_gps"] = f"GIẢ - {ly_do}"
        ket["canh_bao_dtv"] = GPS_CANH_BAO_DTV
        ket["to_do_do"] = True
    elif nghi_thap:
        ket["canh_bao_dtv"] = GPS_CANH_BAO_DTV

    return ket


# ---------------------------------------------------------------------------
# UI: Đăng nhập
# ---------------------------------------------------------------------------
def page_login():
    
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        vai_tro = st.radio(
            "Vai trò đăng nhập",
            ["Quản trị viên", "Điều tra viên"],
            horizontal=True,
        )

        st.caption("Tài khoản ĐTV: sheet **Account** trên Google Sheets.")
        if vai_tro == "Quản trị viên":
            mk = st.text_input("Mật khẩu Admin", type="password", key="login_admin_mk")
            if st.button("Đăng nhập", type="primary", use_container_width=True, key="btn_login_admin"):
                if normalize_ma(mk) == ADMIN_MA:
                    st.session_state["user"] = {
                        "ma": ADMIN_MA,
                        "role": "admin",
                        "ten": "Quản trị viên",
                    }
                    st.rerun()
                else:
                    st.error("Mật khẩu quản trị không đúng.")
        else:
            ma = st.text_input("Mã ĐTV", key="login_ma_dtv_txt")
            mk = st.text_input("Mật khẩu", type="password", key="login_mk_dtv")
            if st.button("Đăng nhập", type="primary", use_container_width=True, key="btn_login_dtv"):
                if not ma or not mk:
                    st.warning("Nhập đầy đủ Mã ĐTV và mật khẩu.")
                    return
                ok, loi, row = xac_thuc_dang_nhap(ma, mk)
                if not ok:
                    st.error(loi)
                    return
                df_ho = ho_mau_can_dieu_tra(
                    ho_theo_ma_dtv(read_sheet(SHEETS["danh_sach_ho"]), ma)
                )
                if df_ho.empty:
                    st.error("Chưa có hộ **Mẫu** — quản trị cần **Chọn mẫu hệ thống**.")
                    return
                st.session_state["user"] = {
                    "ma": str(ma).strip(),
                    "role": "dtv",
                    "ten": str(row.get("HoTen", ma)),
                    "so_ho": len(df_ho),
                }
                if can_doi_mat_khau(mk, ma):
                    st.session_state["bat_doi_mk"] = True
                st.rerun()


def page_doi_mat_khau():
    user = st.session_state["user"]
    render_header("🔐 Đổi mật khẩu bắt buộc")
    st.warning(f"Tài khoản **{user['ma']}** phải đổi mật khẩu mặc định trước khi nhập liệu.")
    mk1 = st.text_input("Mật khẩu mới", type="password")
    mk2 = st.text_input("Nhập lại mật khẩu mới", type="password")
    if st.button("Lưu mật khẩu", type="primary", use_container_width=True):
        if len(mk1) < 4:
            st.error("Mật khẩu tối thiểu 4 ký tự.")
        elif mk1 != mk2:
            st.error("Hai lần nhập không khớp.")
        elif can_doi_mat_khau(mk1, user["ma"]):
            st.error("Mật khẩu mới không được trùng Mã ĐTV.")
        elif cap_nhat_mat_khau(user["ma"], mk1):
            del st.session_state["bat_doi_mk"]
            st.success("Đã đổi mật khẩu.")
            st.rerun()
        else:
            st.error("Không ghi được sheet Account.")


# ---------------------------------------------------------------------------
# ADMIN — Dashboard
# ---------------------------------------------------------------------------
def xa_huyen_theo_dtv(df_ho: pd.DataFrame) -> dict[str, str]:
    """Lấy Xã/Huyện đại diện cho từng Mã ĐTV."""
    ket: dict[str, str] = {}
    if df_ho.empty or "MaDTV" not in df_ho.columns:
        return ket
    for ma, g in df_ho.groupby("MaDTV"):
        r = g.iloc[0]
        xa = str(r.get("Xa", "") or "").strip()
        huyen = str(r.get("Huyen", "") or "").strip()
        if xa and huyen:
            ket[str(ma).strip()] = f"{xa} / {huyen}"
        else:
            ket[str(ma).strip()] = xa or huyen or "—"
    return ket


def _df_mau_tien_do(df_ho: pd.DataFrame, df_kq: pd.DataFrame) -> pd.DataFrame:
    if df_ho.empty:
        return pd.DataFrame()
    df_mau = ho_mau_can_dieu_tra(df_ho) if COL_PHAN_LOAI in df_ho.columns else df_ho.copy()
    done_ho: set[str] = set()
    if not df_kq.empty and "HoSo" in df_kq.columns:
        done_ho = set(df_kq["HoSo"].astype(str))
    work = df_mau.copy()
    work["HoSo_str"] = work["HoSo"].astype(str)
    work["HoanThanh"] = work["HoSo_str"].isin(done_ho)
    return work


def _them_cot_nganh_4(df_kq: pd.DataFrame) -> pd.DataFrame:
    if df_kq.empty:
        return df_kq
    out = df_kq.copy()
    for c in ["ThuLuong", "Thu_SXKD", "ThuKhac", "TongThuNhap", "ThuBQDauNguoi"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
    cols_nlt = [f"Thu_{c}" for c, _ in LINH_VUC_NLN_TS if f"Thu_{c}" in out.columns]
    if cols_nlt:
        for c in cols_nlt:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
        out["Thu_NLT"] = out[cols_nlt].sum(axis=1)
    elif "ThuNNThuan" in out.columns:
        out["Thu_NLT"] = pd.to_numeric(out["ThuNNThuan"], errors="coerce").fillna(0)
    else:
        out["Thu_NLT"] = 0.0
    return out


def _bang_tong_hop_thu_nhap(df_kq_xa: pd.DataFrame) -> pd.DataFrame:
    if df_kq_xa.empty:
        return pd.DataFrame(columns=["Nhóm thu nhập", "Giá trị", "Tỷ trọng (%)", "Số hộ"])
    df = _them_cot_nganh_4(df_kq_xa)
    hang = []
    for col, ten in NHOM_NGANH_4:
        if col not in df.columns:
            continue
        hang.append({"Nhóm thu nhập": ten, "Giá trị": float(df[col].sum()), "Số hộ": int((df[col] > 0).sum())})
    if not hang:
        return pd.DataFrame(columns=["Nhóm thu nhập", "Giá trị", "Tỷ trọng (%)", "Số hộ"])
    bang = pd.DataFrame(hang)
    tong = bang["Giá trị"].sum()
    bang["Tỷ trọng (%)"] = (bang["Giá trị"] / tong * 100).round(1) if tong > 0 else 0.0
    return bang


def render_admin_dashboard() -> None:
    """Hệ thống điều hành thống kê — hiển thị ngay khi Admin đăng nhập."""
    user = st.session_state.get("user", {})
    if user.get("role") != "admin" or not is_admin(str(user.get("ma", ""))):
        st.warning("Bạn không có quyền truy cập trang quản trị.")
        return

    render_header("ĐIỀU HÀNH THỐNG KÊ")

    df_ho = read_sheet(SHEETS["danh_sach_ho"], silent=True)
    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    work = _df_mau_tien_do(df_ho, df_kq)

    tong_ho = len(work) if not work.empty else 0
    da_xong = int(work["HoanThanh"].sum()) if not work.empty and "HoanThanh" in work.columns else 0
    ty_le = round(da_xong / tong_ho * 100, 1) if tong_ho else 0.0

    df_kq_num = _them_cot_nganh_4(df_kq) if not df_kq.empty else pd.DataFrame()
    thu_bq = 0.0
    if not df_kq_num.empty and "ThuBQDauNguoi" in df_kq_num.columns:
        thu_bq = round(float(df_kq_num["ThuBQDauNguoi"].mean()), 1)
    elif not df_kq_num.empty and "TongThuNhap" in df_kq_num.columns:
        thu_bq = round(float(df_kq_num["TongThuNhap"].mean()), 1)

    with card_container():
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng hộ", f"{tong_ho:,}")
        k2.metric("Tiến độ toàn huyện", f"{ty_le}%")
        k3.metric("Thu nhập bình quân", f"{thu_bq:,.0f}")
        k4.metric("Tỷ lệ hoàn thành", f"{ty_le}%")

    if work.empty or "Xa" not in work.columns:
        st.info("Chưa có dữ liệu hộ mẫu — tải Excel và chọn mẫu tại menu **Hệ thống**.")
    else:
        col_trai, col_phai = st.columns(2)
        with col_trai:
            with card_container("Thu nhập bình quân theo Xã"):
                if not df_kq_num.empty and "Xa" in df_kq_num.columns and "ThuBQDauNguoi" in df_kq_num.columns:
                    bx = (
                        df_kq_num.groupby("Xa", as_index=False)["ThuBQDauNguoi"]
                        .mean()
                        .rename(columns={"ThuBQDauNguoi": "ThuBQ"})
                    )
                else:
                    bx = work.groupby("Xa", as_index=False).agg(
                        Tong=("HoSo", "count"),
                        Xong=("HoanThanh", "sum"),
                    )
                    bx["ThuBQ"] = (bx["Xong"] / bx["Tong"].replace(0, 1) * 100).round(1)

                bx = bx.sort_values("ThuBQ", ascending=True).reset_index(drop=True)
                nguong_do = bx["ThuBQ"].quantile(0.25) if len(bx) > 1 else bx["ThuBQ"].min()
                bx["Mau"] = bx["ThuBQ"].apply(
                    lambda v: "#c62828" if v <= nguong_do else NAVY_ACCENT
                )
                fig = px.bar(
                    bx,
                    x="ThuBQ",
                    y="Xa",
                    orientation="h",
                    title="So sánh thu nhập BQ (thấp → cao)",
                    color="Mau",
                    color_discrete_map="identity",
                )
                fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Nghìn đồng/tháng")
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Xã màu đỏ: thu nhập bình quân thấp nhất (cảnh báo).")

        with col_phai:
            with card_container("Cơ cấu 4 nhóm ngành"):
                ds_xa = sorted(work["Xa"].astype(str).str.strip().unique().tolist())
                xa_sel = st.selectbox("Chọn Xã", ds_xa, key="dash_xa_nganh")
                df_xa = df_kq_num[df_kq_num["Xa"].astype(str).str.strip() == xa_sel] if not df_kq_num.empty else pd.DataFrame()
                if df_xa.empty:
                    st.caption("Chưa có phiếu kết quả cho xã này.")
                else:
                    stack_row = {
                        ten: float(df_xa[col].sum()) if col in df_xa.columns else 0.0
                        for col, ten in NHOM_NGANH_4
                    }
                    df_stack = pd.DataFrame(
                        [{"Nhóm": k, "Giá trị": v} for k, v in stack_row.items() if v > 0]
                    )
                    if df_stack.empty:
                        st.caption("Chưa có thu nhập theo nhóm ngành.")
                    else:
                        fig2 = go.Figure()
                        for _, r in df_stack.iterrows():
                            fig2.add_trace(
                                go.Bar(
                                    name=str(r["Nhóm"]),
                                    x=[xa_sel],
                                    y=[r["Giá trị"]],
                                    text=[f"{r['Giá trị']:,.0f}"],
                                    textposition="inside",
                                )
                            )
                        fig2.update_layout(
                            barmode="stack",
                            title=f"Cơ cấu 4 nhóm ngành — {xa_sel}",
                            xaxis_title="",
                            yaxis_title="Nghìn đồng/tháng",
                            legend_title="Nhóm ngành",
                        )
                        st.plotly_chart(fig2, use_container_width=True)

        with card_container("Tổng hợp nhanh thu nhập"):
            xa_tb = st.selectbox(
                "Xã (bảng tổng hợp)",
                ["Toàn huyện"] + sorted(work["Xa"].astype(str).str.strip().unique().tolist()),
                key="dash_xa_bang",
            )
            if xa_tb == "Toàn huyện":
                df_tb = df_kq_num
            else:
                df_tb = df_kq_num[df_kq_num["Xa"].astype(str).str.strip() == xa_tb] if not df_kq_num.empty else pd.DataFrame()
            bang = _bang_tong_hop_thu_nhap(df_tb)
            if bang.empty:
                st.caption("Chưa có dữ liệu thu nhập.")
            else:
                hien_dataframe_an_toan(bang)

    with st.expander("👥 Quản lý ĐTV — Reset mật khẩu", expanded=False):
        df_acc = read_accounts()
        if df_acc.empty:
            st.caption("Chưa có tài khoản ĐTV.")
        else:
            map_xh = xa_huyen_theo_dtv(df_ho)
            for _, row in df_acc.iterrows():
                ma = str(row.get("MaDTV", "")).strip()
                if not ma or normalize_ma(ma) == ADMIN_MA:
                    continue
                c0, c1, c2, c3 = st.columns([1.2, 2.2, 2.0, 1.3])
                c0.write(ma)
                c1.write(str(row.get("HoTen", "") or "").strip())
                c2.write(map_xh.get(ma, "—"))
                if c3.button("Reset MK", key=f"adm_reset_{ma}", use_container_width=True):
                    if reset_mat_khau_dtv(ma):
                        st.toast(f"Đã reset **{ma}**.", icon="🔑")
                        st.rerun()


def admin_trang_chu():
    render_header("🏠 Trang chủ")
    st.markdown(
        """
        **Điều tra thu nhập hộ — QĐ 1099/QĐ-BKHĐT**

        - Sheet **Account**: đăng nhập ĐTV, đổi mật khẩu bắt buộc lần đầu.
        - Tải Excel → 10 ĐTV × 100 hộ nền → chọn **40 hộ mẫu**/ĐTV.
        - Phiếu Phần B: 7 nguồn thu nhập, GPS quản lý từ xa (`Xac_Thuc_GPS`, `Sai_so`, `Do_cao`).
        """
    )


def admin_he_thong():
    render_header("⚙️ Hệ thống")
    tab1, tab2 = st.tabs(["📤 Tải lên danh sách hộ", "🎯 Chọn mẫu hệ thống"])

    with tab1:
        st.caption(
            "Tệp Excel cần có: **Huyện**, **Xã**, **Địa bàn**, **Hộ số**, **Tên chủ hộ**, **Mã ĐTV** "
            "(có dấu hoặc không dấu đều được). Hệ thống tự lọc **10 Mã ĐTV đầu tiên**, "
            "mỗi mã **100 hộ nền đầu tiên** (tối đa **1.000 hộ**). "
            "Sau đó sang tab **Chọn mẫu** để đánh dấu **40 hộ mẫu** / 60 hộ dự phòng."
        )
        f = st.file_uploader("Chọn tệp Excel (.xlsx, .xls)", type=["xlsx", "xls"], key="upload_ho_excel")
        if f and st.button("Tải lên", type="primary", use_container_width=True):
            try:
                df_raw, thieu = doc_excel_danh_sach_ho(f, can_madtv=True)
            except Exception as e:
                st.error(f"Lỗi đọc tệp Excel: {e}")
                return
            if df_raw is None:
                st.error(
                    "Thiếu các cột bắt buộc (sau khi nhận diện tên cột): " + ", ".join(thieu)
                )
                return

            df_loc, dtv_10 = loc_mau_1000_ho(df_raw)
            if df_loc.empty or not dtv_10:
                st.error(
                    "Không lọc được hộ mẫu. Kiểm tra cột **Mã ĐTV** trong file Excel "
                    "và đảm bảo có đủ dữ liệu."
                )
                return

            st.caption(
                f"Trong file gốc có **{len(danh_sach_ma_dtv_theo_thu_tu(df_raw['MaDTV']))}** "
                f"Mã ĐTV; đã lấy **{len(dtv_10)}** mã đầu tiên."
            )

            cot_ho = COL_HO + ["MaDTV"]
            for cot_them in ("DiaChi", "MaDiaBan"):
                if cot_them in df_loc.columns:
                    cot_ho.append(cot_them)
            df_ho_gs = df_loc[cot_ho].copy()
            df_ho_gs[COL_PHAN_LOAI] = PHAN_LOAI_NEN
            ok_ho = write_sheet_replace(SHEETS["danh_sach_ho"], df_ho_gs)

            if ok_ho:
                dong_bo_account_tu_ma_dtv(dtv_10)
                write_sheet_replace(SHEETS["phan_cong"], pd.DataFrame(), silent=True)
                write_sheet_replace(SHEETS["ket_qua"], pd.DataFrame(), silent=True)

                if len(dtv_10) == 10 and len(df_loc) == 1000:
                    st.toast("Đã lọc và nạp thành công 1.000 hộ của 10 ĐTV.", icon="✅")
                else:
                    st.toast(
                        f"Đã nạp {len(df_loc)} hộ của {len(dtv_10)} ĐTV.",
                        icon="✅",
                    )
                st.caption(
                    f"Mã ĐTV: {', '.join(dtv_10)} — Tiếp theo: tab **Chọn mẫu hệ thống**."
                )
                st.markdown("#### Dữ liệu hộ vừa nạp")
                hien_bang_ngang(df_loc)
            else:
                st.toast("Không ghi được dữ liệu. Kiểm tra kết nối.", icon="⚠️")

    with tab2:
        st.caption(
            f"**Bước 1:** Lấy **{SO_HO_NEN} hộ nền** đầu tiên của mỗi Mã ĐTV (đã nạp ở tab Tải lên). "
            f"**Bước 2:** Trong 100 hộ đó, chọn **{SO_HO_MAU} hộ mẫu** theo bước nhảy **k** "
            f"(ví dụ k=2: cách 1 hộ lấy 1 hộ). Nếu chưa đủ {SO_HO_MAU} thì lấy nốt các hộ tiếp theo. "
            f"**Bước 3:** Ghi cả 100 hộ lên Google Sheets với cột **Phân loại**."
        )
        df_ho = read_sheet(SHEETS["danh_sach_ho"])
        if df_ho.empty:
            st.warning("Chưa có danh sách hộ. Vui lòng tải lên Excel ở tab «Tải lên danh sách hộ».")
            return

        if "MaDTV" not in df_ho.columns:
            st.warning("Danh sách hộ chưa có cột Mã ĐTV. Vui lòng tải lên lại file Excel.")
            return
        dtv_list = danh_sach_ma_dtv_theo_thu_tu(df_ho["MaDTV"])
        if not dtv_list:
            st.warning("Không có Mã ĐTV trong danh sách đã nạp.")
            return

        c1, c2, c3 = st.columns(3)
        with c1:
            ma_dtv = st.selectbox("Mã điều tra viên", dtv_list)
        with c2:
            k = st.number_input(
                "k (bước nhảy)",
                min_value=1,
                value=2,
                step=1,
                help=f"Cứ cách k-1 hộ lấy 1 hộ trong {SO_HO_NEN} hộ nền, đến đủ {SO_HO_MAU} hộ mẫu",
            )
        with c3:
            r = st.number_input(
                "r (vị trí bắt đầu trong 100 hộ nền)",
                min_value=1,
                max_value=SO_HO_NEN,
                value=1,
                step=1,
            )

        df_nen = lay_danh_sach_nen(df_ho, ma_dtv)
        st.caption(f"Mã **{ma_dtv}**: có **{len(df_nen)}** hộ nền (tối đa {SO_HO_NEN}).")

        if st.button("Chạy chọn mẫu và ghi Google Sheets", type="primary"):
            if len(df_nen) < SO_HO_MAU:
                st.warning(
                    f"Chỉ có **{len(df_nen)}** hộ nền — cần ít nhất **{SO_HO_MAU}** hộ để chọn mẫu."
                )
                return

            df_da_chon = ap_dung_chon_mau_cho_dtv(df_ho, ma_dtv, int(k), int(r))
            so_mau = int((df_da_chon[COL_PHAN_LOAI] == PHAN_LOAI_MAU).sum())
            so_nen = int((df_da_chon[COL_PHAN_LOAI] == PHAN_LOAI_NEN).sum())

            df_out = cap_nhat_danh_sach_ho_theo_dtv(df_ho, ma_dtv, df_da_chon)
            if write_sheet_replace(SHEETS["danh_sach_ho"], df_out):
                st.toast(
                    f"Đã chọn mẫu {ma_dtv}: {so_mau} hộ Mẫu, {so_nen} hộ Dự phòng.",
                    icon="✅",
                )
                hien_bang_ngang(df_da_chon)


def admin_tien_do():
    render_header("📊 Tiến độ hoàn thành")
    df_ho = read_sheet(SHEETS["danh_sach_ho"])
    df_kq = read_sheet(SHEETS["ket_qua"])
    if df_ho.empty or "MaDTV" not in df_ho.columns:
        st.info("Chưa có danh sách hộ đã nạp. Vui lòng tải lên file Excel.")
        return

    done_ho: set[str] = set()
    if not df_kq.empty and "HoSo" in df_kq.columns:
        done_ho = set(df_kq["HoSo"].astype(str))

    if COL_PHAN_LOAI in df_ho.columns:
        df_ho = ho_mau_can_dieu_tra(df_ho)
    if df_ho.empty:
        st.info("Chưa có hộ Mẫu nào. Vui lòng chạy Chọn mẫu hệ thống.")
        return

    df_pc = df_ho.copy()
    df_pc["HoSo_str"] = df_pc["HoSo"].astype(str)
    df_pc["HoanThanh"] = df_pc["HoSo_str"].isin(done_ho)

    prog_dtv = (
        df_pc.groupby("MaDTV", sort=False)
        .agg(Tong=("HoSo", "count"), Xong=("HoanThanh", "sum"))
        .reset_index()
    )
    prog_dtv["PhanTram"] = (prog_dtv["Xong"] / prog_dtv["Tong"] * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            prog_dtv,
            x="MaDTV",
            y="PhanTram",
            title="Tỷ lệ hoàn thành theo điều tra viên (%)",
            color="PhanTram",
            color_continuous_scale="Blues",
        )
        fig.update_layout(xaxis_title="Mã ĐTV", yaxis_title="Tỷ lệ (%)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        if "Xa" in df_pc.columns:
            prog_xa = (
                df_pc.groupby("Xa")
                .agg(Tong=("HoSo", "count"), Xong=("HoanThanh", "sum"))
                .reset_index()
            )
            prog_xa["PhanTram"] = (prog_xa["Xong"] / prog_xa["Tong"] * 100).round(1)
            fig2 = px.bar(
                prog_xa,
                x="Xa",
                y="PhanTram",
                title="Tỷ lệ hoàn thành theo xã (%)",
                color="PhanTram",
                color_continuous_scale="Teal",
            )
            fig2.update_layout(xaxis_title="Xã", yaxis_title="Tỷ lệ (%)")
            st.plotly_chart(fig2, use_container_width=True)

    hien_bang_ngang(prog_dtv)


def admin_thong_tin_ho():
    render_header("🔍 Thông tin hộ (soi chi tiết)")
    df_kq = read_sheet(SHEETS["ket_qua"])
    if df_kq.empty:
        st.info("Chưa có phiếu nào được gửi lên hệ thống.")
        return

    ho_list = df_kq["HoSo"].astype(str).unique().tolist()
    sel = st.selectbox("Chọn hộ cần xem", ho_list)
    row = df_kq[df_kq["HoSo"].astype(str) == sel].iloc[-1]
    headers = list(df_kq.columns)
    df_mot_ho = pd.DataFrame({col: [row[col]] for col in headers})
    render_header("Chi tiết phiếu (một hàng ngang)")
    hien_bang_ngang(df_mot_ho)

    try:
        lat = float(row.get("GPS_lat"))
        lng = float(row.get("GPS_lng"))
        st.map(pd.DataFrame({"lat": [lat], "lon": [lng]}))
        st.caption(
            f"📍 Tọa độ GPS: {lat}, {lng} — Độ chính xác: {row.get('DoChinhXac', '—')} m"
        )
    except (TypeError, ValueError):
        st.warning("Không có tọa độ GPS hợp lệ để hiển thị bản đồ.")

    st.markdown(f"**Địa chỉ IP khi gửi phiếu:** `{row.get('IP', '—')}`")
    xac_thuc = str(row.get("Xac_Thuc_GPS", ""))
    if xac_thuc:
        st.markdown(f"**Xác thực GPS:** `{xac_thuc}`")
        if row.get("Sai_so") not in (None, "", "nan"):
            st.caption(f"Sai số: {row.get('Sai_so')} m — Độ cao: {row.get('Do_cao', '—')} m")
    if xac_thuc.startswith("GIẢ"):
        st.error("⚠️ Phiếu có dấu hiệu vị trí GPS không hợp lệ (đã tô đỏ trên Google Sheets).")


def admin_tong_hop():
    render_header("📈 Tổng hợp báo cáo")
    df_kq = read_sheet(SHEETS["ket_qua"])
    if df_kq.empty:
        st.info("Chưa có dữ liệu kết quả điều tra.")
        return

    for col in ["ThuLuong", "ThuNNThuan", "ThuSXKD", "ThuKhac", "TongThuNhap"]:
        if col in df_kq.columns:
            df_kq[col] = pd.to_numeric(df_kq[col], errors="coerce").fillna(0)

    t1, t2, t3 = st.tabs(["Theo xã", "Theo điều tra viên", "Theo ngành kinh tế"])

    with t1:
        if "Xa" in df_kq.columns:
            bx = df_kq.groupby("Xa", as_index=False)["TongThuNhap"].sum()
            fig = px.bar(bx, x="Xa", y="TongThuNhap", title="Tổng thu nhập theo xã (nghìn đồng/tháng)")
            fig.update_layout(xaxis_title="Xã", yaxis_title="Tổng thu nhập")
            st.plotly_chart(fig, use_container_width=True)
            hien_dataframe_an_toan(bx)
        else:
            st.warning("Dữ liệu thiếu cột xã để lập báo cáo.")

    with t2:
        if "MaDTV" in df_kq.columns:
            bd = df_kq.groupby("MaDTV", as_index=False).agg(
                SoPhieu=("HoSo", "count"),
                TongThuNhap=("TongThuNhap", "sum"),
            )
            st.dataframe(hien_thi_bang(bd), use_container_width=True)
        else:
            st.warning("Dữ liệu thiếu mã điều tra viên.")

    with t3:
        st.caption("Để báo cáo theo ngành kinh tế, cần có cột «NgànhKT» trong sheet Kết quả.")
        if "NganhKT" in df_kq.columns:
            bn = df_kq.groupby("NganhKT", as_index=False)["TongThuNhap"].sum()
            st.dataframe(hien_thi_bang(bn), use_container_width=True)
        else:
            st.info("Chưa có cột ngành kinh tế (NgànhKT) trong sheet Kết quả.")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_kq.to_excel(writer, sheet_name="ChiTiet", index=False)
        if "Xa" in df_kq.columns:
            df_kq.groupby("Xa")["TongThuNhap"].sum().reset_index().to_excel(
                writer, sheet_name="TheoXa", index=False
            )
        if "MaDTV" in df_kq.columns:
            df_kq.groupby("MaDTV")["TongThuNhap"].sum().reset_index().to_excel(
                writer, sheet_name="TheoDTV", index=False
            )
    buf.seek(0)
    st.download_button(
        "📥 Tải xuống tệp Excel tổng hợp",
        data=buf,
        file_name=f"BaoCao_PMDTV_{datetime.now():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ---------------------------------------------------------------------------
# ĐTV – Nhập phiếu
# ---------------------------------------------------------------------------
def dtv_nhap_phieu():
    user = st.session_state["user"]
    if user.get("role") == "admin":
        st.info("Tài khoản quản trị — chuyển sang màn hình ĐTV hoặc dùng menu Admin.")
        return

    ma = user["ma"]
    if "form_ver" not in st.session_state:
        st.session_state.form_ver = 0
    form_ver = int(st.session_state.form_ver)

    render_header(f"📝 Nhập liệu phiếu hỏi — Mã ĐTV: <strong>{ma}</strong>")

    df_ho = ho_mau_can_dieu_tra(
        ho_theo_ma_dtv(read_sheet(SHEETS["danh_sach_ho"], silent=True), ma)
    )
    if df_ho.empty:
        st.warning(
            "Không có hộ **Mẫu** cho mã này. Quản trị viên cần chạy **Chọn mẫu hệ thống**."
        )
        return

    df_kq = read_sheet(SHEETS["ket_qua"], silent=True)
    done: set[str] = set()
    if not df_kq.empty:
        done = set(
            df_kq[df_kq["MaDTV"].astype(str).str.strip() == str(ma).strip()]["HoSo"].astype(str)
        )

    pending = df_ho[~df_ho["HoSo"].astype(str).isin(done)]
    da_xong = len(df_ho) - len(pending)

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Tổng hộ mẫu ({SO_HO_MAU})", len(df_ho))
    c2.metric("Đã hoàn thành", da_xong)
    c3.metric("Còn lại", len(pending))

    if pending.empty:
        st.success("Bạn đã hoàn thành điều tra toàn bộ hộ được phân.")
        return

    labels = pending.apply(
        lambda r: f"{r.get('HoSo', '')} — {r.get('TenChuHo', '')} ({r.get('Xa', '')})",
        axis=1,
    ).tolist()
    idx = st.selectbox("Chọn hộ cần điều tra", range(len(labels)), format_func=lambda i: labels[i])
    ho = pending.iloc[idx]
    ho_so = str(ho.get("HoSo", ""))
    ma_db = ma_dia_ban_ho(ho)
    if ma_db:
        toa_do_neo_ma_dia_ban(ma_db, str(ho.get("Xa", "")), str(ho.get("Huyen", "")))

    hien_canh_bao_khong_tinh()

    loc: dict | None = None
    with st.expander("📍 Vị trí GPS (bật trước khi lưu)", expanded=False):
        if streamlit_geolocation:
            loc = streamlit_geolocation()
    geo_hien_tai = phan_tich_geofence(ho, loc)
    hien_canh_bao_geofence_nhe(geo_hien_tai)
    if geo_hien_tai.get("bat_buoc_ghi_chu"):
        st.text_area(
            "Ghi chú lý do vị trí lệch (bắt buộc khi lệch > 2 km)",
            key=f"gc_vitri_{ho_so}_{form_ver}",
        )

    tab_tt, tab_nhap, tab_tong = st.tabs(
        ["1. Thông tin hộ", "2. Nhập liệu", "3. Tổng hợp"]
    )

    with tab_tt:
        st.text_input("Tên chủ hộ", value=str(ho.get("TenChuHo", "")), disabled=True)
        st.text_input("Hộ số", value=ho_so, disabled=True)
        st.text_input("Xã", value=str(ho.get("Xa", "")), disabled=True)
        st.text_input("Huyện", value=str(ho.get("Huyen", "")), disabled=True)
        st.text_input("Mã địa bàn", value=ma_db, disabled=True)
        st.number_input(
            "Số nhân khẩu thường trú",
            min_value=1,
            value=1,
            step=1,
            key=f"nk_{ho_so}_{form_ver}",
        )

    with tab_nhap:
        with card_container("Nhập liệu theo 5 nhóm"):
            nhap_lieu_5_nhom(ho_so, form_ver)

    with tab_tong:
        du_lieu_form = tong_hop_du_lieu_phieu(ho_so, form_ver)
        hop_le, ds_loi = kiem_tra_validation_phieu(ho_so, form_ver)
        tong_7 = du_lieu_form["tong_7"]
        tong = tinh_tong_7_nguon(tong_7)
        nk = int(so_hoa(st.session_state.get(f"nk_{ho_so}_{form_ver}", 1)) or 1)
        thu_bq = round(tong / max(1, nk), 2)

        with card_container("Tổng hợp phiếu"):
            if du_lieu_form["hang_bang"]:
                df_tong = pd.DataFrame(du_lieu_form["hang_bang"])
                hien_dataframe_an_toan(df_tong)
            else:
                st.caption("Chưa có dữ liệu — nhập ở tab **Nhập liệu**.")

            m1, m2 = st.columns(2)
            m1.metric("Tổng thu nhập hộ", f"{tong:,.0f}")
            m2.metric("BQ đầu người", f"{thu_bq:,.0f}")

            if ds_loi:
                st.markdown("**Dữ liệu chưa hợp lệ — chỉnh sửa trước khi lưu:**")
                for msg in ds_loi:
                    hien_loi_validation(msg)

        st.markdown("---")
        if st.button(
            "💾 Lưu phiếu",
            type="primary",
            use_container_width=True,
            key=f"luu_{ho_so}_{form_ver}",
            disabled=not hop_le,
        ):
            if geodesic is None:
                st.toast("Thiếu thư viện geopy.", icon="⚠️")
                return

            gps = phan_tich_vi_tri_gps(loc)
            if gps["canh_bao_dtv"]:
                st.toast(gps["canh_bao_dtv"], icon="📍")

            geo = phan_tich_geofence(ho, loc)
            gc = str(st.session_state.get(f"gc_vitri_{ho_so}_{form_ver}", "") or "").strip()
            if geo.get("bat_buoc_ghi_chu") and not gc:
                st.toast("Vui lòng ghi chú lý do khi vị trí lệch quá 2 km.", icon="⚠️")
                return
            if geo.get("muc") == "vang":
                st.toast(geo.get("canh_bao", CANH_BAO_GEO_VANG), icon="📍")
            elif geo.get("muc") == "do":
                st.toast(geo.get("canh_bao", CANH_BAO_GEO_DO), icon="⚠️")

            row = tao_dong_ket_qua_qd1099(
                ma_dtv=ma,
                ho=ho,
                nhan_khau=nk,
                thu_luong=du_lieu_form["thu_luong"],
                linh_vuc=du_lieu_form["linh_vuc"],
                dt_sxkd=du_lieu_form["dt_sxkd"],
                cp_sxkd=du_lieu_form["cp_sxkd"],
                thu_khac=du_lieu_form["thu_khac"],
                loc=loc,
                gps=gps,
                geo=geo,
                ghi_chu_vi_tri=gc,
            )
            if append_ket_qua(row, silent=True):
                reset_du_lieu_phieu_ho(ho_so, form_ver)
                st.session_state.form_ver = form_ver + 1
                st.toast("Đã lưu phiếu thành công.", icon="✅")
                st.rerun()
            else:
                st.toast("Không lưu được phiếu.", icon="⚠️")


# ---------------------------------------------------------------------------
# Điều hướng chính
# ---------------------------------------------------------------------------
def main():
    # Kiểm tra đăng nhập
    if "user" not in st.session_state:
        page_login()
        return

    # 3. Sau khi đăng nhập, các lệnh dưới đây mới chạy
    user = st.session_state["user"]
    st.sidebar.markdown(
        f'<div class="main-header"><b>PMDTV</b><br><small>{user["ma"]}</small></div>',
        unsafe_allow_html=True,
    )

    if user["role"] == "admin" and is_admin(str(user.get("ma", ""))):
        menu = st.sidebar.radio(
            "Menu quản trị",
            [
                "📊 Điều hành thống kê",
                "⚙️ Hệ thống",
                "🔍 Thông tin hộ",
                "📈 Tổng hợp",
            ],
            index=0,
        )
        if st.sidebar.button("Đăng xuất"):
            for k in ("user", "bat_doi_mk"):
                st.session_state.pop(k, None)
            st.rerun()

        routes = {
            "📊 Điều hành thống kê": render_admin_dashboard,
            "⚙️ Hệ thống": admin_he_thong,
            "🔍 Thông tin hộ": admin_thong_tin_ho,
            "📈 Tổng hợp": admin_tong_hop,
        }
        routes[menu]()
    else:
        if st.session_state.get("bat_doi_mk"):
            page_doi_mat_khau()
            return
        st.sidebar.markdown("**Chế độ điều tra viên**")
        st.sidebar.markdown(f"**Mã ĐTV:** {user['ma']}")
        if user.get("so_ho"):
            st.sidebar.caption(f"Hộ mẫu cần điều tra: {user['so_ho']}/{SO_HO_MAU}")
        st.sidebar.caption("Nhập liệu phiếu hỏi thu nhập tại hiện trường")

        ds_dtv = danh_sach_ma_dtv_da_nap()
        if ds_dtv:
            ma_moi = st.sidebar.selectbox(
                "Đổi Mã ĐTV",
                ds_dtv,
                index=ds_dtv.index(user["ma"]) if user["ma"] in ds_dtv else 0,
                key="sidebar_doi_ma_dtv",
            )
            if ma_moi != user["ma"] and st.sidebar.button("Áp dụng Mã ĐTV mới"):
                df_ho = ho_mau_can_dieu_tra(
                    ho_theo_ma_dtv(read_sheet(SHEETS["danh_sach_ho"]), ma_moi)
                )
                st.session_state["user"] = {
                    "ma": ma_moi,
                    "role": "dtv",
                    "ten": f"Điều tra viên — {ma_moi}",
                    "so_ho": len(df_ho),
                }
                st.rerun()

        if st.sidebar.button("Đăng xuất"):
            del st.session_state["user"]
            st.rerun()
        dtv_nhap_phieu()


if __name__ == "__main__":
    main()
