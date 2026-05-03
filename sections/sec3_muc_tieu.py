import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    recolor_tree, CLR_PRIMARY2, CLR_HDR, CLR_TEXT)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)


import copy
from sections.registry import register_section


@register_section(order=3, label="3. Mục tiêu")
class Sec3MucTieu(BaseSection):
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
        """Lưu bản sao của _rows vào undo stack."""
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
        self.mark_modified()

    def _redo(self):
        if not self._redo_stack: return
        import copy
        self._undo_stack.append(copy.deepcopy(self._rows))
        self._rows = self._redo_stack.pop()
        self._refresh(self._rows)
        self.mark_modified()

    def _build_ui(self):
        abbr_mt = self.get_abbr('MT', 'MT')
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        self.lbl_header = tb.Label(head, text=f'3. Mục tiêu của học phần ({abbr_mt})',
                  style='SectionHeader.TLabel')
        self.lbl_header.pack(anchor='w')
        tb.Label(head,
                  text='Học phần này trang bị cho sinh viên / cung cấp cho sinh viên:',
                  font=('Arial', 10, 'italic')).pack(anchor='w', pady=(2, 0))
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # ── Treeview ────────────────────────────────────────────────────────
        content = tb.Frame(self, padding=(16, 4, 16, 4))
        content.pack(fill='both', expand=True)

        cols   = ('stt', 'mo_ta', 'cdr_ma')
        self.tree_heads = (f'Mục tiêu ({abbr_mt})', 'Mô tả', 'CDR CTĐT')
        widths = (80, 560, 100)
        aligns = ('center', 'w', 'center')
        self.tree_frm, self.tree = make_tree(content, cols, self.tree_heads, widths, height=14, column_aligns=aligns, db=self.db, table_id='sec3_muc_tieu')
        self.tree_frm.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda _e: self._edit())
        
        # Drag and Drop bindings
        self.tree.bind('<ButtonPress-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_drop)

        # ── Buttons ─────────────────────────────────────────────────────────
        bf = tb.Frame(self, padding=(16, 4, 16, 8))
        bf.pack(fill='x')
        self.btn_add = tb.Button(bf, text=f'➕ Thêm {abbr_mt}', command=self._add)
        self.btn_add.pack(side='left', padx=4)
        # tb.Button(bf, text='📂 Thêm Nhóm', command=self._add_group).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',   command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',   command=self._delete).pack(side='left', padx=4)
        tb.Button(bf, text='⬆ Lên',   command=lambda: self._move(-1)).pack(side='left', padx=4)
        tb.Button(bf, text='⬇ Xuống', command=lambda: self._move(1)).pack(side='left', padx=4)
        self._rows = []

    def refresh_labels(self):
        """Cập nhật lại các nhãn khi cấu hình viết tắt thay đổi."""
        if not self._ui_built: return
        abbr_mt = self.get_abbr('MT', 'MT')
        self.lbl_header.config(text=f'3. Mục tiêu của học phần ({abbr_mt})')
        self.btn_add.config(text=f'➕ Thêm {abbr_mt}')
        # Update Treeview header
        self.tree.heading('stt', text=f'Mục tiêu ({abbr_mt})')

    def update_theme(self):
        if not self._ui_built: return
        super().update_theme()
        self.tree.tag_configure('group', background=CLR_HDR, foreground=CLR_PRIMARY2)

    def _get_cdr_list(self):
        from utils.data_utils import natural_sort_key
        if not self.hp_id: return []
        links = self.db.get_ctdt_of_hp(self.hp_id)
        res = []
        seen_mas = set()

        for l in links:
            cid = l['ctdt_id']
            plos = self.db.get_plo_by_ctdt(cid)
            # Sắp xếp PLO tự nhiên
            plos.sort(key=lambda x: natural_sort_key(x['ma']))
            
            for plo in plos:
                plo_str = f"{plo['ma']}: {plo['mo_ta']}"
                if plo['ma'] not in seen_mas:
                    res.append(plo_str)
                    seen_mas.add(plo['ma'])
                
                pis = self.db.get_pi_by_plo(plo['id'])
                # Sắp xếp PI tự nhiên
                pis.sort(key=lambda x: natural_sort_key(x['ma']))
                for pi in pis:
                    pi_str = f"{pi['ma']}: {pi['mo_ta']}"
                    if pi['ma'] not in seen_mas:
                        res.append(pi_str)
                        seen_mas.add(pi['ma'])
        
        # Fallback/Merge with global cdr_ctdt (cũng cần sắp xếp nếu muốn đẹp, nhưng ưu tiên theo PLO/PI)
        globals = self.db.get_all_cdr_ctdt()
        globals.sort(key=lambda x: natural_sort_key(x['ma']))
        for g in globals:
            if g['ma'] not in seen_mas:
                res.append(f"{g['ma']}: {g['mo_ta']}")
                seen_mas.add(g['ma'])
        return res

    def _fields(self, initial_cdr=''):
        # Nếu có initial_cdr (ví dụ 'PI1.1, PI1.2'), ta cần tìm string đầy đủ cho các mã
        full_cdr = initial_cdr
        if initial_cdr:
            all_pis = self.db.get_all_cdr_ctdt()
            pi_map = {p['ma']: f"{p['ma']}: {p['mo_ta']}" for p in all_pis}
            codes = [c.strip() for c in initial_cdr.split(',') if c.strip()]
            full_list = [pi_map.get(c, c) for c in codes]
            full_cdr = ", ".join(full_list)
        
        return [
            ('mo_ta',  'Mô tả mục tiêu', 'text',  {}),
            ('cdr_ma_full', 'CDR CTĐT', 'cdr_picker', {'db': self.db, 'hp_id': self.hp_id}),
        ], {'cdr_ma_full': full_cdr}

    def _refresh(self, data_rows):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not hasattr(self, 'tree') or not self.tree: return # FINAL GUARD
        self.tree.delete(*self.tree.get_children())
        from sections.base_section import CLR_HDR, CLR_PRIMARY2
        self.tree.tag_configure('group', font=('Arial', 10, 'bold', 'italic'), 
                               background=CLR_HDR, foreground=CLR_PRIMARY2)
        stt = 1
        for i, row in enumerate(data_rows):
            if row.get('la_tieu_de_nhom'):
                # Still support existing groups in DB for now, but mark them
                iid = self.tree.insert('', 'end', iid=str(i),
                                 values=('', row.get('nhom', ''), ''),
                                 tags=('group',))
            else:
                tag = 'even' if i % 2 == 0 else 'odd'
                abbr_mt = self.get_abbr('MT', 'MT')
                self.tree.insert('', 'end', iid=str(i),
                                 values=(f"{abbr_mt}{stt}",
                                         row.get('mo_ta', ''),
                                         self.extract_codes(row.get('cdr_ma', ''))),
                                 tags=(tag,))
                stt += 1
        self._rows = data_rows

    def apply_data_dict(self, data):
        self.ensure_ui()
        if data and 'rows' in data:
            self._rows = data['rows']
            self._refresh(self._rows)

    def load(self, hp_id):
        super().load(hp_id)
        rows = self.db.get_muc_tieu(hp_id)
        self._rows = [{'so_thu_tu': r['so_thu_tu'],
                       'mo_ta': r['mo_ta'], 'cdr_ma': r['cdr_ma'],
                       'nhom': r['nhom'], 'la_tieu_de_nhom': r['la_tieu_de_nhom']} for r in rows]
        self._refresh(self._rows)

        # Accuracy: Store initial data
        self._initial_data = copy.deepcopy(self.get_data_dict())
        self._loading = False

    def save(self):
        if self.hp_id is not None:
            # Accuracy: Audit Trail
            current_data = self.get_data_dict()
            if hasattr(self, '_initial_data'):
                if str(current_data['rows']) != str(self._initial_data['rows']):
                    self.db.log_change(self.hp_id, 'muc_tieu', 'rows', 
                                       self._initial_data['rows'], current_data['rows'])
            self._initial_data = current_data

            stt = 1
            for r in self._rows:
                if r.get('la_tieu_de_nhom'):
                    r['so_thu_tu'] = None
                else:
                    r['so_thu_tu'] = stt
                    stt += 1
            self.db.set_muc_tieu(self.hp_id, self._rows)

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
        self.mark_modified()

    def _add(self):
        abbr_mt = self.get_abbr('MT', 'MT')
        flds, init = self._fields()
        dlg = RowEditDialog(self, f'Thêm {abbr_mt}', flds, initial=init)
        if dlg.result:
            self._save_undo()
            ma = self.extract_codes(dlg.result.get('cdr_ma_full', ''))
            self._rows.append({'la_tieu_de_nhom': 0, 'nhom': None,
                               'mo_ta': dlg.result.get('mo_ta', ''),
                               'cdr_ma': ma})
            self._refresh(self._rows)
            self.mark_modified()

    def _add_group(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Thêm nhóm", "Tên nhóm (ví dụ: Kiến thức, Kỹ năng...):", parent=self)
        if name:
            self._save_undo()
            self._rows.append({'la_tieu_de_nhom': 1, 'nhom': name, 'mo_ta': '', 'cdr_ma': ''})
            self._refresh(self._rows)
            self.mark_modified()

    def _edit(self):
        abbr_mt = self.get_abbr('MT', 'MT')
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        row = self._rows[idx]
        
        if row.get('la_tieu_de_nhom'):
            from tkinter import simpledialog
            name = simpledialog.askstring("Sửa nhóm", "Tên nhóm:", initialvalue=row.get('nhom', ''), parent=self)
            if name:
                row['nhom'] = name
                self._refresh(self._rows)
                self.mark_modified()
            return

        flds, init = self._fields(row.get('cdr_ma', ''))
        init['mo_ta'] = row.get('mo_ta', '')
        
        dlg = RowEditDialog(self, f'Sửa {abbr_mt}', flds, initial=init)
        if dlg.result:
            self._save_undo()
            ma = self.extract_codes(dlg.result.get('cdr_ma_full', ''))
            row['mo_ta']  = dlg.result.get('mo_ta', '')
            row['cdr_ma'] = ma
            self._refresh(self._rows)
            self.mark_modified()

    def _delete(self):
        abbr_mt = self.get_abbr('MT', 'MT')
        sel = self.tree.selection()
        if not sel:
            return
        if not ask_modern_yesno(self, 'Xác nhận', f'Xóa {abbr_mt} đã chọn?'):
            return
        self._save_undo()
        idx = int(sel[0])
        self._rows.pop(idx)
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

    # ── Drag and Drop Logic ──────────────────────────────────────────────────
    def _on_drag_start(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid: return
        self._drag_idx = int(iid)

    def _on_drag_motion(self, event):
        # Visual feedback could be added here
        pass

    def _on_drag_drop(self, event):
        if not hasattr(self, '_drag_idx'): return
        source_idx = self._drag_idx
        del self._drag_idx
        
        target_iid = self.tree.identify_row(event.y)
        if not target_iid or target_iid == str(source_idx): return
        
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
            
        if source_idx == new_idx: return
        
        self._save_undo()
        row = self._rows.pop(source_idx)
        self._rows.insert(new_idx, row)
        self._refresh(self._rows)
        self.tree.selection_set(str(new_idx))
        self.mark_modified()
