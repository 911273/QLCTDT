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
        lf2 = tb.Labelframe(p, text='8.2. Kế hoạch kiểm tra', padding=10)
        lf2.pack(fill='both', expand=True, padx=16, pady=(0, 8))

        lbl2_frm = tb.Frame(lf2)
        lbl2_frm.pack(fill='x', pady=(0, 4))
        tb.Label(lbl2_frm, text='8.2. Phương pháp, hình thức kiểm tra - đánh giá học phần',
                  font=('Arial', 10)).pack(side='left')
        tb.Button(lbl2_frm, text='🪄 Điền ma trận mẫu', bootstyle='outline-info', 
                   command=self._auto_fill_assessment, padding=2).pack(side='right')

        cols   = ('nhom', 'thu_tu', 'noi_dung', 'hinh_thuc',
                  'thoi_gian', 'thang_diem', 'cap_do', 'ty_trong')
        heads  = ('Nhóm', 'TT', 'Nội dung', 'Hình thức',
                  'Thời gian', 'Thang điểm', 'Mức độ đáp ứng CDR', 'Tỷ trọng')
        widths = (80, 40, 180, 90, 80, 80, 160, 70)
        aligns = ('center', 'center', 'w', 'center', 'center', 'center', 'w', 'center')
        self.kt_frm, self.kt_tree = make_tree(lf2, cols, heads, widths, height=10, column_aligns=aligns, db=self.db, table_id='sec8_kiem_tra')
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
        # Using self.v_tx_pct from __init__
        tb.Entry(lf2, textvariable=self.v_tx_pct, width=8,
                  font=('Arial', 10)).pack(anchor='w')

        tb.Label(lf2, text='Tỷ trọng thi cuối kỳ (%):', font=('Arial', 10)
                  ).pack(anchor='w', pady=(4, 0))
        # Using self.v_ck_pct from __init__
        tb.Entry(lf2, textvariable=self.v_ck_pct, width=8,
                  font=('Arial', 10)).pack(anchor='w')

    def _kt_fields(self, nhom):
        return [
            ('noi_dung',   'Nội dung',                     'text',  {}),
            ('hinh_thuc',  'Hình thức',                    'entry', {}),
            ('thoi_gian',  'Thời gian',                    'entry', {}),
            ('thang_diem', 'Thang điểm',                   'entry', {}),
            ('cap_do',     'Mức độ đáp ứng CDR học phần',  'entry', {}),
            ('ty_trong',   'Tỷ trọng (%)',                 'entry', {}),
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
                                                r.get('thu_tu', ''),
                                                r.get('noi_dung', ''),
                                                r.get('hinh_thuc', ''),
                                                r.get('thoi_gian', ''),
                                                r.get('thang_diem', ''),
                                                r.get('cap_do', ''),
                                                r.get('ty_trong', '')),
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
        self._kt_rows = [{'nhom': r['nhom'], 'thy_trong_nhom': r['ty_trong_nhom'],
                           'thu_tu': r['thu_tu'], 'noi_dung': r['noi_dung'],
                           'hinh_thuc': r['hinh_thuc'], 'thoi_gian': r['thoi_gian'],
                           'thang_diem': r['thang_diem'],
                           'cap_do': r['cap_do_dap_ung'],
                           'clo_lien_quan': r['clo_lien_quan'],
                           'ty_trong': r['ty_trong']} for r in rows]
        self._kt_refresh(self._kt_rows)

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
                              'ty_trong': r.get('ty_trong', '')})
        return {**task_data, 'rows': items}

    def clear(self):
        super().clear()
        for txt in self._task_vars.values():
            txt.delete('1.0', 'end')
        self.kt_tree.delete(*self.kt_tree.get_children())
        self._kt_rows = []

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
                'ty_trong': s['ty_trong']
            })
        self._kt_rows = new_rows
        self._kt_refresh(self._kt_rows)
        show_modern_info(self, 'Hoàn thành', 'Đã tạo ma trận đánh giá mẫu.')
