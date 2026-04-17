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
            self.data_hp = self.repo_hp.get_by_id(hp_id)
        
        # State
        self.clo_id_map = {} 
        self.mt_id_map = {}    # Map Treeview iid -> DB ID for Muc Tieu
        self.hl_id_map = {}    # Map Treeview iid -> tai_lieu_id for Hoc Lieu
        self._dirty = False

        self._build_ui()
        self._setup_shortcuts()
        
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
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._prev_tab = 0
        
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

    def _mark_dirty(self, event=None):
        """Đánh dấu có thay đổi chưa lưu."""
        if not self._dirty:
            self._dirty = True
            self.lbl_status.config(text="⚠ Có thay đổi chưa lưu", foreground='orange')

    def _update_status_bar(self):
        """Cập nhật thông tin tóm tắt trên thanh trạng thái sử dụng Service."""
        try:
            ma_hp = self.ent_ma_hp.get()
            if not ma_hp: return
            
            progress = self.service.get_completion_progress(ma_hp)
            if not progress: return
            
            clo_count = progress.get('clo_count', 0)
            nd_count = progress.get('noi_dung_lt', 0) + progress.get('noi_dung_th', 0)
            total_weight = progress.get('danh_gia_ts', 0)
            percent = progress.get('percent', 0)
            
            status_text = f"📊 CLO: {clo_count} | Nội dung: {nd_count} mục | Đánh giá: {total_weight:.0f}% | Hoàn thành: {percent}%"
            self.lbl_status.config(text=status_text, foreground='blue')
            self._dirty = False
        except Exception as e:
            print(f"Error updating status bar: {e}")

    def _setup_shortcuts(self):
        """Đăng ký các phím tắt."""
        self.bind_all("<Control-s>", lambda e: self.save_all())
        self.bind_all("<Control-S>", lambda e: self._save_all_confirm())
        self.bind_all("<Control-k>", lambda e: self._show_validation())
        self.bind_all("<Control-e>", lambda e: self._export_if_ready())
        self.bind_all("<F5>", lambda e: self.load_data())

    def _save_all_confirm(self):
        self.save_all()
        Messagebox.show_info("Thông báo", "Đã lưu toàn bộ dữ liệu (Ctrl+Shift+S)")

    def _export_if_ready(self):
        if self.btn_export['state'] == NORMAL:
            self._export_word()
        else:
            Messagebox.show_warning("Cảnh báo", "Vui lòng 'Lưu tất cả' hoặc 'Kiểm tra' trước khi xuất Word.")

    def _on_tab_changed(self, event):
        current_tab = self.nb.index("current")
        if self._dirty:
            # Show modern dialog
            res = Messagebox.show_question(
                "Bạn có thay đổi chưa lưu. Lưu lại trước khi chuyển tab?", 
                "Cảnh báo", 
                buttons=["Lưu:success", "Không:danger", "Hủy:secondary"]
            )
            if res == "Lưu":
                self.save_all()
            elif res == "Hủy":
                # Switch back to previous tab
                self.nb.select(self._prev_tab)
                return
        
        self._prev_tab = current_tab

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
        self.ent_ten_vn.bind("<KeyRelease>", self._mark_dirty)
        self.ent_ten_vn.bind("<FocusOut>", self._mark_dirty)

        ttk.Label(container, text="Mã học phần:").grid(row=1, column=0, sticky=W, pady=5)
        self.ent_ma_hp = tb.Entry(container)
        self.ent_ma_hp.grid(row=1, column=1, sticky=EW, padx=5)
        self.ent_ma_hp.bind("<KeyRelease>", self._mark_dirty)
        self.ent_ma_hp.bind("<FocusOut>", self._mark_dirty)

        ttk.Label(container, text="Đơn vị quản lý:").grid(row=2, column=0, sticky=W, pady=5)
        self.cbo_don_vi = tb.Combobox(container, values=self._get_khoas())
        self.cbo_don_vi.grid(row=2, column=1, sticky=EW, padx=5)
        self.cbo_don_vi.bind("<<ComboboxSelected>>", self._mark_dirty)

        ttk.Label(container, text="Số tín chỉ:").grid(row=3, column=0, sticky=W, pady=5)
        self.spn_tc = tb.Spinbox(container, from_=1, to=10, command=self._on_tc_change)
        self.spn_tc.grid(row=3, column=1, sticky=EW, padx=5)
        self.spn_tc.bind("<KeyRelease>", lambda e: self._on_tc_change())

        # Cột 2
        ttk.Label(container, text="Tên HP (Tiếng Anh):").grid(row=0, column=2, sticky=W, pady=5)
        self.ent_ten_en = tb.Entry(container)
        self.ent_ten_en.grid(row=0, column=3, sticky=EW, padx=5)
        self.ent_ten_en.bind("<KeyRelease>", self._mark_dirty)
        self.ent_ten_en.bind("<FocusOut>", self._mark_dirty)

        ttk.Label(container, text="Tổng giờ (TCx50):").grid(row=1, column=2, sticky=W, pady=5)
        self.ent_tong_gio = tb.Entry(container, state='readonly', font=('', 10, 'bold'))
        self.ent_tong_gio.grid(row=1, column=3, sticky=EW, padx=5)

        ttk.Label(container, text="Loại HP:").grid(row=2, column=2, sticky=W, pady=5)
        self.var_loai = tk.StringVar(value='bat_buoc')
        f_loai = ttk.Frame(container)
        f_loai.grid(row=2, column=3, sticky=W)
        tb.Radiobutton(f_loai, text="Bắt buộc", variable=self.var_loai, value='bat_buoc', command=self._mark_dirty).pack(side=LEFT, padx=5)
        tb.Radiobutton(f_loai, text="Tự chọn", variable=self.var_loai, value='tu_chon', command=self._mark_dirty).pack(side=LEFT, padx=5)

        ttk.Label(container, text="Loại hình:").grid(row=3, column=2, sticky=W, pady=5)
        self.var_loai_hinh = tk.StringVar(value='truc_tiep')
        f_lh = ttk.Frame(container)
        f_lh.grid(row=3, column=3, sticky=W)
        tb.Radiobutton(f_lh, text="Trực tiếp", variable=self.var_loai_hinh, value='truc_tiep', command=self._mark_dirty).pack(side=LEFT, padx=5)
        tb.Radiobutton(f_lh, text="Trực tuyến", variable=self.var_loai_hinh, value='truc_tuyen', command=self._mark_dirty).pack(side=LEFT, padx=5)

        # Tính chất HP
        ttk.Label(container, text="Tính chất HP:").grid(row=4, column=0, sticky=W, pady=5)
        self.var_tinh_chat = tk.StringVar(value='ly_thuyet')
        f_tc = ttk.Frame(container)
        f_tc.grid(row=4, column=1, columnspan=3, sticky=W)
        for val in ['Lý thuyết', 'Hỗn hợp', 'Thực hành', 'Thực tập']:
            tb.Radiobutton(f_tc, text=val, variable=self.var_tinh_chat, value=val.lower(), 
                           command=lambda: [self._on_tinh_chat_change(), self._mark_dirty()]).pack(side=LEFT, padx=10)

        # Phân bổ giờ (Frame)
        lf_gio = tb.Labelframe(container, text="Phân bổ giờ chi tiết", padding=10)
        lf_gio.grid(row=5, column=0, columnspan=4, sticky=NSEW, pady=15)
        
        self.entries_gio = {}
        labels_gio = [("Lý thuyết", "gio_lt"), ("Bài tập", "gio_bt"), ("Thực hành/TN", "gio_th_tn"), 
                      ("Thảo luận", "gio_tl"), ("Tự học", "gio_tu_hoc")]
        
        for i, (lbl, key) in enumerate(labels_gio):
            ttk.Label(lf_gio, text=lbl).grid(row=0, column=i, padx=5)
            ent = tb.Entry(lf_gio, width=8, justify='center')
            ent.grid(row=1, column=i, padx=5, pady=5)
            ent.bind("<KeyRelease>", lambda e: [self._validate_gio(), self._mark_dirty()])
            ent.bind("<FocusOut>", self._mark_dirty)
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

    def _add_gv(self, vai_tro):
        dlg = tb.Toplevel(title=f"Thêm Giảng viên ({'Chính' if vai_tro=='chinh' else 'Tham gia'})", size=(400, 350))
        container = ttk.Frame(dlg, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        fields = [("Họ tên:", "ten"), ("Học vị:", "hv"), ("SĐT:", "sdt"), ("Email:", "email")]
        ents = {}
        for i, (lbl, key) in enumerate(fields):
            ttk.Label(container, text=lbl).pack(anchor=W, pady=(5,0))
            ent = tb.Entry(container)
            ent.pack(fill=X, pady=2)
            ents[key] = ent
            
        def _on_confirm():
            stt = len(self.tree_gv.get_children()) + 1
            info = f"{ents['hv'].get()}, {ents['ten'].get()}"
            self.tree_gv.insert("", END, values=(stt, info, ents['sdt'].get(), ents['email'].get()))
            dlg.destroy()
            
        tb.Button(container, text="Xác nhận", bootstyle=SUCCESS, command=_on_confirm).pack(pady=20)
        dlg.position_center()
        dlg.grab_set()

    def _delete_gv(self):
        selected = self.tree_gv.selection()
        for item in selected:
            self.tree_gv.delete(item)

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
        self.tree_mt.bind("<Double-1>", lambda e: self._edit_mt())
        
        self.tree_mt.heading("stt", text="STT")
        self.tree_mt.heading("ma", text="Mã MT")
        self.tree_mt.heading("mota", text="Mô tả")
        self.tree_mt.heading("plo", text="PLO tương ứng")
        
        self.tree_mt.column("stt", width=50, anchor=CENTER)
        self.tree_mt.column("ma", width=80, anchor=CENTER)
        self.tree_mt.column("plo", width=150)
        
        return tab

    def _add_mt(self):
        dlg = tb.Toplevel(title="Thêm Mục tiêu Học phần", size=(500, 400))
        container = ttk.Frame(dlg, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        ttk.Label(container, text="Mã Mục tiêu (VD: MT1):").pack(anchor=W)
        ent_ma = tb.Entry(container)
        ent_ma.pack(fill=X, pady=5)
        
        ttk.Label(container, text="Mô tả:").pack(anchor=W)
        txt_mota = scrolledtext.ScrolledText(container, height=5)
        txt_mota.pack(fill=X, pady=5)
        
        ttk.Label(container, text="PLO ánh xạ:").pack(anchor=W)
        cbo_plo = tb.Combobox(container, values=[p['ma'] for p in self.db.get_all_cdr_ctdt()])
        cbo_plo.pack(fill=X, pady=5)
        
        def _on_save():
            data = {
                'so_thu_tu': len(self.tree_mt.get_children()) + 1,
                'ma_mt': ent_ma.get(),
                'mo_ta': txt_mota.get("1.0", END).strip(),
                'cdr_ma': cbo_plo.get()
            }
            # Add to Tree
            iid = self.tree_mt.insert("", END, values=(data['so_thu_tu'], data['ma_mt'], data['mo_ta'], data['cdr_ma']))
            # Add to DB
            db_id = self.repo_hp.add_muc_tieu(self.hp_id, data)
            self.mt_id_map[iid] = db_id
            dlg.destroy()
            
        tb.Button(container, text="💾 Lưu", command=_on_save, bootstyle=SUCCESS).pack(pady=20)
        dlg.position_center()
        dlg.grab_set()

    def _edit_mt(self):
        selected = self.tree_mt.selection()
        if not selected: return
        iid = selected[0]
        vals = self.tree_mt.item(iid, 'values')
        
        dlg = tb.Toplevel(title="Sửa Mục tiêu Học phần", size=(500, 400))
        container = ttk.Frame(dlg, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        ttk.Label(container, text="Mã Mục tiêu:").pack(anchor=W)
        ent_ma = tb.Entry(container); ent_ma.insert(0, vals[1]); ent_ma.pack(fill=X, pady=5)
        ttk.Label(container, text="Mô tả:").pack(anchor=W)
        txt_mota = scrolledtext.ScrolledText(container, height=5); txt_mota.insert("1.0", vals[2]); txt_mota.pack(fill=X, pady=5)
        ttk.Label(container, text="PLO ánh xạ:").pack(anchor=W)
        cbo_plo = tb.Combobox(container, values=[p['ma'] for p in self.db.get_all_cdr_ctdt()]); cbo_plo.set(vals[3]); cbo_plo.pack(fill=X, pady=5)
        
        def _on_save():
            new_vals = (vals[0], ent_ma.get(), txt_mota.get("1.0", END).strip(), cbo_plo.get())
            self.tree_mt.item(iid, values=new_vals)
            # Need a better way to update specific MT in DB if we want immediate save
            # For now, save_all will handle full update
            dlg.destroy()
            
        tb.Button(container, text="💾 Cập nhật", command=_on_save, bootstyle=INFO).pack(pady=20)
        dlg.position_center(); dlg.grab_set()

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
            data = dlg.result
            data['ma_hp'] = self.ent_ma_hp.get()
            data['thu_tu'] = len(self.tree_clo.get_children()) + 1
            
            db_id = self.repo_clo.insert(data)
            
            stt = data['thu_tu']
            iid = self.tree_clo.insert("", END, values=(stt, data['ma_clo'], data['mo_ta'], data['plo_id'], data['level_irm']))
            self.clo_id_map[iid] = db_id

    def _edit_clo(self):
        selected = self.tree_clo.selection()
        if not selected:
            Messagebox.show_warning("Cảnh báo", "Vui lòng chọn một CLO để sửa.")
            return
        
        iid = selected[0]
        db_id = self.clo_id_map.get(iid)
        
        # Lấy data hiện tại
        vals = self.tree_clo.item(iid, 'values')
        initial_data = {
            'ma_clo': vals[1],
            'mo_ta': vals[2],
            'plo_id': vals[3],
            'level_irm': vals[4]
        }
        
        dlg = CLOEditDialog(self, "Sửa Chuẩn đầu ra", initial_data=initial_data)
        if dlg.result:
            data = dlg.result
            self.repo_clo.update(db_id, data)
            
            # Update UI
            self.tree_clo.item(iid, values=(vals[0], data['ma_clo'], data['mo_ta'], data['plo_id'], data['level_irm']))

    def _delete_clo(self):
        selected = self.tree_clo.selection()
        if not selected: return
        
        if not ask_modern_yesno("Xác nhận", "Bạn có chắc chắn muốn xóa CLO này?"):
            return
            
        for iid in selected:
            db_id = self.clo_id_map.pop(iid, None)
            if db_id:
                self.repo_clo.delete(db_id)
            self.tree_clo.delete(iid)
            
        # Renumber STT
        for i, idx in enumerate(self.tree_clo.get_children()):
            stt = i + 1
            vals = list(self.tree_clo.item(idx, 'values'))
            vals[0] = stt
            self.tree_clo.item(idx, values=vals)
            # Update thu_tu in DB too? Yes, for consistency
            db_id = self.clo_id_map.get(idx)
            if db_id:
                self.repo_clo.update(db_id, {'thu_tu': stt})

    def _move_clo(self, direction):
        selected = self.tree_clo.selection()
        if not selected: return
        
        iid = selected[0]
        idx = self.tree_clo.index(iid)
        new_idx = idx + direction
        
        if 0 <= new_idx < len(self.tree_clo.get_children()):
            # Swap in UI
            others = self.tree_clo.get_children()
            target_iid = others[new_idx]
            
            # Move selection
            self.tree_clo.move(iid, "", new_idx)
            
            # Recalculate all STT and update DB
            for i, item_iid in enumerate(self.tree_clo.get_children()):
                stt = i + 1
                curr_vals = list(self.tree_clo.item(item_iid, 'values'))
                curr_vals[0] = stt
                self.tree_clo.item(item_iid, values=curr_vals)
                
                db_id = self.clo_id_map.get(item_iid)
                if db_id:
                    self.repo_clo.update(db_id, {'thu_tu': stt})
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
        
        self.trees_hoc_lieu = {}
        tab_chinh = self._init_hoc_lieu_tab(sub_nb, 'chinh')
        self.trees_hoc_lieu['chinh'] = tab_chinh.tree
        sub_nb.add(tab_chinh, text="Tài liệu chính")
        
        tab_tk = self._init_hoc_lieu_tab(sub_nb, 'tham_khao')
        self.trees_hoc_lieu['tham_khao'] = tab_tk.tree
        sub_nb.add(tab_tk, text="Tài liệu tham khảo")
        
        tab_khac = self._init_hoc_lieu_tab(sub_nb, 'khac')
        self.trees_hoc_lieu['khac'] = tab_khac.tree
        sub_nb.add(tab_khac, text="Tài liệu khác")
        
        sub_nb.add(self._init_tab5_csvc(sub_nb), text="CSVC & Phần mềm")
        return tab

    def _init_hoc_lieu_tab(self, master, loai):
        frame = ttk.Frame(master)
        
        # BUG 1 Fix: Create tree BEFORE creating buttons that use it in lambda
        cols = ("stt", "tac_gia", "nam", "ten", "nxb", "link")
        tree = tb.Treeview(frame, columns=cols, show='headings', height=8)
        frame.tree = tree # Store reference
        
        toolbar = ttk.Frame(frame, padding=5)
        toolbar.pack(side=TOP, fill=X)
        tb.Button(toolbar, text="+ Thêm mới", bootstyle=SUCCESS).pack(side=LEFT, padx=2)
        tb.Button(toolbar, text="📂 Chọn từ Thư viện", bootstyle=INFO, 
                  command=lambda t=tree, l=loai: self._pick_tai_lieu(t, l)).pack(side=LEFT, padx=2)
        
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
            iid = tree.insert("", END, values=(stt, tac_gia, nam, ten, nxb, ""))
            self.hl_id_map[iid] = tl_id

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
        frame.tree = tree # Expose tree
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
        self.lbl_sum_ts.pack(side=LEFT, pady=5)
        
        tb.Button(ctrl, text="🗑 Xóa", bootstyle=DANGER, command=self._delete_danh_gia).pack(side=RIGHT, padx=5)

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
        tb.Button(f_list, text="+ Tạo Rubric", bootstyle=SUCCESS, command=self._create_rubric).pack(fill=X)
        
        # Detail Rubric
        f_detail = ttk.Frame(paned)
        paned.add(f_detail, weight=3)
        cols_rb = ("tc", "ts", "xs", "t", "d", "cd")
        self.tree_rb_tc = tb.Treeview(f_detail, columns=cols_rb, show='headings', height=5)
        self.tree_rb_tc.pack(fill=BOTH, expand=YES, padx=5)
        for c in cols_rb: self.tree_rb_tc.heading(c, text=c.upper())
        tb.Button(f_detail, text="+ Thêm tiêu chí", bootstyle=INFO, command=self._add_rubric_tc).pack(side=RIGHT, padx=5, pady=5)
        
        return tab
    # TAB 7 Logic
    def _delete_danh_gia(self):
        sel = self.tree_dg.selection()
        if not sel: return
        if ask_modern_yesno(self, "Xác nhận", "Xóa bài đánh giá này?"):
            self.tree_dg.delete(sel[0])
            self._update_ts_label()
            self._mark_dirty()

    def _update_ts_label(self):
        total = 0
        for iid in self.tree_dg.get_children():
            try:
                # Giả sử cột trọng số là cột 1 (index 1) theo SCHEMA
                # cols = ("tp", "ts", "bai", "ht", "tc", "clo", "max_cdr", "ts_cdr")
                ts_val = self.tree_dg.item(iid, 'values')[1]
                total += float(ts_val.replace('%', '').strip() or 0)
            except: pass
        
        color = SUCCESS if abs(total - 50) < 0.1 or abs(total - 100) < 0.1 else DANGER
        self.lbl_sum_ts.config(text=f"Tổng trọng số: {total:.0f}%", bootstyle=color)

    def _create_rubric(self):
        dlg = RubricEditDialog(self, self.db, self.hp_id)
        if hasattr(dlg, 'result') and dlg.result:
            self.lst_rubrics.insert(END, dlg.result['ten'])
            self._mark_dirty()

    def _add_rubric_tc(self):
        sel_rubric = self.lst_rubrics.curselection()
        if not sel_rubric:
            Messagebox.show_warning("Cảnh báo", "Chọn một Rubric trước.")
            return
        
        # Mở mini dialog nhập tiêu chí (Tạm dùng simple dialog hoặc Toplevel)
        dlg = tb.Toplevel(title="Thêm tiêu chí Rubric", size=(400, 300))
        container = ttk.Frame(dlg, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        fields = ["Tiêu chí", "Trọng số (%)", "Xuất sắc", "Tốt", "Đạt", "Chưa đạt"]
        entries = []
        for f in fields:
            ttk.Label(container, text=f"{f}:").pack(anchor=W)
            e = tb.Entry(container)
            e.pack(fill=X, pady=2)
            entries.append(e)
            
        def save():
            vals = [e.get() for e in entries]
            self.tree_rb_tc.insert('', END, values=vals)
            dlg.destroy()
            self._mark_dirty()
            
        tb.Button(container, text="Thêm", command=save, bootstyle=SUCCESS).pack(pady=10)

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

    def _add_history(self):
        dlg = tb.Toplevel(title="Thêm Lịch sử Cập nhật", size=(450, 450))
        container = ttk.Frame(dlg, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        ttk.Label(container, text="Nội dung cập nhật:").pack(anchor=W)
        txt_nd = scrolledtext.ScrolledText(container, height=5)
        txt_nd.pack(fill=X, pady=5)
        
        ttk.Label(container, text="Ngày (yyyy-mm-dd):").pack(anchor=W)
        ent_ngay = tb.Entry(container); ent_ngay.insert(0, datetime.now().strftime('%Y-%m-%d')); ent_ngay.pack(fill=X, pady=5)
        
        ttk.Label(container, text="Người thực hiện:").pack(anchor=W)
        ent_nguoi = tb.Entry(container); ent_nguoi.pack(fill=X, pady=5)
        
        def _on_save():
            all_rows = self.tree_history.get_children()
            lan = 1
            if all_rows:
                try: lan = max(int(self.tree_history.item(r, 'values')[0]) for r in all_rows) + 1
                except: lan = len(all_rows) + 1
                
            data = {
                'lan': lan,
                'noi_dung': txt_nd.get("1.0", END).strip(),
                'nguoi_cap_nhat': ent_nguoi.get(),
                'ngay_cap_nhat': ent_ngay.get()
            }
            # Add to Tree
            self.tree_history.insert("", END, values=(data['lan'], data['noi_dung'], "", data['nguoi_cap_nhat'], "", data['ngay_cap_nhat']))
            # Save immediate? Yes, as per user request (Lưu vào DB)
            self.repo_hp.add_lich_su(self.hp_id, data)
            dlg.destroy()
            
        tb.Button(container, text="💾 Lưu", command=_on_save, bootstyle=SUCCESS).pack(pady=20)
        dlg.position_center(); dlg.grab_set()

    def save_all(self):
        if not self.hp_id:
            Messagebox.show_warning("Cảnh báo", "Không tìm thấy ID học phần.")
            return

        try:
            # 1. Tab 1
            self.save_tab1()

            # 2. Tab 3 (Mục tiêu)
            mt_list = []
            for iid in self.tree_mt.get_children():
                vals = self.tree_mt.item(iid, 'values')
                mt_list.append({
                    'so_thu_tu': vals[0],
                    'mo_ta': vals[2],
                    'cdr_ma': vals[3],
                    'nhom': '',
                    'la_tieu_de_nhom': 0
                })
            self.db.set_muc_tieu(self.hp_id, mt_list)

            # 3. Tab 4 (CLO) - Using set_clo logic
            clo_list = []
            for iid in self.tree_clo.get_children():
                vals = self.tree_clo.item(iid, 'values')
                clo_list.append({
                    'ma': vals[1],
                    'mo_ta': vals[2],
                    'cdr_ma': vals[3],
                    'level_irm': vals[4],
                    'nhom': '',
                    'la_tieu_de_nhom': 0
                })
            self.db.set_clo(self.hp_id, clo_list)

            # 4. Tab 5 (Học liệu)
            hl_list = []
            for loai, tree in self.trees_hoc_lieu.items():
                for idx, iid in enumerate(tree.get_children()):
                    vals = tree.item(iid, 'values')
                    tl_id = self.hl_id_map.get(iid)
                    if tl_id:
                        hl_list.append({
                            'tai_lieu_id': tl_id,
                            'so_thu_tu': idx + 1,
                            'loai': loai,
                            'yc_trang_thiet_bi': ''
                        })
            self.db.set_hoc_lieu(self.hp_id, hl_list)
            
            # Tab 5 CSVC
            csvc_data = {}
            for k, ent in self.csvc_entries.items():
                csvc_data[k] = ent.get()
            self.repo_hp.update(self.hp_id, {'co_so_vat_chat': json.dumps(csvc_data)})

            # 5. Tab 8 History
            hist_list = []
            for iid in self.tree_history.get_children():
                v = self.tree_history.item(iid, 'values')
                hist_list.append({
                    'lan': v[0], 
                    'noi_dung': v[1], 
                    'nguoi_cap_nhat': v[3], 
                    'ngay_cap_nhat': v[5]
                })
            self.db.set_lich_su(self.hp_id, hist_list)

            self._update_status_bar()
            self._dirty = False
            
            now = datetime.now().strftime("%H:%M")
            self.lbl_status.config(text=f"✅ Đã lưu toàn bộ đề cương lúc {now}", foreground='green')
            self.btn_export.config(state=NORMAL)
            Messagebox.show_info("Thành công", f"Đã lưu toàn bộ dữ liệu đề cương lúc {now}")
            
        except Exception as e:
            Messagebox.show_error("Lỗi", f"Lỗi khi lưu: {str(e)}")

    def _show_validation(self):
        if not self.ent_ma_hp.get():
            Messagebox.show_warning("Cảnh báo", "Vui lòng nhập mã học phần trước khi kiểm tra.")
            return
        
        # Tự động lưu nháp trước khi check (optional)
        ma_hp = self.ent_ma_hp.get()
        # Thu thập data hiện tại từ UI để lưu nháp
        draft_data = {
            'info': {'ma': ma_hp, 'ten_viet': self.ent_ten_vn.get()} # Thêm các field khác nếu cần
        }
        report = self.service.get_validation_report(ma_hp, auto_save_data=draft_data)
        dlg = ValidationReportDialog(self, report)
        
        if report['is_valid']:
            self.btn_export.config(state=NORMAL)
        else:
            self.btn_export.config(state=DISABLED)

    def _export_word(self):
        ma_hp = self.ent_ma_hp.get().strip()
        if not ma_hp:
            Messagebox.show_warning("Cảnh báo", "Chưa có mã học phần.")
            return
        
        # 1. Validate trước
        report = self.service.get_validation_report(ma_hp)
        if not report['is_valid']:
            if not ask_modern_yesno(self, "Cảnh báo", 
                f"Đề cương còn {len(report['errors'])} lỗi. Vẫn xuất?"):
                return
        
        # 2. Chọn đường dẫn lưu
        from tkinter import filedialog
        default_name = f"DCCTHP_{ma_hp}_{datetime.now().strftime('%Y%m%d')}.docx"
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile=default_name,
            title="Lưu file Đề cương"
        )
        if not path:
            return
        
        # 3. Xuất
        try:
            from word_export import export_de_cuong
            success = export_de_cuong(self.db, ma_hp, path)
            if success:
                Messagebox.show_info("Thành công", f"Đã xuất file:\n{path}")
                # Hỏi mở file luôn không?
                if ask_modern_yesno(self, "Mở file?", "Mở file Word vừa xuất?"):
                    import os, subprocess
                    os.startfile(path) if os.name == 'nt' else subprocess.Popen(['open', path])
        except Exception as e:
            Messagebox.show_error("Lỗi", f"Xuất thất bại: {str(e)}")

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
        # Handle the case where key might be gio_th_tn but old data has gio_th
        if 'gio_th_tn' in self.entries_gio and not self.entries_gio['gio_th_tn'].get():
            self.entries_gio['gio_th_tn'].insert(0, str(hp.get('gio_th_tn', hp.get('gio_th', 0))))

        # CLO Tab
        self._load_clos()
        # Tab 3 (Mục tiêu)
        self._load_muc_tieu()
        # Tab 5 (Học liệu)
        self._load_hoc_lieu()
        # Tab 8 (Lịch sử)
        self._load_history()

        self._on_tc_change()
        self._update_status_bar()
        self._dirty = False # Reset dirty after load
        
        self.lbl_status.config(text=f"Đã tải HP: {hp.get('ma')}", foreground='blue')

    def _load_muc_tieu(self):
        self.tree_mt.delete(*self.tree_mt.get_children())
        self.mt_id_map.clear()
        if not self.hp_id: return
        items = self.db.get_muc_tieu(self.hp_id)
        for row in items:
            stt = row['so_thu_tu']
            ma_virtual = f"MT{stt}"
            iid = self.tree_mt.insert("", END, values=(stt, ma_virtual, row['mo_ta'], row['cdr_ma']))
            self.mt_id_map[iid] = row['id']

    def _load_hoc_lieu(self):
        self.hl_id_map.clear()
        for loai, tree in self.trees_hoc_lieu.items():
            tree.delete(*tree.get_children())
            items = self.db.get_hoc_lieu(self.hp_id, loai)
            for i, row in enumerate(items):
                iid = tree.insert("", END, values=(row['so_thu_tu'], row['tac_gia'], row['nam_xb'], row['ten'], row['nha_xb'], ""))
                self.hl_id_map[iid] = row['tai_lieu_id']

    def _load_history(self):
        self.tree_history.delete(*self.tree_history.get_children())
        if not self.hp_id: return
        items = self.db.get_lich_su(self.hp_id)
        for row in items:
            self.tree_history.insert("", END, values=(row['lan'], row['noi_dung'], "", row['nguoi_cap_nhat'], "", row['ngay_cap_nhat']))

    def _load_clos(self):
        self.tree_clo.delete(*self.tree_clo.get_children())
        self.clo_id_map.clear()
        
        ma_hp = self.ent_ma_hp.get()
        if not ma_hp: return
        
        clos = self.repo_clo.get_all(ma_hp)
        for i, row in enumerate(clos):
            stt = i + 1
            iid = self.tree_clo.insert("", END, values=(stt, row['ma_clo'], row['mo_ta'], row['plo_id'], row['level_irm']))
            self.clo_id_map[iid] = row['id']

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
        
        if initial:
            self.ent_ma.insert(0, initial.get('ma_clo', ''))
            self.txt_mota.insert("1.0", initial.get('mo_ta', ''))
            self.cbo_plo.set(initial.get('plo_id', ''))
            self.cbo_irm.set(initial.get('level_irm', ''))

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

    # -------------------------------------------------------------------------
    # VALIDATION & EXPORT (Moved to DeCuongSection - BUG 2)
    # -------------------------------------------------------------------------

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

class RubricEditDialog(tb.Toplevel):
    def __init__(self, master, db, hp_id):
        super().__init__(master, title="Tạo/Sửa Rubric", size=(800, 600))
        self.db = db
        self.hp_id = hp_id
        self.result = None
        
        container = ttk.Frame(self, padding=20)
        container.pack(fill=BOTH, expand=YES)
        
        # Fields
        f_info = ttk.Frame(container)
        f_info.pack(fill=X, pady=10)
        
        ttk.Label(f_info, text="Tên Rubric:").grid(row=0, column=0, sticky=W)
        self.ent_ten = tb.Entry(f_info, width=50)
        self.ent_ten.grid(row=0, column=1, sticky=W, padx=5)
        
        ttk.Label(f_info, text="CLO:").grid(row=1, column=0, sticky=W, pady=5)
        # Lấy list CLO từ master (DeCuongSection)
        clo_list = [master.tree_clo.item(i)['values'][1] for i in master.tree_clo.get_children()]
        self.cbo_clo = tb.Combobox(f_info, values=clo_list)
        self.cbo_clo.grid(row=1, column=1, sticky=W, padx=5)
        
        # Criteria Table
        self.cols = ("tc", "ts", "xs", "t", "d", "cd")
        self.tree = tb.Treeview(container, columns=self.cols, show='headings', height=10)
        self.tree.pack(fill=BOTH, expand=YES, pady=10)
        for c, t in zip(self.cols, ["Tiêu chí", "TS (%)", "Xuất sắc", "Tốt", "Đạt", "Chưa đạt"]):
            self.tree.heading(c, text=t)
            
        f_btns = ttk.Frame(container)
        f_btns.pack(fill=X)
        
        tb.Button(f_btns, text="💾 Lưu Rubric", bootstyle=SUCCESS, command=self._save).pack(side=RIGHT, padx=5)
        tb.Button(f_btns, text="+ Thêm tiêu chí", bootstyle=INFO, command=self._add_tc).pack(side=RIGHT)

    def _add_tc(self):
        # Mở mini dialog
        dlg = tb.Toplevel(title="Tiêu chí", size=(400, 500))
        cont = ttk.Frame(dlg, padding=20)
        cont.pack(fill=BOTH, expand=YES)
        labels = ["Tiêu chí", "Trọng số (%)", "Xuất sắc (9-10)", "Tốt (7-8)", "Đạt (5-6)", "Chưa đạt (<5)"]
        ents = []
        for l in labels:
            ttk.Label(cont, text=l).pack(anchor=W)
            e = tb.Entry(cont)
            e.pack(fill=X, pady=2)
            ents.append(e)
        def add():
            self.tree.insert('', END, values=[e.get() for e in ents])
            dlg.destroy()
        tb.Button(cont, text="Thêm vào bảng", command=add, bootstyle=SUCCESS).pack(pady=10)

    def _save(self):
        ten = self.ent_ten.get().strip()
        if not ten:
            Messagebox.show_warning("Lỗi", "Vui lòng nhập tên Rubric.")
            return
            
        # Thu thập tiêu chí
        tc_list = []
        for iid in self.tree.get_children():
            tc_list.append(self.tree.item(iid)['values'])
            
        self.result = {'ten': ten, 'clo': self.cbo_clo.get(), 'criteria': tc_list}
        self.destroy()
