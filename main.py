# main.py — QLCTDT: Quản lý Đề cương Chi tiết Học phần | EPU
import os
import sys
import ctypes
import tkinter as tk
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk as tb
    HAS_TTKBOOTSTRAP = False
from tkinter import filedialog, messagebox

# Đảm bảo import được các module cùng thư mục
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import Database
from shared_data_dialog import SharedDataDialog
import word_export
import word_import
from statistics_dialog import StatisticsDialog
from settings_dialog import SettingsDialog
from datetime import datetime
import json
from utils.threading_utils import run_threaded_task
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)

# New Architectural Layers
from core.container import get_container, init_container
from sections.registry import SectionRegistry, auto_register_all_sections
from sections.dynamic_section import DynamicSection
from section_manager_dialog import SectionManagerDialog
import db
from template_manager_dialog import TemplateManagerDialog
from version_history_dialog import VersionHistoryDialog
from import_preview_dialog import ImportPreviewDialog
from modules.de_cuong.ui.system_menu.schema_manager_panel import SchemaManagerDialog

from controllers.main_controller import MainController
from controllers.tree_controller import TreeController
from services.import_export_service import ImportExportService
from services.hoc_phan_service import HocPhanService
from services.validation_service import ValidationService
from repositories.hoc_phan_repository import HocPhanRepository

from sections.sec1_thong_tin import Sec1ThongTin
from sections.sec2_mo_ta     import Sec2MoTa
from sections.sec3_muc_tieu  import Sec3MucTieu
from sections.sec4_clo       import Sec4Clo
from sections.sec5_hoc_lieu  import Sec5CoSoVatChat
from sections.sec6_noi_dung  import Sec6NoiDung
from sections.sec7_pp_day    import Sec7PpDay
from sections.sec8_kiem_tra  import Sec8KiemTra
from sections.sec9_quy_dinh  import Sec9QuyDinh
from sections.sec11_doi_ngu   import Sec11DoiNgu
from sections.sec12_phu_luc  import Sec12PhuLuc
from sections.sec13_cap_nhat import Sec13CapNhat
from sections.base_section import setup_treeview_style, apply_theme, THEMES, set_window_icon, \
                                    CLR_BG, CLR_PRIMARY, CLR_PRIMARY2, CLR_TEXT, CLR_ACCENT, \
                                    CLR_SIDEBAR, CLR_SIDEBAR_FG, CLR_SIDEBAR_SEL


APP_TITLE = 'APM System - Quản lý Đề cương Chi tiết Học phần | EPU'
VERSION   = '1.4.5'  # FIXED N-01: Sync với tên thư mục

# Các biến màu sắc chuyển sang base_section để dùng chung


class QLCTDTApp:
    def __init__(self, root):
        self.root = root
        set_window_icon(self.root)
        # Nếu dùng tb.Window thì title và size ở main()
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry('1280x850')
        self.root.minsize(1100, 700)

        self.container = init_container('qlctdt.db')
        self.db = self.container.db
        self.val_service = self.container.validation_svc
        self.deccuong_service = self.container.deccuong_svc

        self.hp_repo = HocPhanRepository(self.db)
        self.hp_service = HocPhanService(self.hp_repo, self.val_service)
        self.ie_service = ImportExportService(self.db)
        
        self.controller = MainController(
            self.hp_service, self.ie_service, self.val_service, self
        )
        
        self.current_hp_id  = None
        self._modified      = False
        self._hp_id_map     = {}   # iid in tree → hp_id
        self._khoa_iid_map  = {}   # iid → khoa name (group node)

        # Load theme from DB
        theme = self.db.get_config('theme', 'dark')
        # Bắt buộc đổi sang dark mode để thể hiện cho user
        self.db.set_config('theme', 'dark') 
        apply_theme('dark')
        
        self._setup_style()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        self.load_hp_list()
        self._show_welcome()

        # Accuracy: Check recovery (sau khi đã nạp list)
        self.root.after(1000, self._check_recovery)
        # Accuracy: Start auto-save loop
        self._start_auto_save()

    def _start_auto_save(self):
        """Khởi chạy vòng lặp tự động lưu nháp mỗi 5 phút."""
        interval = 5 * 60 * 1000 # 5 minutes
        self.root.after(interval, self._on_auto_save)

    def _on_auto_save(self):
        if self.current_hp_id:
            try:
                data = {}
                for i, sec in enumerate(self._sections):
                    # Một số section có thể chưa build UI nếu dùng lazy loading
                    if hasattr(sec, 'get_data_dict'):
                        data[f'sec{i+1}'] = sec.get_data_dict()
                
                if data:
                    self.db.save_draft(self.current_hp_id, json.dumps(data, ensure_ascii=False))
                    self._set_status(f"⏲ Auto-saved: {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                print(f"[Auto-Save Error] {e}")
        
        self._start_auto_save() # Repeat

    def _check_recovery(self):
        """Kiểm tra xem có bản nháp chưa lưu không."""
        try:
            draft_row = self.db.conn.execute("SELECT hp_id, updated_at FROM temp_draft ORDER BY updated_at DESC LIMIT 1").fetchone()
            if draft_row:
                hid = draft_row[0]
                at_time = draft_row[1]
                
                hp_name = "Học phần đang sửa"
                hp_info = self.db.get_hoc_phan(hid)
                if hp_info: hp_name = hp_info['ten_viet']

                msg = f"Hệ thống tìm thấy một bản lưu nháp của học phần:\n'{hp_name}'\nvào lúc {at_time}.\n\nBạn có muốn khôi phục không?"
                if messagebox.askyesno("Khôi phục dữ liệu", msg):
                    self._load_all_sections(hid)
                    # Select in tree
                    for iid, dbid in self._hp_id_map.items():
                        if dbid == hid:
                            self.hp_tree.selection_set(iid)
                            self.hp_tree.see(iid)
                            break
                    
                    # Apply draft data
                    draft = self.db.get_draft(hid)
                    if draft:
                        data = json.loads(draft['data_json'])
                        for i, sec in enumerate(self._sections):
                            key = f'sec{i+1}'
                            # Đảm bảo UI đã build trước khi apply
                            if key in data:
                                if hasattr(sec, 'apply_data_dict'):
                                    sec.apply_data_dict(data[key])
                    
                    messagebox.showinfo("Thành công", "Đã khôi phục dữ liệu từ bản nháp.")
                
                # Xóa nháp sau khi đã hỏi (cho dù có khôi phục hay không)
                self.db.delete_draft(hid)
        except Exception as e:
            print(f"[Recovery Error] {e}")

    def toggle_theme(self):
        from sections.base_section import CURRENT_THEME, apply_theme
        new_theme = 'dark' if CURRENT_THEME == 'light' else 'light'
        apply_theme(new_theme)
        self.db.set_config('theme', new_theme)
        
        # Với ttkbootstrap, ta đổi theme của root style
        if HAS_TTKBOOTSTRAP:
            tb_theme = 'darkly' if new_theme == 'dark' else 'litera'
            self.root.style.theme_use(tb_theme)
        
        # Update toolbar button icon
        theme_icon = '☀️' if new_theme == 'dark' else '🌙'
        self.btn_theme.configure(text=theme_icon)
        
        # Update sidebar tags
        self._hp_tree_setup_tags()

    def _refresh_all_sections_theme(self):
        for sec in self._sections:
            # Recursively update theme for non-ttk widgets
            self._update_widget_colors(sec)
            if hasattr(sec, 'update_theme'):
                sec.update_theme()

    def _update_widget_colors(self, parent):
        from sections.base_section import CLR_BG, CLR_TEXT, CLR_ROW1
        for child in parent.winfo_children():
            if isinstance(child, tk.Text):
                child.configure(background=CLR_ROW1, foreground=CLR_TEXT, insertbackground=CLR_TEXT)
            elif isinstance(child, tk.Canvas):
                child.configure(background=CLR_BG)
            elif isinstance(child, tk.Listbox):
                child.configure(background=CLR_ROW1, foreground=CLR_TEXT)
            
            if child.winfo_children():
                self._update_widget_colors(child)

    # ── Style ───────────────────────────────────────────────────────────────
    def _setup_style(self):
        # Khi dùng ttkbootstrap darkly, đa số style được tự động hóa.
        # Ta chỉ định nghĩa một số bootstyle đặc biệt nếu cần.
        pass

    # ── Menu ────────────────────────────────────────────────────────────────
    def _build_menu(self):
        menubar = tk.Menu(self.root, font=('Arial', 10))
        self.root.config(menu=menubar)

        # File
        mfile = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=mfile)
        mfile.add_command(label='💾 Lưu Đề cương',          command=self.save_hp,    accelerator='Ctrl+S')
        mfile.add_separator()
        mfile.add_command(label='✖ Thoát', command=self._on_quit)

        # Import
        mimport = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Import', menu=mimport)
        mimport.add_command(label='📥 Import 1 file Word',      command=self.import_word_single)
        mimport.add_command(label='📥 Import hàng loạt (folder)', command=self.import_word_batch)

        # Export
        mexport = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Export', menu=mexport)
        mexport.add_command(label='📤 Xuất Word (built-in)',     command=self.export_word_builtin)
        mexport.add_command(label='📤 Xuất Word (template)',     command=self.export_word_template)
        mexport.add_separator()
        mexport.add_command(label='📚 Xuất hàng loạt (built-in)',command=lambda: self.export_bulk('builtin'))
        mexport.add_command(label='📚 Xuất hàng loạt (template)',command=lambda: self.export_bulk('template'))

        # Dữ liệu chung
        mdata = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Dữ liệu Chung', menu=mdata)
        mdata.add_command(label='👤 Giảng viên / Khoa / CDR',
                          command=self.open_shared_data)

        # Template
        mtpl = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Template', menu=mtpl)
        mtpl.add_command(label='📋 Quản lý Template Word', command=self.open_template_manager)

        # Thống kê
        mstats = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Thống kê', menu=mstats)
        mstats.add_command(label='📊 Thống kê & Báo cáo', command=self.open_statistics)

        # Hệ thống
        msys = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Hệ thống', menu=msys)
        msys.add_command(label='📐 Mẫu đề cương', command=self.open_schema_manager)
        msys.add_command(label='📂 Quản lý Mục đề cương', command=self.open_section_manager)
        msys.add_command(label='⚙️ Thiết lập hệ thống', command=self.open_settings)
        msys.add_separator()
        msys.add_command(label='🛠 Tùy biến UI (Inline CRUD)', command=self._toggle_inline_crud)

        # Trợ giúp
        mhelp = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Trợ giúp', menu=mhelp)
        mhelp.add_command(label='� Cấu trúc file Excel mẫu', command=self._show_excel_help)
        mhelp.add_separator()
        mhelp.add_command(label='�👨‍💻 Tác giả', command=self._show_author)
        mhelp.add_command(label=f'ℹ Về {APP_TITLE} v{VERSION}', command=self._show_about)

        # Shortcuts
        self.root.bind('<Control-s>', lambda _e: self.save_hp())
        # FIXED N-06: Xác nhận trước khi thoát
        self.root.protocol('WM_DELETE_WINDOW', self._on_quit)

    # ── Toolbar ─────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        if hasattr(self, 'tb'):
            self.tb.destroy()
            
        from sections.base_section import CURRENT_THEME
        
        # Header phong cách QBMSys (Title + Theme selector)
        header_frm = tb.Frame(self.root)
        header_frm.pack(side='top', fill='x', padx=10, pady=(10, 0))
        tb.Label(header_frm, text="APM System", font=('Arial', 14, 'bold')).pack(side='left')

        # Nút đổi màu ở bên phải Header
        theme_icon = '☀️' if CURRENT_THEME == 'dark' else '🌙'
        self.btn_theme = tb.Button(header_frm, text=f"{theme_icon} Giao diện", 
                                     bootstyle='link', command=self.toggle_theme)
        self.btn_theme.pack(side='right')

        tb_frame = tb.Frame(self.root, padding=(6, 4))
        tb_frame.pack(side='top', fill='x', padx=10)
        self.tb = tb_frame

        btn_data = [
            ('💾 Lưu',           self.save_hp,              'success'),
            (None, None, None), 
            ('📥 Import',        self.import_word_single,   'outline-info'),
            ('📥 Import Folder', self.import_word_batch,    'outline-info'),
            (None, None, None),
            ('📤 Xuất Word',     self.export_word_builtin,  'outline-info'),
            ('📚 Xuất nhiều',    lambda: self.export_bulk('builtin'), 'outline-info'),
            (None, None, None),
            ('👥 Dữ liệu Chung', self.open_shared_data,     'outline-secondary'),
            ('📊 Thống kê',      self.open_statistics,       'outline-warning'),
            ('📜 Lịch sử',      self.open_version_history,  'outline-info'),
            ('🔍 Đối soát',      self.run_full_audit,        'outline-danger'),
        ]
        for item in btn_data:
            text, cmd, bstyle = item
            if text is None:
                tb.Separator(tb_frame, orient='vertical').pack(side='left', padx=6, pady=2, fill='y')
            else:
                tb.Button(tb_frame, text=text, command=cmd, bootstyle=bstyle).pack(side='left', padx=2)

        # Right: Search
        tb.Label(tb_frame, text='🔍', font=('Arial', 12)).pack(side='right', padx=(0, 2))
        self.v_search = tk.StringVar()
        self.v_search.trace_add('write', self._on_search_change)
        tb.Entry(tb_frame, textvariable=self.v_search, width=22).pack(side='right', padx=4)
        tb.Label(tb_frame, text='Tìm học phần:').pack(side='right')

        # Overall Progress Bar
        prog_frm = tb.Frame(header_frm)
        prog_frm.pack(side='right', padx=8)
        self.lbl_percent = tb.Label(prog_frm, text='Hoàn thành: 0%',
                                     font=('Arial', 9), bootstyle='muted')
        self.lbl_percent.pack(side='top', anchor='e')
        self.progress_bar = tb.Progressbar(prog_frm, length=120,
                                            bootstyle='success-striped', maximum=100)
        self.progress_bar.pack(side='top')

    def _toggle_inline_crud(self):
        """Bật/tắt chế độ Inline CRUD cho tab hiện tại."""
        if hasattr(self, '_overlay_window') and self._overlay_window:
            if getattr(self._overlay_window, '_active', False):
                self._overlay_window.deactivate()
                self._overlay_window = None
                return
            
        from sections.inline_crud_overlay import InlineCRUDOverlay
        
        # Chỉ áp dụng overlay cho tab hiện tại đang mở trong Notebook
        try:
            current_tab_idx = self.nb.index("current")
            if 0 <= current_tab_idx < len(self._sections):
                current_section = self._sections[current_tab_idx]
                self._overlay_window = InlineCRUDOverlay(current_section, self.db)
                self._overlay_window.activate()
            else:
                self.show_warning("Chú ý", "Không tìm thấy giao diện tab hiện tại.")
        except Exception as e:
            self.show_warning("Chú ý", f"Không thể bật Tùy biến: {e}")

    # ── Body ─────────────────────────────────────────────────────────────────
    def _build_body(self):
        paned = tb.Panedwindow(self.root, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=10)

        # ── Left panel: HP list ──────────────────────────────────────────────
        left = tb.Frame(paned, width=280)
        paned.add(left, weight=0)

        tb.Label(left, text='📚 Danh sách Học phần', font=('Arial', 11, 'bold')).pack(fill='x', pady=5)

        # Nature filter
        filter_frm = tb.Frame(left)
        filter_frm.pack(fill='x', pady=(0, 5))
        self.v_nature_filter = tk.StringVar(value='-- Tất cả --')
        
        # Load natures from config
        nature_str = self.db.get_config('hp_natures', 'Lý thuyết, Thực hành, Hỗn hợp, Đồ án')
        natures = ['-- Tất cả --'] + [n.strip() for n in nature_str.split(',') if n.strip()]
        
        self.nature_combo = tb.Combobox(filter_frm, textvariable=self.v_nature_filter, values=natures, state='readonly', width=15)
        self.nature_combo.pack(side='left', fill='x', expand=True)
        self.nature_combo.bind('<<ComboboxSelected>>', lambda _: self._on_search_change())

        tree_frm = tb.Frame(left)
        tree_frm.pack(fill='both', expand=True, pady=(2, 4))

        self.hp_tree = tb.Treeview(tree_frm, show='tree', bootstyle='primary', selectmode='extended')
        self.hp_tree.column('#0', width=350, minwidth=200, stretch=True)
        
        vsb = tb.Scrollbar(tree_frm, orient='vertical', command=self.hp_tree.yview)
        hsb = tb.Scrollbar(tree_frm, orient='horizontal', command=self.hp_tree.xview)
        
        self.hp_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        self.hp_tree.pack(side='left', fill='both', expand=True)

        self.hp_tree.bind('<<TreeviewSelect>>', self._on_hp_select)
        self.hp_tree.bind('<Double-1>', self._on_hp_double_click)
        
        # Initialize Tree Controller
        def _update_map(new_map): self._hp_id_map = new_map
        self.tree_controller = TreeController(self.hp_tree, self.db, _update_map)
        self.tree_controller.setup_dnd()
        
        self.hp_tree.bind('<<TreeviewOpen>>', lambda e: self.tree_controller.on_expand(e, 
                          self.v_nature_filter.get() if hasattr(self, 'v_nature_filter') else '-- Tất cả --'))

        # Right-click menu
        self._hp_ctx = tk.Menu(self.root, tearoff=0)
        self._hp_ctx.add_command(label='💾 Lưu Đề cương', command=self.save_hp)
        self._hp_ctx.add_command(label='📋 Sao chép học phần', command=self.clone_hp)
        self._hp_ctx.add_command(label='📤 Xuất Word',    command=self.export_word_builtin)
        self._hp_ctx.add_command(label='📚 Xuất Word nhiều mục', command=self.export_bulk)
        self.hp_tree.bind('<Button-3>', self._on_hp_right_click)

        # Count label
        self.lbl_count = tb.Label(left, text='0 học phần', font=('Arial', 9))
        self.lbl_count.pack(anchor='w')

        # ── Right panel: Editor ─────────────────────────────────────────────
        right = tb.Frame(paned)
        paned.add(right, weight=1)

        self.nb = tb.Notebook(right, bootstyle='info')
        self.nb.pack(fill='both', expand=True, pady=4)
        
        def _on_modified(sec, is_dirty):
            if sec not in self._sections: return
            idx = self._sections.index(sec)
            label = self.nb.tab(idx, "text")
            if is_dirty:
                if not label.endswith(" *"):
                    self.nb.tab(idx, text=label + " *")
            else:
                if label.endswith(" *"):
                    self.nb.tab(idx, text=label[:-2])
            self._modified = any(getattr(s, 'is_modified', False) for s in self._sections)
        
        # Auto-register and Load Sections from Registry
        auto_register_all_sections()
        self._sections = []
        
        # 1. Các Mục mặc định từ code
        tab_list = SectionRegistry.get_all()
        for index, (label, cls) in enumerate(tab_list):
            try:
                sec = cls(self.nb, self.db, lazy=True, modified_callback=_on_modified)
                self.nb.add(sec, text=label)
                self._sections.append(sec)
                if cls.__name__ == 'Sec1ThongTin': self.sec1 = sec
                if cls.__name__ == 'SecProgramInfo': self.sec_program = sec
            except Exception as e:
                print(f"[Main] Error loading section {label}: {e}")

        # 2. Các Mục động từ Database
        dynamic_list = self.db.list_sections()
        for ds in dynamic_list:
            try:
                sec = DynamicSection(self.nb, self.db, 
                                     section_key=ds['section_key'], 
                                     label=ds['label'],
                                     lazy=True, 
                                     modified_callback=_on_modified)
                self.nb.add(sec, text=ds['label'])
                self._sections.append(sec)
            except Exception as e:
                print(f"[Main] Error loading dynamic section {ds['label']}: {e}")

        # Config Tab Badge (Phase 4: Sử dụng Class Name để mapping linh hoạt)
        self._TAB_CONFIG = {
            'Sec1ThongTin': ('1. Thông tin',     's1_thong_tin',    ''),
            'Sec3MucTieu':  ('3. Mục tiêu',      's3_muc_tieu',     ''),
            'Sec4Clo':      ('4. CLO',           's4_clo',          lambda p: f'({p.get("s4_clo_count",0)})'),
            'Sec5CoSoVatChat':  ('5. Cơ sở vật chất', 's5_hoc_lieu', ''),
            'Sec6NoiDung':  ('6. Nội dung',      's6_noi_dung',     lambda p: f'({p.get("s6_lt_count",0)} mục)'),
            'Sec8KiemTra':  ('8. Kiểm tra',      's8_danh_gia_ok',  lambda p: f'({p.get("s8_trong_so",0):.0f}%)'),
            'Sec11DoiNgu':  ('11. Đội ngũ GV',   's11_gv',          ''),
            'Sec13CapNhat': ('13. Cập nhật',     's13_cap_nhat',    ''),
        }

        self.nb.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        
        # Load dashboard by default


    # ── Status bar ───────────────────────────────────────────────────────────
    def _build_statusbar(self):
        # Khung log phong cách QBMSys
        frm_log = tb.Labelframe(self.root, text="Thông báo hệ thống", padding=5)
        frm_log.pack(side='bottom', fill='x', padx=10, pady=(0, 5))
        
        self.v_status = tk.StringVar(value='Sẵn sàng')
        tb.Label(frm_log, textvariable=self.v_status, font=('Arial', 9)).pack(side='left', padx=5)
        
        # Validation Summary
        self.v_val_summary = tk.StringVar(value='✅ Quy chuẩn: Đạt')
        self.lbl_val = tb.Label(frm_log, textvariable=self.v_val_summary, font=('Arial', 9, 'bold'), foreground='green')
        self.lbl_val.pack(side='right', padx=10)
        self.lbl_val.bind("<Button-1>", lambda _: self._toggle_validation_panel())

        # Validation Panel (Hidden by default)
        self.val_panel = tb.Frame(self.root, height=150)
        # We don't pack it yet
        
        cols = ("type", "section", "message")
        heads = ("Loại", "Phần", "Nội dung cảnh báo")
        widths = (80, 150, 600)
        from sections.base_section import make_tree
        self.val_tree_frm, self.val_tree = make_tree(self.val_panel, cols, heads, widths, height=5)
        self.val_tree_frm.pack(fill='both', expand=True, padx=10, pady=5)
        self.val_tree.bind("<<TreeviewSelect>>", self._on_validation_click)

        # Author info bám đáy phải
        info_frame = tb.Frame(self.root)
        info_frame.pack(side='bottom', fill='x', padx=10, pady=(0, 5))
        tb.Label(info_frame, text=f"v{VERSION} | VuPQ | vupq@epu.edu.vn", bootstyle='danger').pack(side='right')

    def _toggle_validation_panel(self):
        if self.val_panel.winfo_ismapped():
            self.val_panel.pack_forget()
        else:
            self.val_panel.pack(side='bottom', fill='x', before=self.lbl_count.master.master) # Insert before sidebar/body paned

    def _on_validation_click(self, event):
        sel = self.val_tree.selection()
        if not sel: return
        item = self.val_tree.item(sel[0])
        sec_name = item['values'][1]
        # Map sec_name back to tab index and select it
        for i, sec in enumerate(self._sections):
            if self.nb.tab(i, "text").strip(" *") == sec_name:
                self.nb.select(i)
                break

    def update_validation_results(self, issues):
        self.val_tree.delete(*self.val_tree.get_children())
        if not issues:
            self.v_val_summary.set("✅ Quy chuẩn: Đạt")
            self.lbl_val.configure(foreground="green")
            if self.val_panel.winfo_ismapped():
                self.val_panel.pack_forget()
            return

        self.v_val_summary.set(f"⚠️ Cảnh báo: {len(issues)} vấn đề")
        self.lbl_val.configure(foreground="orange")
        
        for issue in issues:
            tag = 'accent' if issue['type'] == 'error' else 'odd'
            self.val_tree.insert("", "end", values=(
                issue['type'].upper(), 
                issue.get('section', 'Chung'), 
                issue['message']
            ), tags=(tag,))
        
        # Auto show if errors
        if any(i['type'] == 'error' for i in issues) and not self.val_panel.winfo_ismapped():
            self._toggle_validation_panel()

    def _set_status(self, msg):
        self.v_status.set(msg)
        self.root.after(5000, lambda: self.v_status.set('Sẵn sàng'))
        
    def set_status(self, msg):
        self._set_status(msg)
        
    def show_warning(self, title, msg):
        show_modern_warning(self.root, title, msg)
        
    def show_error(self, title, msg):
        show_modern_error(self.root, title, msg)
        
    def show_info(self, title, msg):
        show_modern_info(self.root, title, msg)
        
    def ask_yesno(self, title, msg):
        return ask_modern_yesno(self.root, title, msg)

    # ── Progress Dialog Management ──────────────────────────────────────────
    def show_progress_dialog(self, title="Đang xử lý..."):
        self._progress_dlg = _ProgressDialog(self.root, title)
        self.root.update()

    def update_progress(self, current, total, message):
        if hasattr(self, '_progress_dlg'):
            self._progress_dlg.update_progress(current, total, message)
        self.root.update()

    def close_progress_dialog(self):
        if hasattr(self, '_progress_dlg'):
            self._progress_dlg.destroy()
            del self._progress_dlg

    def show_import_preview_dialog(self, preview_items):
        dlg = ImportPreviewDialog(self.root, preview_items)
        self.root.wait_window(dlg)
        return dlg.result

    def show_history_dialog(self, history):
        _HistoryDialog(self.root, history)

    def _on_search_change(self, *args):
        """Xử lý tìm kiếm có độ trễ (debounce) để tránh lag giao diện."""
        if hasattr(self, '_search_timer'):
            self.root.after_cancel(self._search_timer)
        self._search_timer = self.root.after(400, self.load_hp_list)

    # ── HP List ──────────────────────────────────────────────────────────────
    def load_hp_list(self):
        kw = self.v_search.get().strip() if hasattr(self, 'v_search') else ''
        nature = self.v_nature_filter.get() if hasattr(self, 'v_nature_filter') else '-- Tất cả --'
        
        count = self.tree_controller.load_list(kw, nature)
        
        if kw:
            self.lbl_count.config(text=f'{count} kết quả tìm kiếm')
        else:
            self.lbl_count.config(text='📚 Danh sách Học phần')

    # Legacy tree methods removed (moved to TreeController)
    def _load_root_nodes(self, nature): pass
    def _on_tree_expand(self, event): pass
    def _load_search_results(self, kw, nature): pass

    def _on_hp_select(self, _e=None):
        sel = self.hp_tree.selection()
        if not sel:
            return
        iid = sel[0]
        
        # 1. Xử lý logic thay đổi dữ liệu
        if self._modified:
            # Chỉ hỏi nếu thực sự chuyển sang đối tượng khác
            # (Ở đây ta tạm đơn giản hóa là luôn hỏi nếu có thay đổi)
            ans = messagebox.askyesnocancel('Chưa lưu',
                'Hệ thống ghi nhận bạn có thay đổi chưa lưu.\nLưu trước khi chuyển không?')
            if ans is None:
                return
            if ans:
                self.save_hp()
            self._modified = False # Reset sau khi đã hỏi/lưu

        # 2. Kiểm tra nếu là node group hoặc CTĐT
        if iid not in self._hp_id_map:
            if iid.startswith('lazy_ctdt_'):
                try:
                    ctdt_id = int(iid.split('_')[2])
                    self.current_hp_id = None # Thoát khỏi ngữ cảnh HP
                    self.show_program_info(ctdt_id)
                except: pass
            return  # group node

        hp_id = self._hp_id_map[iid]
        if hp_id == self.current_hp_id:
            return
            
        self.current_hp_id = hp_id
        self._load_all_sections(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        name = hp['ten_viet'] if hp else f'HP #{hp_id}'
        self.root.title(f'{name} — {APP_TITLE}')
        self._set_status(f'Đang xem: {name}')
        self._modified = False

    def show_program_info(self, ctdt_id):
        """Hiển thị thông tin tổng quan của Chương trình đào tạo."""
        if hasattr(self, 'sec_program'):
            # Chuyển sang tab đầu tiên (Thông tin CTĐT)
            for i, sec in enumerate(self._sections):
                if sec == self.sec_program:
                    self.nb.select(i)
                else:
                    # Xóa trắng dữ liệu các tab học phần khi đang xem CTĐT
                    if hasattr(sec, 'clear'):
                        sec.clear()
            
            self.sec_program.load_ctdt(ctdt_id)
            
            ctdt_data = self.db.get_ctdt(ctdt_id)
            name = ctdt_data['ten'] if ctdt_data else f'CTĐT #{ctdt_id}'
            self.root.title(f'{name} — {APP_TITLE}')
            self._set_status(f'Đang xem CTĐT: {name}')
        else:
            print("[WARN] SecProgramInfo not found in _sections")

    def _on_hp_double_click(self, e):
        self._on_hp_select()
        self.nb.select(0)

    def clone_hp(self):
        new_id = self.controller.clone_hp(self.current_hp_id)
        if new_id:
            self.load_hp_list()
            # Select the new one
            new_iid = f'hp_{new_id}_none'
            if self.hp_tree.exists(new_iid):
                self.hp_tree.selection_set(new_iid)
                self.hp_tree.see(new_iid)

    def _on_hp_right_click(self, e):
        iid = self.hp_tree.identify_row(e.y)
        if iid and iid in self._hp_id_map:
            self.hp_tree.selection_set(iid)
            self._on_hp_select()
            self._hp_ctx.tk_popup(e.x_root, e.y_root)

    def _hp_tree_setup_tags(self):
        """Cấu hình màu sắc các dòng trong Sidebar theo theme."""
        if not hasattr(self, 'hp_tree'):
            return
        from sections.base_section import CLR_ACCENT, CLR_PRIMARY, CLR_PRIMARY2, CLR_TEXT
        # Thay đổi màu sắc sang phong cách tối giản (minimalist)
        self.hp_tree.tag_configure('bac',   foreground=CLR_TEXT, font=('Arial', 10, 'bold'))
        self.hp_tree.tag_configure('ctdt',  foreground=CLR_PRIMARY, font=('Arial', 9, 'bold'))
        self.hp_tree.tag_configure('khoi',  foreground=CLR_TEXT, font=('Arial', 9, 'bold')) 
        self.hp_tree.tag_configure('cn',    foreground=CLR_TEXT, font=('Arial', 9, 'italic'))
        self.hp_tree.tag_configure('hp',    foreground=CLR_TEXT)

    def _load_all_sections(self, hp_id):
        # Chỉ load tab đang active hiện tại
        active_tab = self.nb.index("current")
        if 0 <= active_tab < len(self._sections):
            sec = self._sections[active_tab]
            try:
                sec.load(hp_id)
                self.update_tab_badges(hp_id)
            except Exception as ex:
                print(f'[WARN] {sec.__class__.__name__}.load: {ex}')

    def _on_tab_changed(self, event):
        """Khi chuyển tab, nạp dữ liệu cho tab mới nếu có học phần đang chọn."""
        active_tab = self.nb.index("current")
        
        if 0 <= active_tab < len(self._sections):
            sec = self._sections[active_tab]
            # Đảm bảo giao diện được khởi tạo khi tab được hiển thị
            if hasattr(sec, 'ensure_ui'):
                sec.ensure_ui()
            
            if self.current_hp_id:
                # BaseSection.load sẽ tự gọi ensure_ui()
                if sec.hp_id != self.current_hp_id:
                    try:
                        sec.load(self.current_hp_id)
                        self.update_tab_badges(self.current_hp_id)
                    except Exception as ex:
                        print(f'[WARN] {sec.__class__.__name__}.load (tab change): {ex}')

    # ── CRUD HP ──────────────────────────────────────────────────────────────
    def export_bulk(self, mode='builtin'):
        """Xuất hàng loạt đề cương đã chọn."""
        sel = self.hp_tree.selection()
        hp_ids = []
        for iid in sel:
            if iid in self._hp_id_map:
                hid = self._hp_id_map[iid]
                if hid not in hp_ids:
                    hp_ids.append(hid)
        
        if not hp_ids:
            messagebox.showinfo('Thông báo', 'Vui lòng chọn ít nhất một học phần để xuất.\n'
                                '(Giữ Ctrl hoặc Shift để chọn nhiều)')
            return

        # Chọn template nếu mode là template
        template_path = None
        if mode == 'template':
            templates = self.db.get_all_templates()
            if not templates:
                messagebox.showinfo('Không có template',
                                    'Chưa có template nào. Dùng menu Template > Quản lý để thêm.')
                return
            # Use default template
            default_tpl = next((t for t in templates if t['la_mac_dinh']), templates[0])
            template_path = default_tpl['file_path']
            if not template_path or not os.path.exists(template_path):
                messagebox.showerror('Lỗi', f'File template không tồn tại: {template_path}')
                return

        dir_path = filedialog.askdirectory(title='Chọn thư mục lưu các file Word')
        if not dir_path:
            return

        self._set_status(f'Đang xuất {len(hp_ids)} học phần...')
        
        try:
            results = run_threaded_task(
                self.root,
                word_export.export_batch,
                title=f"Đang xuất {len(hp_ids)} học phần...",
                args=(self.db, hp_ids, dir_path, template_path)
            )

            msg = f"Thành công: {results['success']}\nLỗi: {results['errors']}"
            if results['errors'] > 0:
                err_details = [d['error'] for d in results['details'] if d['status'] == 'error']
                msg += '\n\nChi tiết lỗi:\n' + '\n'.join(err_details[:5])
            show_modern_info(self.root, 'Hoàn thành xuất hàng loạt', msg)
            self._set_status('Đã hoàn thành xuất hàng loạt.')
        except Exception as e:
            show_modern_error(self.root, 'Lỗi xuất hàng loạt', str(e))
            self._set_status('Lỗi xuất hàng loạt.')

    def save_hp(self):
        if self.current_hp_id is None:
            # FIXED M-08: Không có HP nào được chọn
            return

        # 1. Thu thập dữ liệu từ các section đã được load
        full_data = {}      # For validation
        modified_data = {}  # For actual DB save
        for i, sec in enumerate(self._sections):
            if hasattr(sec, 'get_data_dict') and sec.hp_id == self.current_hp_id:
                try:
                    d = sec.get_data_dict()
                    full_data[f'sec{i+1}'] = d
                    
                    # Tự động lưu dữ liệu các trường bổ sung (Inline CRUD)
                    extra_d = sec.get_extra_data_dict()
                    if extra_d:
                         self.db.save_extra_data(self.current_hp_id, sec.section_key, extra_d)

                    if getattr(sec, 'is_modified', False):
                        modified_data[f'sec{i+1}'] = d
                except Exception as ex:
                    print(f'[WARN] {sec.__class__.__name__}.get_data_dict: {ex}')

        if not modified_data:
            # FIXED M-04: Vẫn refresh badge dù không có thay đổi
            self._set_status('ℹ Không có thay đổi nào để lưu.')
            self.update_tab_badges(self.current_hp_id)
            return

        # 2. Delegate to controller
        # FIXED M-08: Nếu full_data rỗng (section chưa load) thì không validate
        data_for_validation = full_data if full_data else modified_data
        success = self.controller.save_current_hp(self.current_hp_id, data_for_validation, modified_data)
        
        if success:
            self._modified = False
            # Reset all section dirty states
            for sec in self._sections:
                if hasattr(sec, 'reset_modified'):
                    sec.reset_modified()

            self.load_hp_list()
            
            # Re-select items belonging to current_hp_id
            new_selection = [iid for iid, hid in self._hp_id_map.items() if hid == self.current_hp_id]
            if new_selection:
                self.hp_tree.selection_set(new_selection)
                self.hp_tree.see(new_selection[0])
            
            self._set_status(f'✔ Đã lưu thành công')
            self.update_tab_badges()

    def _validate_accuracy(self):
        """Deprecated: Validation is now handled by MainController/ValidationService."""
        return True

    def _on_quit(self):
        """FIXED N-06: Xác nhận trước khi thoát nếu có dữ liệu chưa lưu."""
        if self._modified:
            ans = messagebox.askyesnocancel(
                'Chưa lưu',
                'Bạn có thay đổi chưa được lưu.\nLưu trước khi thoát không?'
            )
            if ans is None:
                return  # Cancel — không thoát
            if ans:
                self.save_hp()
        self.root.quit()

    def delete_hp(self):
        hp = self.db.get_hoc_phan(self.current_hp_id)
        name = hp['ten_viet'] if hp else f'HP #{self.current_hp_id}'
        
        if self.controller.delete_hp(self.current_hp_id, name):
            self.current_hp_id = None
            self._modified = False
            self.load_hp_list()
            for sec in self._sections:
                try: sec.clear()
                except Exception: pass
            self.root.title(APP_TITLE)

    def update_tab_badges(self, hp_id=None):
        """Cập nhật badge ✅/⚠ trên tab labels sau khi load/save HP."""
        if hp_id is None:
            hp_id = getattr(self, 'current_hp_id', None)
        if hp_id is None:
            return
        
        try:
            progress = self.deccuong_service.get_completion_progress(hp_id)
        except Exception:
            return
        
        for tab_idx, sec in enumerate(self._sections):
            cls_name = sec.__class__.__name__
            if cls_name not in self._TAB_CONFIG:
                continue
                
            base_label, prog_key, extra_fn = self._TAB_CONFIG[cls_name]
            try:
                # Get current text to preserve dirty flag
                current_text = self.nb.tab(tab_idx, "text")
                is_dirty = current_text.endswith(" *")
                
                ok = progress.get(prog_key, False)
                icon = '✅' if ok else '⚠'
                extra = ''
                if callable(extra_fn):
                    extra = extra_fn(progress)
                elif isinstance(extra_fn, str):
                    extra = extra_fn
                
                new_label = f'{icon} {base_label} {extra}'.strip()
                if is_dirty:
                    new_label += " *"
                self.nb.tab(tab_idx, text=new_label)
            except Exception:
                pass
        
        # Cập nhật progress bar tổng thể
        if hasattr(self, 'progress_bar'):
            self.progress_bar['value'] = progress.get('percent', 0)
        if hasattr(self, 'lbl_percent'):
            self.lbl_percent.config(
                text=f"Hoàn thành: {progress.get('percent', 0)}%"
            )

    # ── Export Word ──────────────────────────────────────────────────────────
    def export_word_builtin(self):
        if self.current_hp_id is None:
            self.show_warning('Cảnh báo', 'Chưa chọn học phần nào.')
            return
        # Save first
        self.save_hp()
        hp = self.db.get_hoc_phan(self.current_hp_id)
        default_name = (hp.get('ten_viet') if hp else 'DecuongHP').replace(' ', '_') + '.docx'
        out_path = filedialog.asksaveasfilename(
            title='Lưu file Word',
            defaultextension='.docx',
            initialfile=default_name,
            filetypes=[('Word Document', '*.docx')])
        if not out_path: return

        # Check default template
        templates = self.db.get_all_templates()
        default_tpl = next((t for t in templates if t.get('la_mac_dinh')), None)
        
        mode = 'builtin'
        template_path = None
        if default_tpl and default_tpl.get('file_path') and os.path.exists(default_tpl['file_path']):
            mode = 'template'
            template_path = default_tpl['file_path']

        if self.controller.export_word(self.current_hp_id, out_path, mode=mode, template_path=template_path):
            mode_text = ' theo Template mặc định' if mode == 'template' else ' theo mẫu hệ thống'
            if self.ask_yesno('Xuất thành công', f'Đã xuất{mode_text}:\n{out_path}\n\nMở file ngay không?'):
                os.startfile(out_path)

    def export_word_template(self):
        """Xuất dùng template Word."""
        if self.current_hp_id is None:
            self.show_warning('Cảnh báo', 'Chưa chọn học phần nào.')
            return
        
        # Save first
        self.save_hp()
        
        _TemplateChoiceDialog(self, self.current_hp_id)

    def import_word_single(self):
        path = filedialog.askopenfilename(
            title='Chọn file Word đề cương',
            filetypes=[('Word Document', '*.docx'), ('All files', '*.*')])
        if not path: return
        
        results = self.controller.import_batch_with_preview([path])
        if results and results['success'] > 0:
             # Select the new HP if possible
             pass

    def import_word_batch(self):
        """Import hàng loạt đề cương từ folder."""
        folder = filedialog.askdirectory(title='Chọn folder chứa các file .docx đề cương')
        if not folder:
            return

        # Count files
        docx_files = [
            os.path.join(folder, f) 
            for f in os.listdir(folder) 
            if f.lower().endswith('.docx') and not f.startswith('~')
        ]
        
        if not docx_files:
            messagebox.showinfo('Không tìm thấy', 'Folder không chứa file .docx nào.')
            return

        # Lấy khoa_id hiện tại nếu có (có thể hỏi user hoặc lấy từ context)
        # Ở đây ta cứ để None để service tự xử lý hoặc user chọn sau
        self.controller.import_batch_with_preview(docx_files)
        self.load_hp_list()


    def open_statistics(self):
        StatisticsDialog(self.root, self.db)

    def open_schema_manager(self):
        dlg = SchemaManagerDialog(self.root, self.db)
        self.root.wait_window(dlg)
        self.load_hp_list()

    def open_section_manager(self):
        """Mở cửa sổ quản lý các Mục đề cương bổ sung."""
        dlg = SectionManagerDialog(self.root, self.db)
        self.root.wait_window(dlg)
        if dlg.result_changed:
            if ask_modern_yesno(self.root, "Khởi động lại", "Danh sách các Mục đã thay đổi. Bạn có muốn khởi động lại ứng dụng để áp dụng thay đổi ngay bây giờ không?"):
                import sys
                import os
                python = sys.executable
                os.execl(python, python, *sys.argv)

    def open_settings(self):
        dlg = SettingsDialog(self.root, self.db)
        self.root.wait_window(dlg)
        # Refresh main tree view to reflect CTĐT/Nganh changes
        self.load_hp_list()
        # Refresh khoa combo in sec1
        try:
            self.sec1.refresh_khoa_combo()
        except Exception:
            pass

    def open_shared_data(self):
        dlg = SharedDataDialog(self.root, self.db)
        self.root.wait_window(dlg)
        # Refresh main tree view to reflect CTĐT/Nganh changes
        self.load_hp_list()
        # Refresh khoa combo in sec1
        try:
            self.sec1.refresh_khoa_combo()
        except Exception:
            pass

    def open_template_manager(self):
        TemplateManagerDialog(self.root, self.db)

    def open_version_history(self):
        if not self.current_hp_id:
            self.show_warning('Thông báo', 'Vui lòng chọn một học phần để xem lịch sử.')
            return
        VersionHistoryDialog(self.root, self.db, self.current_hp_id)

    # ── Welcome / About ──────────────────────────────────────────────────────
    def _show_welcome(self):
        self._set_status(f'Chào mừng đến {APP_TITLE} v{VERSION}')

    def _show_about(self):
        messagebox.showinfo('Về phần mềm',
            f'{APP_TITLE}\nPhiên bản {VERSION}\n\n'
            f'Phần mềm soạn thảo và quản lý tập trung\n'
            f'Đề cương Chi tiết Học phần theo chuẩn EPU.\n\n'
            f'Tác giả: VuPQ | vupq@epu.edu.vn\n'
            f'© 2026 EPU')

    def _show_author(self):
        messagebox.showinfo('Thông tin tác giả',
            f'Tác giả: VuPQ\n'
            f'Email: vupq@epu.edu.vn\n\n'
            f'Đại học Điện lực (EPU)')

    def _show_excel_help(self):
        help_text = (
            "📄 HƯỚNG DẪN CẤU TRÚC FILE EXCEL NHẬP DỮ LIỆU CHUNG\n\n"
            "Để nhập dữ liệu vào phần 'Dữ liệu Chung', file Excel cần tuân thủ cấu trúc các cột sau (dữ liệu bắt đầu từ hàng thứ 2):\n\n"
            "1. Tab KHOA / ĐƠN VỊ:\n"
            "   - Cột 1: Mã đơn vị (VD: K.CNTT)\n"
            "   - Cột 2: Tên đơn vị (Bắt buộc)\n\n"
            "2. Tab DANH MỤC HỌC PHẦN:\n"
            "   - Cột 1: Mã học phần\n"
            "   - Cột 2: Tên tiếng Việt (Bắt buộc)\n"
            "   - Cột 3: Tên tiếng Anh\n"
            "   - Cột 4: Số tín chỉ (Số)\n"
            "   - Cột 5: Tên Khoa quản lý (Phải khớp chính xác với tên trong danh mục Khoa)\n\n"
            "3. Tab GIẢNG VIÊN:\n"
            "   - Cột 1: Họ và tên (Bắt buộc)\n"
            "   - Cột 2: Ngày sinh (dd/mm/yyyy)\n"
            "   - Cột 3: Học vị\n"
            "   - Cột 4: Chức danh\n"
            "   - Cột 5: Tên Đơn vị/Khoa\n"
            "   - Cột 6: Email\n"
            "   - Cột 7: Số điện thoại\n"
            "   - Cột 8: Số CMND/CCCD\n\n"
            "4. Tab THƯ VIỆN HỌC LIỆU:\n"
            "   - Cột 1: Tên giáo trình/sách (Bắt buộc)\n"
            "   - Cột 2: Tác giả\n"
            "   - Cột 3: Năm xuất bản\n"
            "   - Cột 4: Nhà xuất bản\n"
            "   - Cột 5: Loại tài liệu (Giáo trình/Tài liệu tham khảo)\n\n"
            "5. Tab MỤC TIÊU (PO) và CHUẨN ĐẦU RA (PLO):\n"
            "   - Cột 1: Mã (VD: PO1, PLO1)\n"
            "   - Cột 2: Nội dung mô tả (Bắt buộc)\n\n"
            "Lưu ý: Bạn nên sử dụng định dạng file .xlsx và đảm bảo không có các dòng trống xen kẽ."
        )
        top = tb.Toplevel(self.root)
        top.title('Hướng dẫn cấu trúc file Excel')
        top.geometry('650x700')
        txt = tk.Text(top, font=('Arial', 10), wrap='word', padx=15, pady=15)
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', help_text)
        txt.config(state='disabled')
        tb.Button(top, text='Đóng', command=top.destroy).pack(pady=10)

    def run_full_audit(self):
        """Chạy đối soát toàn diện cho học phần hiện tại."""
        if not self.current_hp_id:
            show_modern_warning(self.root, 'Thông báo', 'Vui lòng chọn một học phần để đối soát.')
            return
        
        # Lưu dữ liệu hiện tại trước khi audit từ DB
        self.save_hp()
        
        issues = ValidationService.audit_full_consistency(self.db, self.current_hp_id)
        if not issues:
            show_modern_info(self.root, 'Kết quả đối soát', '✅ Dữ liệu hoàn toàn nhất quán!')
        else:
            _AuditDialog(self.root, issues)


# ─── Audit Dialog ─────────────────────────────────────────────────────────────
class _AuditDialog(tb.Toplevel):
    def __init__(self, parent, issues):
        super().__init__(parent)
        set_window_icon(self)
        self.title('Dashboard Đối soát Dữ liệu')
        self.geometry('750x550')
        self.issues = issues
        self.grab_set()
        self._build()
        self.transient(parent)

    def _build(self):
        frm = tb.Frame(self, padding=16)
        frm.pack(fill='both', expand=True)

        tb.Label(frm, text='🔍 Dashboard Cảnh báo & Đối soát', 
                 font=('Arial', 14, 'bold'), bootstyle='inverse-danger', padding=10).pack(fill='x', pady=(0,15))

        # List of issues
        container = tb.Frame(frm)
        container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        vsb = tb.Scrollbar(container, orient='vertical', command=canvas.yview)
        scroll_frm = tb.Frame(canvas)
        
        window_id = canvas.create_window((0,0), window=scroll_frm, anchor='nw')
        canvas.configure(yscrollcommand=vsb.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Sync scroll_frm width to canvas width for proper wrapping
        def _on_canvas_configure(e):
            canvas.itemconfig(window_id, width=e.width)
        canvas.bind('<Configure>', _on_canvas_configure)

        for iss in self.issues:
            card = tb.Frame(scroll_frm, bootstyle='secondary', padding=10)
            card.pack(fill='x', pady=4, padx=5)
            
            header = tb.Frame(card, bootstyle='secondary')
            header.pack(fill='x')
            
            color = 'danger' if iss['level'] == 'error' else 'warning'
            icon = '❌ ERROR' if iss['level'] == 'error' else '⚠ WARNING'
            
            tb.Label(header, text=icon, font=('Arial', 9, 'bold'), bootstyle=color).pack(side='left')
            tb.Label(header, text=f" [{iss['section']}]", font=('Arial', 9, 'bold'), bootstyle='secondary').pack(side='left')
            
            tb.Label(card, text=iss['msg'], font=('Arial', 10), 
                     wraplength=680, bootstyle='secondary').pack(fill='x', pady=(5,0))

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scroll_frm.bind("<Configure>", _on_frame_configure)

        tb.Button(frm, text='Đóng', command=self.destroy, bootstyle='secondary', width=15).pack(pady=(15,0))


# ─── Template Manager Dialog ──────────────────────────────────────────────────
class _TemplateManagerDialog(tb.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        set_window_icon(self)
        self.title('Quản lý Template Word')
        self.geometry('800x500')
        self.db   = db
        self.grab_set()
        self._build()
        self.transient(parent)

    def _build(self):
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        tb.Label(frm,
            text='📋 Quản lý Template Word\n'
                 'Template là file .docx chứa các thẻ như [TEN_VIET], [MA_HP]...',
            font=('Arial', 10), justify='left').pack(anchor='w', pady=(0, 8))

        # List
        from sections.base_section import make_tree
        cols   = ('ten', 'mo_ta', 'file_path', 'la_mac_dinh')
        heads  = ('Tên template', 'Mô tả', 'File .docx', 'Mặc định')
        widths = (150, 200, 250, 70)
        tf, self.tree = make_tree(frm, cols, heads, widths, height=10, db=self.db, table_id='word_templates')
        tf.pack(fill='both', expand=True)

        bf = tb.Frame(frm)
        bf.pack(fill='x', pady=6)
        tb.Button(bf, text='➕ Thêm template', command=self._add).pack(side='left', padx=4)
        tb.Button(bf, text='✏ Sửa',           command=self._edit).pack(side='left', padx=4)
        tb.Button(bf, text='🗑 Xóa',           command=self._delete).pack(side='left', padx=4)
        tb.Button(bf, text='⭐ Đặt mặc định',  command=self._set_default).pack(side='left', padx=4)
        tb.Separator(bf, orient='vertical').pack(side='left', padx=8, fill='y')
        tb.Button(bf, text='📋 Xem placeholder',
                   command=self._show_placeholders).pack(side='left', padx=4)

        tb.Button(self, text='Đóng', command=self.destroy).pack(pady=4)
        self._refresh()

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        self._tpl_ids = []
        for i, r in enumerate(self.db.get_all_templates()):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.tree.insert('', 'end', iid=str(i),
                              values=(r['ten'], r['mo_ta'] or '',
                                      r['file_path'] or '',
                                      '✔' if r['la_mac_dinh'] else ''),
                              tags=(tag,))
            self._tpl_ids.append(r['id'])

    def _add(self):
        path = filedialog.askopenfilename(
            title='Chọn file Word template',
            filetypes=[('Word Document', '*.docx')])
        if not path:
            return
        from sections.base_section import RowEditDialog
        k_names = [k['ten'] for k in self.db.get_all_khoa()]
        dlg = RowEditDialog(self, 'Thêm template', [
            ('ten',   'Tên template', 'entry', {}),
            ('khoa', 'Khoa quản lý', 'combo', {'values': k_names}),
        ])
        if dlg.result:
            self.db.add_template(dlg.result.get('ten', os.path.basename(path)),
                                  dlg.result.get('mo_ta', ''), path)
            self._refresh()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        tpl_id = self._tpl_ids[int(sel[0])]
        rows = self.db.get_all_templates()
        row  = next((dict(r) for r in rows if r['id'] == tpl_id), None)
        if not row:
            return
        from sections.base_section import RowEditDialog
        dlg = RowEditDialog(self, 'Sửa template', [
            ('ten',       'Tên template', 'entry', {}),
            ('mo_ta',     'Mô tả',        'entry', {}),
            ('file_path', 'Đường dẫn file', 'entry', {}),
        ], initial=row)
        if dlg.result:
            self.db.update_template(tpl_id, dlg.result['ten'],
                                     dlg.result.get('mo_ta', ''),
                                     dlg.result.get('file_path', ''))
            self._refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno('Xác nhận', 'Xóa template này?'):
            self.db.delete_template(self._tpl_ids[int(sel[0])])
            self._refresh()

    def _set_default(self):
        sel = self.tree.selection()
        if not sel:
            return
        tpl_id = self._tpl_ids[int(sel[0])]
        for r in self.db.get_all_templates():
            self.db.update_template(r['id'], r['ten'], r['mo_ta'] or '',
                                     r['file_path'] or '', r['config_json'] or '{}',
                                     1 if r['id'] == tpl_id else 0)
        self._refresh()

    def _show_placeholders(self):
        ph_text = (
            "📋 Danh sách các thẻ [TAG] có thể dùng trong template Word:\n\n"
            "── Thẻ đơn (Gõ bất kỳ đâu) ──\n"
            "[TEN_VIET]        — Tên học phần (Việt)\n"
            "[TEN_ANH]         — Tên học phần (Anh)\n"
            "[MA_HP]           — Mã học phần\n"
            "[TRINH_DO]        — Trình độ đào tạo\n"
            "[SO_TIN_CHI]      — Số tín chỉ\n"
            "[LOAI_HP]         — Loại học phần\n"
            "[TINH_CHAT]       — Tính chất học phần\n"
            "[GIO_LT]          — Giờ lý thuyết\n"
            "[GIO_TH_TN]       — Giờ thực hành\n"
            "[GIO_TU_HOC]      — Giờ tự học\n"
            "[TONG_GIO]        — Tổng cộng giờ\n"
            "[MO_TA]           — Mô tả tóm tắt\n"
            "[PP_DAY_HOC]      — Phương pháp dạy học\n\n"
            "── Bảng lặp (Dùng trong dòng mẫu của bảng) ──\n"
            "Phần mềm sẽ nhân bản các dòng chứa các thẻ sau:\n"
            "  Giảng viên chính: [GV_CHINH_HO_TEN], [GV_CHINH_EMAIL], [GV_CHINH_SDT]\n"
            "  Giảng viên tham gia: [GV_THAM_HO_TEN], [GV_THAM_EMAIL]\n"
            "  Mục tiêu: [MT_STT], [MT_MO_TA], [MT_CDR_MA]\n"
            "  Chuẩn đầu ra (CLO): [CLO_MA], [CLO_MO_TA], [CLO_CDR_MA]\n"
            "  Nội dung (LT): [ND_LT_TEN], [ND_LT_GIO_LT], [ND_LT_CDR_MA]\n"
            "  Kế hoạch kiểm tra: [KT_NOI_DUNG], [KT_HINH_THUC], [KT_TY_TRONG]\n\n"
            "Lưu ý: Bạn có thể tự thiết kế bảng và đặt thẻ vào đúng cột mong muốn."
        )
        top = tb.Toplevel(self)
        top.title('Danh sách Placeholder')
        top.geometry('550x600')
        txt = tk.Text(top, font=('Consolas', 10), wrap='word', padx=10, pady=10)
        txt.pack(fill='both', expand=True)
        txt.insert('1.0', ph_text)
        txt.config(state='disabled')
        tb.Button(top, text='Đóng', command=top.destroy).pack(pady=6)


class _TemplateChoiceDialog(tb.Toplevel):
    def __init__(self, main_app, hp_id):
        super().__init__(main_app.root)
        set_window_icon(self)
        self.title('Chọn Template Xuất Word')
        self.app = main_app
        self.hp_id = hp_id
        self.db = main_app.db
        self.grab_set()
        self.geometry('500x350')

        tb.Label(self, text='Chọn template để xuất:', font=('Arial', 10)
                  ).pack(padx=16, pady=12, anchor='w')

        self._templates = self.db.get_all_templates()
        self._tpl_names = [r['ten'] for r in self._templates]
        lb = tk.Listbox(self, listvariable=tk.StringVar(value=self._tpl_names),
                        font=('Arial', 10), height=8, selectmode='single')
        lb.pack(fill='both', expand=True, padx=16, pady=4)
        self.lb = lb
        if self._templates:
            lb.selection_set(0)

        bf = tb.Frame(self, padding=(16, 6))
        bf.pack(fill='x')
        tb.Button(bf, text='📤 Xuất', command=self._export, bootstyle='primary').pack(side='right', padx=4)
        tb.Button(bf, text='Hủy',    command=self.destroy, bootstyle='secondary').pack(side='right', padx=4)
        self.transient(main_app.root)

    def _export(self):
        sel = self.lb.curselection()
        if not sel: return
        tpl = self._templates[sel[0]]
        self.destroy()

        # Lấy tên HP từ DB để đặt tên file mặc định
        hp = self.db.get_hoc_phan(self.hp_id)
        default_name = (hp['ten_viet'] or 'DecuongHP').replace(' ', '_') + '_Template.docx'
        
        out_path = filedialog.asksaveasfilename(
            title='Lưu file Word',
            defaultextension='.docx',
            initialfile=default_name,
            filetypes=[('Word Document', '*.docx')])
        
        if not out_path: return

        try:
            # tpl is a dict from db.get_all_templates() [fixed in db.py to return dicts]
            # or it's a Row if db.py is not yet updated safely. Using [] is safer for both.
            template_path = tpl['file_path'] if 'file_path' in tpl.keys() else tpl.get('file_path')
            if not template_path or not os.path.exists(template_path):
                self.app.show_error('Lỗi', f'Không tìm thấy file template tại:\n{template_path}')
                return

            if self.app.controller.export_word(self.hp_id, out_path, mode='template', template_path=template_path):
                if self.app.ask_yesno('Xuất thành công',
                                        f'Đã xuất đề cương theo template "{tpl["ten"]}"\n'
                                        f'Đường dẫn: {out_path}\n\nMở file ngay không?'):
                    os.startfile(out_path)
        except Exception as ex:
            self.app.show_error('Lỗi xuất Word (Template)', str(ex))


class _ProgressDialog(tb.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        set_window_icon(self)
        self.title(title)
        self.geometry("450x150")
        self.resizable(False, False)
        self.center_window()
        
        self.lbl_msg = tb.Label(self, text="Đang khởi tạo...", font=("Arial", 10))
        self.lbl_msg.pack(pady=(20, 10))
        
        self.pb = tb.Progressbar(self, mode=DETERMINATE, length=350, bootstyle=INFO)
        self.pb.pack(pady=10, padx=20)
        
        self.lbl_status = tb.Label(self, text="0/0", font=("Arial", 9))
        self.lbl_status.pack()
        
        self.grab_set()

    def update_progress(self, current, total, message):
        self.lbl_msg.config(text=message)
        self.pb['value'] = (current / total) * 100 if total > 0 else 0
        self.lbl_status.config(text=f"{current}/{total}")
        self.update()

    def center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.geometry(f'+{x}+{y}')

class _HistoryDialog(tb.Toplevel):
    def __init__(self, parent, history):
        super().__init__(parent)
        set_window_icon(self)
        self.title("Lịch sử Nhập/Xuất")
        self.geometry("900x600")
        self.grab_set()
        
        frm = tb.Frame(self, padding=15)
        frm.pack(fill=BOTH, expand=YES)
        
        tb.Label(frm, text="Lịch sử hoạt động hệ thống", font=("Arial", 12, "bold")).pack(anchor=W, pady=(0, 10))
        
        from sections.base_section import make_tree
        cols = ("time", "type", "success", "errors", "details")
        heads = ("Thời gian", "Loại", "Thành công", "Lỗi", "Chi tiết")
        widths = (160, 100, 100, 80, 400)
        
        tf, self.tree = make_tree(frm, cols, heads, widths, height=15)
        tf.pack(fill=BOTH, expand=YES)
        
        self._history = history
        for i, r in enumerate(history):
            # Cột: id, type, timestamp, total_files, success_count, error_count, details_json, user_action
            self.tree.insert("", END, iid=str(i), values=(
                r.get('timestamp') or r.get('created_at', ''),
                "NHẬP" if (r.get('type') == 'IMPORT' or r.get('operation_type') == 'IMPORT') else "XUẤT",
                r.get('success_count', 0),
                r.get('error_count', 0),
                (r.get('details_json') or r.get('details', ''))[:100] + "..." if (r.get('details_json') or r.get('details')) and len(r.get('details_json') or r.get('details')) > 100 else (r.get('details_json') or r.get('details', ''))
            ))
            
        self.tree.bind("<Double-1>", self._show_details)
        tb.Button(self, text="Đóng", command=self.destroy).pack(pady=10)

    def _show_details(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        idx = int(sel[0])
        record = self._history[idx]
        
        # Parse JSON for better view
        import json
        try:
            details_obj = json.loads(record['details'])
            formatted_json = json.dumps(details_obj, indent=4, ensure_ascii=False)
        except:
            formatted_json = record['details']

        top = tb.Toplevel(self)
        top.title(f"Chi tiết: {record['operation_type']} - {record['created_at']}")
        top.geometry("700x500")
        
        txt = tk.Text(top, font=("Consolas", 10), wrap=tk.NONE)
        txt.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Scrollbars
        v_scroll = tb.Scrollbar(txt, orient=VERTICAL, command=txt.yview)
        v_scroll.pack(side=RIGHT, fill=Y)
        h_scroll = tb.Scrollbar(txt, orient=HORIZONTAL, command=txt.xview)
        h_scroll.pack(side=BOTTOM, fill=X)
        txt.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        txt.insert(END, formatted_json)
        txt.config(state=DISABLED)
        tb.Button(top, text="Đóng", command=top.destroy).pack(pady=5)


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    from sections.base_section import HAS_TTKBOOTSTRAP
    from db import Database
    import tkinter as tk
    
    # 1. Đọc config trước (không cần UI)
    db_tmp = Database()
    saved_theme = db_tmp.get_config('theme', 'dark')
    db_tmp.conn.close()
    
    # 2. Khởi tạo Main Root trước (nhưng ẩn đi)
    if HAS_TTKBOOTSTRAP:
        import ttkbootstrap as tb
        root = tb.Window(title=APP_TITLE, themename='darkly' if saved_theme == 'dark' else 'litera')
    else:
        root = tk.Tk()
        root.title(APP_TITLE)
    
    root.withdraw()
    from sections.base_section import set_window_icon
    set_window_icon(root)

    # 3. Tạo Splash Screen là Toplevel của root
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg='#1A1A1A')
    
    # Center splash
    w, h = 400, 250
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    
    pb = None
    try:
        import ttkbootstrap as tb
        lbl = tb.Label(splash, text="APM SYSTEM", font=('Arial', 24, 'bold'), 
                       bootstyle="inverse-primary", padding=20)
        lbl.pack(expand=True, fill='both')
        pb = tb.Progressbar(splash, mode='indeterminate', bootstyle="info-striped")
        pb.pack(fill='x', side='bottom')
        pb.start(10)
    except:
        tk.Label(splash, text="APM SYSTEM\nLoading...", font=('Arial', 18), bg='#1A1A1A', fg='white').pack(expand=True)
    
    splash.update()

    # 4. Khởi tạo App
    app = QLCTDTApp(root)
    
    def _finish_splash():
        if pb: pb.stop() # Dừng animation để tránh lỗi destroy
        splash.destroy()
        root.deiconify()
        try: root.state('zoomed')
        except: pass

    # Phút 1.2 kết thúc splash
    root.after(1200, _finish_splash)
    root.mainloop()
