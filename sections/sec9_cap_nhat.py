# sections/sec9_cap_nhat.py — Tiến trình cập nhật đề cương chi tiết học phần
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import (BaseSection, RowEditDialog, make_tree,
                                    CLR_PRIMARY2)
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)


class Sec9CapNhat(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._rows = []
        self.v_dia_diem = tk.StringVar(value='Hà Nội')
        self.v_ngay_ky = tk.StringVar(value='ngày ... tháng ... năm 2023')
        self.v_chuc_trai = tk.StringVar(value='Trưởng khoa')
        self.v_ten_trai = tk.StringVar()
        self.v_chuc_phai = tk.StringVar(value='Người biên soạn')
        self.v_ten_phai = tk.StringVar()
        
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
        tb.Label(head, text='9. Thông tin về các lần cập nhật, chỉnh sửa nội dung đề cương',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        # ── Audit Panel ──────────────────────────────────────────────────────
        self.audit_frm = tb.Labelframe(self, text='🔍 Kiểm tra tính hợp lệ của đề cương', padding=10)
        self.audit_frm.pack(fill='x', padx=16, pady=4)
        
        self.audit_text = tk.Text(self.audit_frm, height=4, font=('Arial', 9),
                                  background='#fff3cd', foreground='#856404', 
                                  relief='flat', state='disabled')
        self.audit_text.pack(fill='x', side='left', expand=True)
        
        btn_audit = tb.Button(self.audit_frm, text='🔄 Kiểm tra lại', command=self.run_audit)
        btn_audit.pack(side='right', padx=5)

        content = tb.Frame(self, padding=(16, 4, 16, 4))
        content.pack(fill='both', expand=True)

        cols   = ('lan', 'noi_dung', 'quyet_dinh', 'nguoi_cap_nhat', 'truong_khoa', 'ngay')
        heads  = ('Lần', 'Nội dung cập nhật', 'Quyết định', 'Người cập nhật', 'Trưởng khoa', 'Ngày')
        widths = (40, 240, 180, 130, 130, 100)
        aligns = ('center', 'w', 'w', 'center', 'center', 'center')
        self.tree_frm, self.tree = make_tree(content, cols, heads, widths, height=12, column_aligns=aligns, db=self.db, table_id='sec9_cap_nhat')
        self.tree_frm.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', lambda _e: self._edit())

        bf = tb.Frame(self, padding=(16, 4, 16, 8))
        bf.pack(fill='x')
        tb.Button(bf, text='➕ Thêm',  command=self._add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',   command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',   command=self._delete).pack(side='left', padx=4)

        # ── Signature block ──────────────────────────────────────────────────
        sig_frm = tb.Labelframe(self, text='Thông tin ký tên cuối đề cương', padding=10)
        sig_frm.pack(fill='both', expand=True, padx=16, pady=10)

        r = 0
        tb.Label(sig_frm, text='Địa điểm ký:').grid(row=r, column=0, sticky='w', pady=2)
        # Using self.v_dia_diem from __init__
        tb.Entry(sig_frm, textvariable=self.v_dia_diem).grid(row=r, column=1, sticky='ew', padx=5, pady=2)

        tb.Label(sig_frm, text='Ngày ký:').grid(row=r, column=2, sticky='w', pady=2)
        # Using self.v_ngay_ky from __init__
        tb.Entry(sig_frm, textvariable=self.v_ngay_ky, width=30).grid(row=r, column=3, sticky='ew', padx=5, pady=2)

        r += 1
        tb.Label(sig_frm, text='Bên trái (Chức danh):').grid(row=r, column=0, sticky='w', pady=2)
        # Using self.v_chuc_trai from __init__
        tb.Entry(sig_frm, textvariable=self.v_chuc_trai).grid(row=r, column=1, sticky='ew', padx=5, pady=2)

        tb.Label(sig_frm, text='Họ tên:').grid(row=r, column=2, sticky='w', pady=2)
        # Using self.v_ten_trai from __init__
        tb.Entry(sig_frm, textvariable=self.v_ten_trai).grid(row=r, column=3, sticky='ew', padx=5, pady=2)

        r += 1
        tb.Label(sig_frm, text='Bên phải (Chức danh):').grid(row=r, column=0, sticky='w', pady=2)
        # Using self.v_chuc_phai from __init__
        tb.Entry(sig_frm, textvariable=self.v_chuc_phai).grid(row=r, column=1, sticky='ew', padx=5, pady=2)

        tb.Label(sig_frm, text='Họ tên:').grid(row=r, column=2, sticky='w', pady=2)
        # Using self.v_ten_phai from __init__
        tb.Entry(sig_frm, textvariable=self.v_ten_phai).grid(row=r, column=3, sticky='ew', padx=5, pady=2)

        sig_frm.columnconfigure(1, weight=1)
        sig_frm.columnconfigure(3, weight=1)

    def _fields(self, initial=None):
        return [
            ('noi_dung',       'Nội dung cập nhật', 'text',  {}),
            ('quyet_dinh',     'Quyết định số',      'entry', {}),
            ('nguoi_cap_nhat', 'Người cập nhật',     'entry', {}),
            ('truong_khoa',    'Trưởng khoa',         'entry', {}),
            ('ngay_cap_nhat',  'Ngày cập nhật',      'entry', {}),
        ]

    def _refresh(self, rows):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                             values=(r.get('lan', i+1),
                                     r.get('noi_dung', ''),
                                     r.get('quyet_dinh', ''),
                                     r.get('nguoi_cap_nhat', ''),
                                     r.get('truong_khoa', ''),
                                     r.get('ngay_cap_nhat', '')),
                             tags=(tag,))
        self._rows = rows

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        if hp:
            self.v_dia_diem.set(hp['dia_diem_ky'] or 'Hà Nội')
            self.v_ngay_ky.set(hp['ngay_ky'] or 'ngày ... tháng ... năm 2023')
            self.v_chuc_trai.set(hp['chuc_danh_ky_trai'] or 'Trưởng khoa')
            self.v_ten_trai.set(hp['ho_ten_ky_trai'] or '')
            self.v_chuc_phai.set(hp['chuc_danh_ky_phai'] or 'Người biên soạn')
            self.v_ten_phai.set(hp['ho_ten_ky_phai'] or '')

        rows = self.db.get_lich_su(hp_id)
        self._rows = [{'lan': r['lan'], 'noi_dung': r['noi_dung'],
                       'quyet_dinh': r['quyet_dinh'], 'nguoi_cap_nhat': r['nguoi_cap_nhat'],
                       'truong_khoa': r['truong_khoa'], 'ngay_cap_nhat': r['ngay_cap_nhat']}
                      for r in rows]
        self._refresh(self._rows)
        self.run_audit()

    def run_audit(self):
        """Kiểm tra các lỗi phổ biến trong đề cương."""
        if not self.hp_id: return
        hp = self.db.get_hoc_phan(self.hp_id)
        clos = self.db.get_clo(self.hp_id)
        mt = self.db.get_muc_tieu(self.hp_id)
        nd = self.db.get_noi_dung(self.hp_id)
        
        issues = []
        # 1. Kiểm tra tiết học
        nd_hours = self.db.conn.execute("SELECT SUM(gio_lt+gio_bt+gio_tl+gio_th_tn+gio_th+gio_bt_th+gio_kt) FROM noi_dung WHERE hp_id=?", (self.hp_id,)).fetchone()[0] or 0
        if abs(nd_hours - (hp['tong_gio'] or 0)) > 0.1:
            issues.append(f"• Lệch tổng giờ: Mục 1 ({hp['tong_gio']}) vs Mục 6 ({nd_hours}). Hãy nhấn 🔄 ở Mục 1.")
            
        # 2. Kiểm tra CLO mapping
        clo_mas = {c['ma'] for c in clos}
        mt_clo_mas = {m['cdr_ma'] for m in mt if m['cdr_ma']}
        missing_clo = clo_mas - mt_clo_mas
        if missing_clo:
            issues.append(f"• CLO chưa được gắn vào Mục tiêu (Mục 3): {', '.join(missing_clo)}.")
            
        # 3. Kiểm tra thông tin bắt buộc
        if not hp['ma']: issues.append("• Thiếu Mã học phần.")
        if not self._rows: issues.append("• Chưa có lịch sử cập nhật đề cương.")
        
        # 4. Kiểm tra trùng lặp hệ thống (Advanced Check)
        dups = self.db.check_duplicates()
        if dups:
            issues.extend(dups)
        
        self.audit_text.configure(state='normal')
        self.audit_text.delete('1.0', 'end')
        if not issues:
            self.audit_frm.configure(text='✅ Đề cương hợp lệ')
            self.audit_text.insert('1.0', "Chúc mừng! Không tìm thấy vấn đề nghiêm trọng nào trong đề cương hiện tại.")
            self.audit_text.configure(background='#d4edda', foreground='#155724')
        else:
            self.audit_frm.configure(text='⚠️ Phát hiện vấn đề cần lưu ý')
            self.audit_text.insert('1.0', "\n".join(issues))
            self.audit_text.configure(background='#fff3cd', foreground='#856404')
        self.audit_text.configure(state='disabled')

    def save(self):
        if self.hp_id is not None:
            self.controller.save_current_hp(self.hp_id, None, {'sec9': self.get_data_dict()})

    def get_data_dict(self):
        self.ensure_ui()
        data = {
            'dia_diem_ky': self.v_dia_diem.get(),
            'ngay_ky': self.v_ngay_ky.get(),
            'chuc_danh_ky_trai': self.v_chuc_trai.get(),
            'ho_ten_ky_trai': self.v_ten_trai.get(),
            'chuc_danh_ky_phai': self.v_chuc_phai.get(),
            'ho_ten_ky_phai': self.v_ten_phai.get(),
        }
        rows = []
        for i, r in enumerate(self._rows):
            r['lan'] = i + 1
            rows.append(r)
        return {**data, 'rows': rows}

    def clear(self):
        super().clear()
        self.tree.delete(*self.tree.get_children())
        self._rows = []
        for v in [self.v_ten_trai, self.v_ten_phai]:
            v.set('')
        self.v_dia_diem.set('Hà Nội')
        self.v_ngay_ky.set('ngày ... tháng ... năm 2023')
        self.v_chuc_trai.set('Trưởng khoa')
        self.v_chuc_phai.set('Người biên soạn')

    def _add(self):
        dlg = RowEditDialog(self, 'Thêm lần cập nhật', self._fields())
        if dlg.result:
            self._save_undo()
            self._rows.append({'lan': len(self._rows)+1, **dlg.result})
            self._refresh(self._rows)

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        dlg = RowEditDialog(self, 'Sửa lần cập nhật', self._fields(), initial=self._rows[idx])
        if dlg.result:
            self._save_undo()
            self._rows[idx].update(dlg.result)
            self._refresh(self._rows)

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not ask_modern_yesno(self, 'Xác nhận', 'Xóa bản ghi cập nhật đã chọn?'):
            return
        self._save_undo()
        self._rows.pop(int(sel[0]))
        self._refresh(self._rows)
