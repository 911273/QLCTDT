# sections/noidung_section.py
"""
NoiDung Section — Panel quản lý Nội dung chi tiết học phần.
Hỗ trợ quản lý phần Lý thuyết (LT) và Thực hành (TH).
Tương thích ttkbootstrap + BaseSection pattern.
"""
import tkinter as tk
import ttkbootstrap as tb
import json
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    CLR_PRIMARY2, CLR_HDR, CLR_ROW1, CLR_ROW2)
from utils.ui_utils import (show_modern_info, show_modern_warning,
                             show_modern_error, ask_modern_yesno)

class NoiDungSection(tb.Frame):
    """
    Panel quản lý nội dung chi tiết.
    Sử dụng Notebook để tách biệt Lý thuyết và Thực hành.
    """

    def __init__(self, parent, db, repo=None, clo_repo=None, **kw):
        super().__init__(parent, **kw)
        self.db = db
        self.repo = repo
        self.clo_repo = clo_repo
        self.ma_hp = None
        
        self._lt_rows = []
        self._th_rows = []
        
        self._build_ui()

    def _build_ui(self):
        # Header
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='6. Nội dung chi tiết học phần', 
                 font=('Times New Roman', 12, 'bold')).pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # Notebook for LT and TH
        self.nb = tb.Notebook(self, bootstyle='primary')
        self.nb.pack(fill='both', expand=True, padx=16, pady=10)

        self.lt_tab = tb.Frame(self.nb, padding=10)
        self.th_tab = tb.Frame(self.nb, padding=10)
        self.nb.add(self.lt_tab, text=' 📖 Lý thuyết ')
        self.nb.add(self.th_tab, text=' 🛠 Thực hành ')

        self._build_lt_ui()
        self._build_th_ui()

    def _build_lt_ui(self):
        # Tree for LT
        cols = ('stt', 'tieu_de', 'gio', 'clo', 'bai_dg')
        heads = ('STT', 'Tên chương/mục', 'Số tiết (LT-BT-TH)', 'CLO', 'Đánh giá')
        widths = (50, 400, 150, 100, 100)
        self.tree_lt_frm, self.tree_lt = make_tree(self.lt_tab, cols, heads, widths, height=15)
        self.tree_lt_frm.pack(fill='both', expand=True)
        
        btn_frm = tb.Frame(self.lt_tab, pady=10)
        btn_frm.pack(fill='x')
        tb.Button(btn_frm, text='➕ Thêm chương/mục', bootstyle='success', command=self._add_lt).pack(side='left', padx=2)
        tb.Button(btn_frm, text='✏ Sửa', command=self._edit_lt).pack(side='left', padx=2)
        tb.Button(btn_frm, text='🗑 Xóa', bootstyle='danger', command=self._delete_lt).pack(side='left', padx=2)
        tb.Button(btn_frm, text='💾 Lưu LT', bootstyle='primary', command=self._save_lt).pack(side='right', padx=2)

    def _build_th_ui(self):
        # Tree for TH
        cols = ('stt', 'ten_bai', 'gio', 'clo', 'bai_dg')
        heads = ('STT', 'Tên bài thực hành', 'Số tiết', 'CLO', 'Đánh giá')
        widths = (50, 400, 100, 100, 100)
        self.tree_th_frm, self.tree_th = make_tree(self.th_tab, cols, heads, widths, height=15)
        self.tree_th_frm.pack(fill='both', expand=True)
        
        btn_frm = tb.Frame(self.th_tab, pady=10)
        btn_frm.pack(fill='x')
        tb.Button(btn_frm, text='➕ Thêm bài TH', bootstyle='success', command=self._add_th).pack(side='left', padx=2)
        tb.Button(btn_frm, text='✏ Sửa', command=self._edit_th).pack(side='left', padx=2)
        tb.Button(btn_frm, text='🗑 Xóa', bootstyle='danger', command=self._delete_th).pack(side='left', padx=2)
        tb.Button(btn_frm, text='💾 Lưu TH', bootstyle='primary', command=self._save_th).pack(side='right', padx=2)

    # --- Data Loading ---
    def load_data(self, ma_hp):
        self.ma_hp = ma_hp
        if not self.repo: return
        
        rows_lt = self.repo.get_lt_all(ma_hp)
        self._lt_rows = [dict(r) for r in rows_lt]
        self._refresh_lt()
        
        rows_th = self.repo.get_th_all(ma_hp)
        self._th_rows = [dict(r) for r in rows_th]
        self._refresh_th()

    def _refresh_lt(self):
        self.tree_lt.delete(*self.tree_lt.get_children())
        for i, r in enumerate(self._lt_rows):
            tag = 'group' if r.get('is_header') else ('even' if i%2==0 else 'odd')
            gio_str = f"{r.get('gio_lt',0)}-{r.get('gio_bt',0)}-{r.get('gio_th_tn',0)}"
            # parse clo_ids from json if exists
            clo_txt = r.get('clo_ids', '')
            self.tree_lt.insert('', 'end', iid=str(i),
                                values=(r.get('stt', i+1), r.get('tieu_de',''), 
                                        gio_str, clo_txt, r.get('bai_dg_ma','')),
                                tags=(tag,))
        self.tree_lt.tag_configure('group', font=('Times New Roman', 10, 'bold'), background=CLR_HDR, foreground='white')

    def _refresh_th(self):
        self.tree_th.delete(*self.tree_th.get_children())
        for i, r in enumerate(self._th_rows):
            tag = 'even' if i%2==0 else 'odd'
            gio_str = f"{r.get('gio_th_tn',0)}"
            self.tree_th.insert('', 'end', iid=str(i),
                                values=(r.get('stt', i+1), r.get('ten_bai',''), 
                                        gio_str, r.get('clo_ids',''), r.get('bai_dg_ma','')),
                                tags=(tag,))

    # --- LT Actions ---
    def _add_lt(self):
        fields, defaults = self._lt_fields()
        dlg = RowEditDialog(self, 'Thêm nội dung LT', fields, initial=defaults)
        if dlg.result:
            self._lt_rows.append(dlg.result)
            self._refresh_lt()

    def _edit_lt(self):
        sel = self.tree_lt.selection()
        if not sel: return
        idx = int(sel[0])
        fields, defaults = self._lt_fields(self._lt_rows[idx])
        dlg = RowEditDialog(self, 'Sửa nội dung LT', fields, initial=defaults)
        if dlg.result:
            self._lt_rows[idx].update(dlg.result)
            self._refresh_lt()

    def _delete_lt(self):
        sel = self.tree_lt.selection()
        if not sel: return
        self._lt_rows.pop(int(sel[0]))
        self._refresh_lt()

    def _lt_fields(self, init=None):
        init = init or {}
        fields = [
            ('is_header', 'Là tiêu đề chương (Header)', 'check', {}),
            ('stt', 'STT', 'entry', {}),
            ('tieu_de', 'Tiêu đề chương/mục', 'entry', {}),
            ('gio_lt', 'Giờ Lý thuyết', 'entry', {}),
            ('gio_bt', 'Giờ Bài tập', 'entry', {}),
            ('gio_th_tn', 'Giờ Thực hành/TN', 'entry', {}),
            ('clo_ids', 'CLO liên kết (vd: CLO1, CLO2)', 'entry', {}),
            ('bai_dg_ma', 'Mã bài đánh giá', 'entry', {}),
        ]
        defaults = {
            'is_header': init.get('is_header', 0),
            'stt': init.get('stt', len(self._lt_rows)+1),
            'tieu_de': init.get('tieu_de', ''),
            'gio_lt': init.get('gio_lt', 0),
            'gio_bt': init.get('gio_bt', 0),
            'gio_th_tn': init.get('gio_th_tn', 0),
            'clo_ids': init.get('clo_ids', ''),
            'bai_dg_ma': init.get('bai_dg_ma', ''),
        }
        return fields, defaults

    def _save_lt(self):
        if not self.ma_hp or not self.repo: return
        try:
            self.db.conn.execute("DELETE FROM NoiDung_LT WHERE ma_hp=?", (self.ma_hp,))
            for i, r in enumerate(self._lt_rows):
                r['ma_hp'] = self.ma_hp
                self.repo.insert_lt(r)
            show_modern_info(self, 'Thành công', 'Đã lưu nội dung Lý thuyết.')
        except Exception as e:
            show_modern_error(self, 'Lỗi', str(e))

    # --- TH Actions (Tương tự LT) ---
    def _add_th(self):
        # Tương tự cấu trúc LT nhưng ít trường hơn
        fields = [
            ('stt', 'STT', 'entry', {}),
            ('ten_bai', 'Tên bài thực hành', 'entry', {}),
            ('gio_th_tn', 'Số tiết', 'entry', {}),
            ('clo_ids', 'CLO liên kết', 'entry', {}),
        ]
        dlg = RowEditDialog(self, 'Thêm nội dung TH', fields)
        if dlg.result:
            self._th_rows.append(dlg.result)
            self._refresh_th()
    
    def _edit_th(self):
        sel = self.tree_th.selection()
        if not sel: return
        idx = int(sel[0])
        row = self._th_rows[idx]
        fields = [
            ('stt', 'STT', 'entry', {}),
            ('ten_bai', 'Tên bài thực hành', 'entry', {}),
            ('gio_th_tn', 'Số tiết', 'entry', {}),
            ('clo_ids', 'CLO liên kết', 'entry', {}),
        ]
        dlg = RowEditDialog(self, 'Sửa nội dung TH', fields, initial=row)
        if dlg.result:
            self._th_rows[idx].update(dlg.result)
            self._refresh_th()

    def _delete_th(self):
        sel = self.tree_th.selection()
        if not sel: return
        self._th_rows.pop(int(sel[0]))
        self._refresh_th()

    def _save_th(self):
        if not self.ma_hp or not self.repo: return
        try:
            self.db.conn.execute("DELETE FROM NoiDung_TH WHERE ma_hp=?", (self.ma_hp,))
            for r in self._th_rows:
                r['ma_hp'] = self.ma_hp
                self.repo.insert_th(r)
            show_modern_info(self, 'Thành công', 'Đã lưu nội dung Thực hành.')
        except Exception as e:
            show_modern_error(self, 'Lỗi', str(e))
