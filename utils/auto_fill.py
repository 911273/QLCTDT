# utils/auto_fill.py
"""
Cung cấp nội dung mẫu cho các phần trong đề cương học phần.
"""

AUTO_FILL_DATA = {
    'pp_day_hoc': {
        'Lý thuyết': (
            "+ Thuyết trình: Cung cấp kiến thức cơ sở và chuyên sâu.\n"
            "+ Thảo luận nhóm: Giải quyết các tình huống (case study) thực tế.\n"
            "+ Dạy học dựa trên vấn đề (PBL): Kích thích tư duy phản biện của sinh viên.\n"
            "+ Hướng dẫn tự học: Đọc tài liệu tham khảo và làm bài tập về nhà."
        ),
        'Thực hành': (
            "+ Hướng dẫn trực quan: Thao tác mẫu trên thiết bị/phần mềm.\n"
            "+ Thực hành cá nhân/nhóm: Sinh viên trực tiếp thực hiện bài tập thực hành.\n"
            "+ Giải đáp thắc mắc: Hướng dẫn xử lý các lỗi phát sinh trong quá trình thực hành.\n"
            "+ Báo cáo kết quả: Sinh viên trình bày sản phẩm hoặc kết quả thực hành."
        ),
        'Hỗn hợp': (
            "+ Kết hợp thuyết trình lý thuyết và hướng dẫn thực hành tại chỗ.\n"
            "+ Giao bài tập về nhà kết hợp chuẩn bị nội dung cho buổi thực hành kế tiếp.\n"
            "+ Sử dụng E-learning để cung cấp học liệu và kiểm tra trắc nhiệm nhanh."
        ),
        'Đồ án': (
            "+ Hướng dẫn trực tiếp: Giảng viên theo dõi và góp ý tiến độ hàng tuần.\n"
            "+ Làm việc nhóm: Sinh viên phối hợp triển khai dự án.\n"
            "+ Thuyết trình tiến độ: Báo cáo kết quả từng giai đoạn của đồ án."
        )
    },
    'nhiem_vu_sv': {
        'default': (
            "+ Dự lớp: Đảm bảo ít nhất 80% thời gian lên lớp lý thuyết.\n"
            "+ Chuẩn bị: Đọc trước tài liệu, giáo trình theo hướng dẫn của giảng viên.\n"
            "+ Bài tập: Hoàn thành đầy đủ các bài tập cá nhân và bài tập nhóm.\n"
            "+ Thái độ: Tích cực tham gia thảo luận và các hoạt động trên lớp."
        ),
        'Thực hành': (
            "+ Tham gia đầy đủ 100% các buổi thực hành/thí nghiệm.\n"
            "+ Chuẩn bị dụng cụ, phần mềm cần thiết trước khi vào phòng thực hành.\n"
            "+ Tuân thủ nội quy phòng thực hành và các quy định về an toàn.\n"
            "+ Hoàn thành báo cáo thực hành sau mỗi buổi học."
        )
    },
    'danh_gia': {
        'Normal': [
            {'nhom': 'Chuyên cần', 'ty_trong': 10, 'hinh_thuc': 'Điểm danh, thái độ'},
            {'nhom': 'Thường xuyên', 'ty_trong': 20, 'hinh_thuc': 'BT cá nhân, thảo luận'},
            {'nhom': 'Cuối kỳ',     'ty_trong': 70, 'hinh_thuc': 'Thi viết/Trắc nghiệm'}
        ],
        'Practical': [
            {'nhom': 'Chuyên cần', 'ty_trong': 10, 'hinh_thuc': 'Điểm danh'},
            {'nhom': 'Thường xuyên', 'ty_trong': 40, 'hinh_thuc': 'Báo cáo thực hành'},
            {'nhom': 'Cuối kỳ',     'ty_trong': 50, 'hinh_thuc': 'Vấn đáp/Sản phẩm'}
        ]
    }
}

def get_suggested_pp_day_hoc(tinh_chat):
    return AUTO_FILL_DATA['pp_day_hoc'].get(tinh_chat, AUTO_FILL_DATA['pp_day_hoc']['Lý thuyết'])

def get_suggested_nhiem_vu(tinh_chat):
    if tinh_chat == 'Thực hành':
        return AUTO_FILL_DATA['nhiem_vu_sv']['Thực hành']
    return AUTO_FILL_DATA['nhiem_vu_sv']['default']

def get_suggested_assessment(tinh_chat):
    if tinh_chat in ['Thực hành', 'Đồ án']:
        return AUTO_FILL_DATA['danh_gia']['Practical']
    return AUTO_FILL_DATA['danh_gia']['Normal']
