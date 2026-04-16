# HƯỚNG DẪN TẠO VÀ CHỈNH SỬA WORD TEMPLATE — QLCTDT

## Giới thiệu

Template là file Word (.docx) có chứa các **thẻ placeholder** (ký hiệu `[TAG]`).  
Khi xuất đề cương, phần mềm sẽ thay thế các thẻ bằng dữ liệu thực từ cơ sở dữ liệu.

---

## 1. Cách Tạo Template

1. Soạn file Word (.docx) theo mẫu đề cương mong muốn  
2. Tại những vị trí cần điền dữ liệu, gõ thẻ tương ứng (xem bảng bên dưới)  
3. Lưu file, sau đó thêm vào phần mềm qua **Template > Quản lý Template**

---

## 2. Danh Sách Thẻ Đơn (Single Tags)

Sử dụng ở bất kỳ vị trí nào trong paragraph hoặc ô bảng:

| Thẻ | Mô tả | Ví dụ giá trị |
|-----|-------|---------------|
| `[TEN_VIET]` | Tên học phần tiếng Việt | BƠM QUẠT MÁY NÉN |
| `[TEN_ANH]` | Tên học phần tiếng Anh | PUMPS, FANS AND COMPRESSORS |
| `[MA_HP]` | Mã học phần | 000084 |
| `[TRINH_DO]` | Trình độ đào tạo | Đại học |
| `[SO_TIN_CHI]` | Số tín chỉ | 3 |
| `[LOAI_HP]` | Loại học phần | Bắt buộc |
| `[TINH_CHAT]` | Tính chất học phần | Hỗn hợp |
| `[GIO_LT]` | Giờ lý thuyết, bài tập, kiểm tra | 30 |
| `[GIO_TH_TN]` | Giờ thực hành, thí nghiệm | 30 |
| `[GIO_TL]` | Giờ thảo luận | 0 |
| `[GIO_TIEU_LUAN]` | Giờ tiểu luận, đồ án | 0 |
| `[GIO_THUC_TAP]` | Giờ thực tập | 0 |
| `[GIO_TU_HOC]` | Giờ tự học, nghiên cứu | 90 |
| `[TONG_GIO]` | Tổng giờ học tập | 150 |
| `[HP_TIEN_QUYET]` | HP tiên quyết | Vật lý đại cương; Mã: 003 |
| `[HP_THAY_THE]` | HP thay thế | Không có |
| `[MO_TA]` | Mô tả tóm tắt nội dung | Học phần cung cấp... |
| `[PP_DAY_HOC]` | Phương pháp dạy học | + Thuyết trình:... |
| `[NHIEM_VU_SV]` | Nhiệm vụ sinh viên (lên lớp) | Dự lớp chuyên cần... |
| `[NHIEM_VU_BT]` | Nhiệm vụ bài tập | Làm bài tập ở nhà... |
| `[NHIEM_VU_DC]` | Dụng cụ học tập | Giáo trình, bút vở... |
| `[DIA_DIEM_KY]` | Địa điểm ký | Hà Nội |
| `[NGAY_KY]` | Ngày ký | ngày ... tháng ... năm 2023 |
| `[CHUC_DANH_TRAI]` | Chức danh ký bên trái | Trưởng khoa |
| `[HO_TEN_TRAI]` | Họ tên ký bên trái | TS. Nguyễn Đăng Toản |
| `[CHUC_DANH_PHAI]` | Chức danh ký bên phải | Người biên soạn |
| `[HO_TEN_PHAI]` | Họ tên ký bên phải | ThS. Phùng Anh Xuân |

---

## 3. Thẻ Bảng Lặp (Repeating Table Tags)

Dùng trong **dòng mẫu** của bảng. Phần mềm sẽ **nhân bản dòng** cho mỗi bản ghi.

### 3.1 Giảng viên chính
Đặt trong 1 dòng bảng, phần mềm sẽ tạo đủ dòng cho mỗi GV:
```
| [GV_CHINH_STT] | [GV_CHINH_HO_TEN] | [GV_CHINH_SDT] | [GV_CHINH_EMAIL] |
```

### 3.2 Giảng viên tham gia
```
| [GV_THAM_STT] | [GV_THAM_HO_TEN] | [GV_THAM_SDT] | [GV_THAM_EMAIL] |
```

### 3.3 Mục tiêu học phần
```
| [MT_STT] | [MT_MO_TA] | [MT_CDR_MA] |
```

### 3.4 Chuẩn đầu ra (CLO)
```
| [CLO_MA] | [CLO_MO_TA] | [CLO_CDR_MA] |
```

### 3.5 Nội dung chi tiết (Lý thuyết)
```
| [ND_LT_TEN] | [ND_LT_GIO_LT] | [ND_LT_GIO_BT] | [ND_LT_GIO_TL] | [ND_LT_GIO_TH] | [ND_LT_YEU_CAU] | [ND_LT_CDR_MA] |
```

### 3.6 Nội dung chi tiết (Thực hành)
```
| [ND_TH_TEN] | [ND_TH_GIO_TH] | [ND_TH_YEU_CAU] | [ND_TH_CDR_MA] |
```

### 3.7 Kế hoạch kiểm tra
```
| [KT_NHOM] | [KT_NOI_DUNG] | [KT_HINH_THUC] | [KT_THOI_GIAN] | [KT_CLO] | [KT_TY_TRONG] |
```

### 3.8 Học liệu
```
| [HL_STT] | [HL_NOI_DUNG] |
```

### 3.9 Lịch sử cập nhật
```
| [LS_LAN] | [LS_NOI_DUNG] | [LS_QUYET_DINH] | [LS_NGUOI_CAP_NHAT] | [LS_TRUONG_KHOA] |
```

---

## 4. Lưu Ý Quan Trọng

1. **Thẻ phải viết CHÍNH XÁC** — chữ IN HOA, có dấu ngoặc vuông `[ ]`
2. **Dấu cách bên trong**: `[TEN_VIET]` ✅ ; `[ TEN_VIET ]` ❌
3. **Không tách thẻ**: Mỗi thẻ phải nằm gọn trong **1 run** (đoạn text liền). 
   Nếu bạn copy-paste và Word tách format, hãy xóa đi và gõ lại trực tiếp.
4. **Bảng lặp**: Cả dòng chứa thẻ sẽ được nhân bản. Giữ mẫu ở đúng 1 dòng.
5. **Định dạng**: Template giữ nguyên format (font, cỡ chữ, màu, border...) khi xuất.

---

## 5. Ví Dụ Template Đơn Giản

```
ĐỀ CƯƠNG CHI TIẾT HỌC PHẦN
[TEN_VIET]
Trình độ đào tạo: [TRINH_DO]

1. Thông tin chung
Mã học phần: [MA_HP]        Số tín chỉ: [SO_TIN_CHI]
Loại HP: [LOAI_HP]          Tính chất: [TINH_CHAT]

2. Mô tả tóm tắt
[MO_TA]

(Bảng nội dung chi tiết với thẻ lặp...)
```
