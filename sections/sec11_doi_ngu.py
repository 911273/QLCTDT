# sections/sec11_doi_ngu.py — Đội ngũ giảng viên giảng dạy và hướng dẫn học phần
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    CLR_PRIMARY2, CLR_HDR)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)

from sections.registry import register_section


@register_section(order=11, label="11. Đội ngũ GV")
class Sec11DoiNgu(BaseSection):
    """Mục 11: Đội ngũ giảng viên giảng dạy và hướng dẫn học phần."""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._rows = []
        self.tree = None # FIXED: Initialize for safety
        
        # Undo/Redo
        self._undo_stack = []
        self._redo_stack = []
        self.bind_all('<Control-z>', lambda e: self._undo())
        self.bind_all('<Control-y>', lambda e: self._redo())

    def _save_undo(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        if len(self._undo_stack) > 20: self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        import copy
        self._redo_stack.append(copy.deepcopy(self._rows))
        self._rows = self._undo_stack.pop()
        self._refresh(self._rows)

    def _redo(self):
        if not self._redo_stack: return
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        self._rows = self._redo_stack.pop()
        self._refresh(self._rows)

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='11. Đội ngũ giảng viên giảng dạy và hướng dẫn học phần',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        frm = tb.Frame(self, padding=(16, 4, 16, 16))
        frm.pack(fill='both', expand=True)

        # Toolbar
        toolbar = tb.Frame(frm, padding=5)
        toolbar.pack(fill='x')
        
        tb.Button(toolbar, text='➕ Thêm mới GV',  command=self._add, bootstyle='success-outline').pack(side='left', padx=2)
        tb.Button(toolbar, text='👥 Chọn từ Danh sách', command=self._pick, bootstyle='primary-outline').pack(side='left', padx=2)
        tb.Separator(toolbar, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Button(toolbar, text='✏ Sửa',       command=self._edit).pack(side='left', padx=2)
        tb.Button(toolbar, text='🗑 Xóa',       command=self._delete).pack(side='left', padx=2)
        tb.Separator(toolbar, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Button(toolbar, text='⬆ Lên',       command=lambda: self._move(-1)).pack(side='left', padx=2)
        tb.Button(toolbar, text='⬇ Xuống',     command=lambda: self._move(1)).pack(side='left', padx=2)

        # Treeview
        cols   = ('stt', 'ma_can_bo', 'vai_tro', 'ho_ten', 'chuc_vu', 'don_vi', 'sdt', 'email')
        heads  = ('TT', 'Mã CB', 'Vai trò', 'Học hàm/vị, Họ tên', 'Chức vụ', 'Đơn vị', 'Số ĐT', 'Email')
        widths = (40, 80, 120, 220, 120, 150, 100, 150)
        aligns = ('center', 'center', 'w', 'w', 'w', 'w', 'center', 'center')
        
        tf, self.tree = make_tree(frm, cols, heads, widths, height=15, column_aligns=aligns, db=self.db, table_id='sec11_gv')
        tf.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda _e: self._edit())

    def load(self, hp_id):
        super().load(hp_id)
        rows = self.db.conn.execute(
            "SELECT * FROM hp_giang_vien WHERE hp_id=? ORDER BY thu_tu", (hp_id,)
        ).fetchall()
        self._rows = [dict(r) for r in rows]
        self._refresh(self._rows)
        self._loading = False

    def save(self):
        if self.hp_id is not None:
            # Synced via controller or directly
            self.db.update_hp_giang_vien(self.hp_id, self._rows)

    def get_data_dict(self):
        return {'rows': self._rows}

    def _refresh(self, rows):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not hasattr(self, 'tree') or not self.tree: return # FINAL GUARD
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            vt = 'Chính' if r.get('vai_tro') == 'phu_trach' else 'Tham gia'
            self.tree.insert('', 'end', iid=str(i),
                             values=(i+1, r.get('ma_can_bo', '') or '', vt, 
                                     f"{r.get('hoc_ham_vi','') or ''} {r.get('ho_ten','') or ''}".strip(),
                                     r.get('chuc_vu',''), r.get('don_vi',''), r.get('sdt',''), r.get('email','')),
                             tags=(tag,))

    def _fields(self):
        return [
            ('vai_tro',    'Vai trò',      'combo', {'values': ['Giảng viên phụ trách', 'Giảng viên tham gia']}),
            ('ma_can_bo',  'Mã cán bộ',    'entry', {}),
            ('ho_ten',     'Họ và tên',    'entry', {}),
            ('gioi_tinh',  'Giới tính',    'combo', {'values': ['Nam', 'Nữ', 'Khác']}),
            ('hoc_ham_vi', 'Học hàm/vị',   'entry', {}),
            ('chuc_vu',    'Chức vụ',      'entry', {}),
            ('don_vi',     'Đơn vị',       'entry', {}),
            ('sdt',        'Số ĐT',        'entry', {}),
            ('email',      'Email',        'entry', {}),
            ('dia_chi',    'Địa chỉ',      'entry', {}),
        ]

    def _add(self):
        dlg = RowEditDialog(self, 'Thêm giảng viên', self._fields())
        if dlg.result:
            self._save_undo()
            row = dlg.result
            row['vai_tro'] = 'phu_trach' if row['vai_tro'] == 'Giảng viên phụ trách' else 'tham_gia'
            self._rows.append(row)
            self._refresh(self._rows)
            self.mark_modified()

    def _edit(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        curr = self._rows[idx].copy()
        curr['vai_tro'] = 'Giảng viên phụ trách' if curr.get('vai_tro') == 'phu_trach' else 'Giảng viên tham gia'
        
        dlg = RowEditDialog(self, 'Sửa giảng viên', self._fields(), initial=curr)
        if dlg.result:
            self._save_undo()
            row = dlg.result
            row['vai_tro'] = 'phu_trach' if row['vai_tro'] == 'Giảng viên phụ trách' else 'tham_gia'
            self._rows[idx].update(row)
            self._refresh(self._rows)
            self.mark_modified()

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa giảng viên này khỏi học phần?'):
            self._save_undo()
            self._rows.pop(int(sel[0]))
            self._refresh(self._rows)
            self.mark_modified()

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self._rows):
            self._save_undo()
            self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
            self._refresh(self._rows)
            self.tree.selection_set(str(new_idx))
            self.mark_modified()

    def _pick(self):
        """Hộp thoại chọn giảng viên từ danh sách toàn trường."""
        all_gvs = self.db.get_all_giang_vien()
        if not all_gvs:
            show_modern_info(self, 'Thông báo', 'Chưa có giảng viên nào trong pool.\nThêm GV qua menu Dữ liệu Chung > Giảng viên.')
            return
        dlg = _GvPickDialog(self, all_gvs)
        if dlg.result:
            self._save_undo()
            for gv_raw in dlg.result:
                gv = dict(gv_raw) if not isinstance(gv_raw, dict) else gv_raw
                # Check if already added
                if any(r.get('gv_id') == gv.get('id') for r in self._rows):
                    continue
                
                self._rows.append({
                    'hp_id': self.hp_id,
                    'gv_id': gv.get('id'),
                    'ho_ten': gv.get('ho_ten', ''),
                    'hoc_ham_vi': gv.get('hoc_vi') or '',
                    'don_vi': gv.get('don_vi') or '',
                    'email': gv.get('email') or '',
                    'sdt': gv.get('sdt') or '',
                    'ma_can_bo': gv.get('ma_can_bo') or '',
                    'gioi_tinh': gv.get('gioi_tinh') or '',
                    'chuc_vu': gv.get('chuc_vu') or '',
                    'dia_chi': gv.get('dia_chi') or '',
                    'vai_tro': dlg.vai_tro
                })
            self._refresh(self._rows)
            self.mark_modified()

class _GvPickDialog(tb.Toplevel):
    def __init__(self, parent, gv_list):
        super().__init__(parent)
        self.db = parent.db
        self.title('Chọn giảng viên từ danh sách')
        self.geometry('1000x700')
        self.resizable(True, True)
        self.result = None
        self.vai_tro = 'tham_gia'
        self.grab_set()

        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        tb.Label(frm, text='Tìm kiếm:', font=('Arial', 10)).pack(anchor='w')
        self.v_search = tk.StringVar()
        self.v_search.trace_add('write', lambda *_: self._filter())
        tb.Entry(frm, textvariable=self.v_search, width=50,
                  font=('Arial', 10)).pack(fill='x', pady=4)

        from sections.base_section import make_tree
        cols = ('ma_can_bo', 'ho_ten', 'hoc_vi', 'sdt', 'email')
        heads = ('Mã CB', 'Họ và tên', 'Học vị', 'SĐT', 'Email')
        widths = (80, 200, 80, 100, 200)
        tf, self.tree = make_tree(frm, cols, heads, widths, height=15, db=self.db, table_id='sec11_gv_pick')
        self.tree.configure(selectmode='extended')
        tf.pack(fill='both', expand=True)

        self._all = gv_list
        self._refresh(gv_list)

        tb.Label(frm, text='Vai trò:', font=('Arial', 10)).pack(anchor='w', pady=(8, 2))
        self.v_vaitro = tk.StringVar(value='Giảng viên tham gia giảng dạy')
        tb.Combobox(frm, textvariable=self.v_vaitro,
                     values=['Giảng viên phụ trách chính', 'Giảng viên tham gia giảng dạy'],
                     width=40, state='readonly').pack(anchor='w')

        bf = tb.Frame(self, padding=(12, 4, 12, 12))
        bf.pack(fill='x')
        tb.Button(bf, text='✔ Chọn', command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='✘ Hủy',  command=self.destroy).pack(side='right', padx=4)
        self.transient(parent)
        self.wait_window()

    def _refresh(self, gvs):
        self.tree.delete(*self.tree.get_children())
        self._shown = gvs
        for i, g in enumerate(gvs):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                             values=(g.get('ma_can_bo','') or '', g.get('ho_ten',''), g.get('hoc_vi') or '', g.get('sdt') or '',
                                     g.get('email') or ''), tags=(tag,))

    def _filter(self):
        kw = self.v_search.get().lower()
        filtered = [g for g in self._all
                    if kw in (g.get('ho_ten', '') or '').lower()
                    or kw in (g.get('email', '') or '').lower()]
        self._refresh(filtered)

    def _ok(self):
        sel = self.tree.selection()
        if not sel:
            show_modern_warning(self, 'Cảnh báo', 'Chưa chọn giảng viên.')
            return
        
        selected_data = []
        for iid in sel:
            idx = int(iid)
            selected_data.append(self._shown[idx])
            
        self.result = selected_data
        vrl = self.v_vaitro.get()
        self.vai_tro = 'phu_trach' if 'chính' in vrl else 'tham_gia'
        self.destroy()
