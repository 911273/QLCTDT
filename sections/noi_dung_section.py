# sections/noi_dung_section.py
"""
NoiDung Section — Panel Nội dung chi tiết học phần (Mục 6 ĐCCTHP).
Hỗ trợ phần Lý thuyết (LT) và Thực hành (TH).
Tương thích ttkbootstrap + BaseSection pattern.
"""
import tkinter as tk
import ttkbootstrap as tb
import json
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    CLR_HDR, CLR_PRIMARY2, CLR_ACCENT)
from utils.ui_utils import (show_modern_info, show_modern_warning,
                             show_modern_error, ask_modern_yesno)

class MultiCLOPickerDialog(tb.Toplevel):
    """Dialog checklist multi-select CLO."""
    def __init__(self, parent, clo_list, initial_selection=None):
        super().__init__(parent)
        self.title("Chọn CLO")
        self.geometry("300x400")
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self._vars = {}
        
        container = tb.Frame(self, padding=15)
        container.pack(fill='both', expand=True)
        
        tb.Label(container, text="Chọn các CLO liên kết:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        scroll_frm = tb.Frame(container)
        scroll_frm.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(scroll_frm, highlightthickness=0)
        sb = tb.Scrollbar(scroll_frm, orient='vertical', command=canvas.yview)
        self.scroll_inner = tb.Frame(canvas)
        
        self.scroll_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_inner, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        
        initial_set = set(initial_selection or [])
        for clo in clo_list:
            var = tk.BooleanVar(value=(clo in initial_set))
            self._vars[clo] = var
            cb = tb.Checkbutton(self.scroll_inner, text=clo, variable=var, bootstyle="round-toggle")
            cb.pack(anchor='w', pady=2)
            
        btn_frm = tb.Frame(container, pady=10)
        btn_frm.pack(fill='x')
        tb.Button(btn_frm, text="Xác nhận", bootstyle='primary', command=self._confirm).pack(side='right', padx=5)
        tb.Button(btn_frm, text="Hủy", bootstyle='secondary', command=self.destroy).pack(side='right')

    def _confirm(self):
        self.result = [clo for clo, var in self._vars.items() if var.get()]
        self.destroy()

class NoiDungSection(tb.Frame):
    """
    Panel Nội dung chi tiết (Mục 6).
    Tách biệt tab Lý thuyết và Thực hành.
    """
    def __init__(self, parent, db, repo=None, clo_provider=None, **kw):
        super().__init__(parent, **kw)
        self.db = db
        self.repo = repo
        self.clo_provider = clo_provider # Cần để lấy list CLO từ Mục 4
        
        self.ma_hp = None
        self.loai_hinh = 'LT+TH'
        self.so_tin_chi = 0
        
        self._lt_rows = []
        self._th_rows = []
        
        self._build_ui()

    def _build_ui(self):
        # Header
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='6. Nội dung chi tiết học phần', font=('Times New Roman', 12, 'bold')).pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # Tabs
        self.nb = tb.Notebook(self, bootstyle='primary')
        self.nb.pack(fill='both', expand=True, padx=16, pady=5)

        self.lt_tab = tb.Frame(self.nb, padding=10)
        self.th_tab = tb.Frame(self.nb, padding=10)
        self.nb.add(self.lt_tab, text=' Lý thuyết ')
        self.nb.add(self.th_tab, text=' Thực hành ')

        self._build_table_ui(self.lt_tab, 'LT')
        self._build_table_ui(self.th_tab, 'TH')

        # Footer
        self.footer = tb.Frame(self, padding=(16, 5, 16, 10))
        self.footer.pack(fill='x')
        
        self.lbl_stats = tb.Label(self.footer, text="Tổng: 0 giờ", font=('Arial', 10, 'bold'))
        self.lbl_stats.pack(side='left')
        
        self.lbl_warn = tb.Label(self.footer, text="", font=('Arial', 9, 'italic'), foreground='orange')
        self.lbl_warn.pack(side='right')

    def _build_table_ui(self, parent, type_):
        if type_ == 'LT':
            cols = ('stt', 'tieu_de', 'hours', 'gd', 'ht', 'clo', 'bai_dg')
            heads = ('STT', 'Tên chương/bài', 'Giờ (LT-BT-TH)', 'Hoạt động GD', 'Hoạt động HT', 'CLO', 'Bài ĐG')
            widths = (40, 250, 100, 120, 120, 100, 80)
        else:
            cols = ('stt', 'ten_bai', 'hours', 'gd', 'ht', 'clo', 'bai_dg')
            heads = ('STT', 'Tên bài thực hành', 'Giờ', 'Hoạt động GD', 'Hoạt động HT', 'CLO', 'Bài ĐG')
            widths = (40, 250, 80, 120, 120, 100, 80)

        tree_frm, tree = make_tree(parent, cols, heads, widths, height=12)
        tree_frm.pack(fill='both', expand=True)
        tree.bind('<Double-1>', lambda _: self._edit_row(type_))
        
        if type_ == 'LT': self.tree_lt = tree
        else: self.tree_th = tree

        btn_frm = tb.Frame(parent, pady=10)
        btn_frm.pack(fill='x')
        tb.Button(btn_frm, text='➕ Thêm', bootstyle='success-outline', command=lambda: self._add_row(type_)).pack(side='left', padx=2)
        tb.Button(btn_frm, text='🗑 Xóa', bootstyle='danger-outline', command=lambda: self._delete_row(type_)).pack(side='left', padx=2)
        tb.Button(btn_frm, text='⬆', command=lambda: self._move(type_, -1)).pack(side='left', padx=2)
        tb.Button(btn_frm, text='⬇', command=lambda: self._move(type_, 1)).pack(side='left', padx=2)
        tb.Button(btn_frm, text='💾 Lưu ' + type_, bootstyle='primary', command=lambda: self._save_click(type_)).pack(side='right', padx=2)

    # --- Data Methods ---
    def load_data(self, ma_hp, loai_hinh='LT+TH'):
        self.ma_hp = ma_hp
        self.loai_hinh = loai_hinh
        
        # Load tin chi
        hp = self.db.conn.execute("SELECT so_tin_chi FROM hoc_phan WHERE ma=?", (ma_hp,)).fetchone()
        self.so_tin_chi = hp['so_tin_chi'] if hp else 0
        
        # Filter tabs
        self.nb.tab(0, state='normal' if 'LT' in loai_hinh else 'hidden')
        self.nb.tab(1, state='normal' if 'TH' in loai_hinh else 'hidden')
        if 'LT' not in loai_hinh: self.nb.select(1)
        else: self.nb.select(0)

        if self.repo:
            self._lt_rows = [dict(r) for r in self.repo.get_lt_all(ma_hp)]
            self._th_rows = [dict(r) for r in self.repo.get_th_all(ma_hp)]
        
        self._refresh('LT')
        self._refresh('TH')
        self._update_stats()

    def _refresh(self, type_):
        tree = self.tree_lt if type_ == 'LT' else self.tree_th
        rows = self._lt_rows if type_ == 'LT' else self._th_rows
        
        tree.delete(*tree.get_children())
        for i, r in enumerate(rows):
            r['stt'] = i + 1 # Auto re-number
            tag = 'even' if i % 2 == 0 else 'odd'
            
            if type_ == 'LT':
                h_str = f"{r.get('gio_lt',0)}-{r.get('gio_bt',0)}-{r.get('gio_th_tn',0)}"
                clo_list = json.loads(r.get('clo_ids', '[]'))
                tree.insert('', 'end', iid=str(i), tags=(tag,),
                            values=(r['stt'], r.get('tieu_de',''), h_str, 
                                    r.get('hoat_dong_day',''), r.get('hoat_dong_hoc',''),
                                    ", ".join(clo_list), r.get('bai_dg_ma','')))
            else:
                h_str = str(r.get('gio_th_tn',0))
                clo_list = json.loads(r.get('clo_ids', '[]'))
                tree.insert('', 'end', iid=str(i), tags=(tag,),
                            values=(r['stt'], r.get('ten_bai',''), h_str, 
                                    r.get('hoat_dong_day',''), r.get('hoat_dong_hoc',''),
                                    ", ".join(clo_list), r.get('bai_dg_ma','')))

    def _update_stats(self):
        total_lt = sum(float(r.get('gio_lt', 0)) for r in self._lt_rows)
        total_bt = sum(float(r.get('gio_bt', 0)) for r in self._lt_rows)
        total_th_lt = sum(float(r.get('gio_th_tn', 0)) for r in self._lt_rows)
        
        total_th_pure = sum(float(r.get('gio_th_tn', 0)) for r in self._th_rows)
        
        all_lt = total_lt
        all_bt = total_bt
        all_th = total_th_lt + total_th_pure
        grand_total = all_lt + all_bt + all_th
        
        self.lbl_stats.config(text=f"Tổng LT={all_lt} | Tổng BT={all_bt} | Tổng TH={all_th} | Tổng cộng={grand_total} giờ")
        
        # Mismatch check
        expected = self.so_tin_chi * 50
        if grand_total > 0 and abs(grand_total - expected) > 0.1:
            self.lbl_warn.config(text=f"⚠ Lệch {grand_total - expected} giờ so với chuẩn ({self.so_tin_chi}TC = {expected}h)")
        else:
            self.lbl_warn.config(text="")

    # --- CRUD ---
    def _add_row(self, type_):
        fields, defaults = self._get_fields(type_)
        dlg = RowEditDialog(self, f"Thêm {type_}", fields, initial=defaults)
        if dlg.result:
            res = dlg.result
            # Chuyển comma-string sang JSON array
            raw_clo = res.get('clo_ids_raw', '')
            clo_list = [c.strip() for c in raw_clo.split(',') if c.strip()]
            res['clo_ids'] = json.dumps(clo_list)
            
            if type_ == 'LT': self._lt_rows.append(res)
            else: self._th_rows.append(res)
            self._refresh(type_)
            self._update_stats()

    def _edit_row(self, type_):
        tree = self.tree_lt if type_ == 'LT' else self.tree_th
        rows = self._lt_rows if type_ == 'LT' else self._th_rows
        sel = tree.selection()
        if not sel: return
        idx = int(sel[0])
        
        fields, defaults = self._get_fields(type_, rows[idx])
        dlg = RowEditDialog(self, f"Sửa {type_}", fields, initial=defaults)
        if dlg.result:
            res = dlg.result
            # Chuyển comma-string sang JSON array
            raw_clo = res.get('clo_ids_raw', '')
            clo_list = [c.strip() for c in raw_clo.split(',') if c.strip()]
            res['clo_ids'] = json.dumps(clo_list)
            
            rows[idx].update(res)
            self._refresh(type_)
            self._update_stats()

    def _get_fields(self, type_, init=None):
        init = init or {}
        clo_list = []
        if self.clo_provider:
            clo_list = self.clo_provider.get_clo_list()
        
        initial_clos = json.loads(init.get('clo_ids', '[]'))
        
        fields = [
            ('stt', 'STT', 'entry', {'state': 'readonly'}),
        ]
        if type_ == 'LT':
            fields += [('tieu_de', 'Tên chương/bài', 'entry', {}),
                       ('gio_lt', 'Giờ Lý thuyết', 'spin', {'from_': 0, 'to': 100, 'increment': 0.5}),
                       ('gio_bt', 'Giờ Bài tập', 'spin', {'from_': 0, 'to': 100, 'increment': 0.5}),
                       ('gio_th_tn', 'Giờ TH-TN', 'spin', {'from_': 0, 'to': 100, 'increment': 0.5})]
        else:
            fields += [('ten_bai', 'Tên bài thực hành', 'entry', {}),
                       ('gio_th_tn', 'Số tiết', 'spin', {'from_': 0, 'to': 100, 'increment': 0.5})]
            
        fields += [('hoat_dong_day', 'Hoạt động GD', 'text', {'height': 2}),
                   ('hoat_dong_hoc', 'Hoạt động HT', 'text', {'height': 2}),
                   ('clo_ids_raw', 'Chọn CLO', 'multi_picker', {'values': clo_list}),
                   ('bai_dg_ma', 'Bài ĐG (vd: GK1)', 'entry', {})]
        
        defaults = init.copy()
        defaults['stt'] = init.get('stt', (len(self._lt_rows) if type_ == 'LT' else len(self._th_rows)) + 1)
        
        # RowEditDialog's multi_picker expects a comma-separated string
        initial_clos = json.loads(init.get('clo_ids', '[]'))
        defaults['clo_ids_raw'] = ", ".join(initial_clos)
        
        return fields, defaults

    def _delete_row(self, type_):
        tree = self.tree_lt if type_ == 'LT' else self.tree_th
        rows = self._lt_rows if type_ == 'LT' else self._th_rows
        sel = tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa hàng đã chọn?'):
            rows.pop(int(sel[0]))
            self._refresh(type_)
            self._update_stats()

    def _move(self, type_, direction):
        tree = self.tree_lt if type_ == 'LT' else self.tree_th
        rows = self._lt_rows if type_ == 'LT' else self._th_rows
        sel = tree.selection()
        if not sel: return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(rows):
            rows[idx], rows[new_idx] = rows[new_idx], rows[idx]
            self._refresh(type_)
            tree.selection_set(str(new_idx))

    def _save_click(self, type_):
        if not self.ma_hp or not self.repo: return
        try:
            if type_ == 'LT':
                self.db.conn.execute("DELETE FROM NoiDung_LT WHERE ma_hp=?", (self.ma_hp,))
                for r in self._lt_rows:
                    r['ma_hp'] = self.ma_hp
                    self.repo.insert_lt(r)
            else:
                self.db.conn.execute("DELETE FROM NoiDung_TH WHERE ma_hp=?", (self.ma_hp,))
                for r in self._th_rows:
                    r['ma_hp'] = self.ma_hp
                    self.repo.insert_th(r)
            self.db.conn.commit()
            show_modern_info(self, 'Thành công', f'Đã lưu nội dung {type_}.')
        except Exception as e:
            show_modern_error(self, 'Lỗi', str(e))
