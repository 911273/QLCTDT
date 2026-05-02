# section_manager_dialog.py
import tkinter as tk
import ttkbootstrap as tb
from tkinter import messagebox, simpledialog
from sections.base_section import make_tree, ask_modern_yesno

class SectionManagerDialog(tb.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Quản lý các Mục trong đề cương")
        self.geometry("600x450")
        self.db = db
        self.parent = parent
        self.result_changed = False
        
        self._build_ui()
        self._refresh_list()
        
        self.transient(parent)
        self.grab_set()
        
    def _build_ui(self):
        container = tb.Frame(self, padding=20)
        container.pack(fill='both', expand=True)
        
        tb.Label(container, text="Danh sách các Mục bổ sung", font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Treeview
        cols = ("thu_tu", "label", "section_key")
        heads = ("STT", "Tên Mục (Tab)", "Mã định danh")
        widths = (60, 250, 150)
        self.tree_frm, self.tree = make_tree(container, cols, heads, widths, height=10)
        self.tree_frm.pack(fill='both', expand=True)
        
        # Buttons
        btn_frm = tb.Frame(container, padding=(0, 15))
        btn_frm.pack(fill='x')
        
        tb.Button(btn_frm, text="➕ Thêm Mục mới", bootstyle='success', command=self._add_sec).pack(side='left', padx=5)
        tb.Button(btn_frm, text="✏ Sửa tên", bootstyle='info', command=self._edit_sec).pack(side='left', padx=5)
        tb.Button(btn_frm, text="🗑 Xóa Mục", bootstyle='danger', command=self._delete_sec).pack(side='left', padx=5)
        
        tb.Separator(btn_frm, orient='vertical').pack(side='left', padx=10, fill='y')
        
        tb.Button(btn_frm, text="⬆ Lên", command=lambda: self._move(-1)).pack(side='left', padx=2)
        tb.Button(btn_frm, text="⬇ Xuống", command=lambda: self._move(1)).pack(side='left', padx=2)
        
        tb.Button(btn_frm, text="✕ Đóng", bootstyle='secondary', command=self.destroy).pack(side='right', padx=5)
        
        # Tip
        tb.Label(container, text="* Sau khi thêm/bớt Mục, vui lòng khởi động lại ứng dụng để áp dụng thay đổi.", 
                 font=('Arial', 9, 'italic'), foreground='orange').pack(anchor='w', pady=(10, 0))

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        self.sections = self.db.list_sections(include_hidden=True)
        for i, s in enumerate(self.sections):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=s['section_key'], 
                             values=(s['thu_tu'], s['label'], s['section_key']),
                             tags=(tag,))

    def _add_sec(self):
        name = simpledialog.askstring("Thêm Mục", "Nhập tên Mục mới (ví dụ: 16. Phụ lục bổ sung):", parent=self)
        if name:
            order = len(self.sections) + 16 # Thường bắt đầu sau 15 mục mặc định
            self.db.add_section(name, order=order)
            self.result_changed = True
            self._refresh_list()

    def _edit_sec(self):
        sel = self.tree.selection()
        if not sel: return
        key = sel[0]
        curr_label = self.tree.item(key)['values'][1]
        new_name = simpledialog.askstring("Sửa tên Mục", "Nhập tên mới:", initialvalue=curr_label, parent=self)
        if new_name:
            self.db.update_section(key, label=new_name)
            self.result_changed = True
            self._refresh_list()

    def _delete_sec(self):
        sel = self.tree.selection()
        if not sel: return
        key = sel[0]
        label = self.tree.item(key)['values'][1]
        if ask_modern_yesno(self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa Mục '{label}'? \nToàn bộ dữ liệu trong Mục này của TẤT CẢ học phần sẽ bị mất!"):
            self.db.delete_section(key)
            self.result_changed = True
            self._refresh_list()

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel: return
        key = sel[0]
        idx = next((i for i, s in enumerate(self.sections) if s['section_key'] == key), -1)
        if idx == -1: return
        
        target = idx + direction
        if 0 <= target < len(self.sections):
            # Swap orders in DB
            s1 = self.sections[idx]
            s2 = self.sections[target]
            o1, o2 = s1['thu_tu'], s2['thu_tu']
            self.db.update_section(s1['section_key'], thu_tu=o2)
            self.db.update_section(s2['section_key'], thu_tu=o1)
            self.result_changed = True
            self._refresh_list()
            self.tree.selection_set(key)
