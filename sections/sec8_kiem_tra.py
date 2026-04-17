# sections/sec8_kiem_tra.py — Phương pháp, hình thức kiểm tra – đánh giá kết quả
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, ScrollableFrame, RowEditDialog,
                                    make_tree, CLR_PRIMARY2, CLR_HDR)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
from utils.auto_fill import get_suggested_nhiem_vu, get_suggested_assessment


class Sec8KiemTra(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._kt_rows = []
        self._rubric_list = []     # [{'ten','ky_hieu','mo_ta','thu_tu','tieu_chi_list':[...]}]
        self._sel_rubric_idx = None
        self._task_vars = {}
        self.v_tx_pct = tk.StringVar(value='30')
        self.v_ck_pct = tk.StringVar(value='70')
        
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

        tb.Label(lf2, text='Tỷ trọng KT thường xuyên (%):', font=('Arial', 10)
                  ).pack(anchor='w', pady=(8, 0))
        tb.Entry(lf2, textvariable=self.v_tx_pct, width=8,
                  font=('Arial', 10)).pack(anchor='w')

        tb.Label(lf2, text='Tỷ trọng thi cuối kỳ (%):', font=('Arial', 10)
                  ).pack(anchor='w', pady=(4, 0))
        tb.Entry(lf2, textvariable=self.v_ck_pct, width=8,
                  font=('Arial', 10)).pack(anchor='w')

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

    # ─── Kế hoạch KT ─────────────────────────────────────────────────────────
    def _kt_fields(self, nhom):
        return [
            ('noi_dung',          'Bài đánh giá',                    'text',  {}),
            ('hinh_thuc',         'Hình thức đánh giá',              'entry', {}),
            ('tieu_chi',          'Tiêu chí đánh giá (mã Rubric)',   'entry', {}),
            ('clo_lien_quan',     'CĐR được đánh giá',               'entry', {}),
            ('diem_toi_da_cdr',   'Điểm tối đa của CĐR',            'entry', {}),
            ('trong_so_cdr',      'Trọng số đánh giá theo CĐR (%)', 'entry', {}),
            ('thoi_gian',         'Thời gian',                       'entry', {}),
            ('thang_diem',        'Thang điểm',                      'entry', {}),
            ('cap_do',            'Mức độ đáp ứng CDR học phần',     'entry', {}),
            ('ty_trong',          'Tỷ trọng (%)',                    'entry', {}),
        ]

    def _kt_refresh(self, rows):
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
                                                r.get('clo_lien_quan', ''),
                                                r.get('diem_toi_da_cdr', ''),
                                                r.get('trong_so_cdr', '')),
                                        tags=(tag,))
        self._kt_rows = rows

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

    def save(self):
        if self.hp_id is not None:
            self.controller.save_current_hp(self.hp_id, None, {'sec8': self.get_data_dict()})

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
        if not hasattr(self, 'rb_tree'): return
        self.rb_tree.delete(*self.rb_tree.get_children())
        for i, rb in enumerate(self._rubric_list):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.rb_tree.insert('', 'end', iid=str(i),
                                values=(rb.get('ky_hieu', ''), rb.get('ten', '')),
                                tags=(tag,))

    def _tc_refresh(self):
        if not hasattr(self, 'tc_tree'): return
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

    def _tc_add(self):
        if self._sel_rubric_idx is None:
            show_modern_warning(self, 'Chưa chọn', 'Vui lòng chọn Rubric trước.')
            return
        dlg = RowEditDialog(self, 'Thêm tiêu chí', self._tc_fields())
        if dlg.result:
            tcs = self._rubric_list[self._sel_rubric_idx].setdefault('tieu_chi_list', [])
            tcs.append({**dlg.result, 'thu_tu': len(tcs) + 1})
            self._tc_refresh()

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
        show_modern_info(self, 'Hoàn thành', 'Đã điền 3 tiêu chí mẫu.')

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
        show_modern_info(self, 'Hoàn thành', 'Đã tạo ma trận đánh giá mẫu.')
