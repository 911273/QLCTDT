# HƯỚNG DẪN TẠO VÀ CHỈNH SỬA WORD TEMPLATE (v2.0) — QLCTDT

## 1. Giới thiệu

Hệ thống QLCTDT v2.0 sử dụng công nghệ **Template Automation** dựa trên thư viện `docxtpl` (Jinja2). 
Thay vì chỉ thay thế văn bản đơn thuần, hệ thống mới cho phép:
- **Lặp dữ liệu**: Tự động tạo bảng nội dung chi tiết, danh sách CLO, danh sách giảng viên...
- **Logic**: Ẩn/hiện các đoạn văn bản dựa trên điều kiện.
- **Giữ nguyên định dạng**: Mọi Font, Cỡ chữ, Màu sắc, Style của Word đều được giữ nguyên.

---

## 2. Cách Tạo Template

1. Sử dụng Microsoft Word soạn thảo mẫu đề cương chuẩn (Mẫu 13 EPU).
2. Tại vị trí cần chèn dữ liệu, gõ Placeholder theo cú pháp Jinja2: `{{ ... }}`.
3. Đối với các bảng dữ liệu (danh sách), sử dụng cặp lệnh `{% for ... %}` và `{% endfor %}`.
4. Lưu file `.docx` và nạp vào phần mềm qua menu **Template > Quản lý Template**.

---

## 3. Cú pháp Placeholder phổ biến

### 3.1 Thẻ đơn (Scalars)
Dùng cho Paragraph hoặc bên trong ô bảng:

| Placeholder | Mô tả | 
|:---|:---|
| `{{ CourseName }}` | Tên học phần (Tiếng Việt) |
| `{{ CourseNameEN }}` | Tên học phần (Tiếng Anh) |
| `{{ CourseCode }}` | Mã học phần |
| `{{ Credits }}` | Số tín chỉ |
| `{{ TotalHours }}` | Tổng số giờ |
| `{{ Description }}` | Mô tả tóm tắt học phần |

### 3.2 Thẻ lặp trong Bảng (Loops)
Để tạo danh sách, bạn phải đặt thẻ bắt đầu vả kết thúc bên trong bảng.

#### Danh sách Chuẩn đầu ra (CLOs):
Cấu trúc trong dòng bảng:
```
{% for clo in CLOs %}
{{ clo.Code }} | {{ clo.Desc }} | {{ clo.PLO }} | {{ clo.Level }}
{% endfor %}
```

#### Danh sách Giảng viên (Lecturers):
```
{% for lect in Lecturers %}
{{ loop.index }} | {{ lect.Degree }} {{ lect.Name }} | {{ lect.Phone }} | {{ lect.Email }}
{% endfor %}
```

---

## 4. Danh sách Placeholder đầy đủ

Bạn có thể xem **Danh sách đầy đủ** và **Xuất file tra cứu** trực tiếp trong phần mềm:
1. Mở menu **Template > Quản lý Template**.
2. Nhấn nút **"Xem danh sách tất cả Placeholder"**.
3. Sử dụng tính năng **Nháy đúp** để sao chép nhanh tên biến.

---

## 5. Lưu ý kỹ thuật quan trọng

- **Dấu ngoặc**: Luôn sử dụng cặp ngoặc nhọn kép `{{` và `}}`.
- **Chính xác**: Tên biến phân biệt chữ hoa/thường (ví dụ `{{ CourseName }}` khác `{{ coursename }}`).
- **Format trong Loop**: Dòng chứa `{% for ... %}` và `{% endfor %}` sẽ biến mất trong file kết quả, chỉ còn lại các dòng dữ liệu ở giữa.
- **Kiểm tra**: Trước khi sử dụng, hãy dùng tính năng **"Validate Template"** trong phần mềm để phát hiện lỗi cú pháp Placeholder.

---

## 6. Ví dụ minh họa

**Trong file Word bạn soạn:**
> Học phần: **{{ CourseName }}**
> Mã học phần: **{{ CourseCode }}**
>
> Danh sách CLO:
> | Mã | Mô tả |
> |---|---|
> | `{% for c in CLOs %}` | |
> | `{{ c.Code }}` | `{{ c.Desc }}` |
> | `{% endfor %}` | |

**Kết quả khi xuất file:**
> Học phần: **LẬP TRÌNH PYTHON**
> Mã học phần: **IT3010**
>
> Danh sách CLO:
> | Mã | Mô tả |
> |---|---|
> | CLO1 | Nắm vững cú pháp cơ bản của Python |
> | CLO2 | Xây dựng được ứng dụng xử lý dữ liệu |
