import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from sections.base_section import (BaseSection, ScrollableFrame, RowEditDialog,
                                    make_tree, CLR_PRIMARY2, CLR_HDR, CLR_BG)
from utils.ui_utils import AutocompleteCombobox, show_modern_warning
from sections.registry import register_section

TRINH_DO  = ['Đại học', 'Thạc sĩ', 'Tiến sĩ']
LOAI_HP   = ['Bắt buộc', 'Tự chọn']
TINH_CHAT = ['Lý thuyết', 'Thực hành', 'Hỗn hợp', 'Đồ án']
VAI_TRO   = ['chinh', 'tham_gia']
VAI_TRO_LABEL = {'chinh': 'Giảng viên phụ trách chính',
                  'tham_gia': 'Giảng viên tham gia giảng dạy'}
KHOI_KIEN_THUC = ['Đại cương', 'Cơ sở ngành', 'Ngành', 'Chuyên ngành', 'Chuyên sâu đặc thù']


@register_section(order=1, label="1. Thông tin chung")
class Sec1ThongTin(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._gv_rows = []
        self._ctdt_links = []
        self.v_ten_viet = tk.StringVar()
        self.v_ten_anh = tk.StringVar()
        self.v_khoa = tk.StringVar()
        self.v_trinh_do = tk.StringVar(value='Đại học')
        self.v_ma = tk.StringVar()
        self.v_loai = tk.StringVar(value='Bắt buộc')
        self.v_tinh_chat = tk.StringVar(value='Lý thuyết')
        self.v_tc = tk.StringVar(value='3')
        self.v_co_thuc_hanh = tk.IntVar(value=1)
        self.v_nhom_hp_dac_thu = tk.StringVar(value='Thông thường')
        self.v_tq = tk.StringVar()
        self.v_sh = tk.StringVar()
        self.v_tt = tk.StringVar()
        self._time_vars = {
            'gio_lt': tk.StringVar(value='0'),
            'gio_th_tn': tk.StringVar(value='0'),
            'gio_tl': tk.StringVar(value='0'),
            'gio_bt': tk.StringVar(value='0'),
            'gio_tieu_luan': tk.StringVar(value='0'),
            'gio_thuc_tap': tk.StringVar(value='0'),
            'gio_tu_hoc': tk.StringVar(value='0'),
            'tong_gio': tk.StringVar(value='0'),
        }

    def _build_ui(self):
        # ── Scrollable container ─────────────────────────────────────────────
        from utils.undo_redo import UndoManager
        self.undo_mgr = UndoManager()
        
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        p = sf.inner  # parent frame bên trong scroll
        self._extra_parent = p

        # Load dynamic configs FIRST
        levels_str = self.db.get_config('trinh_do', 'Đại học, Thạc sĩ, Tiến sĩ')
        list_levels = [s.strip() for s in levels_str.split(',') if s.strip()]
        
        types_str = self.db.get_config('hp_types', 'Bắt buộc, Tự chọn')
        list_types = [s.strip() for s in types_str.split(',') if s.strip()]
        
        natures_str = self.db.get_config('hp_natures', 'Lý thuyết, Thực hành, Hỗn hợp, Đồ án')
        list_natures = [s.strip() for s in natures_str.split(',') if s.strip()]

        pad = dict(padx=16, pady=4)

        # ── Tiêu đề ──────────────────────────────────────────────────────────
        tb.Label(p, text='1. Thông tin chung về học phần',
                  style='SectionHeader.TLabel'
                  ).grid(row=0, column=0, columnspan=4, sticky='w', padx=16, pady=(12, 4))
        tb.Separator(p, orient='horizontal').grid(
            row=1, column=0, columnspan=4, sticky='ew', padx=16, pady=4)

        # ── 1.1 Thông tin Hành chính ──────────────────────────────────────────
        admin_lf = tb.Labelframe(p, text='1.1. Thông tin hành chính học phần', padding=10)
        admin_lf.grid(row=2, column=0, columnspan=4, sticky='ew', padx=16, pady=8)

        lbl_ten_vn = tb.Label(admin_lf, text='Tên tiếng Việt:', font=('Arial', 10))
        lbl_ten_vn.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ent_ten_vn = tb.Entry(admin_lf, textvariable=self.v_ten_viet, width=60, font=('Arial', 10))
        ent_ten_vn.grid(row=0, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

        lbl_ten_en = tb.Label(admin_lf, text='Tên tiếng Anh:', font=('Arial', 10))
        lbl_ten_en.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ent_ten_en = tb.Entry(admin_lf, textvariable=self.v_ten_anh, width=60, font=('Arial', 10))
        ent_ten_en.grid(row=1, column=1, columnspan=3, sticky='ew', padx=5, pady=5)

        lbl_khoa = tb.Label(admin_lf, text='Khoa quản lý:', font=('Arial', 10))
        lbl_khoa.grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.cb_khoa = AutocompleteCombobox(admin_lf, textvariable=self.v_khoa, width=40, font=('Arial', 10), state='normal')
        self.cb_khoa.grid(row=2, column=1, sticky='ew', padx=5, pady=5)
        
        lbl_trinh_do = tb.Label(admin_lf, text='Bậc đào tạo:', font=('Arial', 10))
        lbl_trinh_do.grid(row=2, column=2, sticky='e', padx=5, pady=5)
        self.cb_trinh_do = AutocompleteCombobox(admin_lf, textvariable=self.v_trinh_do, values=list_levels, width=15, font=('Arial', 10), state='readonly')
        self.cb_trinh_do.grid(row=2, column=3, sticky='w', padx=5, pady=5)
        
        self._register_field('ten_viet', label_widget=lbl_ten_vn, input_widget=ent_ten_vn)
        self._register_field('ten_anh', label_widget=lbl_ten_en, input_widget=ent_ten_en)
        self._register_field('khoa', label_widget=lbl_khoa, input_widget=self.cb_khoa)
        self._register_field('trinh_do', label_widget=lbl_trinh_do, input_widget=self.cb_trinh_do)
        admin_lf.columnconfigure(1, weight=1)

        # ── 1.2 Chương trình Đào tạo ────────────────────────────────────────
        ctdt_lf = tb.Labelframe(p, text='1.2. Ngành đào tạo & Bậc (Chương trình)', padding=10)
        ctdt_lf.grid(row=3, column=0, columnspan=4, sticky='ew', padx=16, pady=8)

        cols_ct   = ('bac', 'ten', 'khoi', 'cn')
        heads_ct  = ('Bậc', 'Chương trình đào tạo', 'Khối kiến thức', 'Chuyên ngành')
        widths_ct = (80, 250, 120, 150)
        self.ct_list_frm, self.ct_tree = make_tree(ctdt_lf, cols_ct, heads_ct, widths_ct, height=3, 
                                                   column_aligns=('center', 'w', 'w', 'center'), 
                                                   db=self.db, table_id='sec1_ctdt',
                                                   undo_manager=self.undo_mgr, on_change=self.mark_modified)
        self.ct_list_frm.pack(fill='x', expand=True)
        self.ct_tree.bind('<Double-1>', lambda _e: self._ct_edit())
        
        ct_bf = tb.Frame(ctdt_lf)
        ct_bf.pack(fill='x', pady=(4, 0))
        tb.Button(ct_bf, text='➕ Gán vào CTĐT', command=self._ct_add, bootstyle='outline-primary').pack(side='left', padx=2)
        tb.Button(ct_bf, text='✏ Sửa',       command=self._ct_edit, bootstyle='outline-info').pack(side='left', padx=2)
        tb.Button(ct_bf, text='🗑 Xóa',       command=self._ct_remove, bootstyle='outline-danger').pack(side='left', padx=2)

        r = 4

        p.columnconfigure(1, weight=1)

        # ── 1.3 Giảng viên ──────────────────────────────────────────────────
        gv_lf = tb.Labelframe(p, text='1.3. Các giảng viên phụ trách học phần', padding=10)
        gv_lf.grid(row=r, column=0, columnspan=4, sticky='ew', padx=16, pady=8)

        cols   = ('stt', 'vai_tro', 'ho_ten', 'ma_can_bo', 'chuc_vu', 'don_vi', 'sdt', 'email')
        heads  = ('TT', 'Vai trò', 'Học hàm, Học vị, Họ và tên', 'Mã CB', 'Chức vụ', 'Đơn vị công tác', 'Số ĐT', 'Email')
        widths = (35, 140, 250, 80, 120, 150, 110, 180)
        aligns = ('center', 'w', 'w', 'center', 'w', 'w', 'center', 'center')
        self.gv_frm, self.gv_tree = make_tree(gv_lf, cols, heads, widths, height=6, column_aligns=aligns, db=self.db, table_id='sec1_gv',
                                               undo_manager=self.undo_mgr, on_change=self.mark_modified)
        self.gv_frm.pack(fill='x', expand=True)
        self.gv_tree.bind('<Double-1>', lambda _e: self._gv_edit())

        gv_bf = tb.Frame(gv_lf)
        gv_bf.pack(fill='x', pady=(4, 0))
        tb.Button(gv_bf, text='➕ Thêm mới GV',  command=self._gv_add, bootstyle='success-outline').pack(side='left', padx=2)
        tb.Button(gv_bf, text='👥 Chọn từ Danh sách',
                   command=self._gv_pick, bootstyle='primary-outline').pack(side='left', padx=2)
        tb.Separator(gv_bf, orient='vertical').pack(side='left', padx=6, fill='y')
        tb.Button(gv_bf, text='✏ Sửa',       command=self._gv_edit, bootstyle='info-outline').pack(side='left', padx=2)
        tb.Button(gv_bf, text='🗑 Xóa',       command=self._gv_delete, bootstyle='danger-outline').pack(side='left', padx=2)
        tb.Button(gv_bf, text='⬆ Lên',       command=lambda: self._gv_move(-1)).pack(side='left', padx=2)
        tb.Button(gv_bf, text='⬇ Xuống',     command=lambda: self._gv_move(1)).pack(side='left', padx=2)
        r += 1

        # ── Thông tin học phần ───────────────────────────────────────────────
        r += 1
        info_lf = tb.Labelframe(p, text='Thông tin học phần', padding=8)
        info_lf.grid(row=r, column=0, columnspan=4, sticky='ew', padx=16, pady=(8, 4))

        lbl_ma = tb.Label(info_lf, text='Mã học phần:', font=('Arial', 10))
        lbl_ma.grid(row=0, column=0, sticky='w', padx=8, pady=3)
        ent_ma = tb.Entry(info_lf, textvariable=self.v_ma, width=20, font=('Arial', 10))
        ent_ma.grid(row=0, column=1, sticky='w', padx=8, pady=3)

        lbl_tc = tb.Label(info_lf, text='Số tín chỉ:', font=('Arial', 10))
        lbl_tc.grid(row=0, column=2, sticky='w', padx=8, pady=3)
        sp_tc = tb.Spinbox(info_lf, textvariable=self.v_tc, from_=1, to=10, width=6, font=('Arial', 10))
        sp_tc.grid(row=0, column=3, sticky='w', padx=8, pady=3)

        lbl_loai = tb.Label(info_lf, text='Loại học phần:', font=('Arial', 10))
        lbl_loai.grid(row=1, column=0, sticky='w', padx=8, pady=3)
        self.cb_loai = AutocompleteCombobox(info_lf, textvariable=self.v_loai, values=list_types, width=18, font=('Arial', 10), state='readonly')
        self.cb_loai.grid(row=1, column=1, sticky='w', padx=8, pady=3)

        lbl_tc_hp = tb.Label(info_lf, text='Tính chất học phần:', font=('Arial', 10))
        lbl_tc_hp.grid(row=1, column=2, sticky='w', padx=8, pady=3)
        self.cb_tinh_chat = AutocompleteCombobox(info_lf, textvariable=self.v_tinh_chat, values=list_natures, width=18, font=('Arial', 10), state='readonly')
        self.cb_tinh_chat.grid(row=1, column=3, sticky='w', padx=8, pady=3)

        lbl_nhom = tb.Label(info_lf, text='Nhóm đặc thù:', font=('Arial', 10))
        lbl_nhom.grid(row=2, column=0, sticky='w', padx=8, pady=3)
        self.cb_nhom = AutocompleteCombobox(info_lf, textvariable=self.v_nhom_hp_dac_thu, values=['Thông thường', 'Tiểu luận tổng quan', 'Chuyên đề Tiến sĩ'], width=18, font=('Arial', 10), state='readonly')
        self.cb_nhom.grid(row=2, column=1, sticky='w', padx=8, pady=3)

        cb_th = tb.Checkbutton(info_lf, text='Học phần có Thực hành/Thí nghiệm', variable=self.v_co_thuc_hanh)
        cb_th.grid(row=2, column=2, columnspan=2, sticky='w', padx=8, pady=4)
        
        self._register_field('ma', label_widget=lbl_ma, input_widget=ent_ma)
        self._register_field('so_tin_chi', label_widget=lbl_tc, input_widget=sp_tc)
        self._register_field('loai', label_widget=lbl_loai, input_widget=self.cb_loai)
        self._register_field('tinh_chat', label_widget=lbl_tc_hp, input_widget=self.cb_tinh_chat)
        self._register_field('nhom_hp_dac_thu', label_widget=lbl_nhom, input_widget=self.cb_nhom)
        self._register_field('co_thuc_hanh', label_widget=cb_th, input_widget=cb_th)

        # ── Phân bổ thời gian ────────────────────────────────────────────────
        r += 1
        time_lf = tb.Labelframe(p, text='Phân bổ thời gian', padding=8)
        time_lf.grid(row=r, column=0, columnspan=4, sticky='ew', padx=16, pady=4)
        
        btn_sync = tb.Button(time_lf, text='🔄 Đồng bộ từ Mục 6', 
                               bootstyle='outline-info', command=self._sync_hours)
        btn_sync.grid(row=0, column=0, sticky='w', padx=6, pady=(0, 10))

        btn_calc = tb.Button(time_lf, text='🧮 Tự động tính Tự học', 
                               bootstyle='outline-success', command=self._auto_calc_hours)
        btn_calc.grid(row=0, column=1, sticky='w', padx=6, pady=(0, 10))

        time_rows = [
            ('gio_lt',      'Lý thuyết, Bài tập, Kiểm tra:'),
            ('gio_th_tn',   'Thực hành, Thí nghiệm:'),
            ('gio_tl',      'Thảo luận (có nội dung):'),
            ('gio_bt',      'Bài tập:'),
            ('gio_tieu_luan','Tiểu luận, Đồ án:'),
            ('gio_thuc_tap', 'Thực tập (tại doanh nghiệp, cssx,...):'),
            ('gio_tu_hoc',  'Tự học, nghiên cứu, trải nghiệm:'),
            ('tong_gio',    'Tổng giờ học tập theo định mức:'),
        ]
        for ti, (key, lbl_text) in enumerate(time_rows):
            tb.Label(time_lf, text=lbl_text, font=('Arial', 10)
                      ).grid(row=ti+1, column=0, sticky='w', padx=6, pady=2)
            var = self._time_vars[key]
            tb.Entry(time_lf, textvariable=var, width=8,
                      font=('Arial', 10)).grid(row=ti+1, column=1, sticky='w', padx=6, pady=2)

        # ── Học phần liên quan ───────────────────────────────────────────────
        r += 1
        rel_lf = tb.Labelframe(p, text='Học phần liên quan (Nhập mã - tên. Dùng dấu phẩy nếu có nhiều học phần)', padding=8)
        rel_lf.grid(row=r, column=0, columnspan=4, sticky='ew', padx=16, pady=4)

        tb.Label(rel_lf, text='Học phần tiên quyết:', font=('Arial', 10)
                  ).grid(row=0, column=0, sticky='w', padx=6, pady=3)
        tb.Entry(rel_lf, textvariable=self.v_tq, width=65,
                  font=('Arial', 10)).grid(row=0, column=1, sticky='ew', padx=6, pady=3)

        tb.Label(rel_lf, text='Học phần song hành:', font=('Arial', 10)
                  ).grid(row=1, column=0, sticky='w', padx=6, pady=3)
        tb.Entry(rel_lf, textvariable=self.v_sh, width=65,
                  font=('Arial', 10)).grid(row=1, column=1, sticky='ew', padx=6, pady=3)

        tb.Label(rel_lf, text='Học phần thay thế:', font=('Arial', 10)
                  ).grid(row=2, column=0, sticky='w', padx=6, pady=3)
        tb.Entry(rel_lf, textvariable=self.v_tt, width=65,
                  font=('Arial', 10)).grid(row=2, column=1, sticky='ew', padx=6, pady=3)
        rel_lf.columnconfigure(1, weight=1)

        p.columnconfigure(1, weight=1)

        # automatic dirty tracking
        self.auto_track_vars(self.v_ten_viet, self.v_ten_anh, self.v_khoa, self.v_trinh_do,
                             self.v_ma, self.v_tc, self.v_loai, self.v_tinh_chat,
                             self.v_co_thuc_hanh, self.v_nhom_hp_dac_thu, self.v_tq, self.v_sh, self.v_tt, *self._time_vars.values())

    def get_data_dict(self):
        self.ensure_ui()
        data = {
            'ten_viet': self.v_ten_viet.get(),
            'ten_anh': self.v_ten_anh.get(),
            'khoa': self.v_khoa.get(),
            'trinh_do': self.v_trinh_do.get(),
            'ma': self.v_ma.get(),
            'tc': self.v_tc.get(),
            'loai': self.v_loai.get(),
            'tinh_chat': self.v_tinh_chat.get(),
            'co_th': self.v_co_thuc_hanh.get(),
            'nhom_hp_dac_thu': self.v_nhom_hp_dac_thu.get(),
            'tq': self.v_tq.get(),
            'sh': self.v_sh.get(),
            'tt': self.v_tt.get(),
            'time': {k: v.get() for k, v in self._time_vars.items()}
        }
        return data

    def apply_data_dict(self, data):
        self.ensure_ui() # FIXED: Ensure UI built before access
        if not data: return
        self.v_ten_viet.set(data.get('ten_viet', ''))
        self.v_ten_anh.set(data.get('ten_anh', ''))
        self.v_khoa.set(data.get('khoa', ''))
        self.v_trinh_do.set(data.get('trinh_do', ''))
        self.v_ma.set(data.get('ma', ''))
        self.v_tc.set(data.get('tc', '3'))
        self.v_loai.set(data.get('loai', ''))
        self.v_tinh_chat.set(data.get('tinh_chat', ''))
        self.v_co_thuc_hanh.set(data.get('co_th', False))
        self.v_nhom_hp_dac_thu.set(data.get('nhom_hp_dac_thu', 'Thông thường'))
        self.v_tq.set(data.get('tq', ''))
        self.v_sh.set(data.get('sh', ''))
        self.v_tt.set(data.get('tt', ''))
        time_data = data.get('time', {})
        for k, v in self._time_vars.items():
            if k in time_data: v.set(time_data[k])

    def _auto_calc_hours(self):
        """Tính giờ tự học dựa trên số tín chỉ: 1 TC = 45 giờ học tập (bao gồm cả tự học)."""
        try:
            tc = int(self.v_tc.get() or 3)
            tong_quy_dinh = tc * 45
            
            # Tính tổng giờ tiếp xúc
            contact_keys = ['gio_lt', 'gio_th_tn', 'gio_tl', 'gio_bt', 'gio_tieu_luan', 'gio_thuc_tap']
            total_contact = 0
            for k in contact_keys:
                total_contact += int(self._time_vars[k].get() or 0)
            
            # Giờ tự học = Tổng quy định - Tổng tiếp xúc
            tu_hoc = max(0, tong_quy_dinh - total_contact)
            self._time_vars['gio_tu_hoc'].set(str(tu_hoc))
            self._time_vars['tong_gio'].set(str(tong_quy_dinh))
            show_modern_warning(self, 'Thông báo', f'Đã tính toán:\n- Tổng giờ định mức ({tc} TC): {tong_quy_dinh}\n- Giờ tự học: {tu_hoc}')
        except Exception as e:
            show_modern_warning(self, 'Lỗi', str(e))

    def _sync_hours(self):
        """Đồng bộ số giờ từ Mục 6."""
        if not self.hp_id:
            return
        if messagebox.askyesno('Xác nhận', 'Hệ thống sẽ tính toán tổng số tiết dựa trên Nội dung chi tiết (Mục 6) và cập nhật vào đây. Bạn có chắc chắn?'):
            if self.db.calculate_and_update_hours(self.hp_id):
                # Reload UI
                hp = self.db.get_hoc_phan(self.hp_id)
                for key, var in self._time_vars.items():
                    var.set(str(hp[key] or 0))
                messagebox.showinfo('Thành công', 'Đã cập nhật số tiết từ nội dung chi tiết.')
            else:
                messagebox.showwarning('Cảnh báo', 'Không tìm thấy dữ liệu nội dung chi tiết hoặc có lỗi xảy ra.')

    def refresh_khoa_combo(self):
        khoas = self.db.get_all_khoa()
        self._khoa_map = {k['ten']: k['id'] for k in khoas}
        self.cb_khoa.set_completion_list(list(self._khoa_map.keys()))

    def load(self, hp_id):
        super().load(hp_id)
        self.ensure_ui()
        self.refresh_khoa_combo()
        hp = self.db.get_hoc_phan(hp_id)
        if not hp:
            return
        self.v_ten_viet.set(hp['ten_viet'] or '')
        self.v_ten_anh.set(hp['ten_anh'] or '')
        self.v_ma.set(hp['ma'] or '')
        self.v_trinh_do.set(hp['trinh_do'] or 'Đại học')
        self.v_loai.set(hp['loai'] or 'Bắt buộc')
        self.v_tinh_chat.set(hp['tinh_chat'] or 'Hỗn hợp')
        self.v_tc.set(str(hp['so_tin_chi'] or 3))
        self.v_tq.set(hp['hp_tien_quyet'] or '')
        self.v_sh.set(hp['hp_song_hanh'] or '')
        self.v_tt.set(hp['hp_thay_the'] or '')
        self.v_nhom_hp_dac_thu.set(hp.get('nhom_hp_dac_thu') or 'Thông thường')
        self.v_co_thuc_hanh.set(hp['co_thuc_hanh'] if hp['co_thuc_hanh'] is not None else 1)
        
        self._ctdt_links = [dict(r) for r in self.db.get_ctdt_of_hp(hp_id)]
        self._ct_refresh()

        khoas = self.db.get_all_khoa()
        self._khoa_map = {k['ten']: k['id'] for k in khoas}
        if hp['khoa_id']:
            for ten, kid in self._khoa_map.items():
                if kid == hp['khoa_id']:
                    self.v_khoa.set(ten)
                    break

        for key, var in self._time_vars.items():
            var.set(str(hp[key] or 0))

        gvs = self.db.get_gv_of_hp(hp_id)
        self._gv_rows = []
        for r in gvs:
            rd = dict(r)
            self._gv_rows.append({
                'gv_id': rd.get('gv_id') or rd.get('master_gv_id'), 
                'ho_ten': rd.get('ho_ten', ''),
                'hoc_vi': rd.get('hoc_ham_vi') or rd.get('hoc_vi') or '', 
                'don_vi': rd.get('don_vi') or '',
                'sdt': rd.get('sdt') or '',
                'email': rd.get('email') or '', 
                'vai_tro': rd.get('vai_tro'),
                'thu_tu': rd.get('thu_tu'),
                'ma_can_bo': rd.get('ma_can_bo') or '',
                'gioi_tinh': rd.get('gioi_tinh') or '',
                'chuc_vu': rd.get('chuc_vu') or '',
                'dia_chi': rd.get('dia_chi') or ''
            })
        self._gv_refresh()
        self._initial_data = self.get_data_dict()
        self._loading = False

    def save(self):
        if self.hp_id is None:
            return
        
        current_data = self.get_data_dict()
        if hasattr(self, '_initial_data'):
            for field, new_val in current_data.items():
                old_val = self._initial_data.get(field)
                if str(new_val) != str(old_val):
                    self.db.log_change(self.hp_id, 'hoc_phan', field, old_val, new_val)
        
        self._initial_data = current_data

        khoa_id = self._khoa_map.get(self.v_khoa.get())
        data = {
            'ten_viet':    self.v_ten_viet.get().strip(),
            'ten_anh':     self.v_ten_anh.get().strip(),
            'ma':          self.v_ma.get().strip(),
            'trinh_do':    self.v_trinh_do.get(),
            'hp_tien_quyet': self.v_tq.get().strip(),
            'hp_song_hanh':  self.v_sh.get().strip(),
            'hp_thay_the':   self.v_tt.get().strip(),
            'co_thuc_hanh':  self.v_co_thuc_hanh.get(),
            'so_tin_chi':    int(self.v_tc.get() or 3),
            'loai':          self.v_loai.get(),
            'tinh_chat':     self.v_tinh_chat.get(),
            'nhom_hp_dac_thu': self.v_nhom_hp_dac_thu.get(),
            'khoa_id':       khoa_id
        }
        for key, var in self._time_vars.items():
            try:
                data[key] = int(var.get() or 0)
            except ValueError:
                data[key] = 0
        self.db.update_hoc_phan(self.hp_id, data)
        self.db.update_hp_ctdt_links(self.hp_id, self._ctdt_links)
        self.db.set_gv_of_hp(self.hp_id, self._gv_rows)

    def get_data_dict(self):
        self.ensure_ui()
        res = {
            'ten_viet': self.v_ten_viet.get(),
            'ten_anh': self.v_ten_anh.get(),
            'ma': self.v_ma.get(),
            'khoa': self.v_khoa.get(),
            'trinh_do': self.v_trinh_do.get(),
            'loai': self.v_loai.get(),
            'tinh_chat': self.v_tinh_chat.get(),
            'so_tin_chi': self.v_tc.get(),
            'co_thuc_hanh': self.v_co_thuc_hanh.get(),
            'tq': self.v_tq.get(),
            'sh': self.v_sh.get(),
            'tt': self.v_tt.get(),
            'gv_rows': self._gv_rows,
            'ctdt_links': self._ctdt_links
        }
        for k, v in self._time_vars.items():
            res[k] = v.get()
        return res

    def apply_data_dict(self, data):
        if not data: return
        self.ensure_ui()
        if 'ten_viet' in data: self.v_ten_viet.set(data['ten_viet'])
        if 'ten_anh' in data: self.v_ten_anh.set(data['ten_anh'])
        if 'ma' in data: self.v_ma.set(data['ma'])
        if 'khoa' in data: self.v_khoa.set(data['khoa'])
        if 'trinh_do' in data: self.v_trinh_do.set(data['trinh_do'])
        if 'loai' in data: self.v_loai.set(data['loai'])
        if 'tinh_chat' in data: self.v_tinh_chat.set(data['tinh_chat'])
        if 'so_tin_chi' in data: self.v_tc.set(data['so_tin_chi'])
        if 'co_thuc_hanh' in data: self.v_co_thuc_hanh.set(data['co_thuc_hanh'])
        if 'tq' in data: self.v_tq.set(data['tq'])
        if 'sh' in data: self.v_sh.set(data['sh'])
        if 'tt' in data: self.v_tt.set(data['tt'])
        
        for k, v in self._time_vars.items():
            if k in data: v.set(str(data[k]))
            
        if 'gv_rows' in data:
            self._gv_rows = data['gv_rows']
            self._gv_refresh()
        if 'ctdt_links' in data:
            self._ctdt_links = data['ctdt_links']
            self._ct_refresh()

    def get_basic_data(self):
        return {'ten_viet': self.v_ten_viet.get().strip() or 'Học phần mới',
                'ten_anh': self.v_ten_anh.get().strip(),
                'ma': self.v_ma.get().strip(),
                'trinh_do': self.v_trinh_do.get()}

    def clear(self):
        super().clear()
        for v in [self.v_ten_viet, self.v_ten_anh, self.v_ma, self.v_tq, self.v_sh, self.v_tt]:
            v.set('')
        self.v_trinh_do.set('Đại học')
        self.v_loai.set('Bắt buộc')
        self.v_tinh_chat.set('Hỗn hợp')
        self.v_khoa.set('')
        self.v_tc.set('3')
        self.v_co_thuc_hanh.set(1)
        self.v_nhom_hp_dac_thu.set('Thông thường')
        self._ctdt_links = []
        self._ct_refresh()
        for var in self._time_vars.values():
            var.set('0')
        self._gv_rows = []
        self._gv_refresh()

    def _ct_refresh(self):
        self.ct_tree.delete(*self.ct_tree.get_children())
        for i, r in enumerate(self._ctdt_links):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.ct_tree.insert('', 'end', iid=str(i),
                                 values=(r.get('bac', 'Đại học'),
                                         r.get('ten_ctdt', ''),
                                         r.get('khoi_kien_thuc', ''),
                                         r.get('chuyen_nganh', '')),
                                 tags=(tag,))

    def _ct_add(self):
        all_ctdt = self.db.get_all_ctdt()
        if not all_ctdt:
            messagebox.showinfo('Thông báo', 'Chưa có CTĐT nào. Thêm tại menu Dữ liệu chung.')
            return
        dlg = _AddCtdtToHpDialog(self, all_ctdt)
        if dlg.result:
            self.ct_tree.snapshot()
            self._ctdt_links.append(dlg.result)
            self._ct_refresh()
            self.mark_modified()

    def _ct_remove(self):
        sel = self.ct_tree.selection()
        if sel:
            self.ct_tree.snapshot()
            self._ctdt_links.pop(int(sel[0]))
            self._ct_refresh()
            self.mark_modified()

    def _ct_edit(self):
        sel = self.ct_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        all_ctdt = self.db.get_all_ctdt()
        dlg = _AddCtdtToHpDialog(self, all_ctdt, initial=self._ctdt_links[idx])
        if dlg.result:
            self.ct_tree.snapshot()
            self._ctdt_links[idx] = dlg.result
            self._ct_refresh()
            self.mark_modified()

    def _gv_refresh(self):
        self.gv_tree.delete(*self.gv_tree.get_children())
        stt_c = {'chinh': 0, 'tham_gia': 0}
        for i, r in enumerate(self._gv_rows):
            vr = r.get('vai_tro', 'tham_gia')
            stt_c[vr] += 1
            ho_ten_full = f"{r.get('hoc_vi', '')} {r.get('ho_ten', '')}".strip()
            tag = 'even' if i % 2 == 0 else 'odd'
            self.gv_tree.insert('', 'end', iid=str(i),
                                values=(stt_c[vr],
                                        VAI_TRO_LABEL.get(vr, vr),
                                        ho_ten_full,
                                        r.get('ma_can_bo', ''),
                                        r.get('chuc_vu', ''),
                                        r.get('don_vi', ''),
                                        r.get('sdt', ''),
                                        r.get('email', '')),
                                tags=(tag,))

    def _gv_fields(self, initial=None):
        return [
            ('ho_ten',    'Họ và tên',      'entry_with_btn', {'btn_text': '👥 Chọn', 'btn_cmd_key': 'pick_gv'}),
            ('ma_can_bo', 'Mã cán bộ',      'entry', {}),
            ('gioi_tinh', 'Giới tính',      'combo', {'values': ['Nam', 'Nữ', 'Khác']}),
            ('chuc_vu',   'Chức vụ',        'entry', {}),
            ('hoc_vi',    'Học hàm, học vị', 'entry', {}),
            ('don_vi',    'Đơn vị công tác', 'entry', {}),
            ('sdt',       'Số điện thoại',  'entry', {}),
            ('email',     'Email',          'entry', {}),
            ('dia_chi',   'Địa chỉ',        'entry', {}),
            ('vai_tro',   'Vai trò',        'combo', {'values': list(VAI_TRO_LABEL.values())}),
        ]

    def _gv_add(self):
        dlg = RowEditDialog(self, 'Thêm giảng viên', self._gv_fields())
        if dlg.result:
            self.gv_tree.snapshot()
            vr_label = dlg.result.get('vai_tro', 'Giảng viên phụ trách chính')
            vai_tro = 'chinh' if 'chính' in vr_label else 'tham_gia'
            self._gv_rows.append({'gv_id': None,
                                   'ho_ten': dlg.result.get('ho_ten', ''),
                                   'ma_can_bo': dlg.result.get('ma_can_bo', ''),
                                   'gioi_tinh': dlg.result.get('gioi_tinh', ''),
                                   'chuc_vu': dlg.result.get('chuc_vu', ''),
                                   'hoc_vi': dlg.result.get('hoc_vi', ''),
                                   'don_vi': dlg.result.get('don_vi', ''),
                                   'sdt': dlg.result.get('sdt', ''),
                                   'email': dlg.result.get('email', ''),
                                   'dia_chi': dlg.result.get('dia_chi', ''),
                                   'vai_tro': vai_tro,
                                   'thu_tu': len(self._gv_rows) + 1})
            self._gv_refresh()
            self.mark_modified()

    def _gv_edit(self):
        sel = self.gv_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        row = self._gv_rows[idx]
        init = {**row, 'vai_tro': VAI_TRO_LABEL.get(row.get('vai_tro', 'tham_gia'), '')}
        dlg = RowEditDialog(self, 'Sửa giảng viên', self._gv_fields(), initial=init)
        if dlg.result:
            self.gv_tree.snapshot()
            vr_label = dlg.result.get('vai_tro', '')
            vai_tro = 'chinh' if 'chính' in vr_label else 'tham_gia'
            row.update({
                'ho_ten': dlg.result['ho_ten'],
                'ma_can_bo': dlg.result.get('ma_can_bo', ''),
                'gioi_tinh': dlg.result.get('gioi_tinh', ''),
                'chuc_vu': dlg.result.get('chuc_vu', ''),
                'hoc_vi': dlg.result['hoc_vi'],
                'don_vi': dlg.result.get('don_vi', ''),
                'sdt': dlg.result['sdt'],
                'email': dlg.result['email'],
                'dia_chi': dlg.result.get('dia_chi', ''),
                'vai_tro': vai_tro
            })
            self._gv_refresh()
            self.mark_modified()

    def _gv_delete(self):
        sel = self.gv_tree.selection()
        if not sel:
            return
        if messagebox.askyesno('Xác nhận', 'Xóa giảng viên này?'):
            self.gv_tree.snapshot()
            self._gv_rows.pop(int(sel[0]))
            self._gv_refresh()
            self.mark_modified()

    def _gv_move(self, direction):
        sel = self.gv_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        new_idx = idx + direction
        if 0 <= new_idx < len(self._gv_rows):
            self.gv_tree.snapshot()
            self._gv_rows[idx], self._gv_rows[new_idx] = \
                self._gv_rows[new_idx], self._gv_rows[idx]
            self._gv_refresh()
            self.gv_tree.selection_set(str(new_idx))
            self.mark_modified()

    def _gv_pick(self):
        all_gvs = self.db.get_all_giang_vien()
        if not all_gvs:
            messagebox.showinfo('Thông báo', 'Chưa có giảng viên nào trong pool.\n'
                                'Thêm GV qua menu Dữ liệu Chung > Giảng viên.')
            return
        dlg = _GvPickDialog(self, all_gvs)
        if dlg.result:
            self.gv_tree.snapshot()
            vai_tro = dlg.vai_tro
            for gv_raw in dlg.result:
                gv = dict(gv_raw) if not isinstance(gv_raw, dict) else gv_raw
                self._gv_rows.append({'gv_id': gv.get('id'),
                                       'ho_ten': gv.get('ho_ten', ''),
                                       'ma_can_bo': gv.get('ma_can_bo') or '',
                                       'gioi_tinh': gv.get('gioi_tinh') or '',
                                       'chuc_vu': gv.get('chuc_vu') or '',
                                       'hoc_vi': gv.get('hoc_vi') or '',
                                       'don_vi': gv.get('don_vi') or '',
                                       'sdt': gv.get('sdt') or '',
                                       'email': gv.get('email') or '',
                                       'dia_chi': gv.get('dia_chi') or '',
                                       'vai_tro': vai_tro,
                                       'thu_tu': len(self._gv_rows)+1})
            self._gv_refresh()
            self.mark_modified()

    def get_time_allocation(self):
        """Trả về dict chứa phân bổ giờ từ Mục 1 để đối soát."""
        res = {}
        for k, v in self._time_vars.items():
            try:
                res[k] = float(v.get() or 0)
            except:
                res[k] = 0.0
        return res

    def _pick_gv(self, var, dialog=None):
        """Mở _GvPickDialog để chọn GV và điền vào form."""
        all_gvs = self.db.get_all_giang_vien()
        if not all_gvs:
            messagebox.showinfo('Thông báo', 'Chưa có giảng viên nào trong pool.', parent=dialog or self)
            return
            
        dlg = _GvPickDialog(self, all_gvs)
        if dlg.result:
            # Lấy GV đầu tiên được chọn
            gv_raw = dlg.result[0]
            gv = dict(gv_raw) if not isinstance(gv_raw, dict) else gv_raw
            var.set(gv.get('ho_ten', ''))
            
            # Nếu được gọi từ RowEditDialog, điền thêm các field khác
            if dialog and hasattr(dialog, '_vars'):
                d_vars = dialog._vars
                if 'ma_can_bo' in d_vars: d_vars['ma_can_bo'].set(gv.get('ma_can_bo') or '')
                if 'gioi_tinh' in d_vars: d_vars['gioi_tinh'].set(gv.get('gioi_tinh') or 'Nam')
                if 'chuc_vu' in d_vars: d_vars['chuc_vu'].set(gv.get('chuc_vu') or '')
                if 'hoc_vi' in d_vars: d_vars['hoc_vi'].set(gv.get('hoc_vi') or '')
                if 'don_vi' in d_vars: d_vars['don_vi'].set(gv.get('don_vi') or '')
                if 'sdt' in d_vars: d_vars['sdt'].set(gv.get('sdt') or '')
                if 'email' in d_vars: d_vars['email'].set(gv.get('email') or '')
                if 'dia_chi' in d_vars: d_vars['dia_chi'].set(gv.get('dia_chi') or '')
                
                vrl = dlg.v_vaitro.get()
                if 'vai_tro' in d_vars: d_vars['vai_tro'].set(vrl)


class _AddCtdtToHpDialog(tb.Toplevel):
    def __init__(self, parent, ctdt_list, initial=None):
        super().__init__(parent)
        self.db = parent.db
        self.title('Gán vào Chương trình đào tạo' if not initial else 'Sửa thông tin Gán CTĐT')
        self.geometry('700x550')
        self.result = None
        self.initial = initial
        self.grab_set()
        
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        
        tb.Label(frm, text='Chọn Chương trình:').pack(anchor='w')
        self.v_ctdt = tk.StringVar()
        self._ct_map = {f"[{c['bac']}] {c['ten']}": c['id'] for c in ctdt_list}
        self.cb = tb.Combobox(frm, textvariable=self.v_ctdt, values=list(self._ct_map.keys()), state='readonly')
        self.cb.pack(fill='x', pady=4)
        self.cb.bind('<<ComboboxSelected>>', lambda _: self._on_ctdt_change())
        
        tb.Label(frm, text='Khối kiến thức:').pack(anchor='w', pady=(8, 0))
        from sections.sec1_thong_tin import KHOI_KIEN_THUC
        self.v_khoi = tk.StringVar(value='Ngành')
        tb.Combobox(frm, textvariable=self.v_khoi, values=KHOI_KIEN_THUC, state='readonly').pack(fill='x', pady=4)
        
        tb.Label(frm, text='Chuyên ngành (Nếu có):').pack(anchor='w', pady=(8, 0))
        self.v_cn = tk.StringVar()
        self.cb_cn = tb.Combobox(frm, textvariable=self.v_cn, state='normal')
        self.cb_cn.pack(fill='x', pady=4)

        if self.initial:
            search_key = f"[{self.initial.get('bac')}] {self.initial.get('ten_ctdt')}"
            if search_key in self._ct_map:
                self.v_ctdt.set(search_key)
                self._on_ctdt_change()
                self.v_khoi.set(self.initial.get('khoi_kien_thuc', 'Ngành'))
                self.v_cn.set(self.initial.get('chuyen_nganh', ''))
        
        bf = tb.Frame(self, padding=12)
        bf.pack(fill='x')
        tb.Button(bf, text='✔ OK', command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='Hủy', command=self.destroy).pack(side='right', padx=4)
        self.transient(parent)
        self.wait_window()

    def _on_ctdt_change(self):
        txt = self.v_ctdt.get()
        if not txt: return
        cid = self._ct_map[txt]
        cns = self.db.get_chuyen_nganh_by_ctdt(cid)
        cn_vals = [''] + [c['ten'] for c in cns]
        self.cb_cn['values'] = cn_vals
        self.v_cn.set('')

    def _ok(self):
        if not self.v_ctdt.get(): return
        cid = self._ct_map[self.v_ctdt.get()]
        ten_ctdt = self.v_ctdt.get().split('] ', 1)[1]
        bac = self.v_ctdt.get().split('[', 1)[1].split(']', 1)[0]
        
        self.result = {
            'ctdt_id': cid,
            'ten_ctdt': ten_ctdt,
            'bac': bac,
            'khoi_kien_thuc': self.v_khoi.get(),
            'chuyen_nganh': self.v_cn.get().strip()
        }
        self.destroy()


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

        cols = ('ho_ten', 'ma_can_bo', 'hoc_vi', 'chuc_vu', 'sdt', 'email')
        heads = ('Họ và tên', 'Mã CB', 'Học vị', 'Chức vụ', 'SĐT', 'Email')
        widths = (180, 70, 90, 110, 100, 180)
        tf, self.tree = make_tree(frm, cols, heads, widths, height=10, db=self.db, table_id='sec1_gv_pick')
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
                             values=(g['ho_ten'], g['hoc_vi'] or '', g['sdt'] or '',
                                     g['email'] or ''), tags=(tag,))

    def _filter(self):
        kw = self.v_search.get().lower()
        filtered = [g for g in self._all
                    if kw in (g['ho_ten'] or '').lower()
                    or kw in (g['email'] or '').lower()]
        self._refresh(filtered)

    def _ok(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning('Cảnh báo', 'Chưa chọn giảng viên.', parent=self)
            return
        
        selected_data = []
        for iid in sel:
            idx = int(iid)
            selected_data.append(self._shown[idx])
            
        self.result = selected_data
        vrl = self.v_vaitro.get()
        self.vai_tro = 'chinh' if 'chính' in vrl else 'tham_gia'
        self.destroy()
