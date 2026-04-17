import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    recolor_tree, CLR_PRIMARY2, CLR_HDR)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)


class Sec4Clo(BaseSection):
    """Chuẩn đầu ra học phần (CLO) - Giao diện quản lý theo nhóm."""
    
    def __init__(self, parent, db, **kwargs):
        # Load CLO groups from config
        group_str = db.get_config('clo_groups', 'Kiến thức, Kỹ năng, Mức tự chủ và trách nhiệm')
        self.CLO_GROUPS = [g.strip() for g in group_str.split(',') if g.strip()]
        super().__init__(parent, db, **kwargs)
        
        self._rows = []
        # Undo/Redo
        self._undo_stack = []
        self._redo_stack = []
        self.bind_all('<Control-z>', lambda e: self._undo())
        self.bind_all('<Control-y>', lambda e: self._redo())

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='4. Chuẩn đầu ra học phần (CLO)',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Label(head,
                  text='Sau khi kết thúc học phần này, người học có thể:',
                  font=('Arial', 10, 'italic')).pack(anchor='w', pady=(2, 0))
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        content = tb.Frame(self, padding=(16, 4, 16, 4))
        content.pack(fill='both', expand=True)

        cols   = ('ma', 'mo_ta', 'cdr_ma', 'level_irm')
        heads  = ('CDR học phần', 'Mô tả', 'CDR CTĐT', 'Mức độ')
        widths = (100, 480, 100, 60)
        aligns = ('center', 'w', 'center', 'center')
        self.tree_frm, self.tree = make_tree(content, cols, heads, widths, height=14, column_aligns=aligns, db=self.db, table_id='sec4_clo')
        self.tree_frm.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda _e: self._edit())
        
        # Drag and Drop bindings
        self.tree.bind('<ButtonPress-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_drop)

        btns_frm = tb.Frame(self, padding=(16, 4, 16, 8))
        btns_frm.pack(fill='x')
        tb.Button(btns_frm, text='➕ Thêm CLO', style='Primary.TButton',
                   command=self._add).pack(side='left', padx=4)
        tb.Button(btns_frm, text='✏ Sửa',
                   command=self._edit).pack(side='left', padx=4)
        tb.Button(btns_frm, text='🗑 Xóa',
                   command=self._delete).pack(side='left', padx=4)
        tb.Button(btns_frm, text='⬆ Lên',
                   command=lambda: self._move(-1)).pack(side='left', padx=4)
        tb.Button(btns_frm, text='⬇ Xuống',
                   command=lambda: self._move(1)).pack(side='left', padx=4)
        
        tb.Button(btns_frm, text='🔢 Tự đánh số CLO',
                   command=self._auto_number).pack(side='right', padx=4)
        
        self._rows = []

    def update_theme(self):
        super().update_theme()
        self.tree.tag_configure('group', background=CLR_HDR)

    def _get_cdr_list(self):
        if not self.hp_id: return []
        links = self.db.get_ctdt_of_hp(self.hp_id)
        res = []
        for l in links:
            cid = l['ctdt_id'] # ctdt_id
            plos = self.db.get_plo_by_ctdt(cid)
            for plo in plos:
                res.append(f"{plo['ma']}: {plo['mo_ta']}")
                pis = self.db.get_pi_by_plo(plo['id'])
                for pi in pis:
                    res.append(f"{pi['ma']}: {pi['mo_ta']}")
        
        # Fallback/Merge with global cdr_ctdt
        globals = self.db.get_all_cdr_ctdt()
        for g in globals:
            s = f"{g['ma']}: {g['mo_ta']}"
            if s not in res: res.append(s)
        return res

    def _fields(self, initial_cdr='', initial_nhom='Kiến thức', initial_irm='I'):
        # Nếu có initial_cdr (ví dụ 'PI1.1, PI1.2'), ta cần tìm string đầy đủ cho các mã
        full_cdr = initial_cdr
        if initial_cdr:
            all_pis = self.db.get_all_cdr_ctdt()
            pi_map = {p['ma']: f"{p['ma']}: {p['mo_ta']}" for p in all_pis}
            codes = [c.strip() for c in initial_cdr.split(',') if c.strip()]
            full_list = [pi_map.get(c, c) for c in codes]
            full_cdr = ", ".join(full_list)
        
        return [
            # ('nhom',   'Nhóm',               'combo', {'values': self.CLO_GROUPS}), # Removed grouping
            ('ma',     'Mã CLO (vd: CLO1)', 'entry', {}),
            ('mo_ta',  'Mô tả',              'text',  {}),
            ('cdr_ma_full', 'CDR CTĐT',       'multi_picker', {'values': self._get_cdr_list()}),
            ('level_irm', 'Mức độ (I/R/M)',   'combo', {'values': ['I', 'R', 'M']}),
        ], {'cdr_ma_full': full_cdr, 'level_irm': initial_irm}

    def _refresh(self, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree.tag_configure('group', font=('Arial', 10, 'bold', 'italic'), 
                               background=CLR_HDR, foreground=CLR_PRIMARY2)
        
        # Chỉ lấy các CLO thực
        clos = [r for r in rows if not r.get('la_tieu_de_nhom')]
        
        for i, r in enumerate(clos):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(rows.index(r)),
                             values=(r.get('ma', ''), r.get('mo_ta', ''), 
                                     r.get('cdr_ma', ''), r.get('level_irm', 'I')),
                             tags=(tag,))
        self._rows = rows

    def load(self, hp_id):
        super().load(hp_id)
        db_rows = self.db.get_clo(hp_id)
        # Bỏ qua các hàng là tiêu đề nhóm từ DB cũ, chuẩn hóa về CLO thực
        self._rows = [{'ma': r['ma'], 'mo_ta': r['mo_ta'], 'cdr_ma': r['cdr_ma'],
                       'level_irm': r['level_irm'] if r['level_irm'] else 'I',
                       'nhom': r['nhom'] or 'Kiến thức', 'la_tieu_de_nhom': 0}
                      for r in db_rows if not r['la_tieu_de_nhom']]
        self._refresh(self._rows)
        self.is_modified = False # Reset modified after initial load
        
        # Accuracy: Store initial data
        self._initial_data = self.get_data_dict()

    def save(self):
        if self.hp_id is not None:
            # Accuracy: Audit Trail
            current_data = self.get_data_dict()
            if hasattr(self, '_initial_data'):
                if str(current_data['rows']) != str(self._initial_data['rows']):
                    self.db.log_change(self.hp_id, 'clo', 'rows', 
                                       self._initial_data['rows'], current_data['rows'])
            self._initial_data = current_data
            
            self.db.set_clo(self.hp_id, self._rows)

    def get_data_dict(self):
        self.ensure_ui()
        return {'rows': self._rows}

    def apply_data_dict(self, data):
        if data and 'rows' in data:
            self._rows = data['rows']
            self._refresh(self._rows)

    def clear(self):
        self._save_undo()
        super().clear()
        self.tree.delete(*self.tree.get_children())
        self._rows = []

    def _save_undo(self):
        """Lưu bản sao của _rows vào undo stack."""
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        if len(self._undo_stack) > 20:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._undo_stack: return
        import copy
        self._redo_stack.append(copy.deepcopy(self._rows))
        self._rows = self._undo_stack.pop()
        self._refresh(self._rows)
        self.mark_modified()

    def _redo(self):
        if not self._redo_stack: return
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        self._rows = self._redo_stack.pop()
        self._refresh(self._rows)
        self.mark_modified()

    def _add(self):
        flds, init = self._fields()
        dlg = RowEditDialog(self, 'Thêm CLO', flds, initial=init)
        if dlg.result:
            self._save_undo()
            new_ma = dlg.result.get('ma', '').strip().upper()
            # Accuracy: Check uniqueness
            if any(r['ma'].strip().upper() == new_ma for r in self._rows):
                show_modern_error(self, 'Lỗi', f'Mã CLO "{new_ma}" đã tồn tại!')
                return

            cdr_full = dlg.result.get('cdr_ma_full', '')
            codes = [c.split(':')[0].strip() for c in cdr_full.split(',') if c.strip()]
            ma_pi = ", ".join(codes)
            self._rows.append({'la_tieu_de_nhom': 0, 
                               'nhom': None,
                               'ma': new_ma,
                               'mo_ta': dlg.result.get('mo_ta', ''),
                               'cdr_ma': ma_pi,
                               'level_irm': dlg.result.get('level_irm', 'I')})
            self._refresh(self._rows)
            self.mark_modified()

    # REMOVED _add_group as requested

    def _edit(self):
        sel = self.tree.selection()
        if not sel or sel[0].startswith('grp_'):
            return
        idx = int(sel[0])
        row = self._rows[idx]

        flds, init = self._fields(row.get('cdr_ma', ''), initial_nhom=row.get('nhom', 'Kiến thức'))
        init.update({'ma': row.get('ma', ''), 'mo_ta': row.get('mo_ta', '')})

        dlg = RowEditDialog(self, 'Sửa CLO', flds, initial=init)
        if dlg.result:
            self._save_undo()
            new_ma = dlg.result.get('ma', '').strip().upper()
            # Accuracy: Check uniqueness (bỏ qua chính nó)
            if any(i != idx and r['ma'].strip().upper() == new_ma for i, r in enumerate(self._rows)):
                show_modern_error(self, 'Lỗi', f'Mã CLO "{new_ma}" đã tồn tại!')
                return

            cdr_full = dlg.result.get('cdr_ma_full', '')
            codes = [c.split(':')[0].strip() for c in cdr_full.split(',') if c.strip()]
            ma_pi = ", ".join(codes)
            row['ma'] = new_ma
            row['mo_ta'] = dlg.result.get('mo_ta', '')
            row['cdr_ma'] = ma_pi
            row['level_irm'] = dlg.result.get('level_irm', 'I')
            self._refresh(self._rows)
            self.mark_modified()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not ask_modern_yesno(self, 'Xác nhận', 'Xóa CLO đã chọn?'):
            return
        self._save_undo()
        self._rows.pop(int(sel[0]))
        self._refresh(self._rows)
        self.mark_modified()

    def _move(self, direction):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self._rows):
            self._save_undo()
            self._rows[idx], self._rows[new_idx] = self._rows[new_idx], self._rows[idx]
            self._refresh(self._rows)
            self.tree.selection_set(str(new_idx))
            self.mark_modified()

    def _auto_number(self):
        stt = 1
        for i, r in enumerate(self._rows):
            if not r.get('la_tieu_de_nhom'):
                r['ma'] = f'CLO{stt}'
                stt += 1
        self._refresh(self._rows)
        self.mark_modified()

    def get_clo_list(self):
        """Trả về danh sách mã CLO để các section khác tham chiếu."""
        return [r['ma'] for r in self._rows if r.get('ma') and not r.get('la_tieu_de_nhom')]

    # ── Drag and Drop Logic ──────────────────────────────────────────────────
    def _on_drag_start(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        self._drag_idx = int(iid)

    def _on_drag_motion(self, event):
        pass

    def _on_drag_drop(self, event):
        if not hasattr(self, '_drag_idx'): return
        source_idx = self._drag_idx
        del self._drag_idx
        
        target_iid = self.tree.identify_row(event.y)
        if not target_iid or target_iid == str(source_idx): return
        
        source_row = self._rows[source_idx]
        
        target_idx = int(target_iid)
        
        # Determine if dropping above or below
        bbox = self.tree.bbox(target_iid)
        if not bbox: return
        y_in_row = event.y - bbox[1]
        row_height = bbox[3]
        
        new_idx = target_idx
        if y_in_row > row_height / 2:
            new_idx += 1
            
        if source_idx < new_idx:
            new_idx -= 1
            
        if source_idx == new_idx:
            return
        
        self._save_undo()
        row = self._rows.pop(source_idx)
        self._rows.insert(new_idx, row)
        self._refresh(self._rows)
        # Tìm lại iid mới sau khi refresh (vì index có thể đổi do sort)
        new_iid = str(self._rows.index(row))
        self.tree.selection_set(new_iid)
        self.mark_modified()
