import re

def natural_sort_key(s):
    """
    Hàm tạo key để sắp xếp chuỗi theo thứ tự tự nhiên (Natural Sort).
    Ví dụ: 'PO1', 'PO2', 'PO10' thay vì 'PO1', 'PO10', 'PO2'.
    """
    if s is None:
        return []
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', str(s))]
