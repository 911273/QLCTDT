# utils/global_picker.py
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class BasePicker(tb.Toplevel):
    """Lớp nền cho các hộp thoại chọn dữ liệu từ DB."""
    def __init__(self, master, db, title="Chọn dữ liệu", columns=None, headings=None):
        super().__init__(title=title, size=(800, 600))
        self.master = master
        self.db = db
        self.result = None
        self.columns = columns or ("id", "name")
        self.headings = headings or ("ID", "Tên")
        
        self._build_ui()
        self.position_center()
        self.grab_set()
        
    def _build_ui(self):
        container = tb.Frame(self, padding=15)
        container.pack(fill=BOTH, expand=YES)
        
        # Thanh tìm kiếm
        search_f = tb.Frame(container)
        search_f.pack(fill=X, pady=(0, 10))
        tb.Label(search_f, text="🔍 Tìm kiếm:").pack(side=LEFT, padx=5)
        self.ent_search = tb.Entry(search_f)
        self.ent_search.pack(side=LEFT, fill=X, expand=YES, padx=5)
        self.ent_search.bind("<KeyRelease>", lambda e: self._refresh_data())
        
        # Bảng hiển thị
        self.tree = tb.Treeview(container, columns=self.columns, show='headings', bootstyle=INFO)
        self.tree.pack(fill=BOTH, expand=YES)
        
        for col, head in zip(self.columns, self.headings):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=100)
        
        self.tree.bind("<Double-1>", lambda e: self._on_select())
        
        # Nút điều khiển
        btn_f = tb.Frame(container, padding=(0, 10, 0, 0))
        btn_f.pack(fill=X)
        tb.Button(btn_f, text="✅ Chọn", bootstyle=SUCCESS, width=15, command=self._on_select).pack(side=RIGHT, padx=5)
        tb.Button(btn_f, text="❌ Hủy", bootstyle=SECONDARY, width=15, command=self.destroy).pack(side=RIGHT, padx=5)
        
        self._refresh_data()

    def _refresh_data(self):
        search_text = self.ent_search.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        rows = self._fetch_data(search_text)
        for row in rows:
            self.tree.insert("", END, values=row)

    def _fetch_data(self, search_text):
        """Hàm này cần được override bởi lớp con."""
        return []

    def _on_select(self):
        selected = self.tree.focus()
        if selected:
            self.result = self.tree.item(selected)['values']
            self.destroy()

class GiangVienPicker(BasePicker):
    def __init__(self, master, db):
        cols = ("id", "ho_ten", "hoc_vi", "khoa", "email")
        heads = ("ID", "Họ tên", "Học vị", "Khoa/Phòng", "Email")
        super().__init__(master, db, "Danh mục Giảng viên", cols, heads)
        self.tree.column("id", width=50)
        self.tree.column("ho_ten", width=200)

    def _fetch_data(self, search):
        query = """
            SELECT g.id, g.ho_ten, g.hoc_vi, k.ten, g.email 
            FROM giang_vien g 
            LEFT JOIN khoa k ON g.khoa_id = k.id
        """
        if search:
            query += " WHERE unaccent(g.ho_ten) LIKE unaccent(?)"
            return self.db.conn.execute(query, (f"%{search}%",)).fetchall()
        return self.db.conn.execute(query).fetchall()

class TaiLieuPicker(BasePicker):
    def __init__(self, master, db, loai_filter=None):
        self.loai_filter = loai_filter
        cols = ("id", "ten", "tac_gia", "nam", "nxb")
        heads = ("ID", "Tên tài liệu", "Tác giả", "Năm XB", "Nhà xuất bản")
        super().__init__(master, db, f"Thư viện tài liệu ({loai_filter or 'Tất cả'})", cols, heads)
        self.tree.column("ten", width=300)

    def _fetch_data(self, search):
        query = "SELECT id, ten, tac_gia, nam_xb, nha_xb FROM tai_lieu"
        params = []
        if self.loai_filter or search:
            query += " WHERE 1=1"
            if self.loai_filter:
                query += " AND loai = ?"
                params.append(self.loai_filter)
            if search:
                query += " AND (unaccent(ten) LIKE unaccent(?) OR unaccent(tac_gia) LIKE unaccent(?))"
                params.extend([f"%{search}%", f"%{search}%"])
        return self.db.conn.execute(query, params).fetchall()

class PLOPicker(BasePicker):
    def __init__(self, master, db, ctdt_id=None):
        self.ctdt_id = ctdt_id
        cols = ("id", "ma", "mo_ta")
        heads = ("ID", "Mã PLO", "Nội dung mô tả")
        super().__init__(master, db, "Danh mục Chuẩn đầu ra (PLO)", cols, heads)
        self.tree.column("ma", width=80)
        self.tree.column("mo_ta", width=500)

    def _fetch_data(self, search):
        query = "SELECT id, ma, mo_ta FROM cdr_ctdt"
        params = []
        if search:
            query += " WHERE unaccent(ma) LIKE unaccent(?) OR unaccent(mo_ta) LIKE unaccent(?)"
            params.extend([f"%{search}%", f"%{search}%"])
        return self.db.conn.execute(query, params).fetchall()

class HocPhanPicker(BasePicker):
    def __init__(self, master, db):
        cols = ("id", "ma", "ten")
        heads = ("ID", "Mã HP", "Tên học phần")
        super().__init__(master, db, "Danh mục Học phần", cols, heads)
        
    def _fetch_data(self, search):
        query = "SELECT id, ma, ten_viet FROM hoc_phan"
        if search:
            query += " WHERE unaccent(ma) LIKE unaccent(?) OR unaccent(ten_viet) LIKE unaccent(?)"
            return self.db.conn.execute(query, (f"%{search}%", f"%{search}%")).fetchall()
        return self.db.conn.execute(query).fetchall()
