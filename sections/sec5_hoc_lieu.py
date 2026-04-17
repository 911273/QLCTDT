# sections/sec5_hoc_lieu.py — Học liệu
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    CLR_PRIMARY2)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)


class Sec5HocLieu(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._tabs = {}
        self._undo_stack = []
        self._redo_stack = []
        self.bind_all('<Control-z>', lambda e: self._undo())
        self.bind_all('<Control-y>', lambda e: self._redo())

    def _save_undo(self):
        import copy
        # We need a map of tab key -> rows
        snapshot = {k: copy.deepcopy(getattr(t, '_rows', [])) for k, t in self._tabs.items()}
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 20: self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        import copy
        snapshot = self._undo_stack.pop()
        current = {k: copy.deepcopy(getattr(t, '_rows', [])) for k, t in self._tabs.items()}
        self._redo_stack.append(current)
        for k, rows in snapshot.items():
            if k in self._tabs:
                self._tabs[k].load_rows(rows)

    def _redo(self):
        if not self._redo_stack: return
        import copy
        snapshot = self._redo_stack.pop()
        current = {k: copy.deepcopy(getattr(t, '_rows', [])) for k, t in self._tabs.items()}
        self._undo_stack.append(current)
        for k, rows in snapshot.items():
            if k in self._tabs:
                self._tabs[k].load_rows(rows)

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='5. Học liệu',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        nb = tb.Notebook(self)
        nb.pack(fill='both', expand=True, padx=16, pady=4)

        self._tabs = {
            '5.1 Tài liệu học tập (Sách, giáo trình chính)': _HocLieuTab(nb, '5.1 Tài liệu học tập (Sách, giáo trình chính)', self.db, loai='5.1'),
            '5.2 Tài liệu tham khảo': _HocLieuTab(nb, '5.2 Tài liệu tham khảo', self.db, loai='5.2'),
            '5.3 Các tài liệu khác': _HocLieuTab(nb, '5.3 Các tài liệu khác', self.db, loai='5.3'),
            '5.4 Phòng học': _HocLieuTab(nb, '5.4 Phòng học', self.db, loai='5.4',
                               headers=('STT', 'Tên phòng', 'Mô tả diện tích/sức chứa', 'Trang thiết bị đi kèm')),
            '5.5 Trang thiết bị hỗ trợ giảng dạy': _HocLieuTab(nb, '5.5 Trang thiết bị hỗ trợ giảng dạy', self.db, loai='5.5',
                               headers=('STT', 'Tên thiết bị', 'Thông số kỹ thuật/Mô tả', 'Ghi chú')),
            '5.6 Thiết bị thực hành, thí nghiệm': _HocLieuTab(nb, '5.6 Thiết bị thực hành, thí nghiệm', self.db, loai='5.6',
                               headers=('STT', 'Loại thiết bị', 'Cấu hình/Đặc tính', 'Số lượng/Tình trạng')),
            '5.7 Các hoạt động ngoại khóa (nếu có)': _HocLieuTab(nb, '5.7 Các hoạt động ngoại khóa (nếu có)', self.db, loai='5.7',
                               headers=('STT', 'Tên hoạt động', 'Nội dung thực hiện', 'Địa điểm/Thời gian'))
        }
        for k, t in self._tabs.items():
            nb.add(t, text=k)

    def load(self, hp_id):
        super().load(hp_id)
        for k, t in self._tabs.items():
            rows = self.db.get_hoc_lieu(hp_id, k)
            t.load_rows([dict(r) for r in rows])

    def save(self):
        if self.hp_id is not None:
            self.controller.save_current_hp(self.hp_id, None, {'sec5': self.get_data_dict()})

    def get_data_dict(self):
        self.ensure_ui()
        all_rows = []
        for k, t in self._tabs.items():
            all_rows.extend(t.get_rows())
        return {'rows': all_rows}

    def clear(self):
        super().clear()
        for t in self._tabs.values():
            t.load_rows([])


class _HocLieuTab(tb.Frame):
    def __init__(self, parent, label_text, db, loai, headers=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self.loai = loai
        self._rows = []
        self._header_labels = headers or ('STT', 'Tác giả', 'Tên giáo trình/tài liệu', 'Thông tin xuất bản')

        # ── Toolbar (Nhất quán với Section 6) ────────────────────────────────
        toolbar = tb.Frame(self, padding=5)
        toolbar.pack(fill='x')
        
        tb.Button(toolbar, text='➕ Thêm', command=self._add, bootstyle='success-outline').pack(side='left', padx=2)
        tb.Button(toolbar, text='✏ Sửa',   command=self._edit).pack(side='left', padx=2)
        tb.Button(toolbar, text='🗑 Xóa',   command=self._delete).pack(side='left', padx=2)
        tb.Separator(toolbar, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Button(toolbar, text='⬆ Lên',   command=lambda: self._move(-1)).pack(side='left', padx=2)
        tb.Button(toolbar, text='⬇ Xuống', command=lambda: self._move(1)).pack(side='left', padx=2)
        
        # Thêm nút chọn từ thư viện cho 5.1 và 5.2
        if self.loai in ('5.1', '5.2'):
            tb.Separator(toolbar, orient='vertical').pack(side='left', padx=6, fill='y')
            tb.Button(toolbar, text='📚 Chọn từ thư viện', 
                       command=self._pick_from_shared, bootstyle='info-outline').pack(side='left', padx=2)

        cols   = ('stt', 'tac_gia', 'ten', 'thong_tin')
        self.tree_frm, self.tree = make_tree(self, cols, self._header_labels, (40, 160, 280, 280), height=10, db=self.db, table_id='sec5_hoc_lieu_v2')
        self.tree_frm.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<Double-1>', lambda _e: self._edit())

    def _fields(self):
        return [
            ('tac_gia',   self._header_labels[1], 'entry', {}),
            ('ten',       self._header_labels[2], 'text',  {}),
            ('thong_tin', self._header_labels[3], 'entry', {}),
        ]

    def load_rows(self, all_rows):
        """all_rows là list toàn bộ, lọc theo self.loai."""
        self.tree.delete(*self.tree.get_children())
        rows = [r for r in all_rows if r.get('loai') == self.loai]
        rows.sort(key=lambda x: x.get('so_thu_tu', 0))
        
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                             values=(i+1, r.get('tac_gia', ''),
                                     r.get('ten', r.get('noi_dung', '')),
                                     r.get('thong_tin', '')),
                             tags=(tag,))
        self._rows = rows

    def get_rows(self):
        # Cập nhật stt trước khi trả về
        for i, r in enumerate(self._rows):
            r['loai'] = self.loai
            r['so_thu_tu'] = i + 1
        return self._rows

    def _add(self):
        dlg = RowEditDialog(self, 'Thêm mới', self._fields())
        if dlg.result:
            self.master.master._save_undo()
            row = dlg.result
            row['loai'] = self.loai
            self._rows.append(row)
            self.load_rows(self._rows)

    def _edit(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        dlg = RowEditDialog(self, 'Sửa', self._fields(), initial=self._rows[idx])
        if dlg.result:
            self.master.master._save_undo()
            self._rows[idx].update(dlg.result)
            self._rows[idx]['loai'] = self.loai
            self.load_rows(self._rows)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa mục đã chọn?'):
            self.master.master._save_undo()
            self._rows.pop(int(sel[0]))
            self.load_rows(self._rows)

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self._rows):
            self.master.master._save_undo()
            self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
            self.load_rows(self._rows)
            self.tree.selection_set(str(new_idx))

    def _pick_from_shared(self):
        """Mở dialog chọn tài liệu từ kho dùng chung."""
        dlg = _TaiLieuPickDialog(self.winfo_toplevel(), self.db)
        if dlg.result:
            self.master.master._save_undo()
            for item in dlg.result:
                # Mapping từ tai_lieu (DB) sang hoc_lieu (Sec 5)
                new_row = {
                    'loai': self.loai,
                    'tac_gia': item.get('tac_gia', ''),
                    'ten': item.get('ten', ''),
                    'thong_tin': f"{item.get('nam_xb') or ''}, {item.get('nha_xb') or ''}".strip(', ')
                }
                self._rows.append(new_row)
            self.load_rows(self._rows)
            show_modern_info(self, 'Thành công', f'Đã thêm {len(dlg.result)} tài liệu từ thư viện.')


class _TaiLieuPickDialog(tb.Toplevel):
    """Hộp thoại chọn nhiều tài liệu từ bảng tai_lieu."""
    def __init__(self, parent, db):
        super().__init__(parent)
        from sections.base_section import set_window_icon
        set_window_icon(self)
        self.db = db
        self.title('Thư viện Học liệu dùng chung')
        self.geometry('900x650')
        self.result = None
        self.grab_set()
        self._checked_vars = {} # tid -> BooleanVar
        self._build()
        self._refresh()
        self.transient(parent)
        self.wait_window()

    def _build(self):
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        # Tìm kiếm
        sf = tb.Frame(frm)
        sf.pack(fill='x', pady=(0, 10))
        tb.Label(sf, text='🔍 Tìm kiếm:').pack(side='left')
        self.v_search = tk.StringVar()
        self.v_search.trace_add('write', lambda *_: self._refresh())
        tb.Entry(sf, textvariable=self.v_search).pack(side='left', fill='x', expand=True, padx=6)

        # Treeview hiển thị danh sách (có checkbox giả lập hoặc chỉ select)
        from sections.base_section import make_tree
        cols = ('ten', 'tac_gia', 'nam_xb', 'nha_xb')
        heads = ('Tên tài liệu', 'Tác giả', 'Năm XB', 'Nhà xuất bản')
        tf, self.tree = make_tree(frm, cols, heads, (350, 180, 80, 180), height=15, db=self.db, table_id='sec5_shared_pick')
        tf.pack(fill='both', expand=True)
        self.tree.configure(selectmode='extended') # Cho phép chọn nhiều bằng Ctrl/Shift

        # Hướng dẫn
        tb.Label(frm, text='(Giữ Ctrl hoặc Shift để chọn nhiều tài liệu cùng lúc)', 
                  font=('Arial', 9, 'italic'), foreground='gray').pack(pady=4)

        # Buttons
        bf = tb.Frame(self, padding=12)
        bf.pack(fill='x')
        tb.Button(bf, text='✔ Chọn các mục đã đánh dấu', command=self._ok, bootstyle='success').pack(side='right', padx=4)
        tb.Button(bf, text='Hủy', command=self.destroy, bootstyle='secondary-outline').pack(side='right', padx=4)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        kw = self.v_search.get().lower()
        self._items = self.db.get_all_tai_lieu()
        
        filtered = []
        for r in self._items:
            if kw and kw not in (r['ten'] or '').lower() and kw not in (r['tac_gia'] or '').lower():
                continue
            filtered.append(r)

        for i, r in enumerate(filtered):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(r['id']), 
                             values=(r['ten'], r['tac_gia'] or '', r['nam_xb'] or '', r['nha_xb'] or ''),
                             tags=(tag,))

    def _ok(self):
        sel = self.tree.selection()
        if not sel:
            show_modern_warning(self, 'Cảnh báo', 'Vui lòng chọn ít nhất một tài liệu.')
            return
        
        self.result = []
        for iid in sel:
            item = next((r for r in self._items if str(r['id']) == iid), None)
            if item:
                self.result.append(dict(item))
        self.destroy()
