# sections/registry.py
"""
SectionRegistry — Plugin pattern cho hệ thống Section.
Thay thế việc hardcode danh sách tab trong main.py.
Mỗi section tự đăng ký mình với decorator @register_section hoặc gọi trực tiếp.

Lợi ích:
- Thêm section mới không cần sửa main.py
- Dễ bật/tắt section theo cấu hình
- Dễ test từng section độc lập
"""
from typing import List, Tuple, Type, Optional


class SectionRegistry:
    """
    Registry lưu danh sách section UI theo thứ tự.
    Trạng thái là class-level (singleton).
    """
    _entries: List[Tuple[int, str, type]] = []  # (order, label, cls)
    _enabled_set: Optional[set] = None           # None = tất cả enabled

    @classmethod
    def register(cls, order: int, label: str, section_class: type):
        """
        Đăng ký 1 section.
        
        Args:
            order:         Số thứ tự hiển thị (nhỏ hơn = trước)
            label:         Nhãn tab (VD: "1. Thông tin chung")
            section_class: Class kế thừa từ BaseSection hoặc tk.Frame
        """
        # Tránh đăng ký trùng
        for i, (o, l, c) in enumerate(cls._entries):
            if c is section_class:
                cls._entries[i] = (order, label, section_class)
                cls._entries.sort(key=lambda x: x[0])
                return
        cls._entries.append((order, label, section_class))
        cls._entries.sort(key=lambda x: x[0])

    @classmethod
    def get_all(cls) -> List[Tuple[str, type]]:
        """Trả về list [(label, cls)] đã sắp xếp theo order."""
        if cls._enabled_set is None:
            return [(label, sec_cls) for _, label, sec_cls in cls._entries]
        return [
            (label, sec_cls)
            for _, label, sec_cls in cls._entries
            if sec_cls.__name__ in cls._enabled_set
        ]

    @classmethod
    def enable_only(cls, class_names: list):
        """Chỉ hiển thị các section có tên trong list (dùng cho test)."""
        cls._enabled_set = set(class_names)

    @classmethod
    def enable_all(cls):
        """Bật lại tất cả section."""
        cls._enabled_set = None

    @classmethod
    def clear(cls):
        """Xóa toàn bộ registry (dùng khi test)."""
        cls._entries.clear()
        cls._enabled_set = None

    @classmethod
    def count(cls) -> int:
        return len(cls._entries)


def register_section(order: int, label: str):
    """
    Decorator để đăng ký 1 section class với SectionRegistry.
    
    Sử dụng:
        @register_section(order=1, label="1. Thông tin chung")
        class Sec1ThongTin(tb.Frame):
            ...
    """
    def decorator(cls):
        SectionRegistry.register(order, label, cls)
        return cls
    return decorator


# ── Auto-registration: Import tất cả section để kích hoạt decorator ──────────

def auto_register_all_sections():
    """
    Import toàn bộ section modules để trigger @register_section.
    Gọi 1 lần khi khởi động app (trong main.py).
    
    Nếu section chưa dùng decorator, vẫn hỗ trợ backward-compatible
    bằng cách gọi SectionRegistry.register() thủ công.
    """
    section_modules = [
        'sections.sec_program_info',
        'sections.sec1_thong_tin',
        'sections.sec2_mo_ta',
        'sections.sec3_muc_tieu',
        'sections.sec4_clo',
        'sections.sec5_hoc_lieu',
        'sections.sec6_noi_dung',
        'sections.sec7_pp_day',
        'sections.sec8_kiem_tra',
        'sections.sec9_quy_dinh',
        'sections.sec11_doi_ngu',
        'sections.sec12_phu_luc',
        'sections.sec13_cap_nhat',
        'sections.sec14_chinh_sach',
        'sections.sec15_checklist',
    ]
    imported = []
    failed = []
    for mod_name in section_modules:
        try:
            import importlib
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except ImportError as e:
            failed.append((mod_name, str(e)))

    if failed:
        print(f"[SectionRegistry] Warning: {len(failed)} module(s) không import được:")
        for name, err in failed:
            print(f"  - {name}: {err}")

    return imported, failed
