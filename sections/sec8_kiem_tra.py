# sections/sec8_kiem_tra.py — Phương pháp, hình thức kiểm tra – đánh giá kết quả
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, ScrollableFrame, RowEditDialog,
                                    make_tree, CLR_PRIMARY2, CLR_HDR)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
from utils.auto_fill import get_suggested_nhiem_vu, get_suggested_assessment


class CLOPickerDialog(tb.Toplevel):
    """Popup checkbox chọn nhiều CLO từ danh sách thực tế của HP."""
    
    def __init__(self, parent, db, hp_id, current_selected=''):
        super().__init__(parent)
        abbr_clo = db.get_config('abbr_clo', 'CLO')
        self.title(f'Chọn {abbr_clo} liên quan')
        self.resizable(False, False)
        self.result = None
        
        self._vars = {}
        clo_list = db.get_clo(hp_id) if hp_id else []
        from utils.data_utils import natural_sort_key
        clo_list.sort(key=lambda x: natural_sort_key(x.get('ma', '')))
        selected_codes = [c.strip() for c in current_selected.split(',') if c.strip()]
        
        tb.Label(self, text=f'Chọn các {abbr_clo} liên quan:',
                 font=('Arial', 10, 'bold')).pack(anchor='w', padx=16, pady=(12, 4))
        
        frm = ScrollableFrame(self) if len(clo_list) > 8 else tb.Frame(self)
        frm.pack(fill='both', expand=True, padx=16)
        inner = frm.inner if hasattr(frm, 'inner') else frm
        
        if not clo_list:
            tb.Label(inner, text=f'⚠ Chưa có {abbr_clo} nào. Vui lòng điền Tab 4 trước.',
                     bootstyle='warning').pack(pady=8)
        
        for clo in clo_list:
            # FIXED N-08: cột 'ma' trong bảng production, không phải 'ma_clo'
            ma = clo['ma'] if 'ma' in clo.keys() else clo.get('ma_clo', '')
            if not ma: continue
            var = tk.BooleanVar(value=(ma in selected_codes))
            self._vars[ma] = var
            mo_ta = clo.get('mo_ta') or ''
            chk = tb.Checkbutton(
                inner,
                text=f"[{ma}] {mo_ta[:60]}{'...' if len(mo_ta) > 60 else ''}",
                variable=var,
                bootstyle='primary'
            )
            chk.pack(anchor='w', pady=2)
        
        # Nút
        btn_frm = tb.Frame(self)
        btn_frm.pack(fill='x', padx=16, pady=12)
        tb.Button(btn_frm, text='✅ Xác nhận', bootstyle='primary',
                  command=self._confirm).pack(side='left', padx=4)
        tb.Button(btn_frm, text='Chọn tất cả',
                  command=self._select_all).pack(side='left', padx=4)
        tb.Button(btn_frm, text='Bỏ chọn', bootstyle='outline-secondary',
                  command=self._deselect_all).pack(side='left', padx=4)
        tb.Button(btn_frm, text='✖ Hủy', bootstyle='outline-danger',
                  command=self.destroy).pack(side='right', padx=4)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()
    
    def _confirm(self):
        self.result = ', '.join(ma for ma, var in self._vars.items() if var.get())
        self.destroy()
    
    def _select_all(self):
        for var in self._vars.values(): var.set(True)
    
    def _deselect_all(self):
        for var in self._vars.values(): var.set(False)


from sections.registry import register_section


@register_section(order=8, label="8. Kiểm tra đánh giá")
class Sec8KiemTra(BaseSection):
    _TC_CLIPBOARD = []   # Shared clipboard cho tất cả instance
    _TC_CLIPBOARD_SRC = ''  # Tên rubric nguồn để hiển thị

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._kt_rows = []
        self._rubric_list = []     # [{'ten','ky_hieu','mo_ta','thu_tu','tieu_chi_list':[...]}]
        self._sel_rubric_idx = None
        self.kt_tree = None # FIXED: Initialize for safety
        self.rb_tree = None # FIXED: Initialize for safety
        self.tc_tree = None # FIXED: Initialize for safety
        self._task_vars = {}
        self.v_tx_pct = tk.StringVar(value='30')
        self.v_ck_pct = tk.StringVar(value='70')
        self._pct_valid = False  # trạng thái hợp lệ của tỷ trọng
        
        self._undo_stack = []
        self._redo_stack = []
        self.bind_all('<Control-z>', lambda e: self._undo())
        self.bind_all('<Control-y>', lambda e: self._redo())

    def _save_undo(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self._kt_rows))
        if len(self._undo_stack) > 20: self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        import copy
        self._redo_stack.append(copy.deepcopy(self._kt_rows))
        self._kt_rows = self._undo_stack.pop()
        self._kt_refresh(self._kt_rows)

    def _redo(self):
        if not self._redo_stack: return
        import copy
        self._undo_stack.append(copy.deepcopy(self._kt_rows))
        self._kt_rows = self._redo_stack.pop()
        self._kt_refresh(self._kt_rows)

    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        p = sf.inner
        self._extra_parent = p
        
        tb.Label(p, text='8. Phương pháp, hình thức kiểm tra – đánh giá kết quả học tập',
                  style='SectionHeader.TLabel').pack(anchor='w', padx=16, pady=(12, 4))
        tb.Separator(p, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # ── 8.1 Nhiệm vụ SV ─────────────────────────────────────────────────
        lf1 = tb.Labelframe(p, text='8.1. Nhiệm vụ của sinh viên', padding=10)
        lf1.pack(fill='x', padx=16, pady=(0, 8))

        lbl_frm = tb.Frame(lf1)
        lbl_frm.pack(fill='x', pady=(0, 4))
        tb.Label(lbl_frm, text='Nhiệm vụ của sinh viên (dự lớp, bài tập, thảo luận, thực hành, ...)',
                  font=('Arial', 10)).pack(side='left')
        tb.Button(lbl_frm, text='🪄 Tự động điền mẫu', bootstyle='outline-info', 
                   command=self._auto_fill_nhiem_vu, padding=2).pack(side='right')

        task_rows = [
            ('nhiem_vu_sv_len_lop', 'Dự lớp (chuyên cần); Chuẩn bị bài thảo luận:'),
            ('nhiem_vu_sv_bai_tap', 'Bài tập:'),
            ('nhiem_vu_sv_dung_cu', 'Dụng cụ học tập:'),
            ('nhiem_vu_sv_khac',    'Khác:'),
        ]
        
        grid_tasks = tb.Frame(lf1)
        grid_tasks.pack(fill='x', expand=True)
        
        for i, (key, lbl) in enumerate(task_rows):
            tb.Label(grid_tasks, text=lbl, font=('Arial', 10)
                      ).grid(row=i, column=0, sticky='nw', padx=4, pady=3)
            txt = tk.Text(grid_tasks, width=60, height=2, font=('Arial', 10),
                          relief='solid', bd=1, padx=4, pady=4, wrap='word')
            txt.grid(row=i, column=1, sticky='ew', padx=4, pady=3)
            self._task_vars[key] = txt
        grid_tasks.columnconfigure(1, weight=1)

        # ── 8.2 Kế hoạch kiểm tra ─────────────────────────────────────────
        lf2 = tb.Labelframe(p, text='8.2. Kế hoạch kiểm tra – đánh giá', padding=10)
        lf2.pack(fill='both', expand=True, padx=16, pady=(0, 8))

        lbl2_frm = tb.Frame(lf2)
        lbl2_frm.pack(fill='x', pady=(0, 4))
        tb.Label(lbl2_frm, text='Phương pháp, hình thức kiểm tra - đánh giá học phần (theo mẫu DCCTHP mới)',
                  font=('Arial', 10)).pack(side='left')
        tb.Button(lbl2_frm, text='🪄 Điền ma trận mẫu', bootstyle='outline-info', 
                   command=self._auto_fill_assessment, padding=2).pack(side='right')

        # 8 cột theo mẫu DCCTHP mới
        cols   = ('nhom', 'ty_trong_nhom', 'noi_dung', 'hinh_thuc',
                  'tieu_chi', 'clo_lien_quan', 'diem_toi_da_cdr', 'trong_so_cdr')
        heads  = ('Thành phần ĐG', 'Trọng số HP (%)', 'Bài đánh giá', 'Hình thức',
                  'Tiêu chí ĐG', 'CĐR được ĐG', 'Ðiểm tối đa CĐR', 'Trọng số CĐR (%)')
        widths = (110, 80, 160, 80, 120, 80, 100, 100)
        aligns = ('w', 'center', 'w', 'center', 'w', 'center', 'center', 'center')
        self.kt_frm, self.kt_tree = make_tree(lf2, cols, heads, widths, height=10,
                                               column_aligns=aligns, db=self.db,
                                               table_id='sec8_kiem_tra')
        self.kt_frm.pack(fill='both', expand=True)
        self.kt_tree.bind('<Double-1>', lambda _e: self._kt_edit())

        bf = tb.Frame(lf2)
        bf.pack(fill='x', pady=(4, 0))
        tb.Button(bf, text='➕ Thêm KT thường xuyên',
                   command=lambda: self._kt_add('thuong_xuyen')).pack(side='left', padx=4)
        tb.Button(bf, text='➕ Thêm thi cuối kỳ',
                   command=lambda: self._kt_add('cuoi_ky')).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',
                   command=self._kt_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',
                   command=self._kt_delete).pack(side='left', padx=4)

        pct_frame = tb.Labelframe(lf2, text='Tỷ trọng đánh giá', padding=8)
        pct_frame.pack(fill='x', pady=(8, 0))

        row_pct = tb.Frame(pct_frame)
        row_pct.pack(fill='x')

        tb.Label(row_pct, text='KT thường xuyên (%):',
                 font=('Arial', 10)).grid(row=0, column=0, sticky='w', padx=4)
        spn_tx = tb.Spinbox(row_pct, from_=0, to=100, increment=5,
                            textvariable=self.v_tx_pct, width=7, font=('Arial', 10))
        spn_tx.grid(row=0, column=1, sticky='w', padx=4, pady=2)

        tb.Label(row_pct, text='Thi cuối kỳ (%):',
                 font=('Arial', 10)).grid(row=0, column=2, sticky='w', padx=(16, 4))
        spn_ck = tb.Spinbox(row_pct, from_=0, to=100, increment=5,
                            textvariable=self.v_ck_pct, width=7, font=('Arial', 10))
        spn_ck.grid(row=0, column=3, sticky='w', padx=4, pady=2)

        self.lbl_pct_sum = tb.Label(row_pct, text='Tổng: 100% ✅',
                                    bootstyle='success', font=('Arial', 10, 'bold'))
        self.lbl_pct_sum.grid(row=0, column=4, sticky='w', padx=(20, 4))

        btn_auto_pct = tb.Button(row_pct, text='🔄 Tự động chia',
                                 bootstyle='outline-secondary',
                                 command=self._auto_split_pct, padding=2)
        btn_auto_pct.grid(row=0, column=5, sticky='w', padx=4)

        # Trace realtime
        self.v_tx_pct.trace_add('write', lambda *_: self._update_pct_pill())
        self.v_ck_pct.trace_add('write', lambda *_: self._update_pct_pill())

        # ── 8.3 Rubric đánh giá ───────────────────────────────────────────
        lf3 = tb.Labelframe(p, text='8.3. Rubric đánh giá', padding=10)
        lf3.pack(fill='both', expand=True, padx=16, pady=(0, 12))

        tb.Label(lf3, text='Danh sách Rubric (tiêu chí chấm điểm chi tiết theo mẫu DCCTHP):',
                  font=('Arial', 10, 'italic')).pack(anchor='w', pady=(0, 4))

        # Bảng trái: danh sách rubric
        rubric_pane = tb.Frame(lf3)
        rubric_pane.pack(fill='both', expand=True)

        left_frm = tb.Labelframe(rubric_pane, text='Danh sách Rubric', padding=6)
        left_frm.pack(side='left', fill='both', padx=(0, 6))

        rb_cols   = ('ky_hieu', 'ten')
        rb_heads  = ('Ký hiệu', 'Tên Rubric')
        rb_widths = (60, 200)
        self.rb_list_frm, self.rb_tree = make_tree(left_frm, rb_cols, rb_heads,
                                                    rb_widths, height=6,
                                                    db=self.db, table_id='sec8_rubric')
        self.rb_list_frm.pack(fill='both', expand=True)
        self.rb_tree.bind('<<TreeviewSelect>>', lambda _e: self._on_rubric_select())

        # Drag Reorder
        from sections.base_section import enable_drag_reorder
        enable_drag_reorder(self.rb_tree, on_reorder_cb=self._on_rubric_reorder)

        rb_bf = tb.Frame(left_frm)
        rb_bf.pack(fill='x', pady=(4, 0))
        tb.Button(rb_bf, text='➕ Thêm', command=self._rubric_add).pack(side='left', padx=2)
        tb.Button(rb_bf, text='✏ Sửa',  command=self._rubric_edit).pack(side='left', padx=2)
        tb.Button(rb_bf, text='🗑 Xóa',  command=self._rubric_delete).pack(side='left', padx=2)

        # Bảng phải: tiêu chí của rubric đang chọn
        right_frm = tb.Labelframe(rubric_pane, text='Tiêu chí của Rubric đang chọn', padding=6)
        right_frm.pack(side='left', fill='both', expand=True)

        tc_cols   = ('tieu_chi', 'trong_so', 'muc_xuat_sac', 'muc_tot', 'muc_dat', 'muc_chua_dat')
        tc_heads  = ('Tiêu chí', 'Trọng số', 'Xuất sắc (9-10)', 'Tốt (7-8.9)', 'Đạt (5-6.9)', 'Chưa đạt (0-4.9)')
        tc_widths = (130, 60, 120, 120, 120, 120)
        self.tc_list_frm, self.tc_tree = make_tree(right_frm, tc_cols, tc_heads,
                                                    tc_widths, height=6,
                                                    db=self.db, table_id='sec8_rubric_tc')
        self.tc_list_frm.pack(fill='both', expand=True)
        self.tc_tree.bind('<Double-1>', lambda _e: self._tc_edit())

        tc_bf = tb.Frame(right_frm)
        tc_bf.pack(fill='x', pady=(4, 0))
        tb.Button(tc_bf, text='➕ Thêm tiêu chí', command=self._tc_add).pack(side='left', padx=2)
        tb.Button(tc_bf, text='✏ Sửa',            command=self._tc_edit).pack(side='left', padx=2)
        tb.Button(tc_bf, text='🗑 Xóa',            command=self._tc_delete).pack(side='left', padx=2)
        tb.Button(tc_bf, text='📋 Điền mẫu nhanh', bootstyle='outline-info',
                   command=self._tc_auto_fill).pack(side='left', padx=8)

        tb.Separator(tc_bf, orient='vertical').pack(side='left', padx=6, fill='y')
        self.btn_tc_copy = tb.Button(
            tc_bf, text='📋 Copy TC',
            bootstyle='outline-info',
            command=self._tc_copy_all
        )
        self.btn_tc_copy.pack(side='left', padx=2)

        self.btn_tc_paste = tb.Button(
            tc_bf, text='📌 Paste TC',
            bootstyle='outline-warning',
            command=self._tc_paste_all,
            state='disabled'  # Enable sau khi có data trong clipboard
        )
        self.btn_tc_paste.pack(side='left', padx=2)

        # Inline Edit
        from sections.base_section import enable_inline_edit
        enable_inline_edit(
            self.kt_tree,
            editable_cols=['hinh_thuc', 'ty_trong_nhom', 'clo_lien_quan',
                           'diem_toi_da_cdr', 'trong_so_cdr'],
            on_change_cb=self._on_kt_cell_changed
        )
        enable_inline_edit(
            self.tc_tree,
            editable_cols=['trong_so'],
            on_change_cb=self._on_tc_cell_changed
        )

        # ── Quick Summary Panel ──────────────────────────────────────────────────────
        self._summary_collapsed = False
        self.summary_outer = tb.Frame(p)
        self.summary_outer.pack(fill='x', padx=16, pady=(0, 16))

        # Header có thể click để collapse
        summary_header = tb.Frame(self.summary_outer, bootstyle='info')
        summary_header.pack(fill='x')

        self.lbl_summary_toggle = tb.Label(
            summary_header,
            text='📊 Tổng quan đề cương  ▼ (click để thu gọn)',
            font=('Arial', 10, 'bold'),
            bootstyle='inverse-info',
            cursor='hand2',
            padding=(8, 4)
        )
        self.lbl_summary_toggle.pack(fill='x')
        self.lbl_summary_toggle.bind('<Button-1>', lambda _e: self._toggle_summary())

        # Nội dung summary
        self.summary_body = tb.Frame(self.summary_outer)
        self.summary_body.pack(fill='x')

        # Grid 2 cột, 4 dòng
        summary_grid = tb.Frame(self.summary_body)
        summary_grid.pack(fill='x', padx=8, pady=6)

        # Định nghĩa các chỉ số cần hiển thị
        self._summary_labels = {}
        abbr_clo = self.get_abbr('CLO', 'CLO')
        metrics = [
            ('clo',      f'📌 {abbr_clo}:',              'col=0,row=0'),
            ('lt',       '📖 Nội dung LT:',      'col=2,row=0'),
            ('danh_gia', '⚖ Đánh giá:',         'col=0,row=1'),
            ('rubric',   '📋 Rubric:',           'col=2,row=1'),
            ('trong_so', '🎯 Tổng trọng số:',    'col=0,row=2'),
            ('canh_bao', '⚠ Cảnh báo:',         'col=0,row=3'),
        ]

        label_positions = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 2), (1, 2), (2, 2), (3, 2),
            (0, 4), (1, 4),
            (0, 6), (1, 6),
        ]

        self._metric_captions = {} 
        for i, (key, caption, _) in enumerate(metrics):
            r, c = divmod(i, 2)
            lbl_cap = tb.Label(summary_grid, text=caption,
                     font=('Arial', 10), width=16, anchor='w'
                     )
            lbl_cap.grid(row=r, column=c*2, sticky='w', padx=(8, 2), pady=2)
            self._metric_captions[key] = lbl_cap
            self._summary_labels[key] = tb.Label(
                summary_grid, text='—',
                font=('Arial', 10, 'bold'), anchor='w'
            )
            self._summary_labels[key].grid(row=r, column=c*2+1, sticky='w', padx=(0, 16), pady=2)

        # Nút refresh
        tb.Button(
            self.summary_body,
            text='🔄 Cập nhật tóm tắt',
            bootstyle='outline-secondary',
            command=self._refresh_summary,
            padding=2
        ).pack(anchor='e', padx=8, pady=(0, 4))

    def refresh_labels(self):
        """Cập nhật lại các nhãn khi cấu hình viết tắt thay đổi."""
        if not self._ui_built: return
        abbr_clo = self.get_abbr('CLO', 'CLO')
        if 'clo' in self._metric_captions:
            self._metric_captions['clo'].config(text=f'📌 {abbr_clo}:')
        if hasattr(self, 'kt_tree') and self.kt_tree:
            self.kt_tree.heading('clo_lien_quan', text=f'{abbr_clo} liên quan')

    def _on_kt_cell_changed(self, row_id, col_id, new_val):
        """Sync thay đổi inline edit về self._kt_rows."""
        try:
            idx = int(row_id)
            if 0 <= idx < len(self._kt_rows):
                self._kt_rows[idx][col_id] = new_val
                self._refresh_summary()
        except (ValueError, KeyError):
            pass

    def _on_tc_cell_changed(self, row_id, col_id, new_val):
        """Sync thay đổi inline edit về tieu_chi_list."""
        if self._sel_rubric_idx is None:
            return
        try:
            idx = int(row_id)
            tcs = self._rubric_list[self._sel_rubric_idx].get('tieu_chi_list', [])
            if 0 <= idx < len(tcs):
                tcs[idx][col_id] = new_val
                self._refresh_summary()
        except (ValueError, KeyError, IndexError):
            pass

    def _update_pct_pill(self):
        """Cập nhật pill tổng trọng số realtime."""
        if not hasattr(self, 'lbl_pct_sum'):
            return
        try:
            tx = float(self.v_tx_pct.get() or 0)
            ck = float(self.v_ck_pct.get() or 0)
            total = tx + ck
            ok = abs(total - 100) < 0.1
            self._pct_valid = ok
            if ok:
                self.lbl_pct_sum.config(
                    text=f'Tổng: {total:.0f}% ✅',
                    bootstyle='success'
                )
            else:
                diff = 100 - total
                hint = f'(thiếu {diff:.0f}%)' if diff > 0 else f'(dư {-diff:.0f}%)'
                self.lbl_pct_sum.config(
                    text=f'Tổng: {total:.0f}% ❌ {hint}',
                    bootstyle='danger'
                )
            self._refresh_summary()
        except (ValueError, tk.TclError):
            self.lbl_pct_sum.config(text='Tổng: ? ❌', bootstyle='warning')
            self._pct_valid = False

    def _auto_split_pct(self):
        """Tự động chia 30/70 hoặc tùy loại HP."""
        nhom_tx = [r for r in self._kt_rows if r.get('nhom') == 'thuong_xuyen']
        nhom_ck = [r for r in self._kt_rows if r.get('nhom') == 'cuoi_ky']
        if nhom_tx and nhom_ck:
            self.v_tx_pct.set('30')
            self.v_ck_pct.set('70')
        elif nhom_ck:
            self.v_tx_pct.set('0')
            self.v_ck_pct.set('100')
        else:
            self.v_tx_pct.set('100')
            self.v_ck_pct.set('0')
        self._update_pct_pill()

    # ─── Kế hoạch KT ─────────────────────────────────────────────────────────
    def _kt_fields(self, nhom):
        abbr_clo = self.get_abbr('CLO', 'CLO')
        return [
            ('noi_dung',          'Bài đánh giá',                    'text',  {}),
            ('hinh_thuc',         'Hình thức đánh giá',              'entry', {}),
            ('tieu_chi',          'Tiêu chí đánh giá (mã Rubric)',   'entry', {}),
            ('clo_lien_quan', f'{abbr_clo} được đánh giá', 'entry_with_btn',
             {'btn_text': f'🔗 Chọn {abbr_clo}', 'btn_cmd_key': 'pick_clo'}),
            ('diem_toi_da_cdr',   f'Điểm tối đa của {abbr_clo}',            'entry', {}),
            ('trong_so_cdr',      f'Trọng số đánh giá theo {abbr_clo} (%)', 'entry', {}),
            ('thoi_gian',         'Thời gian',                       'entry', {}),
            ('thang_diem',        'Thang điểm',                      'entry', {}),
            ('cap_do',            'Mức độ đáp ứng CDR học phần',     'entry', {}),
            ('ty_trong',          'Tỷ trọng (%)',                    'entry', {}),
        ]

    def _kt_refresh(self, rows):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not hasattr(self, 'kt_tree') or not self.kt_tree: return # FINAL GUARD
        self.kt_tree.delete(*self.kt_tree.get_children())
        nhom_labels = {'thuong_xuyen': '◆ Thường xuyên', 'cuoi_ky': '◆ Cuối kỳ'}
        shown_groups = set()
        r_idx = 0
        for nhom in ['thuong_xuyen', 'cuoi_ky']:
            nhom_rows = [r for r in rows if r.get('nhom') == nhom]
            if nhom_rows:
                if nhom not in shown_groups:
                    self.kt_tree.insert('', 'end', iid=f'grp_{nhom}',
                                        values=(nhom_labels.get(nhom, nhom), '', '', '', '', '', '', ''),
                                        tags=('group',))
                    shown_groups.add(nhom)
                for i, r in enumerate(nhom_rows):
                    tag = 'even' if (r_idx % 2 == 0) else 'odd'
                    r_idx += 1
                    self.kt_tree.insert('', 'end', iid=str(rows.index(r)),
                                        values=(r.get('nhom', ''),
                                                r.get('ty_trong_nhom', ''),
                                                r.get('noi_dung', ''),
                                                r.get('hinh_thuc', ''),
                                                r.get('tieu_chi', ''),
                                                self.extract_codes(r.get('clo_lien_quan', '')),
                                                r.get('diem_toi_da_cdr', ''),
                                                r.get('trong_so_cdr', '')),
                                        tags=(tag,))
        self._kt_rows = rows

    def _pick_clo(self, entry_widget_or_var, dialog=None):
        """Mở CLOPickerDialog và điền kết quả vào widget."""
        if not self.hp_id:
            show_modern_warning(self, 'Chưa chọn HP',
                                'Vui lòng chọn học phần trước.')
            return
        current = ''
        if isinstance(entry_widget_or_var, tk.StringVar):
            current = entry_widget_or_var.get()
        elif hasattr(entry_widget_or_var, 'get'):
            current = entry_widget_or_var.get()
        
        dlg = CLOPickerDialog(self, self.db, self.hp_id, current)
        if dlg.result is not None:
            if isinstance(entry_widget_or_var, tk.StringVar):
                entry_widget_or_var.set(dlg.result)
            elif hasattr(entry_widget_or_var, 'delete'):
                entry_widget_or_var.delete(0, 'end')
                entry_widget_or_var.insert(0, dlg.result)

    def _on_rubric_reorder(self, old_idx, new_idx):
        """Cập nhật self._rubric_list sau khi kéo thả."""
        if 0 <= old_idx < len(self._rubric_list) and \
           0 <= new_idx < len(self._rubric_list):
            item = self._rubric_list.pop(old_idx)
            self._rubric_list.insert(new_idx, item)
            # Cập nhật thu_tu
            for i, rb in enumerate(self._rubric_list):
                rb['thu_tu'] = i + 1
            # Cập nhật sel index theo vị trí mới
            self._sel_rubric_idx = new_idx

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        if hp:
            for key, txt in self._task_vars.items():
                txt.delete('1.0', 'end')
                val = hp[key] or ''
                if val:
                    txt.insert('1.0', val)
        rows = self.db.get_ke_hoach_kt(hp_id)
        self._kt_rows = [{'nhom': r['nhom'], 'ty_trong_nhom': r['ty_trong_nhom'],
                           'thu_tu': r['thu_tu'], 'noi_dung': r['noi_dung'],
                           'hinh_thuc': r['hinh_thuc'], 'thoi_gian': r['thoi_gian'],
                           'thang_diem': r['thang_diem'],
                           'cap_do': r['cap_do_dap_ung'],
                           'clo_lien_quan': r['clo_lien_quan'],
                           'tieu_chi': r['tieu_chi_danh_gia'] if 'tieu_chi_danh_gia' in r.keys() else '',
                           'diem_toi_da_cdr': r['diem_toi_da_cdr'] if 'diem_toi_da_cdr' in r.keys() else '',
                           'trong_so_cdr': r['trong_so_cdr'] if 'trong_so_cdr' in r.keys() else '',
                           'ty_trong': r['ty_trong']} for r in rows]
        self._kt_refresh(self._kt_rows)

        # Load rubric
        self._rubric_list = [dict(rb) | {'tieu_chi_list': [dict(tc) for tc in self.db.get_rubric_tieu_chi(rb['id'])]}
                              for rb in self.db.get_rubric_by_hp(hp_id)]
        self._rb_refresh()
        self._update_pct_pill()
        self._update_paste_btn_state()
        self._after_load_summary()
        self._loading = False

    def save(self):
        """FIXED M-09: Lưu trực tiếp qua DB thay vì dùng self.controller (không tồn tại trong BaseSection)."""
        if self.hp_id is None:
            return
        try:
            data = self.get_data_dict()
            # Lưu nhiệm vụ sinh viên vào học phần
            task_fields = ['nhiem_vu_sv_len_lop', 'nhiem_vu_sv_bai_tap', 'nhiem_vu_sv_dung_cu', 'nhiem_vu_sv_khac']
            hp_update = {k: data[k] for k in task_fields if k in data}
            if hp_update:
                self.db.update_hoc_phan(self.hp_id, hp_update)
            # Lưu kế hoạch kiểm tra
            rows = data.get('rows', [])
            if rows:
                self.db.set_ke_hoach_kt(self.hp_id, rows)
            # Lưu rubric
            rubric_list = data.get('rubric_list', [])
            self.db.set_rubric(self.hp_id, rubric_list)
        except Exception as e:
            print(f'[Sec8.save] Error: {e}')

    def get_data_dict(self):
        self.ensure_ui()
        task_data = {k: v.get('1.0', 'end-1c').strip() for k, v in self._task_vars.items()}
        items = []
        for nhom in ['thuong_xuyen', 'cuoi_ky']:
            nhom_rows = [r for r in self._kt_rows if r.get('nhom') == nhom]
            pct = self.v_tx_pct.get() if nhom == 'thuong_xuyen' else self.v_ck_pct.get()
            for i, r in enumerate(nhom_rows):
                items.append({'nhom': nhom, 'ty_trong_nhom': pct,
                              'thu_tu': i+1, 'noi_dung': r.get('noi_dung', ''),
                              'hinh_thuc': r.get('hinh_thuc', ''),
                              'thoi_gian': r.get('thoi_gian', ''),
                              'thang_diem': r.get('thang_diem', ''),
                              'cap_do_dap_ung': r.get('cap_do', ''),
                              'clo_lien_quan': r.get('clo_lien_quan', ''),
                              'tieu_chi_danh_gia': r.get('tieu_chi', ''),
                              'diem_toi_da_cdr': r.get('diem_toi_da_cdr', ''),
                              'trong_so_cdr': r.get('trong_so_cdr', ''),
                              'ty_trong': r.get('ty_trong', '')})
        return {**task_data, 'rows': items, 'rubric_list': self._rubric_list}

    def clear(self):
        super().clear()
        for txt in self._task_vars.values():
            txt.delete('1.0', 'end')
        self.kt_tree.delete(*self.kt_tree.get_children())
        self._kt_rows = []
        self._rubric_list = []
        self._sel_rubric_idx = None
        if hasattr(self, 'rb_tree'):
            self.rb_tree.delete(*self.rb_tree.get_children())
        if hasattr(self, 'tc_tree'):
            self.tc_tree.delete(*self.tc_tree.get_children())

    def _kt_add(self, nhom):
        dlg = RowEditDialog(self, f'Thêm kiểm tra', self._kt_fields(nhom))
        if dlg.result:
            self._save_undo()
            nhom_rows = [r for r in self._kt_rows if r.get('nhom') == nhom]
            self._kt_rows.append({'nhom': nhom, 'thu_tu': len(nhom_rows)+1,
                                   'noi_dung': dlg.result.get('noi_dung', ''),
                                   'hinh_thuc': dlg.result.get('hinh_thuc', ''),
                                   'thoi_gian': dlg.result.get('thoi_gian', ''),
                                   'thang_diem': dlg.result.get('thang_diem', ''),
                                   'cap_do': dlg.result.get('cap_do', ''),
                                   'clo_lien_quan': dlg.result.get('clo_lien_quan', ''),
                                   'tieu_chi': dlg.result.get('tieu_chi', ''),
                                   'diem_toi_da_cdr': dlg.result.get('diem_toi_da_cdr', ''),
                                   'trong_so_cdr': dlg.result.get('trong_so_cdr', ''),
                                   'ty_trong': dlg.result.get('ty_trong', '')})
            self._kt_refresh(self._kt_rows)

    def _kt_edit(self):
        sel = self.kt_tree.selection()
        if not sel or sel[0].startswith('grp_'):
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        row = self._kt_rows[idx]
        dlg = RowEditDialog(self, 'Sửa kiểm tra', self._kt_fields(row.get('nhom', '')),
                            initial=row)
        if dlg.result:
            self._save_undo()
            row.update(dlg.result)
            self._kt_refresh(self._kt_rows)
            self._refresh_summary()

    def _kt_delete(self):
        sel = self.kt_tree.selection()
        if not sel or sel[0].startswith('grp_'):
            return
        try:
            idx = int(sel[0])
        except ValueError:
            return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa bản ghi kiểm tra đã chọn?'):
            self._save_undo()
            self._kt_rows.pop(idx)
            self._kt_refresh(self._kt_rows)
            self._refresh_summary()

    # ─── Rubric ───────────────────────────────────────────────────────────────
    def _rubric_fields(self):
        return [
            ('ky_hieu', 'Ký hiệu (VD: R1, R2)', 'entry', {}),
            ('ten',     'Tên Rubric',            'entry', {}),
            ('mo_ta',   'Mô tả ngắn',            'entry', {}),
        ]

    def _tc_fields(self):
        return [
            ('tieu_chi',     'Tên tiêu chí',          'entry', {}),
            ('trong_so',     'Trọng số (VD: 40%)',     'entry', {}),
            ('muc_xuat_sac', 'Mức Xuất sắc (9.0–10)', 'text',  {}),
            ('muc_tot',      'Mức Tốt (7.0–8.9)',      'text',  {}),
            ('muc_dat',      'Mức Đạt (5.0–6.9)',       'text',  {}),
            ('muc_chua_dat', 'Mức Chưa đạt (0–4.9)',   'text',  {}),
        ]

    def _rb_refresh(self):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not hasattr(self, 'rb_tree') or not self.rb_tree: return # FINAL GUARD
        self.rb_tree.delete(*self.rb_tree.get_children())
        for i, rb in enumerate(self._rubric_list):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.rb_tree.insert('', 'end', iid=str(i),
                                values=(rb.get('ky_hieu', ''), rb.get('ten', '')),
                                tags=(tag,))

    def _tc_refresh(self):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not hasattr(self, 'tc_tree') or not self.tc_tree: return # FINAL GUARD
        self.tc_tree.delete(*self.tc_tree.get_children())
        if self._sel_rubric_idx is None: return
        tcs = self._rubric_list[self._sel_rubric_idx].get('tieu_chi_list', [])
        for i, tc in enumerate(tcs):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tc_tree.insert('', 'end', iid=str(i),
                                values=(tc.get('tieu_chi', ''), tc.get('trong_so', ''),
                                        tc.get('muc_xuat_sac', ''), tc.get('muc_tot', ''),
                                        tc.get('muc_dat', ''), tc.get('muc_chua_dat', '')),
                                tags=(tag,))

    def _on_rubric_select(self):
        sel = self.rb_tree.selection()
        if sel:
            try:
                self._sel_rubric_idx = int(sel[0])
                self._tc_refresh()
            except (ValueError, IndexError):
                self._sel_rubric_idx = None

    def _rubric_add(self):
        dlg = RowEditDialog(self, 'Thêm Rubric', self._rubric_fields())
        if dlg.result:
            self._rubric_list.append({
                'ky_hieu': dlg.result.get('ky_hieu', ''),
                'ten':     dlg.result.get('ten', ''),
                'mo_ta':   dlg.result.get('mo_ta', ''),
                'thu_tu':  len(self._rubric_list) + 1,
                'tieu_chi_list': []
            })
            self._rb_refresh()
            self._refresh_summary()

    def _rubric_edit(self):
        sel = self.rb_tree.selection()
        if not sel: return
        try: idx = int(sel[0])
        except ValueError: return
        rb = self._rubric_list[idx]
        dlg = RowEditDialog(self, 'Sửa Rubric', self._rubric_fields(), initial=rb)
        if dlg.result:
            rb.update({k: dlg.result[k] for k in ('ky_hieu', 'ten', 'mo_ta') if k in dlg.result})
            self._rb_refresh()
            self._refresh_summary()

    def _rubric_delete(self):
        sel = self.rb_tree.selection()
        if not sel: return
        try: idx = int(sel[0])
        except ValueError: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa Rubric này và tất cả tiêu chí?'):
            self._rubric_list.pop(idx)
            self._sel_rubric_idx = None
            self._rb_refresh()
            self._tc_refresh()
            self._refresh_summary()

    def _tc_add(self):
        if self._sel_rubric_idx is None:
            show_modern_warning(self, 'Chưa chọn', 'Vui lòng chọn Rubric trước.')
            return
        dlg = RowEditDialog(self, 'Thêm tiêu chí', self._tc_fields())
        if dlg.result:
            tcs = self._rubric_list[self._sel_rubric_idx].setdefault('tieu_chi_list', [])
            tcs.append({**dlg.result, 'thu_tu': len(tcs) + 1})
            self._tc_refresh()
            self._refresh_summary()

    def _tc_edit(self):
        if self._sel_rubric_idx is None: return
        sel = self.tc_tree.selection()
        if not sel: return
        try: idx = int(sel[0])
        except ValueError: return
        tcs = self._rubric_list[self._sel_rubric_idx].get('tieu_chi_list', [])
        if idx >= len(tcs): return
        dlg = RowEditDialog(self, 'Sửa tiêu chí', self._tc_fields(), initial=tcs[idx])
        if dlg.result:
            tcs[idx].update(dlg.result)
            self._tc_refresh()
            self._refresh_summary()

    def _tc_delete(self):
        if self._sel_rubric_idx is None: return
        sel = self.tc_tree.selection()
        if not sel: return
        try: idx = int(sel[0])
        except ValueError: return
        tcs = self._rubric_list[self._sel_rubric_idx].get('tieu_chi_list', [])
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa tiêu chí này?'):
            tcs.pop(idx)
            self._tc_refresh()
            self._refresh_summary()

    def _tc_auto_fill(self):
        """Điền mẫu tiêu chí nhanh cho rubric đang chọn."""
        if self._sel_rubric_idx is None:
            show_modern_warning(self, 'Chưa chọn', 'Vui lòng chọn Rubric trước.')
            return
        rb = self._rubric_list[self._sel_rubric_idx]
        if rb.get('tieu_chi_list'):
            if not ask_modern_yesno(self, 'Xác nhận', 'Xóa tiêu chí hiện tại và điền mẫu?'):
                return
        rb['tieu_chi_list'] = [
            {'tieu_chi': 'Nội dung kiến thức', 'trong_so': '40%',
             'muc_xuat_sac': 'Đầy đủ, chính xác, có ví dụ minh họa',
             'muc_tot': 'Đúng các ý chính, thiếu ví dụ',
             'muc_dat': 'Đúng cơ bản, còn thiếu sót',
             'muc_chua_dat': 'Sai hoặc thiếu nghiêm trọng', 'thu_tu': 1},
            {'tieu_chi': 'Trình bày, lập luận', 'trong_so': '30%',
             'muc_xuat_sac': 'Logic, rõ ràng, thuật ngữ chính xác',
             'muc_tot': 'Rõ ràng nhưng chưa chặt chẽ',
             'muc_dat': 'Thiếu ý hoặc chưa rõ cấu trúc',
             'muc_chua_dat': 'Rời rạc, khó hiểu', 'thu_tu': 2},
            {'tieu_chi': 'Liên hệ thực tế / vận dụng', 'trong_so': '30%',
             'muc_xuat_sac': 'Liên hệ đúng, phù hợp, có sáng tạo',
             'muc_tot': 'Có liên hệ nhưng chưa sâu',
             'muc_dat': 'Liên hệ hạn chế',
             'muc_chua_dat': 'Không có hoặc sai', 'thu_tu': 3},
        ]
        self._tc_refresh()
        self._refresh_summary()
        show_modern_info(self, 'Hoàn thành', 'Đã điền 3 tiêu chí mẫu.')

    def _tc_copy_all(self):
        """Sao chép tất cả tiêu chí của rubric đang chọn vào clipboard."""
        if self._sel_rubric_idx is None:
            show_modern_warning(self, 'Chưa chọn', 'Vui lòng chọn Rubric trước.')
            return
        import copy
        tcs = self._rubric_list[self._sel_rubric_idx].get('tieu_chi_list', [])
        if not tcs:
            show_modern_warning(self, 'Rỗng', 'Rubric này chưa có tiêu chí nào.')
            return
        Sec8KiemTra._TC_CLIPBOARD = copy.deepcopy(tcs)
        rb_name = self._rubric_list[self._sel_rubric_idx].get('ten', '')
        Sec8KiemTra._TC_CLIPBOARD_SRC = rb_name
        
        # Bật nút Paste
        if hasattr(self, 'btn_tc_paste'):
            self.btn_tc_paste.config(state='normal')
            self.btn_tc_paste.config(
                text=f'📌 Paste TC ({len(tcs)} TC từ "{rb_name[:15]}")'
            )
        show_modern_info(
            self, 'Đã sao chép',
            f'Đã copy {len(tcs)} tiêu chí từ Rubric "{rb_name}" vào clipboard.'
        )

    def _tc_paste_all(self):
        """Dán tiêu chí từ clipboard vào rubric đang chọn."""
        if not Sec8KiemTra._TC_CLIPBOARD:
            show_modern_warning(self, 'Clipboard rỗng',
                                'Chưa copy tiêu chí nào. Dùng nút "Copy TC" trước.')
            return
        if self._sel_rubric_idx is None:
            show_modern_warning(self, 'Chưa chọn', 'Vui lòng chọn Rubric đích.')
            return
        rb_name = self._rubric_list[self._sel_rubric_idx].get('ten', '')
        n = len(Sec8KiemTra._TC_CLIPBOARD)
        src = Sec8KiemTra._TC_CLIPBOARD_SRC
        if not ask_modern_yesno(
            self, 'Xác nhận',
            f'Dán {n} tiêu chí từ "{src}" vào Rubric "{rb_name}"?\n'
            f'(Tiêu chí hiện tại của Rubric đích sẽ bị thay thế)'
        ):
            return
        import copy
        self._rubric_list[self._sel_rubric_idx]['tieu_chi_list'] = \
            copy.deepcopy(Sec8KiemTra._TC_CLIPBOARD)
        # Cập nhật thu_tu
        for i, tc in enumerate(self._rubric_list[self._sel_rubric_idx]['tieu_chi_list']):
            tc['thu_tu'] = i + 1
        self._tc_refresh()
        self._refresh_summary()
        show_modern_info(self, 'Hoàn thành',
                         f'Đã dán {n} tiêu chí vào Rubric "{rb_name}".')

    def _update_paste_btn_state(self):
        """Cập nhật trạng thái nút Paste dựa trên clipboard."""
        if not hasattr(self, 'btn_tc_paste'):
            return
        if Sec8KiemTra._TC_CLIPBOARD:
            n = len(Sec8KiemTra._TC_CLIPBOARD)
            src = Sec8KiemTra._TC_CLIPBOARD_SRC[:15]
            self.btn_tc_paste.config(
                state='normal',
                text=f'📌 Paste TC ({n} từ "{src}")'
            )
        else:
            self.btn_tc_paste.config(state='disabled', text='📌 Paste TC')

    # ─── Auto-fill ───────────────────────────────────────────────────────────
    def _auto_fill_nhiem_vu(self):
        if not self.hp_id: return
        hp = self.db.get_hoc_phan(self.hp_id)
        if not hp: return
        
        suggestion = get_suggested_nhiem_vu(hp.get('tinh_chat', 'Lý thuyết'))
        has_content = any(txt.get('1.0', 'end-1c').strip() for txt in self._task_vars.values())
        if has_content:
            if not ask_modern_yesno(self, 'Xác nhận', 'Nội dung nhiệm vụ hiện tại sẽ bị ghi đè. Tiếp tục?'):
                return
        
        for txt in self._task_vars.values():
            txt.delete('1.0', 'end')
        self._task_vars['nhiem_vu_sv_len_lop'].insert('1.0', suggestion)
        self._refresh_summary()
        show_modern_info(self, 'Hoàn thành', 'Đã điền nhiệm vụ mẫu.')

    def _auto_fill_assessment(self):
        if not self.hp_id: return
        hp = self.db.get_hoc_phan(self.hp_id)
        if not hp: return
        
        if self._kt_rows:
            if not ask_modern_yesno(self, 'Xác nhận', 'Bảng đánh giá hiện tại sẽ bị thay thế. Tiếp tục?'):
                return
        
        suggested = get_suggested_assessment(hp.get('tinh_chat', 'Lý thuyết'))
        new_rows = []
        for i, s in enumerate(suggested):
            new_rows.append({
                'nhom': s['nhom'],
                'thu_tu': i + 1,
                'noi_dung': s['nhom'],
                'hinh_thuc': s['hinh_thuc'],
                'thoi_gian': 'Theo KMH',
                'thang_diem': 10,
                'cap_do': '',
                'clo_lien_quan': '',
                'tieu_chi': '',
                'diem_toi_da_cdr': '',
                'trong_so_cdr': '',
                'ty_trong': s['ty_trong']
            })
        self._kt_rows = new_rows
        self._kt_refresh(self._kt_rows)
        self._refresh_summary()
        show_modern_info(self, 'Hoàn thành', 'Đã tạo ma trận đánh giá mẫu.')

    # ── Summary Methods ──────────────────────────────────────────────────────────
    def _toggle_summary(self):
        """Thu gọn/mở rộng summary panel."""
        self._summary_collapsed = not self._summary_collapsed
        if self._summary_collapsed:
            self.summary_body.pack_forget()
            self.lbl_summary_toggle.config(
                text='📊 Tổng quan đề cương  ▶ (click để mở)'
            )
        else:
            self.summary_body.pack(fill='x')
            self.lbl_summary_toggle.config(
                text='📊 Tổng quan đề cương  ▼ (click để thu gọn)'
            )

    def _refresh_summary(self):
        """Cập nhật nội dung summary panel từ data hiện tại."""
        if not hasattr(self, '_summary_labels'):
            return
        
        def _set(key, text, style='default'):
            lbl = self._summary_labels.get(key)
            if lbl:
                lbl.config(text=text, bootstyle=style)
        
        # CLO count — lấy từ DB
        clo_count = 0
        if self.hp_id:
            try:
                # Sử dụng get_clo thay vì get_clo_by_hp cho khớp db.py
                clo_count = len(self.db.get_clo(self.hp_id) or [])
            except Exception:
                pass
        _set('clo', f'{clo_count} CLO' + (' ✅' if clo_count >= 2 else ' ⚠'),
             'success' if clo_count >= 2 else 'warning')
        
        # Nội dung LT
        lt_count = 0
        if self.hp_id:
            try:
                # Sử dụng get_noi_dung(..., phan='lt') thay vì get_noi_dung_lt cho khớp db.py
                lt_count = len(self.db.get_noi_dung(self.hp_id, phan='lt') or [])
            except Exception:
                pass
        _set('lt', f'{lt_count} mục' + (' ✅' if lt_count > 0 else ' ⚠'),
             'success' if lt_count > 0 else 'warning')
        
        # Đánh giá
        tx = len([r for r in self._kt_rows if r.get('nhom') == 'thuong_xuyen'])
        ck = len([r for r in self._kt_rows if r.get('nhom') == 'cuoi_ky'])
        _set('danh_gia', f'TX: {tx}  |  CK: {ck}',
             'success' if (tx + ck) > 0 else 'warning')
        
        # Rubric
        rb_count = len(self._rubric_list)
        tc_count = sum(len(rb.get('tieu_chi_list', [])) for rb in self._rubric_list)
        _set('rubric', f'{rb_count} Rubric, {tc_count} tiêu chí',
             'success' if rb_count > 0 else 'warning')
        
        # Tổng trọng số
        try:
            tx_pct = float(self.v_tx_pct.get() or 0)
            ck_pct = float(self.v_ck_pct.get() or 0)
            total = tx_pct + ck_pct
            ok = abs(total - 100) < 0.1
            _set('trong_so', f'TX {tx_pct:.0f}% + CK {ck_pct:.0f}% = {total:.0f}%',
                 'success' if ok else 'danger')
        except ValueError:
            _set('trong_so', 'Chưa điền', 'warning')
        
        # Cảnh báo tổng hợp
        warnings = []
        if clo_count == 0:
            warnings.append('Chưa có CLO')
        if not self._kt_rows:
            warnings.append('Chưa có bài ĐG')
        if rb_count == 0:
            warnings.append('Chưa có Rubric')
        try:
            total_w = float(self.v_tx_pct.get() or 0) + float(self.v_ck_pct.get() or 0)
            if abs(total_w - 100) > 0.1:
                warnings.append('Trọng số ≠ 100%')
        except ValueError:
            pass
        
        if warnings:
            _set('canh_bao', ' | '.join(warnings), 'danger')
        else:
            _set('canh_bao', 'Không có ⭐', 'success')

    def _after_load_summary(self):
        """Gọi sau load() để cập nhật summary."""
        self.after(100, self._refresh_summary)  # delay nhỏ để UI render xong
