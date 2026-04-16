# settings_dialog.py — Thiết lập tham số hệ thống
import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as tb
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
from ttkbootstrap.constants import *
from sections.base_section import CLR_BG, CLR_TEXT, CLR_ROW1, set_window_icon

class SettingsDialog(tb.Toplevel):
    """Giao diện quản lý các tham số cấu hình hệ thống (Dữ liệu chung)."""

    def __init__(self, parent, db):
        super().__init__(parent)
        set_window_icon(self)
        self.title('⚙️ Thiết lập hệ thống')
        self.geometry('600x650')
        self.db = db
        self.grab_set()
        self.transient(parent)
        
        # Danh sách các tham số muốn quản lý
        self.params = [
            ('clo_groups', 'Danh sách nhóm CLO (phân cách bằng dấu phẩy):'),
            ('hp_natures', 'Danh sách tính chất học phần (Nature):'),
            ('hp_types',   'Danh sách loại học phần (Bắt buộc/Tự chọn):'),
            ('trinh_do',   'Danh sách trình độ đào tạo:'),
        ]
        
        self.entries = {}
        self._build_ui()

    def _build_ui(self):
        frm = tb.Frame(self, padding=20)
        frm.pack(fill='both', expand=True)

        tb.Label(frm, text="Cấu hình Dữ liệu chung", font=('Arial', 14, 'bold'), 
                 bootstyle='primary').pack(pady=(0, 20))

        # Container cho các trường nhập liệu
        content = tb.Frame(frm)
        content.pack(fill='both', expand=True)

        for i, (key, label) in enumerate(self.params):
            val = self.db.get_config(key, '')
            
            row = tb.Frame(content)
            row.pack(fill='x', pady=8)
            
            tb.Label(row, text=label, font=('Arial', 10)).pack(anchor='w')
            
            # Sử dụng Text cho các danh sách dài, Entry cho danh sách ngắn
            ent = tb.Entry(row, font=('Arial', 10))
            ent.insert(0, val)
            ent.pack(fill='x', pady=2)
            self.entries[key] = ent

        # Buttons
        btns = tb.Frame(frm)
        btns.pack(fill='x', pady=(20, 0))
        
        tb.Button(btns, text="💾 Lưu thay đổi", command=self._save, 
                  bootstyle='success').pack(side='left', padx=5)
        tb.Button(btns, text="Hủy", command=self.destroy,
                  bootstyle='outline-secondary').pack(side='left', padx=5)
        
        # --- Quản lý dữ liệu ---
        data_frm = tb.Labelframe(frm, text="📦 Quản lý Dữ liệu", padding=15)
        data_frm.pack(fill='x', pady=(30, 0))
        
        tb.Label(data_frm, text="Sao lưu toàn bộ cơ sở dữ liệu hiện tại để dự phòng:").pack(side='left', padx=5)
        tb.Button(data_frm, text="🛡️ Sao lưu ngay", command=self._backup,
                  bootstyle='info-outline').pack(side='right', padx=5)
        
        # Hướng dẫn
        tb.Label(frm, text="* Lưu chú: Các giá trị phân cách nhau bằng dấu phẩy (vd: A, B, C)", 
                 font=('Arial', 9, 'italic'), bootstyle='secondary').pack(anchor='w', pady=(10, 0))

    def _save(self):
        for key, ent in self.entries.items():
            val = ent.get().strip()
            if not val:
                show_modern_warning(self, "Cảnh báo", f"Giá trị cho {key} không được để trống.")
                return
            self.db.set_config(key, val)
            
        show_modern_info(self, "Thành công", "Đã lưu thiết lập hệ thống. Một số thay đổi sẽ có hiệu lực sau khi khởi động lại hoặc tải lại học phần.")
        self.destroy()

    def _backup(self):
        """Xử lý sao lưu dữ liệu."""
        import os
        from datetime import datetime
        
        default_name = f"qlctdt_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        path = filedialog.asksaveasfilename(
            title="Chọn nơi lưu bản sao lưu",
            defaultextension=".db",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if path:
            if self.db.backup(path):
                show_modern_info(self, "Thành công", f"Đã sao lưu dữ liệu thành công tại:\n{path}")
            else:
                show_modern_error(self, "Lỗi", "Không thể thực hiện sao lưu. Vui lòng kiểm tra lại quyền truy cập hoặc dung lượng đĩa.")
