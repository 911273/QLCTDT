# shared_data_dialog.py — Quản lý dữ liệu dùng chung: Khoa, Giảng viên, CDR CTĐT
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import make_tree, RowEditDialog, CLR_PRIMARY2, set_window_icon
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
import openpyxl
from tkinter import filedialog
from utils.data_utils import natural_sort_key


KHOI_KIEN_THUC = ['Đại cương', 'Cơ sở ngành', 'Ngành', 'Chuyên ngành', 'Khác']


class SharedDataDialog(tb.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        set_window_icon(self)
        self.title('Quản lý Dữ liệu Chung')
        self.geometry('1100x750')
        self.resizable(True, True)
        self.db = db
        self.grab_set()
        self._build()
        self.transient(parent)

    def _build(self):
        nb = tb.Notebook(self)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        self._build_khoa_tab(nb)
        self._build_hp_tab(nb)
        self._build_gv_tab(nb)
        self._build_ctdt_tab(nb)
        self._build_hl_tab(nb)

        tb.Button(self, text='✔ Đóng', command=self.destroy).pack(pady=6)

    # ── KHOA ─────────────────────────────────────────────────────────────────
    def _build_khoa_tab(self, nb):
        frm = tb.Frame(nb, padding=10)
        nb.add(frm, text='🏫 Khoa / Đơn vị')
        # Search
        sf = tb.Frame(frm)
        sf.pack(fill='x', pady=(0, 4))
        tb.Label(sf, text='🔍 Tìm:', font=('Arial', 10)).pack(side='left')
        self.v_khoa_search = tk.StringVar()
        self.v_khoa_search.trace_add('write', lambda *_: self._khoa_refresh())
        tb.Entry(sf, textvariable=self.v_khoa_search, width=30,
                  font=('Arial', 10)).pack(side='left', padx=4)

        cols   = ('ma', 'ten')
        heads  = ('Mã', 'Tên đơn vị')
        widths = (80, 600)
        tf, self.khoa_tree = make_tree(frm, cols, heads, widths, height=18, db=self.db, table_id='shared_khoa')
        tf.pack(fill='both', expand=True)
        self.khoa_tree.bind('<Double-1>', lambda _: self._khoa_edit())

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=4)
        tb.Button(bf, text='➕ Thêm mới', command=self._khoa_add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',       command=self._khoa_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',       command=self._khoa_delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._khoa_import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        self._khoa_refresh()

    def _khoa_fields(self):
        return [('ma',  'Mã đơn vị', 'entry', {}),
                ('ten', 'Tên đơn vị', 'entry', {})]

    def _khoa_refresh(self):
        self.khoa_tree.delete(*self.khoa_tree.get_children())
        kw = self.v_khoa_search.get().lower()
        rows = self.db.get_all_khoa()
        for i, r in enumerate(rows):
            if kw and kw not in (r['ma'] or '').lower() and kw not in r['ten'].lower():
                continue
            tag = 'even' if i % 2 == 0 else 'odd'
            self.khoa_tree.insert('', 'end', iid=str(r['id']),
                                   values=(r['ma'] or '', r['ten']), tags=(tag,))

    def _khoa_add(self):
        dlg = RowEditDialog(self, 'Thêm đơn vị', self._khoa_fields())
        if dlg.result:
            ma = dlg.result.get('ma', '').strip()
            ten = dlg.result.get('ten', '').strip()
            # Kiểm tra trùng lặp
            all_khoa = self.db.get_all_khoa()
            dup = next((k for k in all_khoa if (ma and k['ma'] == ma) or (k['ten'] == ten)), None)
            if dup:
                msg = f"Cảnh báo: Đơn vị '{ten}' hoặc mã '{ma}' đã tồn tại.\nBạn có chắc chắn muốn thêm trùng lặp không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return

            self.db.add_khoa(ma, ten)
            self._khoa_refresh()

    def _khoa_edit(self):
        sel = self.khoa_tree.selection()
        if not sel:
            return
        kid = int(sel[0])
        row = next((dict(r) for r in self.db.get_all_khoa() if r['id'] == kid), None)
        if not row:
            return
        dlg = RowEditDialog(self, 'Sửa đơn vị', self._khoa_fields(), initial=row)
        if dlg.result:
            ma = dlg.result.get('ma', '').strip()
            ten = dlg.result.get('ten', '').strip()
            # Kiểm tra trùng lặp (trừ chính nó)
            all_khoa = self.db.get_all_khoa()
            dup = next((k for k in all_khoa if k['id'] != kid and ((ma and k['ma'] == ma) or (k['ten'] == ten))), None)
            if dup:
                msg = f"Cảnh báo: Đơn vị '{ten}' hoặc mã '{ma}' đã tồn tại.\nBạn có chắc chắn muốn cập nhật không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return

            self.db.update_khoa(kid, ma, ten)
            self._khoa_refresh()

    def _khoa_delete(self):
        sel = self.khoa_tree.selection()
        if not sel: return
        count = len(sel)
        msg = f"Xóa {count} đơn vị đã chọn?\nLưu ý: Chỉ xóa được nếu đơn vị không có liên kết dữ liệu."
        if ask_modern_yesno(self, 'Xác nhận', msg):
            import sqlite3
            success, failed = 0, 0
            for iid in sel:
                try:
                    self.db.delete_khoa(int(iid))
                    success += 1
                except sqlite3.IntegrityError:
                    failed += 1
            self._khoa_refresh()
            if failed > 0:
                show_modern_warning(self, 'Kết quả', f"Đã xóa {success} mục. Thất bại {failed} mục do có ràng buộc dữ liệu.")

    # ── GIANG VIEN ───────────────────────────────────────────────────────────
    def _build_gv_tab(self, nb):
        frm = tb.Frame(nb, padding=10)
        nb.add(frm, text='👤 Giảng viên')

        # Search
        sf = tb.Frame(frm)
        sf.pack(fill='x', pady=(0, 4))
        tb.Label(sf, text='🔍 Tìm:', font=('Arial', 10)).pack(side='left')
        self.v_gv_search = tk.StringVar()
        self.v_gv_search.trace_add('write', lambda *_: self._gv_refresh())
        tb.Entry(sf, textvariable=self.v_gv_search, width=30,
                  font=('Arial', 10)).pack(side='left', padx=4)

        cols   = ('ma_can_bo', 'ho_ten', 'hoc_vi', 'chuc_vu', 'ten_khoa', 'email')
        heads  = ('Mã CB', 'Họ và tên', 'Học vị', 'Chức vụ', 'Đơn vị', 'Email')
        widths = (80, 180, 80, 120, 180, 180)
        tf, self.gv_tree = make_tree(frm, cols, heads, widths, height=15, db=self.db, table_id='shared_gv')
        tf.pack(fill='both', expand=True)
        self.gv_tree.bind('<Double-1>', lambda _: self._gv_edit())

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=4)
        tb.Button(bf, text='➕ Thêm mới', command=self._gv_add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',       command=self._gv_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',       command=self._gv_delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._gv_import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        self._gv_refresh()

    def _gv_fields(self):
        khoas = self.db.get_all_khoa()
        khoa_names = [''] + [k['ten'] for k in khoas]
        self._khoa_map_gv = {'': None, **{k['ten']: k['id'] for k in khoas}}
        return [
            # Frame 1: Personal
            ('ma_can_bo', 'Mã cán bộ',         'entry', {}),
            ('ho_ten',  'Họ và tên (*)',      'entry', {}),
            ('gioi_tinh', 'Giới tính',         'combo', {'values': ['Nam', 'Nữ', 'Khác']}),
            ('ngay_sinh', 'Ngày sinh (dd/mm/yyyy)', 'entry', {}),
            ('cmnd_cccd', 'Số CMND/CCCD',      'entry', {}),
            ('sdt',     'Số điện thoại',       'entry', {}),
            ('email',   'Email',                'entry', {}),
            ('dia_chi', 'Địa chỉ',             'entry', {}),
            ('khoa',    'Đơn vị/Khoa',         'combo', {'values': khoa_names, 'state': 'normal'}),
            # Frame 2: Education
            ('hoc_vi',  'Học vị (TS/ThS/...)','entry', {}),
            ('chuc_danh', 'Chức danh (GS/PGS)', 'entry', {}),
            ('chuc_vu', 'Chức vụ',             'entry', {}),
            ('nam_phong_chuc_danh', 'Năm phong chức danh', 'entry', {}),
            ('trinh_do_chuyen_mon', 'Trình độ CM', 'entry', {}),
            ('co_so_dao_tao', 'Cơ sở đào tạo', 'entry', {}),
            ('nam_tot_nghiep', 'Năm tốt nghiệp', 'entry', {}),
            ('nganh_dao_tao', 'Ngành đào tạo', 'entry', {}),
            # Frame 3: Labor
            ('ngay_tuyen_dung', 'Ngày tuyển dụng', 'entry', {}),
            ('ma_so_bao_hiem', 'Mã số bảo hiểm', 'entry', {}),
            ('so_nam_kinh_nghiem', 'Năm kinh nghiệm', 'entry', {}),
        ]

    def _gv_refresh(self):
        kw = self.v_gv_search.get()
        rows = self.db.search_giang_vien(kw) if kw else self.db.get_all_giang_vien()
        self.gv_tree.delete(*self.gv_tree.get_children())
        self._gv_ids = []
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.gv_tree.insert('', 'end', iid=str(i),
                                 values=(r['ma_can_bo'] or '', r['ho_ten'], r['hoc_vi'] or '',
                                         r['chuc_vu'] or '',
                                         r['ten_khoa'] or '', r['email'] or ''), tags=(tag,))
            self._gv_ids.append(r['id'])

    def _gv_add(self):
        dlg = RowEditDialog(self, 'Thêm giảng viên', self._gv_fields())
        if dlg.result:
            ho_ten = dlg.result.get('ho_ten', '').strip()
            email = dlg.result.get('email', '').strip()
            ngay_sinh = dlg.result.get('ngay_sinh', '').strip()
            
            # Kiểm tra trùng lặp
            all_gv = self.db.get_all_giang_vien()
            dup = next((g for g in all_gv if (email and email != '' and g['email'] == email) or 
                        (g['ho_ten'] == ho_ten and (not ngay_sinh or g['ngay_sinh'] == ngay_sinh))), None)
            if dup:
                msg = f"Cảnh báo: Giảng viên '{ho_ten}' đã tồn tại.\nBạn có chắc chắn muốn thêm trùng lặp không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return

            khoa_id = self._khoa_map_gv.get(dlg.result.pop('khoa', ''))
            dlg.result['khoa_id'] = khoa_id
            self.db.add_giang_vien(dlg.result)
            self._gv_refresh()

    def _gv_edit(self):
        sel = self.gv_tree.selection()
        if not sel: return
        gv_id = self._gv_ids[int(sel[0])]
        all_gv = self.db.get_all_giang_vien()
        row = next((dict(g) for g in all_gv if g['id'] == gv_id), None)
        if not row: return
        
        init = {**row, 'khoa': row.get('ten_khoa') or ''}
        dlg = RowEditDialog(self, 'Sửa giảng viên', self._gv_fields(), initial=init)
        if dlg.result:
            ho_ten = dlg.result.get('ho_ten', '').strip()
            email = dlg.result.get('email', '').strip()
            ngay_sinh = dlg.result.get('ngay_sinh', '').strip()
            
            # Kiểm tra trùng lặp (trừ chính nó)
            dup = next((g for g in all_gv if g['id'] != gv_id and ((email and email != '' and g['email'] == email) or 
                        (g['ho_ten'] == ho_ten and (not ngay_sinh or g['ngay_sinh'] == ngay_sinh)))), None)
            if dup:
                msg = f"Cảnh báo: Thông tin giảng viên '{ho_ten}' trùng với dữ liệu khác.\nBạn có chắc chắn muốn cập nhật không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return

            khoa_id = self._khoa_map_gv.get(dlg.result.pop('khoa', ''))
            dlg.result['khoa_id'] = khoa_id
            self.db.update_giang_vien(gv_id, dlg.result)
            self._gv_refresh()

    def _gv_delete(self):
        sel = self.gv_tree.selection()
        if not sel: return
        count = len(sel)
        if ask_modern_yesno(self, 'Xác nhận', f"Xóa {count} giảng viên đã chọn?"):
            import sqlite3
            success, failed = 0, 0
            for iid in sel:
                gid = self._gv_ids[int(iid)]
                try:
                    self.db.delete_giang_vien(gid)
                    success += 1
                except sqlite3.IntegrityError:
                    failed += 1
            self._gv_refresh()
            if failed > 0:
                show_modern_warning(self, 'Kết quả', f"Đã xóa {success} giảng viên. Thất bại {failed} do đang bận dạy.")


    # ── CHUONG TRINH DAO TAO ─────────────────────────────────────────────────
    def _build_ctdt_tab(self, nb):
        frm = tb.Frame(nb, padding=10)
        nb.add(frm, text='🎓 Chương trình đào tạo')

        cols   = ('ten', 'bac', 'ten_khoa')
        heads  = ('Tên chương trình / Chuyên ngành', 'Bậc', 'Khoa quản lý')
        widths = (350, 100, 250)
        tf, self.ctdt_tree = make_tree(frm, cols, heads, widths, height=18, db=self.db, table_id='shared_ctdt')
        tf.pack(fill='both', expand=True)
        self.ctdt_tree.configure(show='tree headings')
        self.ctdt_tree.column('#0', width=40, minwidth=40, stretch=False)
        self.ctdt_tree.heading('#0', text='')

        # Styling
        self.ctdt_tree.tag_configure('major', background='#4682B4', foreground='white', font=('Arial', 10, 'bold'))
        self.ctdt_tree.tag_configure('minor', background='#262626', foreground='white')
        
        self.ctdt_tree.bind('<Double-1>', lambda _: self._ctdt_edit())

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=4)
        tb.Button(bf, text='➕ Thêm Ngành',  command=self._ctdt_add).pack(side='left', padx=4)
        tb.Button(bf, text='🎓 Thêm Chuyên ngành', command=self._ctdt_add_cn).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',        command=self._ctdt_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',        command=self._ctdt_delete).pack(side='left', padx=4)
        
        abbr_po = self.db.get_config('abbr_po', 'PO')
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        tb.Label(bf, text='|').pack(side='left', padx=10)
        tb.Button(bf, text=f'🎯 {abbr_po} (Mục tiêu)', command=self._ctdt_manage_po).pack(side='left', padx=4)
        tb.Button(bf, text=f'✅ {abbr_plo} (Chuẩn đầu ra)', command=self._ctdt_manage_plo).pack(side='left', padx=4)
        tb.Button(bf, text='📚 Học phần', command=self._ctdt_manage_hp).pack(side='left', padx=4)
        self._ctdt_refresh()

    def _ctdt_fields(self):
        khoas = self.db.get_all_khoa()
        k_names = [''] + [k['ten'] for k in khoas]
        self._ctdt_k_map = {'': None, **{k['ten']: k['id'] for k in khoas}}
        return [
            ('ten', 'Tên chương trình đào tạo', 'entry', {}),
            ('bac', 'Bậc đào tạo', 'combo', {'values': ['Đại học', 'Thạc sĩ', 'Tiến sĩ']}),
            ('khoa', 'Khoa/Bộ môn chủ quản', 'combo', {'values': k_names}),
        ]

    def _ctdt_refresh(self):
        self.ctdt_tree.delete(*self.ctdt_tree.get_children())
        majors = self.db.get_all_ctdt()
        for major in majors:
            m_iid = f"ctdt_{major['id']}"
            self.ctdt_tree.insert('', 'end', iid=m_iid,
                                  values=(major['ten'], major['bac'] or '', major['ten_khoa'] or ''),
                                  tags=('major',), open=True)
            cns = self.db.get_chuyen_nganh_by_ctdt(major['id'])
            for cn in cns:
                cn_iid = f"cn_{cn['id']}"
                self.ctdt_tree.insert(m_iid, 'end', iid=cn_iid,
                                      values=(cn['ten'], '', ''),
                                      tags=('minor',))

    def _ctdt_get_selection(self):
        sel = self.ctdt_tree.selection()
        if not sel: return None, None, None
        iid = sel[0]
        if iid.startswith('ctdt_'):
            return 'major', int(iid.replace('ctdt_', '')), iid
        elif iid.startswith('cn_'):
            return 'minor', int(iid.replace('cn_', '')), iid
        return None, None, None

    def _ctdt_add(self):
        dlg = RowEditDialog(self, 'Thêm Ngành (CTĐT)', self._ctdt_fields())
        if dlg.result:
            kid = self._ctdt_k_map.get(dlg.result.pop('khoa', ''))
            self.db.add_ctdt(dlg.result['ten'], dlg.result.get('bac', 'Đại học'), kid)
            self._ctdt_refresh()

    def _ctdt_add_cn(self):
        type, id, iid = self._ctdt_get_selection()
        if not id:
            show_modern_warning(self, 'Cảnh báo', 'Vui lòng chọn một Ngành để thêm Chuyên ngành.')
            return
        
        cid = id
        if type == 'minor':
            # Nếu đang chọn chuyên ngành, lấy ngành cha
            parent_iid = self.ctdt_tree.parent(iid)
            cid = int(parent_iid.replace('ctdt_', ''))

        dlg = RowEditDialog(self, 'Thêm chuyên ngành mới', [('ten', 'Tên chuyên ngành', 'entry', {})])
        if dlg.result:
            self.db.add_chuyen_nganh(cid, dlg.result['ten'].strip())
            self._ctdt_refresh()

    def _ctdt_edit(self):
        type, id, iid = self._ctdt_get_selection()
        if not id: return
        
        if type == 'major':
            row = next((dict(r) for r in self.db.get_all_ctdt() if r['id'] == id), None)
            if not row: return
            init = {**row, 'khoa': row.get('ten_khoa') or ''}
            dlg = RowEditDialog(self, 'Sửa Ngành', self._ctdt_fields(), initial=init)
            if dlg.result:
                kid = self._ctdt_k_map.get(dlg.result.pop('khoa', ''))
                self.db.update_ctdt(id, dlg.result['ten'], dlg.result['bac'], kid)
                self._ctdt_refresh()
        else:
            # Sửa chuyên ngành
            vals = self.ctdt_tree.item(iid, 'values')
            row = {'ten': vals[0]}
            dlg = RowEditDialog(self, 'Sửa chuyên ngành', [('ten', 'Tên chuyên ngành', 'entry', {})], initial=row)
            if dlg.result:
                self.db.update_chuyen_nganh(id, dlg.result['ten'].strip())
                self._ctdt_refresh()

    def _ctdt_delete(self):
        sel = self.ctdt_tree.selection()
        if not sel: return
        count = len(sel)
        msg = f"Xóa {count} mục đã chọn?\nLưu ý: Xóa Ngành sẽ xóa tất cả Chuyên ngành thuộc ngành đó."
        if ask_modern_yesno(self, 'Xác nhận', msg):
            for iid in sel:
                if iid.startswith('ctdt_'):
                    cid = int(iid.replace('ctdt_', ''))
                    self.db.delete_ctdt(cid)
                elif iid.startswith('cn_'):
                    # Chỉ xóa nếu chuyên ngành vẫn tồn tại (trường hợp cha nó chưa bị xóa ở bước trên)
                    try:
                        mid = int(iid.replace('cn_', ''))
                        self.db.delete_chuyen_nganh(mid)
                    except: pass
            self._ctdt_refresh()

    def _ctdt_manage_hp(self):
        type, id, iid = self._ctdt_get_selection()
        if not id: return
        cid = id
        if type == 'minor':
            cid = int(self.ctdt_tree.parent(iid).replace('ctdt_', ''))
        
        row = next((dict(r) for r in self.db.get_all_ctdt() if r['id'] == cid), None)
        _CtdtHpManagerDialog(self, self.db, cid, row['ten'])

    def _ctdt_manage_po(self):
        type, id, iid = self._ctdt_get_selection()
        if not id: return
        cid = id
        if type == 'minor':
            cid = int(self.ctdt_tree.parent(iid).replace('ctdt_', ''))
            
        row = next((dict(r) for r in self.db.get_all_ctdt() if r['id'] == cid), None)
        _PoManagerDialog(self, cid, row['ten'])

    def _ctdt_manage_plo(self):
        type, id, iid = self._ctdt_get_selection()
        if not id: return
        cid = id
        if type == 'minor':
            cid = int(self.ctdt_tree.parent(iid).replace('ctdt_', ''))
            
        row = next((dict(r) for r in self.db.get_all_ctdt() if r['id'] == cid), None)
        _PloManagerDialog(self, cid, row['ten'])

    # ── HOC LIEU (TAI LIEU BANK) ─────────────────────────────────────────────
    def _build_hl_tab(self, nb):
        frm = tb.Frame(nb, padding=10)
        nb.add(frm, text='📚 Thư viện Học liệu')
        # Search
        sf = tb.Frame(frm)
        sf.pack(fill='x', pady=(0, 4))
        tb.Label(sf, text='🔍 Tìm:', font=('Arial', 10)).pack(side='left')
        self.v_hl_search = tk.StringVar()
        self.v_hl_search.trace_add('write', lambda *_: self._hl_refresh())
        tb.Entry(sf, textvariable=self.v_hl_search, width=30,
                  font=('Arial', 10)).pack(side='left', padx=4)

        cols   = ('ten', 'tac_gia', 'nam_xb', 'nha_xb', 'loai')
        heads  = ('Tên sách', 'Tác giả', 'Năm XB', 'Nhà xuất bản', 'Loại')
        widths = (250, 150, 80, 180, 100)
        tf, self.hl_tree = make_tree(frm, cols, heads, widths, height=16, db=self.db, table_id='shared_hl')
        tf.pack(fill='both', expand=True)
        self.hl_tree.bind('<Double-1>', lambda _: self._hl_edit())

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=4)
        tb.Button(bf, text='➕ Thêm mới', command=self._hl_add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',       command=self._hl_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',       command=self._hl_delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._hl_import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        self._hl_refresh()

    def _hl_fields(self):
        return [
            ('ten',       'Tên giáo trình/sách', 'entry', {}),
            ('tac_gia',   'Tác giả',              'entry', {}),
            ('nam_xb',    'Năm xuất bản',         'entry', {}),
            ('nha_xb',    'Nhà xuất bản',         'entry', {}),
            ('loai',      'Loại tài liệu',        'combo', {'values': ['Giáo trình', 'Tài liệu tham khảo', 'Khác']}),
            ('so_luong_thu_vien', 'Số lượng TV',  'entry', {}),
            ('nuoc_xb',   'Nước xuất bản',         'entry', {}),
        ]

    def _hl_add(self):
        dlg = RowEditDialog(self, 'Thêm học liệu', self._hl_fields())
        if dlg.result:
            ten = dlg.result.get('ten', '').strip()
            tac_gia = dlg.result.get('tac_gia', '').strip()
            # Kiểm tra trùng lặp
            all_hl = self.db.get_all_tai_lieu()
            dup = next((h for h in all_hl if h['ten'] == ten and h['tac_gia'] == tac_gia), None)
            if dup:
                msg = f"Cảnh báo: Học liệu '{ten}' của tác giả '{tac_gia}' đã tồn tại.\nBạn có chắc chắn muốn thêm trùng lặp không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return
            self.db.add_tai_lieu(dlg.result)
            self._hl_refresh()

    def _hl_edit(self):
        sel = self.hl_tree.selection()
        if not sel: return
        hl_id = self._hl_ids[int(sel[0])]
        row = next((dict(r) for r in self.db.get_all_tai_lieu() if r['id'] == hl_id), None)
        if not row: return
        dlg = RowEditDialog(self, 'Sửa học liệu', self._hl_fields(), initial=row)
        if dlg.result:
            ten = dlg.result.get('ten', '').strip()
            tac_gia = dlg.result.get('tac_gia', '').strip()
            # Kiểm tra trùng lặp
            all_hl = self.db.get_all_tai_lieu()
            dup = next((h for h in all_hl if h['id'] != hl_id and h['ten'] == ten and h['tac_gia'] == tac_gia), None)
            if dup:
                msg = f"Cảnh báo: Học liệu '{ten}' đã tồn tại trùng với dữ liệu khác.\nBạn có muốn tiếp tục cập nhật?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return
            self.db.update_tai_lieu(hl_id, dlg.result)
            self._hl_refresh()

    def _hl_refresh(self):
        self.hl_tree.delete(*self.hl_tree.get_children())
        kw = self.v_hl_search.get().lower()
        self._hl_ids = []
        for i, r in enumerate(self.db.get_all_tai_lieu()):
            if kw and kw not in (r['ten'] or '').lower() and kw not in (r['tac_gia'] or '').lower():
                continue
            tag = 'even' if i % 2 == 0 else 'odd'
            self.hl_tree.insert('', 'end', iid=str(i),
                                 values=(r['ten'], r['tac_gia'] or '',
                                         r['nam_xb'] or '', r['nha_xb'] or '',
                                         r['loai'] or ''), tags=(tag,))
            self._hl_ids.append(r['id'])


    def _hl_delete(self):
        sel = self.hl_tree.selection()
        if not sel: return
        count = len(sel)
        if ask_modern_yesno(self, 'Xác nhận', f"Xóa {count} tài liệu đã chọn khỏi kho dùng chung?"):
            import sqlite3
            success, failed = 0, 0
            for iid in sel:
                hl_id = self._hl_ids[int(iid)]
                try:
                    self.db.delete_tai_lieu(hl_id)
                    success += 1
                except sqlite3.IntegrityError:
                    failed += 1
            self._hl_refresh()
            if failed > 0:
                show_modern_warning(self, 'Kết quả', f"Đã xóa {success} tài liệu. Thất bại {failed} do đang được sử dụng.")

    # ── HỌC PHẦN (DANH MỤC TỔNG) ─────────────────────────────────────────────
    def _build_hp_tab(self, nb):
        frm = tb.Frame(nb, padding=10)
        nb.add(frm, text='📚 Danh mục Học phần')

        self.v_search_hp = tk.StringVar()
        self.v_search_hp.trace_add('write', lambda *_: self._hp_refresh())
        sf = tb.Frame(frm)
        sf.pack(fill='x', pady=(0, 6))
        tb.Label(sf, text='🔍 Tìm kiếm:').pack(side='left')
        tb.Entry(sf, textvariable=self.v_search_hp).pack(side='left', fill='x', expand=True, padx=6)

        cols   = ('ma', 'ten_viet', 'so_tin_chi', 'ten_khoa')
        heads  = ('Mã HP', 'Tên tiếng Việt', 'Tín chỉ', 'Khoa quản lý')
        widths = (100, 350, 70, 250)
        tf, self.hp_tree = make_tree(frm, cols, heads, widths, height=16, db=self.db, table_id='shared_hp_root')
        tf.pack(fill='both', expand=True)

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=8)
        tb.Button(bf, text='➕ Thêm học phần', command=self._hp_add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',           command=self._hp_edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',           command=self._hp_delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._hp_import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        
        self._hp_refresh()

    def _hp_fields(self):
        khoas = self.db.get_all_khoa()
        k_names = [''] + [k['ten'] for k in khoas]
        self._hp_k_map = {'': None, **{k['ten']: k['id'] for k in khoas}}
        return [
            ('ma', 'Mã học phần', 'entry', {}),
            ('ten_viet', 'Tên tiếng Việt', 'entry', {}),
            ('ten_anh', 'Tên tiếng Anh', 'entry', {}),
            ('so_tin_chi', 'Số tín chỉ', 'entry', {}),
            ('khoa', 'Khoa quản lý', 'combo', {'values': k_names}),
        ]

    def _hp_refresh(self):
        self.hp_tree.delete(*self.hp_tree.get_children())
        kw = self.v_search_hp.get().strip()
        rows = self.db.search_hoc_phan(kw)
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.hp_tree.insert('', 'end', iid=str(r['id']),
                                values=(r['ma'] or '', r['ten_viet'], r['so_tin_chi'] or '', r['ten_khoa'] or ''),
                                tags=(tag,))
        self._current_hp_rows = rows

    def _hp_add(self):
        dlg = RowEditDialog(self, 'Thêm học phần mới', self._hp_fields())
        if dlg.result:
            ma = dlg.result.get('ma', '').strip()
            # Kiểm tra trùng lặp
            all_hp = self.db.get_all_hoc_phan()
            dup = next((h for h in all_hp if ma and h['ma'] == ma), None)
            if dup:
                msg = f"Cảnh báo: Mã học phần '{ma}' đã tồn tại cho '{dup['ten_viet']}'.\nBạn có chắc chắn muốn thêm trùng lặp không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return
                    
            data = dlg.result.copy()
            kid = self._hp_k_map.get(data.pop('khoa', ''))
            data['khoa_id'] = kid
            self.db.add_hoc_phan(data)
            self._hp_refresh()

    def _hp_edit(self):
        sel = self.hp_tree.selection()
        if not sel: return
        iid = int(sel[0])
        old_hp = next(dict(r) for r in self._current_hp_rows if r['id'] == iid)
        init = {**old_hp, 'khoa': old_hp.get('ten_khoa') or ''}
        dlg = RowEditDialog(self, 'Sửa thông tin học phần', self._hp_fields(), initial=init)
        if dlg.result:
            ma = dlg.result.get('ma', '').strip()
            # Kiểm tra trùng lặp (trừ chính nó)
            all_hp = self.db.get_all_hoc_phan()
            dup = next((h for h in all_hp if h['id'] != iid and ma and h['ma'] == ma), None)
            if dup:
                msg = f"Cảnh báo: Mã học phần '{ma}' đã tồn tại cho '{dup['ten_viet']}'.\nBạn có muốn tiếp tục cập nhật không?"
                if not ask_modern_yesno(self, "Trùng lặp dữ liệu", msg):
                    return

            data = dlg.result.copy()
            kid = self._hp_k_map.get(data.pop('khoa', ''))
            data['khoa_id'] = kid
            self.db.update_hoc_phan(iid, data)
            self._hp_refresh()

    def _hp_delete(self):
        sel = self.hp_tree.selection()
        if not sel: return
        count = len(sel)
        if ask_modern_yesno(self, 'Xác nhận', f"Xóa {count} học phần đã chọn?\nLưu ý: Thao tác này có thể ảnh hưởng đến các đề cương và CTĐT liên quan."):
            success = 0
            for iid in sel:
                self.db.delete_hoc_phan(int(iid))
                success += 1
            self._hp_refresh()
            if success > 0:
                show_modern_info(self, "Thành công", f"Đã xóa {success} học phần.")

    # ── EXCEL IMPORT HELPERS ────────────────────────────────────────────────
    def _read_excel(self, title, cols_info):
        """
        cols_info: list of (field_name, col_index, converter_fn)
        """
        path = filedialog.askopenfilename(title=title, filetypes=[("Excel files", "*.xlsx")])
        if not path: return None
        
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            ws = wb.active
            data = []
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
                if not any(row): continue
                item = {}
                for field, idx, conv in cols_info:
                    val = row[idx] if idx < len(row) else None
                    try:
                        item[field] = conv(val) if conv and val is not None else val
                    except:
                        item[field] = val
                data.append(item)
            return data
        except Exception as e:
            show_modern_error(self, "Lỗi đọc file", f"Không thể đọc file Excel: {e}")
            return None

    def _khoa_import_excel(self):
        cols = [('ma', 0, str), ('ten', 1, str)]
        data = self._read_excel("Nhập danh sách Khoa/Đơn vị (Cột 1: Mã, Cột 2: Tên)", cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào cơ sở dữ liệu?"):
                success, skip = 0, 0
                all_khoa = self.db.get_all_khoa()
                existing_mas = {k['ma'] for k in all_khoa if k['ma']}
                existing_tens = {k['ten'].lower() for k in all_khoa}
                
                for item in data:
                    m = item['ma'].strip() if item['ma'] else None
                    t = item['ten'].strip() if item['ten'] else ""
                    if not t: continue
                    if (m and m in existing_mas) or (t.lower() in existing_tens):
                        skip += 1
                        continue
                    self.db.add_khoa(m, t)
                    success += 1
                self._khoa_refresh()
                show_modern_info(self, "Hoàn thành", f"Đã nhập {success} đơn vị. Bỏ qua {skip} mục trùng lặp.")

    def _hp_import_excel(self):
        # 0: Mã, 1: Tên Việt, 2: Tên Anh, 3: Tín chỉ, 4: Tên Khoa
        cols = [('ma', 0, str), ('ten_viet', 1, str), ('ten_anh', 2, str), 
                ('so_tin_chi', 3, lambda v: int(v) if v else 0), ('khoa_name', 4, str)]
        data = self._read_excel("Nhập danh mục Học phần (Mã, Tên Việt, Tên Anh, Tín chỉ, Tên Khoa)", cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào cơ sở dữ liệu?"):
                khoas = self.db.get_all_khoa()
                k_map = {k['ten'].lower(): k['id'] for k in khoas}
                all_hp = self.db.get_all_hoc_phan()
                existing_mas = {h['ma'] for h in all_hp if h['ma']}
                
                success, skip = 0, 0
                for item in data:
                    ma = item.get('ma', '').strip() if item.get('ma') else None
                    if ma and ma in existing_mas:
                        skip += 1
                        continue
                    
                    k_name = item.pop('khoa_name', '').strip().lower() if item.get('khoa_name') else ""
                    item['khoa_id'] = k_map.get(k_name)
                    self.db.add_hoc_phan(item)
                    success += 1
                self._hp_refresh()
                show_modern_info(self, "Hoàn thành", f"Đã nhập {success} học phần. Bỏ qua {skip} mục trùng mã.")

    def _gv_import_excel(self):
        # 0: Mã CB, 1: Họ tên, 2: Giới tính, 3: Ngày sinh, 4: Học vị, 5: Chức danh, 6: Chức vụ, 7: Đơn vị, 8: Email, 9: SĐT, 10: CC/CMND, 11: Địa chỉ,
        # 12: Năm phong CD, 13: Trình độ CM, 14: Cơ sở đào tạo, 15: Năm tốt nghiệp, 16: Ngành đào tạo, 17: Ngày tuyển dụng, 18: Mã BH, 19: Kinh nghiệm
        cols = [
            ('ma_can_bo', 0, str), ('ho_ten', 1, str), ('gioi_tinh', 2, str),
            ('ngay_sinh', 3, str), ('hoc_vi', 4, str), ('chuc_danh', 5, str),
            ('chuc_vu', 6, str), ('khoa_name', 7, str), ('email', 8, str),
            ('sdt', 9, str), ('cmnd_cccd', 10, str), ('dia_chi', 11, str),
            ('nam_phong_chuc_danh', 12, str), ('trinh_do_chuyen_mon', 13, str), 
            ('co_so_dao_tao', 14, str), ('nam_tot_nghiep', 15, str),
            ('nganh_dao_tao', 16, str), ('ngay_tuyen_dung', 17, str),
            ('ma_so_bao_hiem', 18, str), ('so_nam_kinh_nghiem', 19, str)
        ]
        msg = "Nhập giảng viên từ Excel (20 cột dữ liệu từ Mã CB đến Kinh nghiệm)"
        data = self._read_excel(msg, cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào cơ sở dữ liệu?"):
                khoas = self.db.get_all_khoa()
                k_map = {k['ten'].lower(): k['id'] for k in khoas}
                
                success = 0
                for item in data:
                    if not item.get('ho_ten'): continue
                    kn = item.pop('khoa_name', '').strip().lower() if item.get('khoa_name') else ""
                    item['khoa_id'] = k_map.get(kn)
                    self.db.add_giang_vien(item)
                    success += 1
                self._gv_refresh()
                show_modern_info(self, "Hoàn thành", f"Đã nhập {success} giảng viên.")

    def _hl_import_excel(self):
        # 0: Tên, 1: Tác giả, 2: Năm, 3: NXB, 4: Loại
        cols = [
            ('ten', 0, str), ('tac_gia', 1, str), ('nam_xb', 2, str),
            ('nha_xb', 3, str), ('loai', 4, str)
        ]
        data = self._read_excel("Nhập thư viện Học liệu (Tên, Tác giả, Năm XB, NXB, Loại)", cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào cơ sở dữ liệu?"):
                success = 0
                for item in data:
                    if not item.get('ten'): continue
                    self.db.add_tai_lieu(item)
                    success += 1
                self._hl_refresh()
                show_modern_info(self, "Hoàn thành", f"Đã nhập {success} học liệu.")


# ─── Dialog Quản lý học phần trong CTĐT ───────────────────────────────────────
class _CtdtHpManagerDialog(tb.Toplevel):
    def __init__(self, parent, db, ctdt_id, ctdt_name):
        super().__init__(parent)
        set_window_icon(self)
        self.db = db
        self.ctdt_id = ctdt_id
        self.title(f'Quản lý Học phần: {ctdt_name}')
        self.geometry('1100x750')
        self.grab_set()
        self._build()
        self._refresh()

    def _build(self):
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        tb.Label(frm, text='Danh sách học phần thuộc chương trình:', 
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 6))

        cols   = ('stt', 'ma', 'ten_viet', 'khoi', 'cn')
        heads  = ('STT', 'Mã HP', 'Tên học phần', 'Khối kiến thức', 'Chuyên ngành')
        widths = (40, 100, 350, 150, 150)
        from sections.base_section import make_tree
        tf, self.tree = make_tree(frm, cols, heads, widths, height=18, db=self.db, table_id='ctdt_hp_manager')
        tf.pack(fill='both', expand=True)

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=8)
        tb.Button(bf, text='➕ Thêm môn vào CTĐT', command=self._add_hp).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa phân loại môn', command=self._edit_hp).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Loại khỏi CTĐT', command=self._remove_hp).pack(side='left', padx=4)
        
        tb.Button(self, text='Đóng', command=self.destroy).pack(pady=6)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = self.db.get_hp_of_ctdt(self.ctdt_id)
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                             values=(i+1, r['ma'] or '', r['ten_viet'], 
                                     r['khoi_kien_thuc'] or '', r['chuyen_nganh'] or ''),
                             tags=(tag,))
        self._current_rows = rows

    def _add_hp(self):
        # Mở dialog chọn môn từ kho học phần
        dlg = _HpPickDialog(self, self.db)
        if dlg.result:
            hp = dlg.result
            # Thêm vào bảng liên kết
            exists = self.db.conn.execute(
                "SELECT id FROM ctdt_hoc_phan WHERE ctdt_id=? AND hp_id=?", 
                (self.ctdt_id, hp['id'])).fetchone()
            if exists:
                show_modern_warning(self, 'Cảnh báo', 'Học phần này đã có trong chương trình.')
                return
            
            # Lấy danh sách chuyên ngành của CTĐT này
            cn_list = [c['ten'] for c in self.db.get_chuyen_nganh_by_ctdt(self.ctdt_id)]
            
            # Dialog chọn khối kiến thức và chuyên ngành
            dlg_info = RowEditDialog(self, 'Phân loại học phần trong CTĐT', [
                ('khoi_kien_thuc', 'Khối kiến thức', 'combo', {'values': KHOI_KIEN_THUC}),
                ('chuyen_nganh',   'Chuyên ngành (Nếu có)', 'combo', {'values': [''] + cn_list, 'state': 'normal'}),
            ], initial={'khoi_kien_thuc': 'Ngành'})
            
            if dlg_info.result:
                self.db.conn.execute("""
                    INSERT INTO ctdt_hoc_phan(ctdt_id, hp_id, khoi_kien_thuc, chuyen_nganh)
                    VALUES(?,?,?,?)
                """, (self.ctdt_id, hp['id'], 
                      dlg_info.result['khoi_kien_thuc'], dlg_info.result.get('chuyen_nganh', '')))
                self.db.conn.commit()
                self._refresh()

    def _edit_hp(self):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        r = self._current_rows[idx]
        # Lấy danh sách chuyên ngành của CTĐT này
        cn_list = [c['ten'] for c in self.db.get_chuyen_nganh_by_ctdt(self.ctdt_id)]
        
        dlg = RowEditDialog(self, 'Sửa phân loại', [
            ('khoi_kien_thuc', 'Khối kiến thức', 'combo', {'values': KHOI_KIEN_THUC}),
            ('chuyen_nganh',   'Chuyên ngành (Nếu có)', 'combo', {'values': [''] + cn_list, 'state': 'normal'}),
        ], initial={'khoi_kien_thuc': r['khoi_kien_thuc'], 'chuyen_nganh': r['chuyen_nganh']})
        
        if dlg.result:
            self.db.conn.execute("""
                UPDATE ctdt_hoc_phan SET khoi_kien_thuc=?, chuyen_nganh=? WHERE id=?
            """, (dlg.result['khoi_kien_thuc'], dlg.result.get('chuyen_nganh', ''), r['id']))
            self.db.conn.commit()
            self._refresh()

    def _remove_hp(self):
        sel = self.tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Loại học phần này khỏi chương trình?'):
            idx = int(sel[0])
            rid = self._current_rows[idx]['id']
            self.db.conn.execute("DELETE FROM ctdt_hoc_phan WHERE id=?", (rid,))
            self.db.conn.commit()
            self._refresh()


class _HpPickDialog(tb.Toplevel):
    """Dialog chọn học phần từ danh sách tổng."""
    def __init__(self, parent, db):
        super().__init__(parent)
        set_window_icon(self)
        self.db = db
        self.title('Chọn học phần')
        self.geometry('800x600')
        self.result = None
        self.grab_set()
        self._build()
        self._refresh()

    def _build(self):
        frm = tb.Frame(self, padding=10)
        frm.pack(fill='both', expand=True)
        
        tb.Label(frm, text='Tìm học phần:').pack(anchor='w')
        self.v_search = tk.StringVar()
        self.v_search.trace_add('write', lambda *_: self._refresh())
        tb.Entry(frm, textvariable=self.v_search).pack(fill='x', pady=4)
        
        cols   = ('ma', 'ten')
        heads  = ('Mã HP', 'Tên học phần')
        widths = (100, 500)
        from sections.base_section import make_tree
        tf, self.tree = make_tree(frm, cols, heads, widths, height=12, db=self.db, table_id='hp_pick_dialog')
        tf.pack(fill='both', expand=True)
        
        bf = tb.Frame(self, padding=8)
        bf.pack(fill='x')
        tb.Button(bf, text='✔ Chọn', command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='Hủy',     command=self.destroy).pack(side='right', padx=4)

    def _refresh(self):
        kw = self.v_search.get()
        rows = self.db.search_hoc_phan(kw)
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i), values=(r['ma'] or '', r['ten_viet']), tags=(tag,))
        self._current_rows = rows

    def _ok(self):
        sel = self.tree.selection()
        if sel:
            self.result = dict(self._current_rows[int(sel[0])])
            self.destroy()


# ─── PO Manager Dialog ───────────────────────────────────────────────────────
class _PoManagerDialog(tb.Toplevel):
    def __init__(self, parent, ctdt_id, ctdt_name):
        super().__init__(parent)
        set_window_icon(self)
        self.db = parent.db
        self.ctdt_id = ctdt_id
        abbr_po = self.db.get_config('abbr_po', 'PO')
        self.title(f'Quản lý Mục tiêu ({abbr_po}) - {ctdt_name}')
        self.geometry('800x550')
        self.grab_set()
        
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        
        cols = ('ma', 'mo_ta')
        heads = (f'Mã {abbr_po}', f'Mô tả Mục tiêu ({abbr_po})')
        widths = (100, 450)
        from sections.base_section import make_tree
        self.tf, self.tree = make_tree(frm, cols, heads, widths, height=12, db=self.db, table_id='po_manager')
        self.tf.pack(fill='both', expand=True)
        
        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=8)
        self.btn_add = tb.Button(bf, text=f'➕ Thêm {abbr_po}', command=self._add)
        self.btn_add.pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',      command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',      command=self._delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        tb.Button(bf, text='🔢 Tự đánh số', command=self._auto_number, bootstyle='warning-outline').pack(side='right', padx=4)
        
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._items = self.db.get_po_by_ctdt(self.ctdt_id)
        # Sắp xếp tự nhiên theo mã
        self._items.sort(key=lambda x: natural_sort_key(x['ma']))
        
        for i, r in enumerate(self._items):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i), values=(r['ma'], r['mo_ta']), tags=(tag,))

    def _auto_number(self):
        abbr_po = self.db.get_config('abbr_po', 'PO')
        if not self._items: return
        if not ask_modern_yesno(self, 'Xác nhận', f'Tự động đánh lại mã {abbr_po} từ {abbr_po}1 đến {abbr_po}n?'):
            return
        for i, r in enumerate(self._items):
            new_ma = f"{abbr_po}{i+1}"
            if r['ma'] != new_ma:
                self.db.update_po(r['id'], new_ma, r['mo_ta'])
        self._refresh()

    def _add(self):
        abbr_po = self.db.get_config('abbr_po', 'PO')
        dlg = RowEditDialog(self, f'Thêm {abbr_po}', [('ma',f'Mã {abbr_po}','entry',{}), ('mo_ta','Mô tả','text',{})])
        if dlg.result:
            self.db.add_po(self.ctdt_id, dlg.result['ma'], dlg.result['mo_ta'])
            self._refresh()

    def _edit(self):
        abbr_po = self.db.get_config('abbr_po', 'PO')
        sel = self.tree.selection()
        if not sel: return
        row = self._items[int(sel[0])]
        dlg = RowEditDialog(self, f'Sửa {abbr_po}', [('ma',f'Mã {abbr_po}','entry',{}), ('mo_ta','Mô tả','text',{})], initial=dict(row))
        if dlg.result:
            self.db.update_po(row['id'], dlg.result['ma'], dlg.result['mo_ta'])
            self._refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        if ask_modern_yesno(self, 'Xác nhận', 'Xóa PO này?'):
            self.db.delete_po(self._items[int(sel[0])]['id'])
            self._refresh()

    def _import_excel(self):
        if not hasattr(self.master, '_read_excel'): return
        cols = [('ma', 0, str), ('mo_ta', 1, str)]
        data = self.master._read_excel("Nhập danh sách PO (Mã PO, Mô tả)", cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào CTĐT này?"):
                success = 0
                for item in data:
                    if not item.get('ma'): continue
                    self.db.add_po(self.ctdt_id, item['ma'], item['mo_ta'])
                    success += 1
                self._refresh()
                show_modern_info(self, "Thành công", f"Đã nhập {success} mục PO.")


# ─── PLO & PI Manager Dialog (Hierarchical Tree) ───────────────────────────
class _PloManagerDialog(tb.Toplevel):
    def __init__(self, parent, ctdt_id, ctdt_name):
        super().__init__(parent)
        set_window_icon(self)
        self.db = parent.db
        self.ctdt_id = ctdt_id
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        abbr_pi = self.db.get_config('abbr_pi', 'PI')
        self.title(f'Quản lý Chuẩn đầu ra ({abbr_plo}) & Chỉ báo ({abbr_pi}) - {ctdt_name}')
        self.geometry('1000x750')
        self.grab_set()
        
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        
        tb.Label(frm, text=f'Danh sách {abbr_plo} và các Chỉ báo ({abbr_pi}) tương ứng:', 
                  font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 6))

        cols = ('ma', 'mo_ta')
        heads = ('Mã', f'Nội dung {abbr_plo} / Chỉ báo ({abbr_pi})')
        widths = (120, 600)
        from sections.base_section import make_tree
        self.tf, self.tree = make_tree(frm, cols, heads, widths, height=18, db=self.db, table_id='plo_manager')
        self.tf.pack(fill='both', expand=True)
        
        self.tree.configure(show='tree headings')
        self.tree.column('#0', width=40, minwidth=40, stretch=False)
        self.tree.heading('#0', text='')

        self.tree.tag_configure('plo', background='#4682B4', foreground='white', font=('Arial', 10, 'bold'))
        self.tree.tag_configure('pi',  background='#262626', foreground='white')
        
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        abbr_pi = self.db.get_config('abbr_pi', 'PI')

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=8)
        tb.Button(bf, text=f'➕ Thêm {abbr_plo}', command=self._add_plo).pack(side='left', padx=4)
        tb.Button(bf, text=f'🎯 Thêm {abbr_pi}',  command=self._add_pi).pack(side='left', padx=4)
        tb.Separator(bf, orient='vertical').pack(side='left', padx=10, fill='y')
        tb.Button(bf, text='✏ Sửa',      command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',      command=self._delete).pack(side='left', padx=4)
        tb.Button(bf, text='📥 Nhập từ Excel', command=self._import_excel, bootstyle='info-outline').pack(side='left', padx=4)
        tb.Button(bf, text='🔢 Tự đánh số', command=self._auto_number, bootstyle='warning-outline').pack(side='right', padx=4)
        
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._plo_items = self.db.get_plo_by_ctdt(self.ctdt_id)
        # Sắp xếp tự nhiên theo mã PLO
        self._plo_items.sort(key=lambda x: natural_sort_key(x['ma']))
        
        for plo in self._plo_items:
            plo_iid = f"plo_{plo['id']}"
            self.tree.insert('', 'end', iid=plo_iid, 
                             values=(plo['ma'], plo['mo_ta']), 
                             tags=('plo',), open=True)
            
            pis = self.db.get_pi_by_plo(plo['id'])
            # Sắp xếp tự nhiên theo mã PI
            pis.sort(key=lambda x: natural_sort_key(x['ma']))
            for pi in pis:
                pi_iid = f"pi_{pi['id']}"
                self.tree.insert(plo_iid, 'end', iid=pi_iid,
                                 values=(pi['ma'], pi['mo_ta']),
                                 tags=('pi',))

    def _auto_number(self):
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        abbr_pi = self.db.get_config('abbr_pi', 'PI')
        if not self._plo_items: return
        if not ask_modern_yesno(self, 'Xác nhận', f'Tự động đánh lại mã cho tất cả {abbr_plo} và {abbr_pi}?'):
            return
        
        for i, plo in enumerate(self._plo_items):
            new_plo_ma = f"{abbr_plo}{i+1}"
            if plo['ma'] != new_plo_ma:
                self.db.update_plo(plo['id'], new_plo_ma, plo['mo_ta'])
            
            pis = self.db.get_pi_by_plo(plo['id'])
            # Sắp xếp PI hiện tại trước khi đánh số
            pis.sort(key=lambda x: natural_sort_key(x['ma']))
            for j, pi in enumerate(pis):
                new_pi_ma = f"{abbr_pi}{i+1}.{j+1}"
                if pi['ma'] != new_pi_ma:
                    self.db.update_pi(pi['id'], new_pi_ma, pi['mo_ta'])
        
        self._refresh()

    def _get_selection(self):
        sel = self.tree.selection()
        if not sel: return None, None, None
        iid = sel[0]
        if iid.startswith('plo_'):
            pid = int(iid.replace('plo_', ''))
            return 'plo', pid, iid
        elif iid.startswith('pi_'):
            pi_id = int(iid.replace('pi_', ''))
            return 'pi', pi_id, iid
        return None, None, None

    def _add_plo(self):
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        dlg = RowEditDialog(self, f'Thêm {abbr_plo} mới', [('ma',f'Mã {abbr_plo}','entry',{}), ('mo_ta','Mô tả','text',{})])
        if dlg.result:
            self.db.add_plo(self.ctdt_id, dlg.result['ma'], dlg.result['mo_ta'])
            self._refresh()

    def _add_pi(self):
        abbr_plo = self.db.get_config('abbr_plo', 'PLO')
        abbr_pi = self.db.get_config('abbr_pi', 'PI')
        type, id, iid = self._get_selection()
        if not id:
            show_modern_warning(self, 'Cảnh báo', f'Vui lòng chọn một {abbr_plo} để thêm {abbr_pi}.')
            return
        
        plo_id = id
        if type == 'pi':
            parent_iid = self.tree.parent(iid)
            plo_id = int(parent_iid.replace('plo_', ''))

        dlg = RowEditDialog(self, f'Thêm {abbr_pi}', [('ma',f'Mã {abbr_pi}','entry',{}), ('mo_ta','Mô tả','text',{})])
        if dlg.result:
            self.db.add_pi(plo_id, dlg.result['ma'], dlg.result['mo_ta'])
            self._refresh()

    def _edit(self):
        type, id, iid = self._get_selection()
        if not id: return
        
        if type == 'plo':
            item = dict(next(r for r in self._plo_items if r['id'] == id))
            title = 'Sửa PLO'
            fields = [('ma', 'Mã PLO', 'entry', {}), ('mo_ta', 'Mô tả', 'text', {})]
        else:
            vals = self.tree.item(iid, 'values')
            item = {'ma': vals[0], 'mo_ta': vals[1]}
            title = 'Sửa PI'
            fields = [('ma', 'Mã PI', 'entry', {}), ('mo_ta', 'Mô tả', 'text', {})]

        dlg = RowEditDialog(self, title, fields, initial=item)
        if dlg.result:
            if type == 'plo':
                self.db.update_plo(id, dlg.result['ma'], dlg.result['mo_ta'])
            else:
                self.db.update_pi(id, dlg.result['ma'], dlg.result['mo_ta'])
            self._refresh()

    def _delete(self):
        type, id, iid = self._get_selection()
        if not id: return
        
        msg = 'Xóa PLO này? (Các PI liên quan cũng sẽ bị xóa)' if type == 'plo' else 'Xóa Chỉ báo (PI) này?'
        if ask_modern_yesno(self, 'Xác nhận', msg):
            if type == 'plo':
                self.db.delete_plo(id)
            else:
                self.db.delete_pi(id)
            self._refresh()

    def _import_excel(self):
        if not hasattr(self.master, '_read_excel'): return
        # Hỗ trợ nhập PLO đơn giản trước. Cột 1: Mã, Cột 2: Mô tả
        cols = [('ma', 0, str), ('mo_ta', 1, str)]
        data = self.master._read_excel("Nhập danh sách PLO (Mã PLO, Mô tả)", cols)
        if data:
            if ask_modern_yesno(self, "Xác nhận", f"Tìm thấy {len(data)} dòng. Nhập vào CTĐT này?"):
                success = 0
                for item in data:
                    if not item.get('ma'): continue
                    self.db.add_plo(self.ctdt_id, item['ma'], item['mo_ta'])
                    success += 1
                self._refresh()
                show_modern_info(self, "Thành công", f"Đã nhập {success} mục PLO.")

