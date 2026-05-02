import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree, CLR_PRIMARY2,
                                    CLR_HDR, CLR_ROW1, CLR_ROW2, CLR_PRIMARY,
                                    CLR_ACCENT, CLR_BORDER)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)


from sections.registry import register_section


@register_section(order=6, label="6. Nội dung chi tiết")
class Sec6NoiDung(BaseSection):
    """Nội dung chi tiết với cấu trúc cây (2-4 cấp tùy biến)."""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._lt_tab = None
        self._th_tab = None
        self.tree = None # FIXED: Initialize for safety
        self.clo_list = []

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='6. Nội dung chi tiết học phần',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        nb = tb.Notebook(self)
        nb.pack(fill='both', expand=True, padx=16, pady=4)
        self._nb = nb

        self._lt_tab = _NoiDungTab(nb, 'lt', self.db, sec_parent=self)
        nb.add(self._lt_tab, text='6.1 Phần Lý thuyết')

        self._th_tab = _NoiDungTab(nb, 'th', self.db, sec_parent=self)
        nb.add(self._th_tab, text='6.2 Phần Thực hành')

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        if hp and not hp.get('co_thuc_hanh', 1):
            self._nb.tab(1, state='disabled')
        else:
            self._nb.tab(1, state='normal')

        rows_lt = self.db.get_noi_dung(hp_id, 'lt')
        rows_th = self.db.get_noi_dung(hp_id, 'th')
        
        # Lấy danh sách CLO cho picker (chỉ lấy CLO thực, bỏ qua tiêu đề nhóm)
        clos = self.db.get_clo(hp_id)
        self.clo_list = [r['ma'] for r in clos if not r['la_tieu_de_nhom'] and r['ma']]
        
        is_phd = hp and hp.get('nhom_hp_dac_thu') == 'Chuyên đề Tiến sĩ'
        self._lt_tab.set_phd_mode(is_phd)
        self._th_tab.set_phd_mode(is_phd)
        
        self._lt_tab.load_rows([dict(r) for r in rows_lt])
        self._th_tab.load_rows([dict(r) for r in rows_th])

    def save(self):
        if self.hp_id is None:
            return
        data = self.get_data_dict()
        self.db.delete_noi_dung_hp(self.hp_id, 'lt')
        self.db.delete_noi_dung_hp(self.hp_id, 'th')
        for row in data['lt_rows']:
            row['hp_id'] = self.hp_id
            row['phan'] = 'lt'
            self.db.add_noi_dung(row)
        for row in data['th_rows']:
            row['hp_id'] = self.hp_id
            row['phan'] = 'th'
            self.db.add_noi_dung(row)
            
        # Tự động đồng bộ ngược lại Mục 1
        self.db.calculate_and_update_hours(self.hp_id)

    def get_data_dict(self):
        self.ensure_ui()
        return {
            'lt_rows': self._lt_tab.get_flat_rows() if self._lt_tab else [],
            'th_rows': self._th_tab.get_flat_rows() if self._th_tab else []
        }

    def clear(self):
        super().clear()
        self._lt_tab.load_rows([])
        self._th_tab.load_rows([])

    def update_theme(self):
        self._lt_tab.update_theme()
        self._th_tab.update_theme()


# ─────────────────────────────────────────────────────────────────────────────
class _NoiDungTab(tb.Frame):
    """Một tab nội dung (Lý thuyết hoặc Thực hành) với cây phân cấp."""

    LT_COLS  = ('ten', 'gio_len_lop', 'nhiem_vu_ncs', 'pp_day', 'pp_hoc', 'cdr_ma', 'bai_danh_gia')
    LT_HEADS = ('Nội dung / Task', 'Giờ (L/B/T/T)', 'Nhiệm vụ cho NCS (*TS)', 'Hoạt động dạy & PP', 'Hoạt động học', 'CĐR HP', 'Bài ĐG')
    LT_WIDTHS= (250, 90, 160, 140, 140, 80, 80)

    TH_COLS  = ('ten', 'gio_len_lop', 'nhiem_vu_ncs', 'pp_day', 'pp_hoc', 'cdr_ma', 'bai_danh_gia')
    TH_HEADS = ('Nội dung thực hành', 'Giờ (T/B/T/K)', 'Nhiệm vụ cho NCS (*TS)', 'Hoạt động dạy & PP', 'Hoạt động học', 'CĐR HP', 'Bài ĐG')
    TH_WIDTHS= (250, 90, 160, 140, 140, 80, 80)

    def __init__(self, parent, phan, db, sec_parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.phan = phan
        self.db = db
        self.sec_parent = sec_parent
        
        cols   = self.LT_COLS   if phan == 'lt' else self.TH_COLS
        heads  = self.LT_HEADS  if phan == 'lt' else self.TH_HEADS
        widths = self.LT_WIDTHS if phan == 'lt' else self.TH_WIDTHS
        self._flat = []   # list of dicts (flat, with temp_id for tree building)
        self.is_phd = False

        # ── Treeview ─────────────────────────────────────────────────────────
        tree_frm = tb.Frame(self)
        tree_frm.pack(fill='both', expand=True)

        tf, self.tree = make_tree(tree_frm, cols, heads, widths, height=18, db=self.db, table_id=f'sec6_{phan}')
        tf.pack(fill='both', expand=True)
        
        # First col = tree column (hierarchical indent)
        self.tree.column('#0', width=20, minwidth=20, stretch=True)
        self.tree.heading('#0', text='')
        
        # Cấu hình lại lề cho các cột đặc thù (Nội dung và Yêu cầu)
        for i, col in enumerate(cols):
            if i in (0, 6): # 'Nội dung' and 'Yêu cầu SV chuẩn bị'
                self.tree.heading(col, anchor='w')
                self.tree.column(col, anchor='w')

        # Tags are now globally defined in MyTree.Treeview, but we can override if needed
        self.tree.tag_configure('test', foreground=CLR_ACCENT, font=('Arial', 10, 'bold', 'italic'))
        self.tree.tag_configure('total', background=CLR_PRIMARY, foreground='white', font=('Arial', 10, 'bold'))
        self.tree.bind('<Double-1>', lambda _e: self._edit())
        
        # Undo/Redo
        self._undo_stack = []
        self._redo_stack = []
        self.bind_all('<Control-z>', lambda e: self._undo())
        self.bind_all('<Control-y>', lambda e: self._redo())
        
        # Drag and Drop bindings
        self.tree.bind('<ButtonPress-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_drop)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar_frm = tb.Frame(self)
        toolbar_frm.pack(fill='x', pady=(4, 0))

        tb.Button(toolbar_frm, text='➕ Thêm mục cấp 1',
                   command=lambda: self._add(1, None)).pack(side='left', padx=2)
        tb.Button(toolbar_frm, text='➕ Thêm mục con',
                   command=self._add_child).pack(side='left', padx=2)
        
        if self.phan == 'lt':
            tb.Button(toolbar_frm, text='📝 Thêm Bài kiểm tra',
                       command=self._add_test).pack(side='left', padx=2)
        tb.Button(toolbar_frm, text='✏ Sửa',
                   command=self._edit).pack(side='left', padx=2)
        tb.Button(toolbar_frm, text='🗑 Xóa + con',
                   command=self._delete).pack(side='left', padx=2)
        tb.Button(toolbar_frm, text='⬆ Lên',
                   command=lambda: self._move(-1)).pack(side='left', padx=2)
        tb.Button(toolbar_frm, text='⬇ Xuống',
                   command=lambda: self._move(1)).pack(side='left', padx=2)
        
        tb.Separator(toolbar_frm, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Button(toolbar_frm, text='📥 Nhập từ Excel', style='Accent.TButton',
                   command=self._import_excel).pack(side='left', padx=2)
        tb.Separator(toolbar_frm, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Label(toolbar_frm, text='Tổng chi tiết:', font=('Arial', 10, 'bold')).pack(side='left')
        self.lbl_total = tb.Label(toolbar_frm, text='LT:0 BT:0', font=('Arial', 10))
        self.lbl_total.pack(side='left', padx=4)
        
        self.lbl_diff = tb.Label(toolbar_frm, text='', font=('Arial', 10, 'italic'))
        self.lbl_diff.pack(side='left', padx=20)
        
    def set_phd_mode(self, is_phd):
        self.is_phd = is_phd
        if is_phd:
            cols = ('ten', 'nhiem_vu_ncs', 'pp_day', 'pp_hoc', 'cdr_ma', 'bai_danh_gia')
            self.lbl_total.config(text="")
        else:
            cols = ('ten', 'gio_len_lop', 'pp_day', 'pp_hoc', 'cdr_ma', 'bai_danh_gia')
        self.tree['displaycolumns'] = cols

    def update_theme(self):
        pass # rely on base_section.setup_treeview_style() if global

    def _save_undo(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self._flat))
        if len(self._undo_stack) > 20: self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        import copy
        self._redo_stack.append(copy.deepcopy(self._flat))
        self._flat = self._undo_stack.pop()
        self._rebuild_tree()
        self.sec_parent.mark_modified()

    def _redo(self):
        if not self._redo_stack: return
        import copy
        self._undo_stack.append(copy.deepcopy(self._flat))
        self._flat = self._redo_stack.pop()
        self._rebuild_tree()
        self.sec_parent.mark_modified()

    # ── Data helpers ──────────────────────────────────────────────────────────
    def _tmp_id(self, row):
        return row.get('_tid', id(row))

    def load_rows(self, db_rows):
        self._flat = [dict(r) for r in db_rows]
        # Xây dựng map ID -> TID và Parent map để tăng tốc O(N)
        id_to_tid = {r['id']: (r.get('_tid') or self._tmp_id(r)) for r in self._flat}
        for r in self._flat:
            r['_tid'] = id_to_tid[r['id']]
            r['_parent_tid'] = id_to_tid.get(r.get('parent_id')) if r.get('parent_id') else None
        
        self._rebuild_tree()

    def get_data_dict(self):
        self.ensure_ui()
        return {'flat': self._flat}

    def apply_data_dict(self, data):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if data and 'flat' in data:
            self._flat = data['flat']
            self._rebuild_tree()

    def get_flat_rows(self):
        """Trả về rows theo thứ tự DFS (để insert lại vào DB)."""
        def _dfs(parent_tid, order_start):
            result = []
            children = [r for r in self._flat if r.get('_parent_tid') == parent_tid]
            children.sort(key=lambda r: r.get('thu_tu', 0))
            for i, c in enumerate(children):
                c['thu_tu'] = order_start + i
                cleaned = {k: v for k, v in c.items() if not k.startswith('_')}
                cleaned.pop('id', None)
                cleaned.pop('hp_id', None)
                cleaned.pop('phan', None)
                cleaned.pop('parent_id', None)
                # Re-attach parent via temp id (will be resolved after first insert)
                result.append(cleaned)
                result.extend(_dfs(c['_tid'], 10))
            return result
        # Flatten ignoring hierarchy (simple flat export for DB re-build)
        result = []
        visited = set()
        def dfs2(parent_tid, depth):
            children = [r for r in self._flat if r.get('_parent_tid') == parent_tid]
            children.sort(key=lambda r: r.get('thu_tu', 0))
            for c in children:
                tid = c['_tid']
                if tid in visited:
                    continue
                visited.add(tid)
                cleaned = {k: v for k, v in c.items()
                           if not k.startswith('_') and k not in ('id', 'hp_id', 'phan')}
                cleaned.pop('parent_id', None)
                cleaned['cap_do'] = depth
                result.append(cleaned)
                dfs2(tid, depth + 1)
        dfs2(None, 1)
        return result

    def _rebuild_tree(self):
        if not hasattr(self, 'tree') or not self.tree: return # FINAL GUARD
        self.tree.delete(*self.tree.get_children())
        
        # Tiền tính toán children (O(N))
        from collections import defaultdict
        children_map = defaultdict(list)
        for r in self._flat:
            children_map[r.get('_parent_tid')].append(r)

        def _insert_children(parent_tid, tree_parent):
            children = children_map.get(parent_tid, [])
            children.sort(key=lambda r: r.get('thu_tu', 0))
            for r in children:
                cap = r.get('cap_do', 1)
                if r.get('loai') == 'bai_kiem_tra':
                    tag = 'test'
                elif cap == 1:
                    tag = 'subgroup'
                else:
                    tag = 'even' if len(self.tree.get_children()) % 2 == 0 else 'odd'
                
                vals = self._row_values(r)
                iid = str(r['_tid'])
                self.tree.insert(tree_parent, 'end', iid=iid,
                                  text='',
                                  values=vals,
                                  tags=(tag,), open=True)
                _insert_children(r['_tid'], iid)

        _insert_children(None, '')
        
        # Thêm hàng Tổng
        totals = self._update_totals()
        if self.phan == 'lt':
            gio_str = f"({totals.get('gio_lt'):g}/{totals.get('gio_bt'):g}/{totals.get('gio_tl'):g}/{totals.get('gio_th_tn'):g})"
            vals = ('TỔNG CỘNG', gio_str, '', '', '', '')
        else:
            gio_str = f"({totals.get('gio_th'):g}/{totals.get('gio_bt'):g}/{totals.get('gio_tl'):g}/{totals.get('gio_kt'):g})"
            vals = ('TỔNG CỘNG', gio_str, '', '', '', '')
        
        self.tree.insert('', 'end', iid='total_row', values=vals, tags=('total',))

    # ── Drag and Drop Logic ──────────────────────────────────────────────────
    def _on_drag_start(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid or iid == 'total_row':
            return
        self._drag_source_iid = iid

    def _on_drag_motion(self, event):
        # Có thể thêm hiệu ứng hover ở đây nếu cần
        pass

    def _on_drag_drop(self, event):
        if not hasattr(self, '_drag_source_iid'):
            return
        
        source_iid = self._drag_source_iid
        del self._drag_source_iid
        
        target_iid = self.tree.identify_row(event.y)
        if not target_iid or target_iid == 'total_row' or target_iid == source_iid:
            return

        bbox = self.tree.bbox(target_iid)
        if not bbox: return
        
        y_in_row = event.y - bbox[1]
        row_height = bbox[3]
        
        source_row = next((r for r in self._flat if str(r['_tid']) == source_iid), None)
        target_row = next((r for r in self._flat if str(r['_tid']) == target_iid), None)
        
        if not source_row or not target_row: return

        if self._is_descendant(source_iid, target_iid):
            show_modern_warning(self, 'Lỗi', 'Không thể di chuyển mục vào chính nó hoặc mục con của nó.')
            return
        
        self._save_undo()

        if y_in_row < row_height * 0.25: # Thả vào phía trên
            new_parent_tid = target_row.get('_parent_tid')
            self._move_item(source_row, new_parent_tid, target_row, 'before')
        elif y_in_row > row_height * 0.75: # Thả vào phía dưới
            new_parent_tid = target_row.get('_parent_tid')
            self._move_item(source_row, new_parent_tid, target_row, 'after')
        else: # Thả vào làm mục con
            if target_row.get('loai') == 'bai_kiem_tra':
                 new_parent_tid = target_row.get('_parent_tid')
                 self._move_item(source_row, new_parent_tid, target_row, 'after')
            else:
                self._move_item(source_row, target_row['_tid'], None, 'inside')

        self._rebuild_tree()

    def _is_descendant(self, parent_tid, child_tid):
        curr = next((r for r in self._flat if str(r['_tid']) == child_tid), None)
        while curr and curr.get('_parent_tid'):
            if str(curr['_parent_tid']) == str(parent_tid):
                return True
            curr = next((r for r in self._flat if str(r['_tid']) == str(curr['_parent_tid'])), None)
        return False

    def _update_cap_do(self, row, new_cap):
        row['cap_do'] = new_cap
        children = [r for r in self._flat if r.get('_parent_tid') == row['_tid']]
        for c in children:
            self._update_cap_do(c, new_cap + 1)

    def _move_item(self, source_row, new_parent_tid, target_row, position):
        source_row['_parent_tid'] = new_parent_tid
        if new_parent_tid is None:
            new_cap = 1
        else:
            p_row = next(r for r in self._flat if r['_tid'] == new_parent_tid)
            new_cap = p_row['cap_do'] + 1
        
        self._update_cap_do(source_row, new_cap)

        siblings = [r for r in self._flat if r.get('_parent_tid') == new_parent_tid and r['_tid'] != source_row['_tid']]
        siblings.sort(key=lambda r: r.get('thu_tu', 0))
        
        if position == 'before':
            idx = siblings.index(target_row)
            siblings.insert(idx, source_row)
        elif position == 'after':
            idx = siblings.index(target_row)
            siblings.insert(idx + 1, source_row)
        else: # inside
            siblings.append(source_row)
        
        for i, r in enumerate(siblings):
            r['thu_tu'] = (i + 1) * 10

    def _row_values(self, r):
        if self.phan == 'lt':
            indent = '  ' * max(0, r.get('cap_do', 1) - 1)
            gio_str = f"({r.get('gio_lt') or 0:g}/{r.get('gio_bt') or 0:g}/{r.get('gio_tl') or 0:g}/{r.get('gio_th_tn') or 0:g})"
            return (indent + (r.get('ten') or ''),
                    gio_str,
                    r.get('nhiem_vu_ncs') or '',
                    r.get('pp_day') or '', r.get('pp_hoc') or '',
                    r.get('cdr_ma') or '', r.get('bai_danh_gia') or '')
        else:
            indent = '  ' * max(0, r.get('cap_do', 1) - 1)
            gio_str = f"({r.get('gio_th') or 0:g}/{r.get('gio_bt') or 0:g}/{r.get('gio_tl') or 0:g}/{r.get('gio_kt') or 0:g})"
            return (indent + (r.get('ten') or ''),
                    gio_str,
                    r.get('nhiem_vu_ncs') or '',
                    r.get('pp_day') or '', r.get('pp_hoc') or '',
                    r.get('cdr_ma') or '', r.get('bai_danh_gia') or '')

    def _fmt_num(self, val):
        if val is None or val == 0: return ''
        return f'{val:g}'

    def _update_totals(self):
        top_level = [r for r in self._flat if r.get('_parent_tid') is None]
        totals = {}
        if self.phan == 'lt':
            keys = ('gio_lt', 'gio_bt', 'gio_tl', 'gio_th_tn', 'gio_tu_hoc')
            for k in keys:
                totals[k] = sum(float(r.get(k) or 0) for r in top_level)
            self.lbl_total.config(text=f"LT:{totals['gio_lt']:g} BT:{totals['gio_bt']:g} TL:{totals['gio_tl']:g} TH/TN:{totals['gio_th_tn']:g} Tự học:{totals['gio_tu_hoc']:g}")
        else:
            keys = ('gio_th', 'gio_bt', 'gio_tl', 'gio_kt', 'gio_tu_hoc')
            for k in keys:
                totals[k] = sum(float(r.get(k) or 0) for r in top_level)
            self.lbl_total.config(text=f"TH:{totals['gio_th']:g} BT:{totals['gio_bt']:g} TL:{totals['gio_tl']:g} KT:{totals['gio_kt']:g} Tự học:{totals['gio_tu_hoc']:g}")
        
        # Cross-check with Sec 1
        self._check_with_sec1(totals)
        return totals

    def _check_with_sec1(self, current_totals):
        try:
            # Truy cập Sec1 thông qua main (sec_parent -> main)
            main = self.sec_parent.winfo_toplevel()
            if hasattr(main, 'sec1'):
                sec1_data = main.sec1.get_time_allocation()
                mismatches = []
                
                check_map = {
                    'lt': [('gio_lt', 'Lý thuyết'), ('gio_bt', 'Bài tập'), ('gio_tl', 'Thảo luận'), ('gio_th_tn', 'TH/TN'), ('gio_tu_hoc', 'Tự học')],
                    'th': [('gio_th', 'Thực hành'), ('gio_bt', 'Bài tập'), ('gio_tl', 'Thảo luận'), ('gio_kt', 'Kiểm tra'), ('gio_tu_hoc', 'Tự học')]
                }
                
                for key, label in check_map[self.phan]:
                    s1_val = sec1_data.get(key, 0)
                    s6_val = current_totals.get(key, 0)
                    if abs(s1_val - s6_val) > 0.001:
                        mismatches.append(f"{label}: {s6_val:g}/{s1_val:g}")
                
                if mismatches:
                    self.lbl_diff.config(text="⚠ Sai lệch với Mục 1: " + ", ".join(mismatches), bootstyle='danger')
                else:
                    self.lbl_diff.config(text="✔ Khớp với Mục 1", bootstyle='success')
        except:
            pass

    def _get_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        iid = sel[0]
        if iid == 'total_row':
            return iid, None
        try:
            tid = int(iid)
        except ValueError:
            return iid, None
        for r in self._flat:
            if r['_tid'] == tid:
                return iid, r
        return iid, None

    def _make_fields(self, cap_do=1):
        core_fields = [
            ('ten',       'Tên nội dung',      'entry', {}),
            ('in_dam',    'In đậm (tiêu đề chương)', 'combo', {'values': ['Có', 'Không']}),
        ]
        if self.is_phd:
            hours_fields = [('gio_tu_hoc','Giờ Tự học/Nghiên cứu', 'entry', {})]
            phd_fields = [('nhiem_vu_ncs', 'Nhiệm vụ cụ thể cho NCS', 'text', {})]
        else:
            if self.phan == 'lt':
                hours_fields = [
                    ('gio_lt',    'Giờ Lý thuyết',      'entry', {}),
                    ('gio_bt',    'Giờ Bài tập',         'entry', {}),
                    ('gio_tl',    'Giờ Thảo luận (TL)',  'entry', {}),
                    ('gio_th_tn', 'Giờ TH/Thí nghiệm',  'entry', {}),
                    ('gio_tu_hoc','Giờ Tự học',          'entry', {}),
                ]
            else:
                hours_fields = [
                    ('gio_th',    'Giờ Thực hành',      'entry', {}),
                    ('gio_bt',    'Giờ Bài tập',         'entry', {}),
                    ('gio_tl',    'Giờ Thảo luận',       'entry', {}),
                    ('gio_kt',    'Giờ Kiểm tra',        'entry', {}),
                    ('gio_tu_hoc','Giờ Tự học',          'entry', {}),
                ]
            phd_fields = []

        tail_fields = [
            ('pp_day',    'Hoạt động dạy & PP','text',  {}),
            ('pp_hoc',    'Hoạt động học',     'text',  {}),
            ('cdr_ma',    'CDR đáp ứng',         'multi_picker', {'values': self.sec_parent.clo_list}),
            ('bai_danh_gia', 'Bài đánh giá (VD: KTGK)', 'entry', {}),
        ]
        return core_fields + hours_fields + phd_fields + tail_fields

    def _result_to_row(self, result, cap_do, parent_tid, thu_tu):
        in_dam = 1 if result.get('in_dam', 'Không') == 'Có' else 0
        loai = result.get('loai', 'thuong')
        row = {'_tid': id(result), '_parent_tid': parent_tid,
               'cap_do': cap_do, 'thu_tu': thu_tu, 'in_dam': in_dam,
               'loai': loai,
               'ten': result.get('ten', ''), 
               'pp_day': result.get('pp_day', ''), 
               'pp_hoc': result.get('pp_hoc', ''),
               'bai_danh_gia': result.get('bai_danh_gia', ''),
               'cdr_ma': result.get('cdr_ma', '')}
        for k in ('gio_lt', 'gio_bt', 'gio_tl', 'gio_th_tn', 'gio_tu_hoc',
                  'gio_th', 'gio_kt', 'gio_bt_th'):
            val = result.get(k, '')
            try:
                row[k] = float(val) if val else None
            except ValueError:
                row[k] = None
        row['nhiem_vu_ncs'] = result.get('nhiem_vu_ncs', '')
        return row

    def _add(self, cap_do, parent_tid):
        # Count siblings
        siblings = [r for r in self._flat if r.get('_parent_tid') == parent_tid]
        thu_tu = len(siblings) + 1
        fields = self._make_fields(cap_do)
        init = {'in_dam': 'Có' if cap_do == 1 else 'Không'}
        
        def _on_dlg_build(dlg):
            if self.phan == 'lt':
                def _suggest_tu_hoc():
                    try:
                        lt = float(dlg.entries['gio_lt'].get() or 0)
                        bt = float(dlg.entries['gio_bt'].get() or 0)
                        tl = float(dlg.entries['gio_tl'].get() or 0)
                        th = float(dlg.entries['gio_th_tn'].get() or 0)
                        suggested = lt * 2 + bt * 1 + tl * 1 + th * 1
                        dlg.entries['gio_tu_hoc'].delete(0, tk.END)
                        dlg.entries['gio_tu_hoc'].insert(0, f"{suggested:g}")
                    except: pass
                
                btn_suggest = tb.Button(dlg.btn_frame, text='💡 Gợi ý Tự học', 
                                        bootstyle='info-outline', command=_suggest_tu_hoc)
                btn_suggest.pack(side='left', padx=5)

        dlg = RowEditDialog(self.winfo_toplevel(), f'Thêm mục cấp {cap_do}', fields, 
                            initial=init, on_build=_on_dlg_build)

        if dlg.result:
            self._save_undo()
            row = self._result_to_row(dlg.result, cap_do, parent_tid, thu_tu)
            self._flat.append(row)
            self._rebuild_tree()
            self.sec_parent.mark_modified()

    def _add_child(self):
        iid, row = self._get_selected_row()
        if row is None:
            show_modern_warning(self, 'Cảnh báo', 'Chọn một mục để thêm mục con.')
            return
        if row.get('loai') == 'bai_kiem_tra':
            show_modern_warning(self, 'Cảnh báo', 'Không thể thêm mục con cho bài kiểm tra.')
            return
        parent_tid = row['_tid']
        child_cap  = row.get('cap_do', 1) + 1
        self._add(child_cap, parent_tid)

    def _add_test(self):
        # Always at level 1
        siblings = [r for r in self._flat if r.get('_parent_tid') is None]
        thu_tu = len(siblings) + 1
        fields = [
            ('ten',    'Tên bài kiểm tra', 'entry', {}),
            ('gio_lt', 'Số giờ (LT)',      'entry', {}),
            ('cdr_ma', 'CDR đáp ứng',      'multi_picker', {'values': self.sec_parent.clo_list}),
        ]
        init = {'ten': f'Bài kiểm tra số {thu_tu // 2 + 1}'} # Guessing number
        dlg = RowEditDialog(self.winfo_toplevel(), 'Thêm bài kiểm tra', fields, initial=init)
        if dlg.result:
            self._save_undo()
            row = self._result_to_row(dlg.result, 1, None, thu_tu)
            row['loai'] = 'bai_kiem_tra'
            row['in_dam'] = 1
            self._flat.append(row)
            self._rebuild_tree()
            self.sec_parent.mark_modified()

    def _edit(self):
        iid, row = self._get_selected_row()
        if row is None:
            return
        fields = self._make_fields(row.get('cap_do', 1))
        init = {**row, 'in_dam': 'Có' if row.get('in_dam') else 'Không'}
        for k in ('gio_lt', 'gio_bt', 'gio_tl', 'gio_th_tn', 'gio_tu_hoc',
                  'gio_th', 'gio_kt'):
            v = row.get(k)
            init[k] = str(v) if v is not None else ''
            
        def _on_dlg_build(dlg):
            if self.phan == 'lt':
                def _suggest_tu_hoc():
                    try:
                        lt = float(dlg.entries['gio_lt'].get() or 0)
                        bt = float(dlg.entries['gio_bt'].get() or 0)
                        tl = float(dlg.entries['gio_tl'].get() or 0)
                        th = float(dlg.entries['gio_th_tn'].get() or 0)
                        suggested = lt * 2 + bt * 1 + tl * 1 + th * 1
                        dlg.entries['gio_tu_hoc'].delete(0, tk.END)
                        dlg.entries['gio_tu_hoc'].insert(0, f"{suggested:g}")
                    except: pass
                
                btn_suggest = tb.Button(dlg.btn_frame, text='💡 Gợi ý Tự học', 
                                        bootstyle='info-outline', command=_suggest_tu_hoc)
                btn_suggest.pack(side='left', padx=5)

        dlg = RowEditDialog(self.winfo_toplevel(), 'Sửa nội dung', fields, 
                            initial=init, on_build=_on_dlg_build)

        if dlg.result:
            self._save_undo()
            updated = self._result_to_row(dlg.result, row['cap_do'],
                                          row['_parent_tid'], row['thu_tu'])
            updated['_tid'] = row['_tid']
            self._flat[self._flat.index(row)] = updated
            self._rebuild_tree()
            self.sec_parent.mark_modified()

    def _delete(self):
        iid, row = self._get_selected_row()
        if row is None:
            return
        if not ask_modern_yesno(self, 'Xác nhận', 'Xóa mục này và tất cả mục con?'):
            return
        self._save_undo()
        self._delete_recursive(row['_tid'])
        self._rebuild_tree()
        self.sec_parent.mark_modified()

    def _delete_recursive(self, tid):
        children = [r for r in self._flat if r.get('_parent_tid') == tid]
        for c in children:
            self._delete_recursive(c['_tid'])
        self._flat = [r for r in self._flat if r['_tid'] != tid]

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]
        # move logically in self._flat
        idx = next((i for i, r in enumerate(self._flat) if str(r.get('_tid')) == iid), -1)
        if idx == -1: return
        
        target = idx + direction
        if 0 <= target < len(self._flat):
            # rudimentary swap for flat list (only works for same level items effectively)
            self._flat[idx], self._flat[target] = self._flat[target], self._flat[idx]
            self._rebuild_tree()
            self.tree.selection_set(str(self._flat[target].get('_tid')))
            self.sec_parent.mark_modified()

    def _import_excel(self):
        """Nhập dữ liệu từ file Excel .xlsx."""
        import openpyxl
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
        if not path: return
        
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            
            rows = []
            # Giả định: Hàng 1 là tiêu đề, bắt đầu từ hàng 2
            # Columns mapping: 1: Tên, 2: LT/TH, 3: BT, 4: TL, 5: TH_TN/KT, 6: Tự học, 7: Yêu cầu, 8: CDR
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
                if not row[0]: continue # Bỏ qua dòng trống
                
                d = {
                    '_tid': id(row),
                    '_parent_tid': None,
                    'thu_tu': i,
                    'ten': str(row[0]),
                    'cap_do': 1,
                    'yeu_cau': str(row[6]) if len(row) > 6 and row[6] else '',
                    'cdr_ma': str(row[7]) if len(row) > 7 and row[7] else '',
                    'loai': 'thuong'
                }
                # Phân bổ giờ tùy theo tab LT hay TH
                if self.phan == 'lt':
                    d.update({
                        'gio_lt': float(row[1]) if len(row) > 1 and row[1] else 0,
                        'gio_bt': float(row[2]) if len(row) > 2 and row[2] else 0,
                        'gio_tl': float(row[3]) if len(row) > 3 and row[3] else 0,
                        'gio_th_tn': float(row[4]) if len(row) > 4 and row[4] else 0,
                        'gio_tu_hoc': float(row[5]) if len(row) > 5 and row[5] else 0,
                    })
                else:
                    d.update({
                        'gio_th': float(row[1]) if len(row) > 1 and row[1] else 0,
                        'gio_bt': float(row[2]) if len(row) > 2 and row[2] else 0,
                        'gio_tl': float(row[3]) if len(row) > 3 and row[3] else 0,
                        'gio_kt': float(row[4]) if len(row) > 4 and row[4] else 0,
                        'gio_tu_hoc': float(row[5]) if len(row) > 5 and row[5] else 0,
                    })
                rows.append(d)
                
            if rows:
                if messagebox.askyesno('Xác nhận', f'Tìm thấy {len(rows)} dòng dữ liệu. Nhập vào bảng hiện tại? (Dữ liệu cũ sẽ bị thay thế)'):
                    self._flat = rows
                    self._rebuild_tree()
                    messagebox.showinfo('Thành công', 'Đã nhập dữ liệu từ Excel. Hãy kiểm tra lại cấp độ của các mục.')
            else:
                messagebox.showwarning('Cảnh báo', 'Không tìm thấy dữ liệu hợp lệ trong file Excel.')
                
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể đọc file Excel: {e}')
