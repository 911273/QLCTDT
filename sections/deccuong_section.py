# sections/deccuong_section.py
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
import json
from datetime import datetime

# Import Repositories & Service
from repositories.hoc_phan_repository import HocPhanRepository
from repositories.clo_repository import CLORepository
from repositories.noidung_repository import NoiDungRepository
from repositories.baidanhgia_repository import BaiDanhGiaRepository
from repositories.tailieu_repository import TaiLieuRepository
from repositories.rubric_repository import RubricRepository
from services.deccuong_service import DecCuongService
# Import Utis
from utils.global_picker import GiangVienPicker, TaiLieuPicker, PLOPicker, HocPhanPicker
from utils.ui_utils import ask_modern_yesno

class DeCuongSection(ttk.Frame):
    def __init__(self, master, db, hp_id=None, **kwargs):
        super().__init__(master, **kwargs)
        self.db = db
        self.hp_id = hp_id
        
        # Repositories
        self.repo_hp = HocPhanRepository(db)
        self.repo_clo = CLORepository(db)
        self.repo_nd = NoiDungRepository(db)
        self.repo_bdg = BaiDanhGiaRepository(db)
        self.repo_tl = TaiLieuRepository(db)
        self.repo_rb = RubricRepository(db)
        
        # Service
        self.service = DecCuongService(db)
        
        self.data_hp = {}
        if hp_id:
            self.data_hp = self.repo_hp.get_by_id(hp_id) # Giả định repo có hàm này

        self._build_ui()
        if self.data_hp:
            self.load_data()

    def _build_ui(self):
        # Top Toolbar (Chung)
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(side=TOP, fill=X, padx=5, pady=5)
        
        tb.Button(self.toolbar, text="💾 Lưu tất cả", bootstyle=SUCCESS, 
                  command=self.save_all).pack(side=LEFT, padx=5)
        
        self.lbl_status = tb.Label(self.toolbar, text="Sẵn sàng", font=('', 9, 'italic'))
        self.lbl_status.pack(side=RIGHT, padx=10)

        # Main Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # Tabs
        self.tab1 = self._init_tab1()
        self.tab2 = self._init_tab2()
        self.tab3 = self._init_tab3()
        self.tab4 = self._init_tab4()
        self.tab5 = self._init_tab5()
        self.tab6 = self._init_tab6()
        self.tab7 = self._init_tab7()
        self.tab8 = self._init_tab8()
        
        self.nb.add(self.tab8, text="8. Lịch sử")

        # Bottom Bar
        self.bottom_bar = ttk.Frame(self)
        self.bottom_bar.pack(side=BOTTOM, fill=X, padx=5, pady=5)
        
        tb.Button(self.bottom_bar, text="🔍 Kiểm tra đề cương", bootstyle=INFO, 
                  command=self._show_validation).pack(side=LEFT, padx=5)
        
        self.btn_export = tb.Button(self.bottom_bar, text="📄 Xuất Word", bootstyle=PRIMARY,
                                    command=self._export_word, state=DISABLED)
        self.btn_export.pack(side=RIGHT, padx=5)

    # -------------------------------------------------------------------------
    # TAB 1: THÔNG TIN CHUNG
    # -------------------------------------------------------------------------
    def _init_tab1(self):
        tab = ttk.Frame(self.nb)
        container = ttk.Frame(tab, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        # Grid config
        container.columnconfigure(1, weight=1)
        container.columnconfigure(3, weight=1)

        # Cột 1
        ttk.Label(container, text="Tên HP (Tiếng Việt):").grid(row=0, column=0, sticky=W, pady=5)
        self.ent_ten_vn = tb.Entry(container)
        self.ent_ten_vn.grid(row=0, column=1, sticky=EW, padx=5)

        ttk.Label(container, text="Mã học phần:").grid(row=1, column=0, sticky=W, pady=5)
        self.ent_ma_hp = tb.Entry(container)
        self.ent_ma_hp.grid(row=1, column=1, sticky=EW, padx=5)

        ttk.Label(container, text="Đơn vị quản lý:").grid(row=2, column=0, sticky=W, pady=5)
        self.cbo_don_vi = tb.Combobox(container, values=self._get_khoas())
        self.cbo_don_vi.grid(row=2, column=1, sticky=EW, padx=5)

        ttk.Label(container, text="Số tín chỉ:").grid(row=3, column=0, sticky=W, pady=5)
        self.spn_tc = tb.Spinbox(container, from_=1, to=10, command=self._on_tc_change)
        self.spn_tc.grid(row=3, column=1, sticky=EW, padx=5)
        self.spn_tc.bind("<KeyRelease>", lambda e: self._on_tc_change())

        # Cột 2
        ttk.Label(container, text="Tên HP (Tiếng Anh):").grid(row=0, column=2, sticky=W, pady=5)
        self.ent_ten_en = tb.Entry(container)
        self.ent_ten_en.grid(row=0, column=3, sticky=EW, padx=5)

        ttk.Label(container, text="Tổng giờ (TCx50):").grid(row=1, column=2, sticky=W, pady=5)
        self.ent_tong_gio = tb.Entry(container, state='readonly', font=('', 10, 'bold'))
        self.ent_tong_gio.grid(row=1, column=3, sticky=EW, padx=5)

        ttk.Label(container, text="Loại HP:").grid(row=2, column=2, sticky=W, pady=5)
        self.var_loai = tk.StringVar(value='bat_buoc')
        f_loai = ttk.Frame(container)
        f_loai.grid(row=2, column=3, sticky=W)
        tb.Radiobutton(f_loai, text="Bắt buộc", variable=self.var_loai, value='bat_buoc').pack(side=LEFT, padx=5)
        tb.Radiobutton(f_loai, text="Tự chọn", variable=self.var_loai, value='tu_chon').pack(side=LEFT, padx=5)

        ttk.Label(container, text="Loại hình:").grid(row=3, column=2, sticky=W, pady=5)
        self.var_loai_hinh = tk.StringVar(value='truc_tiep')
        f_lh = ttk.Frame(container)
        f_lh.grid(row=3, column=3, sticky=W)
        tb.Radiobutton(f_lh, text="Trực tiếp", variable=self.var_loai_hinh, value='truc_tiep').pack(side=LEFT, padx=5)
        tb.Radiobutton(f_lh, text="Trực tuyến", variable=self.var_loai_hinh, value='truc_tuyen').pack(side=LEFT, padx=5)

        # Tính chất HP
        ttk.Label(container, text="Tính chất HP:").grid(row=4, column=0, sticky=W, pady=5)
        self.var_tinh_chat = tk.StringVar(value='ly_thuyet')
        f_tc = ttk.Frame(container)
        f_tc.grid(row=4, column=1, columnspan=3, sticky=W)
        for val in ['Lý thuyết', 'Hỗn hợp', 'Thực hành', 'Thực tập']:
            tb.Radiobutton(f_tc, text=val, variable=self.var_tinh_chat, value=val.lower(), 
                           command=self._on_tinh_chat_change).pack(side=LEFT, padx=10)

        # Phân bổ giờ (Frame)
        lf_gio = tb.Labelframe(container, text="Phân bổ giờ chi tiết", padding=10)
        lf_gio.grid(row=5, column=0, columnspan=4, sticky=NSEW, pady=15)
        
        self.entries_gio = {}
        labels_gio = [("Lý thuyết", "gio_lt"), ("Bài tập", "gio_bt"), ("Thực hành/TN", "gio_th"), 
                      ("Thảo luận", "gio_tl"), ("Tự học", "gio_tu_hoc")]
        
        for i, (lbl, key) in enumerate(labels_gio):
            ttk.Label(lf_gio, text=lbl).grid(row=0, column=i, padx=5)
            ent = tb.Entry(lf_gio, width=8, justify='center')
            ent.grid(row=1, column=i, padx=5, pady=5)
            ent.bind("<KeyRelease>", lambda e: self._validate_gio())
            self.entries_gio[key] = ent

        self.lbl_sum_gio = tb.Label(lf_gio, text="Tổng cộng: 0", font=('', 10, 'bold'))
        self.lbl_sum_gio.grid(row=1, column=len(labels_gio), padx=20)

        # HP Tiên quyết / Song hành
        lf_hp = tb.Labelframe(container, text="Học phần liên quan", padding=10)
        lf_hp.grid(row=6, column=0, columnspan=4, sticky=NSEW, pady=5)
        
        self.hp_links = {"tien_quyet": [], "thay_the": [], "song_hanh": []}
        
        btns = [("Tiên quyết", "tien_quyet"), ("Thay thế", "thay_the"), ("Song hành", "song_hanh")]
        for i, (lbl, key) in enumerate(btns):
            f = ttk.Frame(lf_hp)
            f.grid(row=0, column=i, sticky=NSEW, padx=10)
            ttk.Label(f, text=f"HP {lbl}:").pack(anchor=W)
            lst = tk.Listbox(f, height=3, width=30)
            lst.pack(pady=2)
            ttk.Button(f, text="+ Thêm", command=lambda k=key: self._add_hp_link(k)).pack(anchor=E)
            self.hp_links[key] = lst

        # Save Button Tab 1
        tb.Button(tab, text="💾 Lưu thông tin chung", bootstyle=INFO, 
                  command=self.save_tab1).pack(side=BOTTOM, pady=10)
        
        return tab

    def _get_khoas(self):
        rows = self.db.conn.execute("SELECT ten FROM khoa ORDER BY ten").fetchall()
        return [r['ten'] for r in rows]

    def _on_tc_change(self):
        try:
            tc = int(self.spn_tc.get())
            tong = tc * 50
            self.ent_tong_gio.config(state='normal')
            self.ent_tong_gio.delete(0, END)
            self.ent_tong_gio.insert(0, str(tong))
            self.ent_tong_gio.config(state='readonly')
            self._validate_gio()
        except: pass

    def _on_tinh_chat_change(self):
        tc = self.var_tinh_chat.get()
        # Logic ẩn/hiện field nếu cần, nhưng đề bài yêu cầu hiển thị 5 field cơ bản
        pass

    def _validate_gio(self):
        try:
            total = sum(int(e.get() or 0) for e in self.entries_gio.values() if e != self.entries_gio['gio_tu_hoc'])
            target = int(self.ent_tong_gio.get() or 0)
            
            self.lbl_sum_gio.config(text=f"Tổng lên lớp: {total}")
            if total != target:
                self.lbl_sum_gio.config(foreground='red')
            else:
                self.lbl_sum_gio.config(foreground='green')
        except: pass

    def _add_hp_link(self, key):
        picker = HocPhanPicker(self, self.db)
        self.wait_window(picker)
        if picker.result:
            hp_id, ma, ten = picker.result
            self.hp_links[key].insert(END, f"{ma} - {ten}")
            # Ở đây cần lưu vào DB nếu hp_id đã tồn tại

    # -------------------------------------------------------------------------
    # TAB 2: GIẢNG VIÊN
    # -------------------------------------------------------------------------
    def _init_tab2(self):
        tab = ttk.Frame(self.nb)
        toolbar = ttk.Frame(tab, padding=5)
        toolbar.pack(side=TOP, fill=X)
        
        tb.Button(toolbar, text="+ Thêm GV chính", bootstyle=PRIMARY, 
                  command=lambda: self._add_gv('chinh')).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="📂 Chọn từ danh mục GV", bootstyle=INFO, 
                  command=self._pick_gv).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="Xóa", bootstyle=DANGER, 
                  command=self._delete_gv).pack(side=LEFT, padx=5)
        
        cols = ("stt", "info", "sdt", "email")
        self.tree_gv = tb.Treeview(tab, columns=cols, show='headings', height=10)
        self.tree_gv.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        self.tree_gv.heading("stt", text="STT")
        self.tree_gv.heading("info", text="Học hàm/học vị, họ tên")
        self.tree_gv.heading("sdt", text="SĐT")
        self.tree_gv.heading("email", text="Email")
        
        self.tree_gv.column("stt", width=50, anchor=CENTER)
        self.tree_gv.column("info", width=300)
        
        return tab

    def _pick_gv(self):
        picker = GiangVienPicker(self, self.db)
        self.wait_window(picker)
        if picker.result:
            gv_id, ho_ten, hoc_vi, khoa, email = picker.result
            # Thêm vào Treeview và lưu vào hp_giang_vien
            stt = len(self.tree_gv.get_children()) + 1
            info = f"{hoc_vi}, {ho_ten}"
            self.tree_gv.insert("", END, values=(stt, info, "", email))

    def _delete_gv(self):
        # Placeholder: Xóa dòng
        pass

    # -------------------------------------------------------------------------
    # TAB 3: MÔ TẢ & MỤC TIÊU
    # -------------------------------------------------------------------------
    def _init_tab3(self):
        tab = ttk.Frame(self.nb)
        
        lbl_mota = tb.Label(tab, text="2. Mô tả tóm tắt học phần:", font=('', 10, 'bold'))
        lbl_mota.pack(anchor=W, padx=10, pady=(10, 0))
        
        self.txt_mo_ta = scrolledtext.ScrolledText(tab, height=6)
        self.txt_mo_ta.pack(fill=X, padx=10, pady=5)
        
        ttk.Separator(tab, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        lbl_mt = tb.Label(tab, text="3. Mục tiêu học phần:", font=('', 10, 'bold'))
        lbl_mt.pack(anchor=W, padx=10)
        
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=X, padx=10)
        tb.Button(btn_frame, text="+ Thêm mục tiêu", bootstyle=SUCCESS, 
                  command=self._add_mt).pack(side=LEFT, padx=5)
        
        cols = ("stt", "ma", "mota", "plo")
        self.tree_mt = tb.Treeview(tab, columns=cols, show='headings', height=8)
        self.tree_mt.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        self.tree_mt.heading("stt", text="STT")
        self.tree_mt.heading("ma", text="Mã MT")
        self.tree_mt.heading("mota", text="Mô tả")
        self.tree_mt.heading("plo", text="PLO tương ứng")
        
        self.tree_mt.column("stt", width=50, anchor=CENTER)
        self.tree_mt.column("ma", width=80, anchor=CENTER)
        self.tree_mt.column("plo", width=150)
        
        return tab

    def _add_mt(self):
        pass

    # -------------------------------------------------------------------------
    # TAB 4: CHUẨN ĐẦU RA (CLO)
    # -------------------------------------------------------------------------
    def _init_tab4(self):
        tab = ttk.Frame(self.nb)
        toolbar = ttk.Frame(tab, padding=5)
        toolbar.pack(side=TOP, fill=X)
        
        tb.Button(toolbar, text="+ Thêm CLO", bootstyle=SUCCESS, 
                  command=self._add_clo).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="Sửa", bootstyle=INFO, 
                  command=self._edit_clo).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="Xóa", bootstyle=DANGER, 
                  command=self._delete_clo).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="↑", bootstyle=LIGHT, 
                  command=lambda: self._move_clo(-1)).pack(side=LEFT, padx=2)
        tb.Button(toolbar, text="↓", bootstyle=LIGHT, 
                  command=lambda: self._move_clo(1)).pack(side=LEFT, padx=2)

        cols = ("stt", "ma", "mota", "plo", "irm")
        self.tree_clo = tb.Treeview(tab, columns=cols, show='headings', height=12)
        self.tree_clo.pack(fill=BOTH, expand=YES, padx=10, pady=5)
        
        self.tree_clo.heading("stt", text="STT")
        self.tree_clo.heading("ma", text="Mã CLO")
        self.tree_clo.heading("mota", text="Mô tả chi tiết")
        self.tree_clo.heading("plo", text="PLO")
        self.tree_clo.heading("irm", text="Mức (I/R/M)")
        
        self.tree_clo.column("stt", width=50, anchor=CENTER)
        self.tree_clo.column("ma", width=80, anchor=CENTER)
        self.tree_clo.column("irm", width=100, anchor=CENTER)
        
        return tab

    def _add_clo(self):
        # Mở dialog thêm CLO với Bloom validation
        dlg = CLOEditDialog(self, "Thêm Chuẩn đầu ra")
        if dlg.result:
            # Add to tree
            pass

    def _edit_clo(self): pass
    def _delete_clo(self): pass
    def _move_clo(self, dir): pass
    def _init_tab5(self):
        tab = ttk.Frame(self.nb)
        sub_nb = ttk.Notebook(tab)
        sub_nb.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        self.tab5_1 = self._init_hoc_lieu_tab(sub_nb, 'chinh')
        self.tab5_2 = self._init_hoc_lieu_tab(sub_nb, 'tham_khao')
        self.tab5_3 = self._init_hoc_lieu_tab(sub_nb, 'khac')
        
        # Tab 5.4-5.7 CSVC
        self.tab5_csvc = ttk.Frame(sub_nb)
        container = ttk.Frame(self.tab5_csvc, padding=10)
        container.pack(fill=BOTH, expand=YES)
        
        fields = [("5.4 Phòng học", "phong_hoc"), ("5.5 Trang thiết bị", "thiet_bi"), 
                  ("5.6 Thiết bị thực hành", "thiet_bi_th"), ("5.7 Hoạt động ngoại khóa", "ngoai_khoa")]
        self.csvc_entries = {}
        for i, (lbl, key) in enumerate(fields):
            ttk.Label(container, text=lbl, font=('', 9, 'bold')).pack(anchor=W, pady=(5, 0))
            ent = tb.Entry(container)
            ent.pack(fill=X, pady=2)
            self.csvc_entries[key] = ent

        sub_nb.add(self.tab5_1, text="5.1 Tài liệu chính")
        sub_nb.add(self.tab5_2, text="5.2 Tài liệu tham khảo")
        sub_nb.add(self.tab5_3, text="5.3 Khác")
        sub_nb.add(self.tab5_csvc, text="5.4-5.7 CSVC")
        
        return tab

    def _init_hoc_lieu_tab(self, master, loai):
        frame = ttk.Frame(master)
        toolbar = ttk.Frame(frame, padding=5)
        toolbar.pack(side=TOP, fill=X)
        tb.Button(toolbar, text="+ Thêm mới", bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        tb.Button(toolbar, text="📂 Chọn từ Thư viện", bootstyle=INFO, 
                  command=lambda t=tree, l=loai: self._pick_tai_lieu(t, l)).pack(side=LEFT, padx=2)
        
        cols = ("stt", "tac_gia", "nam", "ten", "nxb", "link")
        tree = tb.Treeview(frame, columns=cols, show='headings', height=8)
        tree.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        for c in cols: tree.heading(c, text=c.upper())
        tree.column("stt", width=40, anchor=CENTER)
        return frame

    def _pick_tai_lieu(self, tree, loai):
        picker = TaiLieuPicker(self, self.db, loai_filter='Giáo trình' if loai=='chinh' else 'Tài liệu tham khảo')
        self.wait_window(picker)
        if picker.result:
            tl_id, ten, tac_gia, nam, nxb = picker.result
            stt = len(tree.get_children()) + 1
            tree.insert("", END, values=(stt, tac_gia, nam, ten, nxb, ""))

    # -------------------------------------------------------------------------
    # TAB 6: NỘI DUNG CHI TIẾT
    # -------------------------------------------------------------------------
    def _init_tab6(self):
        tab = ttk.Frame(self.nb)
        sub_nb = ttk.Notebook(tab)
        sub_nb.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        self.tab_lt = self._init_noi_dung_tab(sub_nb, 'Lý thuyết')
        self.tab_th = self._init_noi_dung_tab(sub_nb, 'Thực hành')
        
        sub_nb.add(self.tab_lt, text="6.1 Lý thuyết")
        sub_nb.add(self.tab_th, text="6.2 Thực hành")
        return tab

    def _init_noi_dung_tab(self, master, loai):
        frame = ttk.Frame(master)
        toolbar = ttk.Frame(frame, padding=5)
        toolbar.pack(side=TOP, fill=X)
        
        tb.Button(toolbar, text="+ Thêm chương", bootstyle=INFO).pack(side=LEFT, padx=2)
        tb.Button(toolbar, text="+ Thêm nội dung", bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        
        cols = ("stt", "nd", "lt", "bt", "th", "day", "hoc", "clos", "bdg")
        tree = tb.Treeview(frame, columns=cols, show='headings', height=12)
        tree.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        for c in cols: tree.heading(c, text=c.upper())
        tree.column("stt", width=40, anchor=CENTER)
        tree.column("nd", width=250)
        return frame

    # -------------------------------------------------------------------------
    # TAB 7: KIỂM TRA ĐÁNH GIÁ & RUBRICS
    # -------------------------------------------------------------------------
    def _init_tab7(self):
        tab = ttk.Frame(self.nb)
        
        # Upper: Bảng đánh giá
        f_top = tb.Labelframe(tab, text="Mục 8. Kế hoạch kiểm tra, đánh giá", padding=10)
        f_top.pack(fill=BOTH, expand=YES, padx=10, pady=5)
        
        ctrl = ttk.Frame(f_top)
        ctrl.pack(fill=X, pady=5)
        ttk.Label(ctrl, text="Loại bảng:").pack(side=LEFT)
        self.cbo_loai_dg = tb.Combobox(ctrl, values=["Lý thuyết", "Thực hành", "Thực tập", "Đồ án/KLTN"])
        self.cbo_loai_dg.pack(side=LEFT, padx=5)
        self.cbo_loai_dg.set("Lý thuyết")
        
        cols = ("tp", "ts", "bai", "ht", "tc", "clo", "max_cdr", "ts_cdr")
        self.tree_dg = tb.Treeview(f_top, columns=cols, show='headings', height=6)
        self.tree_dg.pack(fill=BOTH, expand=YES)
        for c in cols: self.tree_dg.heading(c, text=c.upper())
        
        self.lbl_sum_ts = tb.Label(f_top, text="Tổng trọng số: 0%", font=('', 10, 'bold'))
        self.lbl_sum_ts.pack(anchor=E, pady=5)

        # Lower: Rubrics
        f_bot = tb.Labelframe(tab, text="Hệ thống Rubrics", padding=10)
        f_bot.pack(fill=BOTH, expand=YES, padx=10, pady=5)
        
        paned = ttk.PanedWindow(f_bot, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=YES)
        
        # List Rubrics
        f_list = ttk.Frame(paned)
        paned.add(f_list, weight=1)
        self.lst_rubrics = tk.Listbox(f_list)
        self.lst_rubrics.pack(fill=BOTH, expand=YES)
        tb.Button(f_list, text="+ Tạo Rubric", bootstyle=SUCCESS).pack(fill=X)
        
        # Detail Rubric
        f_detail = ttk.Frame(paned)
        paned.add(f_detail, weight=3)
        cols_rb = ("tc", "ts", "xs", "t", "d", "cd")
        self.tree_rb_tc = tb.Treeview(f_detail, columns=cols_rb, show='headings', height=5)
        self.tree_rb_tc.pack(fill=BOTH, expand=YES, padx=5)
        for c in cols_rb: self.tree_rb_tc.heading(c, text=c.upper())
        tb.Button(f_detail, text="+ Thêm tiêu chí", bootstyle=INFO).pack(side=RIGHT, padx=5, pady=5)
        
        return tab
    # -------------------------------------------------------------------------
    # TAB 8: LỊCH SỬ CẬP NHẬT
    # -------------------------------------------------------------------------
    def _init_tab8(self):
        tab = ttk.Frame(self.nb)
        toolbar = ttk.Frame(tab, padding=5)
        toolbar.pack(side=TOP, fill=X)
        tb.Button(toolbar, text="+ Thêm lần cập nhật", bootstyle=INFO, command=self._add_history).pack(side=LEFT, padx=5)
        
        cols = ("lan", "nd", "ngay", "nguoi")
        self.tree_history = tb.Treeview(tab, columns=cols, show='headings', height=10)
        self.tree_history.pack(fill=BOTH, expand=YES, padx=10, pady=5)
        for c, t in zip(cols, ["Lần", "Nội dung", "Ngày", "Người cập nhật"]):
            self.tree_history.heading(c, text=t)
        
        footer = ttk.Frame(tab, padding=10)
        footer.pack(fill=X, side=BOTTOM)
        tb.Label(footer, text="Ngày duyệt: ............", font=('', 9)).pack(side=LEFT)
        tb.Label(footer, text="Trưởng khoa ký tên: ....................", font=('', 9)).pack(side=RIGHT)
        
        return tab

    def _add_history(self): pass

    # -------------------------------------------------------------------------
    # DATA LOGIC (Save/Load)
    # -------------------------------------------------------------------------
    def load_data(self):
        """Populate dữ liệu từ DB vào UI."""
        hp = self.data_hp
        if not hp: return
        
        # Tab 1
        self.ent_ten_vn.delete(0, END); self.ent_ten_vn.insert(0, hp.get('ten_viet', ''))
        self.ent_ten_en.delete(0, END); self.ent_ten_en.insert(0, hp.get('ten_anh', ''))
        self.ent_ma_hp.delete(0, END); self.ent_ma_hp.insert(0, hp.get('ma', ''))
        self.cbo_don_vi.set(hp.get('don_vi_ql', ''))
        self.spn_tc.set(hp.get('so_tin_chi', 3))
        self.var_loai.set(hp.get('loai_hp', 'bat_buoc'))
        self.var_tinh_chat.set(hp.get('tinh_chat', 'ly_thuyet'))
        self.var_loai_hinh.set(hp.get('loai_hinh', 'truc_tiep'))
        
        # Giờ
        for k, ent in self.entries_gio.items():
            ent.delete(0, END); ent.insert(0, str(hp.get(k, 0)))
        self._on_tc_change()
        
        self.lbl_status.config(text=f"Đã tải HP: {hp.get('ma')}", foreground='blue')

    def save_tab1(self):
        if not self.hp_id: return
        try:
            data = {
                'ten_viet': self.ent_ten_vn.get(),
                'ten_anh': self.ent_ten_en.get(),
                'don_vi_ql': self.cbo_don_vi.get(),
                'so_tin_chi': int(self.spn_tc.get()),
                'loai_hp': self.var_loai.get(),
                'tinh_chat': self.var_tinh_chat.get(),
                'loai_hinh': self.var_loai_hinh.get(),
                'tong_gio': int(self.ent_tong_gio.get() or 0)
            }
            for k, ent in self.entries_gio.items():
                data[k] = int(ent.get() or 0)
                
            self.repo_hp.update(self.hp_id, data)
            Messagebox.show_info("Thành công", "Đã lưu thông tin Tab 1.")
        except Exception as e:
            Messagebox.show_error("Lỗi", f"Không thể lưu: {str(e)}")

    def save_all(self):
        """Lưu toàn bộ 8 tab."""
        self.save_tab1()
        # Các tab khác sẽ được gọi tương ứng tại đây
        self.lbl_status.config(text="Đã lưu toàn bộ đề cương!", foreground='green')

# -----------------------------------------------------------------------------
# HELPER DIALOGS
# -----------------------------------------------------------------------------
class CLOEditDialog(tb.Toplevel):
    def __init__(self, master, title, initial_data=None):
        super().__init__(title=title, size=(600, 500))
        self.master = master
        self.result = None
        self.bloom_verbs = json.loads(master.db.get_config('bloom_verbs', '{}'))
        self._build_ui(initial_data)
        self.position_center()
        self.grab_set()
        self.wait_window()
        
    def _build_ui(self, initial):
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        ttk.Label(container, text="Mã CLO (VD: CLO1):", font=('', 9, 'bold')).pack(anchor=W)
        self.ent_ma = tb.Entry(container)
        self.ent_ma.pack(fill=X, pady=(0, 10))
        
        ttk.Label(container, text="Mô tả chi tiết:", font=('', 9, 'bold')).pack(anchor=W)
        self.txt_mota = scrolledtext.ScrolledText(container, height=6)
        self.txt_mota.pack(fill=X, pady=(0, 5))
        self.txt_mota.bind("<KeyRelease>", self._validate_bloom)
        
        self.lbl_warn = tb.Label(container, text="", font=('', 9, 'italic'), foreground='orange')
        self.lbl_warn.pack(anchor=W, pady=(0, 10))

        grid = ttk.Frame(container)
        grid.pack(fill=X)
        grid.columnconfigure(1, weight=1)

        ttk.Label(grid, text="PLO tương ứng:").grid(row=0, column=0, sticky=W, pady=5)
        f_plo = ttk.Frame(grid)
        f_plo.grid(row=0, column=1, sticky=EW, padx=5)
        self.cbo_plo = tb.Combobox(f_plo, values=["PLO1", "PLO2", "PLO3", "PLO4", "PLO5"], width=15)
        self.cbo_plo.pack(side=LEFT)
        tb.Button(f_plo, text="...", width=3, command=self._pick_plo).pack(side=LEFT, padx=2)
        
        ttk.Label(grid, text="Mức giảng dạy:").grid(row=1, column=0, sticky=W, pady=5)
        self.cbo_irm = tb.Combobox(grid, values=["I - Introduce", "R - Reinforce", "M - Master"])
        self.cbo_irm.grid(row=1, column=1, sticky=EW, padx=5)
        
        btn_f = ttk.Frame(container)
        btn_f.pack(side=BOTTOM, pady=20)
        tb.Button(btn_f, text="💾 Xác nhận", bootstyle=SUCCESS, width=15, command=self._save).pack(side=LEFT, padx=10)
        tb.Button(btn_f, text="❌ Hủy", bootstyle=SECONDARY, width=15, command=self.destroy).pack(side=LEFT, padx=10)

    def _validate_bloom(self, event=None):
        text = self.txt_mota.get("1.0", END).strip().lower()
        forbidden = ['biết', 'hiểu', 'nắm vững', 'có kiến thức', 'hiểu biết']
        found = [w for w in forbidden if text.startswith(w)]
        if found:
            self.lbl_warn.config(text=f"⚠️ Cảnh báo: '{found[0]}' là động từ yếu. Nên dùng: Phân tích, Vận dụng...")
        else:
            self.lbl_warn.config(text="")

    def _save(self):
        self.result = {
            'ma_clo': self.ent_ma.get(),
            'mo_ta': self.txt_mota.get("1.0", END).strip(),
            'plo_id': self.cbo_plo.get(),
            'level_irm': self.cbo_irm.get()
        }
        self.destroy()

    def _pick_plo(self):
        picker = PLOPicker(self, self.master.db)
        self.wait_window(picker)
        if picker.result:
            plo_id, ma, mo_ta = picker.result
            self.cbo_plo.set(ma)
    def _show_validation(self):
        if not self.ent_ma_hp.get():
            Messagebox.show_warning("Cảnh báo", "Vui lòng nhập mã học phần trước khi kiểm tra.")
            return
        
        # Lưu dữ liệu hiện tại trước khi check (optional)
        report = self.service.get_validation_report(self.ent_ma_hp.get())
        dlg = ValidationReportDialog(self, report)
        
        if report['is_valid']:
            self.btn_export.config(state=NORMAL)
        else:
            self.btn_export.config(state=DISABLED)

    def _export_word(self):
        Messagebox.show_info("Thông báo", "Đang xuất file Word mẫu chuẩn EPU...")

# -----------------------------------------------------------------------------
# VALIDATION DIALOG
# -----------------------------------------------------------------------------
class ValidationReportDialog(tb.Toplevel):
    def __init__(self, master, report):
        super().__init__(title="Báo cáo Kiểm định Đề cương", size=(800, 600))
        self.master = master
        self.report = report
        self._build_ui()
        self.position_center()
        self.grab_set()
        
    def _build_ui(self):
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        # Score Section
        header = ttk.Frame(container)
        header.pack(fill=X, pady=(0, 20))
        
        score = self.report['score']
        color = SUCCESS if score > 80 else (WARNING if score > 50 else DANGER)
        
        ttk.Label(header, text=f"Điểm chất lượng: {score}/100", font=('', 14, 'bold')).pack(side=LEFT)
        pb = tb.Progressbar(header, value=score, bootstyle=color, length=300)
        pb.pack(side=RIGHT, padx=10)

        # Checklist Icons
        f_check = ttk.Frame(container)
        f_check.pack(fill=X, pady=10)
        icons = {'pass': '✅', 'warn': '⚠️', 'fail': '❌'}
        names = {
            'hinh_thuc': 'Hình thức',
            'thong_tin': 'Thông tin chung',
            'muc_tieu_clo': 'Mục tiêu & CLO',
            'noi_dung': 'Nội dung',
            'danh_gia': 'Đánh giá'
        }
        for key, status in self.report['checklist'].items():
            f = ttk.Frame(f_check)
            f.pack(side=LEFT, expand=YES)
            ttk.Label(f, text=f"{icons[status]} {names[key]}", font=('', 10)).pack()

        # Details (Listbox/Treeview)
        nb = ttk.Notebook(container)
        nb.pack(fill=BOTH, expand=YES, pady=10)
        
        # Tab Lỗi & Cảnh báo
        t_err = ttk.Frame(nb)
        nb.add(t_err, text=f"Lỗi & Cảnh báo ({len(self.report['errors']) + len(self.report['warnings'])})")
        
        txt = scrolledtext.ScrolledText(t_err, height=10)
        txt.pack(fill=BOTH, expand=YES)
        
        if self.report['errors']:
            txt.insert(END, "❌ LỖI CẦN SỬA (BLOCK):\n", 'err_header')
            for e in self.report['errors']:
                txt.insert(END, f" • {e}\n", 'err_item')
                
        if self.report['warnings']:
            txt.insert(END, "\n⚠️ CẢNH BÁO (KHUYÊN DÙNG):\n", 'warn_header')
            for w in self.report['warnings']:
                txt.insert(END, f" • {w}\n", 'warn_item')
        
        txt.tag_config('err_header', foreground='red', font=('', 10, 'bold'))
        txt.tag_config('warn_header', foreground='#cc8800', font=('', 10, 'bold'))
        txt.config(state=DISABLED)

        # Tab Ma trận CLO-PLO
        t_mx = ttk.Frame(nb)
        nb.add(t_mx, text="Ma trận CLO-PLO")
        
        matrix = self.master.service.get_matrix_clo_plo(self.master.ent_ma_hp.get())
        if len(matrix) > 1:
            cols = [f"c{i}" for i in range(len(matrix[0]))]
            tree = tb.Treeview(t_mx, columns=cols, show='headings', height=10)
            tree.pack(fill=BOTH, expand=YES)
            for i, col_name in enumerate(matrix[0]):
                tree.heading(f"c{i}", text=col_name)
                tree.column(f"c{i}", width=70, anchor=CENTER)
            
            for row in matrix[1:]:
                tree.insert("", END, values=row)

        tb.Button(container, text="Đóng", bootstyle=SECONDARY, command=self.destroy).pack(side=BOTTOM, pady=10)
