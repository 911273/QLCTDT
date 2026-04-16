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
            'chinh': _HocLieuTab(nb, 'Giáo trình, bài giảng (chính)', self.db),
            'tk':    _HocLieuTab(nb, 'Sách, tài liệu tham khảo', self.db),
            'khac':  _HocLieuTab(nb, 'Tài liệu khác', self.db)
        }
        nb.add(self._tabs['chinh'], text='5.1 Giáo trình/Bài giảng')
        nb.add(self._tabs['tk'],    text='5.2 Tài liệu tham khảo')
        nb.add(self._tabs['khac'],  text='5.3 Tài liệu khác')

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
            rows = t.get_rows()
            for r in rows:
                r['loai'] = k
            all_rows.extend(rows)
        return {'rows': all_rows}

    def clear(self):
        super().clear()
        for t in self._tabs.values():
            t.load_rows([])


class _HocLieuTab(tb.Frame):
    def __init__(self, parent, label_text, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._rows = []

        lbl_frm = tb.Frame(self, padding=5)
        lbl_frm.pack(fill='x')
        tb.Label(lbl_frm, text=label_text, font=('Arial', 10, 'bold')).pack(side='left')

        cols   = ('stt', 'tac_gia', 'ten', 'thong_tin')
        heads  = ('STT', 'Tác giả', 'Tên giáo trình/tài liệu', 'Thông tin xuất bản')
        widths = (40, 160, 280, 280)
        self.tree_frm, self.tree = make_tree(self, cols, heads, widths, height=8, db=self.db, table_id='sec5_hoc_lieu')
        self.tree_frm.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<Double-1>', lambda _e: self._edit())

        bf = tb.Frame(self, padding=5)
        bf.pack(fill='x')
        tb.Button(bf, text='➕ Thêm', command=self._add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',   command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',   command=self._delete).pack(side='left', padx=4)

    def _fields(self):
        return [
            ('tac_gia',   'Tác giả',            'entry', {}),
            ('ten',       'Tên tài liệu',       'text',  {}),
            ('thong_tin', 'Thông tin xuất bản', 'entry', {}),
        ]

    def load_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                             values=(i+1, r.get('tac_gia', ''),
                                     r.get('ten', ''),
                                     r.get('thong_tin', '')),
                             tags=(tag,))
        self._rows = rows

    def get_rows(self):
        return self._rows

    def _add(self):
        dlg = RowEditDialog(self, 'Thêm học liệu', self._fields())
        if dlg.result:
            self.master.master._save_undo()
            self._rows.append(dlg.result)
            self.load_rows(self._rows)

    def _edit(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        dlg = RowEditDialog(self, 'Sửa học liệu', self._fields(), initial=self._rows[idx])
        if dlg.result:
            self.master.master._save_undo()
            self._rows[idx].update(dlg.result)
            self.load_rows(self._rows)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa tài liệu đã chọn?'):
            self.master.master._save_undo()
            self._rows.pop(int(sel[0]))
            self.load_rows(self._rows)
