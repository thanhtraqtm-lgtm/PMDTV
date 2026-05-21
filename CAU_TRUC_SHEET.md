# Cấu trúc 4 sheet Google Sheets (PMDTV)

Spreadsheet: `1Ss-QAoyHbY81FMAeyT5m7_lcVZgTu5qi3RMgNoL3Ta4`

## DanhSachĐTV
| MaDTV | HoTen | TrangThai |
|-------|-------|-----------|
| DTV01 | Điều tra viên 01 | Active |

## DanhSachHo
| Huyen | Xa | DiaBan | HoSo | TenChuHo |

*(Ứng dụng chấp nhận Excel có tiêu đề có dấu: Huyện, Xã, … — tự ánh xạ trước khi ghi sheet.)*

## PhanCong
| MaDTV | HoSo | Huyen | Xa | DiaBan | TenChuHo | NgayPhanCong |

## KetQua
| MaDTV | HoSo | Huyen | Xa | TenChuHo | ThuLuong | ThuNN | ChiNN | ThuNNThuan | ThuSXKD | ThuKhac | TongThuNhap | GPS_lat | GPS_lng | DoChinhXac | IP | MockGPS | NgayNhap |

**Chia sẻ sheet** cho: `appthunhap@crypto-avenue-410700.iam.gserviceaccount.com` (quyền Editor)

**Tự động tạo sheet:** `python init_sheets.py`
