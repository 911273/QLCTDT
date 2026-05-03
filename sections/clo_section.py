# sections/clo_section.py
"""
CLO Section — Panel nhập liệu Chuẩn đầu ra học phần (CLO).
Dùng cho module ĐCCTHP chuẩn mới (CLO_Standard).
Tương thích ttkbootstrap + BaseSection pattern.
"""
import tkinter as tk
import ttkbootstrap as tb
import re
import json
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    ScrollableFrame, CLR_PRIMARY2, CLR_HDR,
                                    CLR_ROW1, CLR_ROW2, CLR_ACCENT)
from utils.ui_utils import (show_modern_info, show_modern_warning,
                             show_modern_error, ask_modern_yesno)

# Bloom taxonomy — động từ cấp thấp bị cảnh báo
BLOOM_BANNED = re.compile(r'^(Biết|Hiểu|Nắm vững|Nắm được|Nhận biết|Liệt kê)',
                          re.IGNORECASE)

IRM_TOOLTIPS = {
    'I': 'I — Giới thiệu (Introduced)',
    'R': 'R — Củng cố (Reinforced)',
    'M': 'M — Thành thạo (Mastered)',
}


class CLOSection(tb.Frame):
    """
    Panel quản lý CLO cho module ĐCCTHP chuẩn mới.
    Sử dụng CLORepository (CLO_Standard) thay vì db.get_clo/set_clo cũ.

    Signals (callback-based, không dùng pyqtSignal vì đây là Tkinter):
        on_clo_changed: callable — gọi khi danh sách CLO thay đổi.
    """

    def __init__(self, parent, db, clo_repo=None, on_clo_changed=None, **kw):
        super().__init__(parent, **kw)
        self.db = db
        self.repo = clo_repo  # CLORepository instance
        self.on_clo_changed = on_clo_changed
        self.ma_hp = None
        self._rows = []       # list[dict] — dữ liệu CLO hiện tại
        self._plo_list = []   # list[str] — PLO từ DB
        self._undo_stack = []
        self._redo_stack = []
        self._build_ui()

    # ══════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='4. Chuẩn đầu ra học phần (CLO)',
                 font=('Times New Roman', 12, 'bold')).pack(anchor='w')
        tb.Label(head,
                 text='Sau khi kết thúc học phần, người học có thể:',
                 font=('Times New Roman', 10, 'italic')).pack(anchor='w', pady=(2, 0))
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # ── Bảng CLO ─────────────────────────────────────────────────────
        content = tb.Frame(self, padding=(16, 4, 16, 4))
        content.pack(fill='both', expand=True)

        cols   = ('stt', 'ma', 'mo_ta', 'plo', 'irm')
        heads  = ('STT', 'Mã CLO', 'Mô tả', 'PLO', 'Mức I/R/M')
        widths = (50, 80, 400, 100, 80)
        aligns = ('center', 'center', 'w', 'center', 'center')
        self.tree_frm, self.tree = make_tree(
            content, cols, heads, widths, height=12, column_aligns=aligns)
        self.tree_frm.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda _: self._edit())

        # ── Cảnh báo Bloom inline ─────────────────────────────────────────
        self.lbl_bloom_warn = tb.Label(self, text='', foreground='red',
                                        font=('Times New Roman', 9, 'italic'))
        self.lbl_bloom_warn.pack(anchor='w', padx=16)

        # ── Toolbar ──────────────────────────────────────────────────────
        btn = tb.Frame(self, padding=(16, 4, 16, 8))
        btn.pack(fill='x')
        tb.Button(btn, text='➕ Thêm CLO', bootstyle='success',
                  command=self._add).pack(side='left', padx=4)
        tb.Button(btn, text='✏ Sửa', command=self._edit).pack(side='left', padx=4)
        tb.Button(btn, text='🗑 Xóa', bootstyle='danger',
                  command=self._delete).pack(side='left', padx=4)
        tb.Button(btn, text='⬆', command=lambda: self._move(-1)).pack(side='left', padx=2)
        tb.Button(btn, text='⬇', command=lambda: self._move(1)).pack(side='left', padx=2)
        tb.Button(btn, text='💾 Lưu', bootstyle='primary',
                  command=self._save_click).pack(side='right', padx=4)
        tb.Button(btn, text='✔ Validate', bootstyle='info',
                  command=self._validate).pack(side='right', padx=4)

        # ── Ma trận CLO–PLO preview ──────────────────────────────────────
        lf = tb.Labelframe(self, text='Ma trận CLO – PLO (preview)', padding=8)
        lf.pack(fill='x', padx=16, pady=(0, 8))
        self.matrix_frame = tb.Frame(lf)
        self.matrix_frame.pack(fill='x')

    # ══════════════════════════════════════════════════════════════════════
    # DATA I/O
    # ══════════════════════════════════════════════════════════════════════
    def load_data(self, ma_hp):
        """Nạp CLO từ DB theo mã học phần."""
        self.ma_hp = ma_hp
        self._load_plo_list()
        if self.repo:
            db_rows = self.repo.get_all(ma_hp)
            self._rows = [dict(r) for r in db_rows]
        else:
            self._rows = []
        self._refresh()

    def save_data(self) -> bool:
        """Lưu toàn bộ CLO. Return True nếu thành công."""
        if not self.ma_hp or not self.repo:
            return False
        try:
            # Xóa cũ, insert lại
            existing = self.repo.get_all(self.ma_hp)
            for old in existing:
                self.repo.delete(old['id'])
            for i, r in enumerate(self._rows):
                r['ma_hp'] = self.ma_hp
                r['thu_tu'] = i + 1
                self.repo.insert(r)
            self._fire_changed()
            return True
        except Exception as e:
            show_modern_error(self, 'Lỗi lưu CLO', str(e))
            return False

    def get_clo_list(self):
        """Trả về list mã CLO hiện tại."""
        return [r.get('ma_clo', '') for r in self._rows if r.get('ma_clo')]

    # ══════════════════════════════════════════════════════════════════════
    # REFRESH / RENDER
    # ══════════════════════════════════════════════════════════════════════
    def _refresh(self):
        self._auto_renumber()
        self.tree.delete(*self.tree.get_children())
        bloom_warns = []
        for i, r in enumerate(self._rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            mo_ta = r.get('mo_ta', '')
            plo_id = r.get('plo_id', '')
            plo_label = self._plo_id_to_label(plo_id) if plo_id else ''
            self.tree.insert('', 'end', iid=str(i),
                             values=(i + 1,
                                     r.get('ma_clo', ''),
                                     mo_ta,
                                     plo_label,
                                     r.get('muc_giang_day', 'I')),
                             tags=(tag,))
            # Bloom check
            if BLOOM_BANNED.search(mo_ta):
                bloom_warns.append(r.get('ma_clo', f'CLO{i+1}'))

        # Cảnh báo inline
        if bloom_warns:
            self.lbl_bloom_warn.config(
                text=f"⚠ {', '.join(bloom_warns)}: mô tả dùng động từ cấp thấp "
                     f"(Biết/Hiểu/Nắm vững). Hãy dùng động từ Bloom bậc cao.")
        else:
            self.lbl_bloom_warn.config(text='')

        self._refresh_matrix()

    def _auto_renumber(self):
        for i, r in enumerate(self._rows):
            r['ma_clo'] = f'CLO{i + 1}'
            r['thu_tu'] = i + 1

    # ══════════════════════════════════════════════════════════════════════
    # PLO helpers
    # ══════════════════════════════════════════════════════════════════════
    def _load_plo_list(self):
        """Load PLO từ DB dựa trên CTĐT liên kết."""
        self._plo_list = []
        if not self.ma_hp:
            return
        try:
            # Tìm hp_id từ ma_hp
            row = self.db.conn.execute(
                "SELECT id FROM hoc_phan WHERE ma=?", (self.ma_hp,)).fetchone()
            if not row:
                return
            hp_id = row['id']
            links = self.db.get_ctdt_of_hp(hp_id)
            for l in links:
                plos = self.db.get_plo_by_ctdt(l['ctdt_id'])
                for p in plos:
                    entry = {'id': p['id'], 'ma': p['ma'], 'mo_ta': p.get('mo_ta', '')}
                    if entry not in self._plo_list:
                        self._plo_list.append(entry)
        except Exception:
            pass

    def _plo_id_to_label(self, plo_id):
        for p in self._plo_list:
            if p['id'] == plo_id:
                return p['ma']
        return str(plo_id) if plo_id else ''

    def _plo_values(self):
        return [f"{p['ma']}: {p['mo_ta']}" for p in self._plo_list]

    # ══════════════════════════════════════════════════════════════════════
    # CLO–PLO MATRIX
    # ══════════════════════════════════════════════════════════════════════
    def _refresh_matrix(self):
        for w in self.matrix_frame.winfo_children():
            w.destroy()
        if not self._rows or not self._plo_list:
            tb.Label(self.matrix_frame,
                     text='(Chưa có dữ liệu CLO hoặc PLO)',
                     font=('Times New Roman', 9)).pack()
            return

        plo_mas = [p['ma'] for p in self._plo_list]
        # Header row
        tb.Label(self.matrix_frame, text='', width=8).grid(row=0, column=0)
        for j, ma in enumerate(plo_mas):
            tb.Label(self.matrix_frame, text=ma, font=('Times New Roman', 8, 'bold'),
                     width=6, anchor='center').grid(row=0, column=j + 1)

        for i, r in enumerate(self._rows):
            tb.Label(self.matrix_frame, text=r.get('ma_clo', ''),
                     font=('Times New Roman', 8), width=8).grid(row=i + 1, column=0)
            linked_plo = r.get('plo_id')
            irm = r.get('muc_giang_day', '')
            for j, p in enumerate(self._plo_list):
                cell_text = irm if p['id'] == linked_plo else ''
                tb.Label(self.matrix_frame, text=cell_text,
                         font=('Times New Roman', 8), width=6,
                         anchor='center').grid(row=i + 1, column=j + 1)

    # ══════════════════════════════════════════════════════════════════════
    # CRUD
    # ══════════════════════════════════════════════════════════════════════
    def _fields(self, initial=None):
        init = initial or {}
        plo_vals = self._plo_values()
        # Map plo_id back to display string
        plo_init = ''
        if init.get('plo_id') and self._plo_list:
            for p in self._plo_list:
                if p['id'] == init['plo_id']:
                    plo_init = f"{p['ma']}: {p['mo_ta']}"
                    break

        fields = [
            ('ma_clo', 'Mã CLO', 'entry', {}),
            ('mo_ta',  'Mô tả (bắt đầu bằng động từ Bloom)', 'text', {}),
            ('plo_sel', 'PLO liên kết', 'combo', {'values': plo_vals}),
            ('muc_giang_day', 'Mức I/R/M', 'combo', {'values': ['I', 'R', 'M']}),
        ]
        defaults = {
            'ma_clo': init.get('ma_clo', f'CLO{len(self._rows) + 1}'),
            'mo_ta': init.get('mo_ta', ''),
            'plo_sel': plo_init,
            'muc_giang_day': init.get('muc_giang_day', 'I'),
        }
        return fields, defaults

    def _parse_plo_selection(self, plo_sel_str):
        """Chuyển chuỗi 'PLO1: Mô tả' → plo_id."""
        if not plo_sel_str:
            return None
        ma = plo_sel_str.split(':')[0].strip()
        for p in self._plo_list:
            if p['ma'] == ma:
                return p['id']
        return None

    def _save_undo(self):
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _add(self):
        fields, defaults = self._fields()
        dlg = RowEditDialog(self, 'Thêm CLO', fields, initial=defaults)
        if dlg.result:
            self._save_undo()
            plo_id = self._parse_plo_selection(dlg.result.get('plo_sel', ''))
            self._rows.append({
                'ma_hp': self.ma_hp,
                'ma_clo': dlg.result.get('ma_clo', '').strip(),
                'mo_ta': dlg.result.get('mo_ta', '').strip(),
                'plo_id': plo_id,
                'muc_giang_day': dlg.result.get('muc_giang_day', 'I'),
                'thu_tu': len(self._rows) + 1,
            })
            self._refresh()
            self._fire_changed()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        row = self._rows[idx]
        fields, defaults = self._fields(initial=row)
        dlg = RowEditDialog(self, 'Sửa CLO', fields, initial=defaults)
        if dlg.result:
            self._save_undo()
            plo_id = self._parse_plo_selection(dlg.result.get('plo_sel', ''))
            row['ma_clo'] = dlg.result.get('ma_clo', '').strip()
            row['mo_ta'] = dlg.result.get('mo_ta', '').strip()
            row['plo_id'] = plo_id
            row['muc_giang_day'] = dlg.result.get('muc_giang_day', 'I')
            self._refresh()
            self._fire_changed()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not ask_modern_yesno(self, 'Xác nhận', 'Xóa CLO đã chọn?'):
            return
        self._save_undo()
        self._rows.pop(int(sel[0]))
        self._refresh()
        self._fire_changed()

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self._rows):
            self._save_undo()
            self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
            self._refresh()
            self.tree.selection_set(str(new_idx))
            self._fire_changed()

    def _save_click(self):
        if self.save_data():
            show_modern_info(self, 'Thành công', 'Đã lưu CLO thành công.')

    def _fire_changed(self):
        if self.on_clo_changed:
            self.on_clo_changed()

    # ══════════════════════════════════════════════════════════════════════
    # VALIDATE
    # ══════════════════════════════════════════════════════════════════════
    def _validate(self):
        issues = []
        if not self._rows:
            issues.append('❌ Chưa có CLO nào.')

        for r in self._rows:
            ma = r.get('ma_clo', '')
            mo_ta = r.get('mo_ta', '').strip()
            if not mo_ta:
                issues.append(f'⚠ {ma}: mô tả trống.')
            elif BLOOM_BANNED.search(mo_ta):
                issues.append(f'⚠ {ma}: dùng động từ cấp thấp.')
            if not r.get('plo_id'):
                issues.append(f'⚠ {ma}: chưa liên kết PLO.')

        # Hiện dialog kết quả
        dlg = tb.Toplevel(self)
        dlg.title('Kết quả Validate CLO')
        dlg.geometry('500x300')
        dlg.transient(self)
        dlg.grab_set()

        txt = tk.Text(dlg, font=('Times New Roman', 10), wrap='word', padx=10, pady=10)
        txt.pack(fill='both', expand=True, padx=10, pady=10)

        if issues:
            txt.insert('end', f'Phát hiện {len(issues)} vấn đề:\n\n')
            for iss in issues:
                txt.insert('end', f'{iss}\n')
        else:
            txt.insert('end', '✅ Tất cả CLO hợp lệ. Không có cảnh báo.')
        txt.config(state='disabled')

        tb.Button(dlg, text='Đóng', command=dlg.destroy).pack(pady=(0, 10))
