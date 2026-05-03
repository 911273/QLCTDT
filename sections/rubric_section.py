# sections/rubric_section.py
"""
Rubric Section — Panel quản lý Rubric đánh giá.
Hỗ trợ tạo danh sách Rubric và chi tiết các tiêu chí cho từng Rubric.
Tương thích ttkbootstrap + BaseSection pattern (thay thế PyQt5).
"""
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, ScrollableFrame, RowEditDialog,
                                    CLR_PRIMARY2, CLR_HDR, CLR_ROW1, CLR_ROW2, CLR_BG)
from utils.ui_utils import (show_modern_info, show_modern_warning,
                             show_modern_error, ask_modern_yesno)

def auto_resize_text(event):
    """Tự động thay đổi chiều cao của Text widget dựa trên nội dung."""
    widget = event.widget
    # Tính số dòng hiển thị
    num_lines = int(widget.index('end-1c').split('.')[0])
    
    # Lấy thêm số dòng bị wrap (đối với dòng dài)
    display_lines = widget.count('1.0', 'end', 'displaylines')
    if display_lines:
        num_lines = display_lines[0]
        
    # Giới hạn chiều cao từ 3 đến 10 dòng
    new_height = max(3, min(10, num_lines))
    if widget.cget('height') != new_height:
        widget.configure(height=new_height)

class RubricSection(tb.Frame):
    """
    Panel quản lý Rubric đánh giá.
    Sử dụng Splitter (PanedWindow):
    - Trái: Danh sách Rubric (Listbox)
    - Phải: Editor chi tiết (Ma trận tiêu chí với TextEdit)
    """

    def __init__(self, parent, db, rubric_repo=None, clo_repo=None, bdg_repo=None, **kw):
        super().__init__(parent, **kw)
        self.db = db
        self.repo = rubric_repo
        self.clo_repo = clo_repo
        self.bdg_repo = bdg_repo
        self.ma_hp = None
        
        self._rubrics = []      # list[dict] - Thông tin Rubric
        self._criteria = {}     # dict[rubric_idx] -> list[dict] - Tiêu chí
        self._active_idx = None
        
        self._clo_list = []
        self._bdg_list = []
        
        # Biến cho Editor Header
        self.var_ma_rubric = tk.StringVar()
        self.var_ten_rubric = tk.StringVar()
        self.var_clo_id = tk.StringVar()
        self.var_bdg_id = tk.StringVar()
        
        # Danh sách widget chứa dòng tiêu chí
        self._crit_widgets = []
        
        self._build_ui()

    def _build_ui(self):
        # --- Header ---
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='8.2. Rubric đánh giá', 
                 font=('Times New Roman', 12, 'bold')).pack(anchor='w')
        tb.Label(head, text='Ghi chú: Tổng trọng số các tiêu chí phải bằng 100%',
                 font=('Times New Roman', 10, 'italic')).pack(anchor='w', pady=(2, 0))
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # --- Main Splitter ---
        paned = tb.Panedwindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=16, pady=4)

        # ====== LEFT PANE: List Rubric ======
        left_frm = tb.Frame(paned, width=250)
        paned.add(left_frm, weight=1)
        
        tb.Label(left_frm, text='Danh sách Rubric', font=('Times New Roman', 10, 'bold')).pack(anchor='w', pady=2)
        
        list_scroll = tb.Frame(left_frm)
        list_scroll.pack(fill='both', expand=True)
        
        self.listbox = tk.Listbox(list_scroll, font=('Times New Roman', 10), selectmode='single', exportselection=False)
        self.listbox.pack(side='left', fill='both', expand=True)
        sb_list = tb.Scrollbar(list_scroll, orient='vertical', command=self.listbox.yview)
        sb_list.pack(side='right', fill='y')
        self.listbox.config(yscrollcommand=sb_list.set)
        
        self.listbox.bind('<<ListboxSelect>>', self._on_rubric_select)
        
        btn_frm_left = tb.Frame(left_frm, pady=5)
        btn_frm_left.pack(fill='x')
        tb.Button(btn_frm_left, text='➕ Thêm', bootstyle='success', command=self._add_rubric).pack(side='left', fill='x', expand=True, padx=2)
        tb.Button(btn_frm_left, text='🗑 Xóa', bootstyle='danger', command=self._delete_rubric).pack(side='left', fill='x', expand=True, padx=2)

        # ====== RIGHT PANE: Rubric Editor ======
        right_frm = tb.Frame(paned)
        paned.add(right_frm, weight=4)
        
        # --- Editor Header ---
        header_frm = tb.Frame(right_frm, padding=5)
        header_frm.pack(fill='x')
        
        # Dòng 1: Mã, Tên
        r1 = tb.Frame(header_frm)
        r1.pack(fill='x', pady=2)
        tb.Label(r1, text="Mã Rubric:", width=12).pack(side='left')
        tb.Entry(r1, textvariable=self.var_ma_rubric, width=15).pack(side='left', padx=(0, 10))
        
        tb.Label(r1, text="Tên Rubric:").pack(side='left')
        tb.Entry(r1, textvariable=self.var_ten_rubric).pack(side='left', fill='x', expand=True)
        
        # Dòng 2: CLO, BĐG
        r2 = tb.Frame(header_frm)
        r2.pack(fill='x', pady=2)
        tb.Label(r2, text="CLO liên kết:", width=12).pack(side='left')
        self.cb_clo = tb.Combobox(r2, textvariable=self.var_clo_id, state='readonly', width=13)
        self.cb_clo.pack(side='left', padx=(0, 10))
        
        tb.Label(r2, text="BĐG liên kết:").pack(side='left')
        self.cb_bdg = tb.Combobox(r2, textvariable=self.var_bdg_id, state='readonly')
        self.cb_bdg.pack(side='left', fill='x', expand=True)

        tb.Separator(right_frm, orient='horizontal').pack(fill='x', pady=5)

        # --- Editor Matrix (Scrollable) ---
        matrix_container = tb.Frame(right_frm)
        matrix_container.pack(fill='both', expand=True)
        
        # Cột tiêu đề ma trận
        col_hdr_frm = tb.Frame(matrix_container, background=CLR_HDR)
        col_hdr_frm.pack(fill='x')
        widths = [15, 8, 15, 15, 15, 15] # approximate proportions
        heads = ['Tiêu chí', 'Trọng số %', 'Xuất sắc (9-10)', 'Tốt (7-8)', 'Đạt (5-6)', 'Chưa đạt (<5)', '']
        
        for i, h in enumerate(heads):
            w = widths[i] if i < len(widths) else 5
            lbl = tb.Label(col_hdr_frm, text=h, font=('Times New Roman', 10, 'bold'), 
                           background=CLR_HDR, foreground='white', anchor='center')
            if i == len(heads) - 1:
                lbl.pack(side='right', padx=5) # Delete button space
            else:
                lbl.pack(side='left', fill='x', expand=True, padx=2, pady=5)
                
        # Khung cuộn chứa các dòng tiêu chí
        self.matrix_scroll = ScrollableFrame(matrix_container)
        self.matrix_scroll.pack(fill='both', expand=True)
        self.matrix_inner = self.matrix_scroll.inner

        # --- Editor Footer ---
        footer_frm = tb.Frame(right_frm, padding=5)
        footer_frm.pack(fill='x')
        
        tb.Button(footer_frm, text='➕ Thêm tiêu chí', bootstyle='info-outline', command=self._add_criterion_row).pack(side='left')
        
        self.lbl_total_weight = tb.Label(footer_frm, text="Tổng trọng số: 0%", font=('Arial', 10, 'bold'))
        self.lbl_total_weight.pack(side='left', padx=20)
        
        tb.Button(footer_frm, text='💾 Lưu Rubric hiện tại', bootstyle='primary', command=self._save_active_rubric).pack(side='right')

    # --- Data Loading ---
    def load_data(self, ma_hp):
        self.ma_hp = ma_hp
        self._active_idx = None
        self._rubrics = []
        self._criteria = {}
        self._crit_widgets = []
        
        self._load_combobox_data()
        
        if self.repo:
            rows = self.repo.get_all(ma_hp)
            for i, r in enumerate(rows):
                rubric_dict = dict(r)
                self._rubrics.append(rubric_dict)
                # Load criteria
                if rubric_dict.get('id'):
                    crit_rows = self.repo.get_tieu_chi(rubric_dict['id'])
                    self._criteria[i] = [dict(cr) for cr in crit_rows]
                else:
                    self._criteria[i] = []
                    
        self._refresh_listbox()
        self._clear_editor()

    def _load_combobox_data(self):
        self._clo_list = []
        self._bdg_list = []
        if not self.ma_hp: return
        
        # Load CLO
        if self.clo_repo:
            clos = self.clo_repo.get_all(self.ma_hp)
            self._clo_list = [{'id': c['id'], 'ma': c['ma_clo'], 'mo_ta': c.get('mo_ta','')} for c in clos]
            self.cb_clo['values'] = [c['ma'] for c in self._clo_list]
            
        # Load BaiDanhGia
        if self.bdg_repo:
            bdgs = self.bdg_repo.get_all(self.ma_hp)
            self._bdg_list = [{'id': b['id'], 'ma': b['ma_bdg'], 'ten': b.get('ten','')} for b in bdgs]
            self.cb_bdg['values'] = [b['ma'] for b in self._bdg_list]

    def _refresh_listbox(self):
        self.listbox.delete(0, 'end')
        for r in self._rubrics:
            ma = r.get('ma_rubric', 'Mới')
            ten = r.get('ten', 'Chưa đặt tên')
            
            # Map CLO ID to Ma
            clo_str = ''
            if r.get('clo_id'):
                for c in self._clo_list:
                    if c['id'] == r['clo_id']:
                        clo_str = f" [{c['ma']}]"
                        break
                        
            self.listbox.insert('end', f"{ma}: {ten}{clo_str}")

    def _clear_editor(self):
        self.var_ma_rubric.set('')
        self.var_ten_rubric.set('')
        self.var_clo_id.set('')
        self.var_bdg_id.set('')
        
        for w in self.matrix_inner.winfo_children():
            w.destroy()
        self._crit_widgets = []
        self._update_total_weight()

    # --- Actions ---
    def _on_rubric_select(self, event):
        # Tự động lưu panel đang mở nếu có thay đổi (tùy chọn, ở đây yêu cầu bấm Lưu)
        sel = self.listbox.curselection()
        if not sel: return
        
        self._active_idx = int(sel[0])
        r = self._rubrics[self._active_idx]
        
        self.var_ma_rubric.set(r.get('ma_rubric', ''))
        self.var_ten_rubric.set(r.get('ten', ''))
        
        # Map IDs to Combobox values
        clo_val = ''
        if r.get('clo_id'):
            for c in self._clo_list:
                if c['id'] == r['clo_id']: clo_val = c['ma']
        self.var_clo_id.set(clo_val)
        
        bdg_val = ''
        if r.get('bdg_id'):
            for b in self._bdg_list:
                if b['id'] == r['bdg_id']: bdg_val = b['ma']
        self.var_bdg_id.set(bdg_val)
        
        self._render_criteria_matrix()

    def _add_rubric(self):
        new_rubric = {
            'ma_hp': self.ma_hp,
            'ma_rubric': f'R{len(self._rubrics)+1}',
            'ten': 'Rubric mới'
        }
        self._rubrics.append(new_rubric)
        self._criteria[len(self._rubrics)-1] = []
        self._refresh_listbox()
        self.listbox.selection_clear(0, 'end')
        self.listbox.selection_set('end')
        self._on_rubric_select(None)

    def _delete_rubric(self):
        sel = self.listbox.curselection()
        if not sel: return
        idx = int(sel[0])
        
        if not ask_modern_yesno(self, 'Xác nhận', 'Xóa Rubric này và tất cả tiêu chí?'):
            return
            
        rubric = self._rubrics[idx]
        if rubric.get('id') and self.repo:
            try:
                self.repo.conn.execute("DELETE FROM Rubric WHERE id=?", (rubric['id'],))
                self.repo.conn.execute("DELETE FROM Rubric_TieuChi WHERE rubric_id=?", (rubric['id'],))
                self.repo.conn.commit()
            except Exception as e:
                show_modern_error(self, 'Lỗi CSDL', str(e))
                return
                
        self._rubrics.pop(idx)
        # Shift criteria dict
        new_crit = {}
        for i in range(len(self._rubrics)):
            old_i = i if i < idx else i + 1
            new_crit[i] = self._criteria.get(old_i, [])
        self._criteria = new_crit
        
        self._active_idx = None
        self._refresh_listbox()
        self._clear_editor()

    # --- Matrix Rendering ---
    def _render_criteria_matrix(self):
        for w in self.matrix_inner.winfo_children():
            w.destroy()
        self._crit_widgets = []
        
        if self._active_idx is None: return
        
        crits = self._criteria.get(self._active_idx, [])
        for cr in crits:
            self._add_criterion_row(cr)
            
        self._update_total_weight()

    def _add_criterion_row(self, data=None):
        if self._active_idx is None:
            show_modern_warning(self, 'Thông báo', 'Vui lòng chọn hoặc tạo Rubric trước.')
            return
            
        if data is None:
            data = {'tieu_chi': '', 'trong_so': 0, 'xuat_sac': '', 'tot': '', 'dat': '', 'chua_dat': ''}
            self._criteria[self._active_idx].append(data)
            
        idx = len(self._crit_widgets)
        
        row_frm = tb.Frame(self.matrix_inner, padding=2)
        row_frm.pack(fill='x', pady=2)
        
        # Hàm tạo Text widget có auto resize
        def make_text(parent, val):
            txt = tk.Text(parent, font=('Times New Roman', 10), height=3, width=15, wrap='word')
            txt.insert('1.0', val or '')
            txt.bind('<KeyRelease>', auto_resize_text)
            return txt

        # Tiêu chí
        txt_tc = make_text(row_frm, data.get('tieu_chi', ''))
        txt_tc.pack(side='left', fill='x', expand=True, padx=2)
        
        # Trọng số
        var_ts = tk.IntVar(value=int(data.get('trong_so', 0)))
        var_ts.trace_add("write", lambda *_: self._update_total_weight())
        sp_ts = tb.Spinbox(row_frm, from_=0, to=100, textvariable=var_ts, width=5, justify='center')
        sp_ts.pack(side='left', padx=2)
        
        # Các mức độ
        txt_xs = make_text(row_frm, data.get('xuat_sac', ''))
        txt_xs.pack(side='left', fill='x', expand=True, padx=2)
        
        txt_t = make_text(row_frm, data.get('tot', ''))
        txt_t.pack(side='left', fill='x', expand=True, padx=2)
        
        txt_d = make_text(row_frm, data.get('dat', ''))
        txt_d.pack(side='left', fill='x', expand=True, padx=2)
        
        txt_cd = make_text(row_frm, data.get('chua_dat', ''))
        txt_cd.pack(side='left', fill='x', expand=True, padx=2)
        
        # Nút xóa
        def _del_row(f=row_frm, i=idx):
            f.destroy()
            self._crit_widgets[i] = None # Đánh dấu là đã xóa
            self._update_total_weight()
            
        btn_del = tb.Button(row_frm, text='X', bootstyle='danger', width=2, command=_del_row)
        btn_del.pack(side='right', padx=2)
        
        self._crit_widgets.append({
            'frame': row_frm,
            'txt_tc': txt_tc,
            'var_ts': var_ts,
            'txt_xs': txt_xs,
            'txt_t': txt_t,
            'txt_d': txt_d,
            'txt_cd': txt_cd
        })
        
        # Cập nhật height ngay từ đầu
        for txt in [txt_tc, txt_xs, txt_t, txt_d, txt_cd]:
            auto_resize_text(type('Event', (), {'widget': txt})())
            
        self._update_total_weight()

    def _update_total_weight(self):
        total = 0
        for w in self._crit_widgets:
            if w is not None:
                try: total += w['var_ts'].get()
                except: pass
                
        self.lbl_total_weight.config(text=f"Tổng trọng số: {total}%")
        if total != 100:
            self.lbl_total_weight.config(foreground='red')
        else:
            self.lbl_total_weight.config(foreground='green')

    def _save_active_rubric(self):
        if self._active_idx is None or not self.repo: return
        
        # --- Gom dữ liệu từ Header ---
        rubric = self._rubrics[self._active_idx]
        rubric['ma_rubric'] = self.var_ma_rubric.get().strip()
        rubric['ten'] = self.var_ten_rubric.get().strip()
        
        # Resolve CLO ID
        clo_ma = self.var_clo_id.get()
        rubric['clo_id'] = None
        for c in self._clo_list:
            if c['ma'] == clo_ma: rubric['clo_id'] = c['id']
            
        # Resolve BDG ID
        bdg_ma = self.var_bdg_id.get()
        rubric['bdg_id'] = None
        for b in self._bdg_list:
            if b['ma'] == bdg_ma: rubric['bdg_id'] = b['id']
            
        # Kiểm tra tính hợp lệ
        if not rubric['ma_rubric']:
            show_modern_warning(self, 'Cảnh báo', 'Mã Rubric không được để trống.')
            return
            
        # Gom dữ liệu từ Ma trận
        new_crits = []
        total_w = 0
        for i, w in enumerate(self._crit_widgets):
            if w is not None:
                ts = w['var_ts'].get()
                total_w += ts
                new_crits.append({
                    'tieu_chi': w['txt_tc'].get('1.0', 'end-1c').strip(),
                    'trong_so': ts,
                    'xuat_sac': w['txt_xs'].get('1.0', 'end-1c').strip(),
                    'tot': w['txt_t'].get('1.0', 'end-1c').strip(),
                    'dat': w['txt_d'].get('1.0', 'end-1c').strip(),
                    'chua_dat': w['txt_cd'].get('1.0', 'end-1c').strip(),
                    'thu_tu': len(new_crits) + 1
                })
                
        if new_crits and total_w != 100:
            if not ask_modern_yesno(self, 'Cảnh báo', f'Tổng trọng số hiện tại là {total_w}%, không bằng 100%. Bạn vẫn muốn lưu?'):
                return
                
        # --- Lưu vào DB ---
        try:
            # 1. Lưu Rubric
            if rubric.get('id'):
                # Update
                self.repo.conn.execute("""
                    UPDATE Rubric SET ma_rubric=?, ten=?, clo_id=?, bdg_id=? WHERE id=?
                """, (rubric['ma_rubric'], rubric['ten'], rubric['clo_id'], rubric['bdg_id'], rubric['id']))
            else:
                # Insert
                rubric['id'] = self.repo.insert(rubric)
                
            # 2. Lưu Tiêu chí
            self.repo.conn.execute("DELETE FROM Rubric_TieuChi WHERE rubric_id=?", (rubric['id'],))
            for cr in new_crits:
                cr['rubric_id'] = rubric['id']
                self.repo.insert_tieu_chi(cr)
                
            self.repo.conn.commit()
            
            # Cập nhật state
            self._criteria[self._active_idx] = new_crits
            self._refresh_listbox()
            self.listbox.selection_set(self._active_idx)
            
            show_modern_info(self, 'Thành công', 'Đã lưu Rubric thành công!')
        except Exception as e:
            show_modern_error(self, 'Lỗi', str(e))

    def save_data(self):
        """Method được gọi từ bên ngoài (MainController/DCEditor)."""
        # Nếu đang chọn Rubric nào thì tự động lưu Rubric đó
        if self._active_idx is not None:
            self._save_active_rubric()
        return True
