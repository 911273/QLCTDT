# statistics_dialog.py
import tkinter as tk
from tkinter import filedialog
import threading
import re
from datetime import datetime

from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)

# Matplotlib for analytics
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Excel export
try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# Word export
try:
    import docx
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Meter

# Icon / màu sắc thay thế cho cell background trong Tkinter Treeview
IRM_ICONS = {
    'I': '🟨 I',  # Vàng
    'R': '🟧 R',  # Cam
    'M': '🟩 M',  # Xanh lá
    '': '-'
}

class StatisticsDialog(tb.Toplevel):
    def __init__(self, parent, db):
        super().__init__(title="📊 Báo cáo Kiểm định chất lượng", size=(1250, 850))
        self.db = db
        self.parent = parent
        self.cache = {}
        
        self.matrix_data = [] # Data for matrix export
        self.plo_list = []
        self.irm_stats = {} # PLO -> {'I': x, 'R': y, 'M': z}
        self.bloom_counts = [0] * 6
        
        self._build_ui()
        self.position_center()
        self.grab_set()

    def _build_ui(self):
        self.nb = tb.Notebook(self, bootstyle=PRIMARY)
        self.nb.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # 1. Dashboard Tab (Giữ lại cấu trúc cũ cho tương thích)
        self.tab_dash = self._init_tab_dashboard()
        self.nb.add(self.tab_dash, text="🏠 Tổng quan")
        
        # 2. Ma trận CLO-PLO (Cập nhật theo yêu cầu mới)
        self.tab_matrix = self._init_tab_matrix()
        self.nb.add(self.tab_matrix, text="📐 Ma trận CLO-PLO toàn khoa")
        
        # 3. Phân tích Bloom
        self.tab_bloom = self._init_tab_bloom()
        self.nb.add(self.tab_bloom, text="🌸 Bao phủ mức Bloom")
        
        # 4. Phân bổ I/R/M theo PLO
        self.tab_irm = self._init_tab_irm_plo()
        self.nb.add(self.tab_irm, text="🔄 Phân bổ I/R/M theo PLO")

        # Bottom Bar
        footer = tb.Frame(self, padding=10)
        footer.pack(fill=X)
        self.lbl_status = tb.Label(footer, text="Sẵn sàng", foreground='grey')
        self.lbl_status.pack(side=LEFT)
        
        tb.Button(footer, text="🔄 Tải dữ liệu", bootstyle=INFO, command=self.refresh_all).pack(side=LEFT, padx=15)
        tb.Button(footer, text="❌ Đóng", bootstyle=SECONDARY, command=self.destroy).pack(side=RIGHT, padx=5)
        tb.Button(footer, text="📑 Xuất báo cáo kiểm định (Word)", bootstyle=PRIMARY, command=self._export_word_report).pack(side=RIGHT, padx=5)

    # -------------------------------------------------------------------------
    # TAB 1: DASHBOARD (Tổng quan)
    # -------------------------------------------------------------------------
    def _init_tab_dashboard(self):
        tab = tb.Frame(self.nb, padding=20)
        kpi_frame = tb.Frame(tab)
        kpi_frame.pack(fill=X, pady=(0, 20))
        
        self.meters = {}
        stats = [("Số HP số hóa", "success", 0), ("Đã Validate", "info", 0), ("Chất lượng cao", "primary", 0)]
        for label, color, val in stats:
            f = tb.Frame(kpi_frame)
            f.pack(side=LEFT, expand=YES)
            m = Meter(f, metersize=160, padding=5, amounttotal=100, amountused=val, subtext=label, bootstyle=color, textright="%")
            m.pack()
            self.meters[label] = m
            
        return tab

    # -------------------------------------------------------------------------
    # TAB 2: MA TRẬN CLO-PLO (Rows=CLO)
    # -------------------------------------------------------------------------
    def _init_tab_matrix(self):
        tab = tb.Frame(self.nb, padding=10)
        toolbar = tb.Frame(tab, padding=5)
        toolbar.pack(side=TOP, fill=X)
        
        tb.Label(toolbar, text="Chọn CTĐT:").pack(side=LEFT, padx=5)
        self.cbo_ctdt_m = tb.Combobox(toolbar, state="readonly", width=35)
        self.cbo_ctdt_m.pack(side=LEFT, padx=5)
        self._refresh_ctdt_combobox()
        
        tb.Button(toolbar, text="🔍 Chạy Ma trận", bootstyle=SUCCESS, command=self._run_matrix_plo).pack(side=LEFT, padx=5)
        tb.Button(toolbar, text="📊 Xuất Excel", bootstyle=INFO, command=self._export_matrix_excel).pack(side=RIGHT, padx=5)
        
        # Bảng ma trận
        self.tree_matrix = tb.Treeview(tab, show='headings')
        self.tree_matrix.pack(fill=BOTH, expand=YES, pady=10)
        
        # Footer tổng hợp
        self.lbl_matrix_summary = tb.Label(tab, text="Tổng số CLO: 0 | Chưa load", font=('Arial', 10, 'italic'))
        self.lbl_matrix_summary.pack(side=BOTTOM, anchor='w')
        
        return tab

    # -------------------------------------------------------------------------
    # TAB 3: PHÂN TÍCH BLOOM
    # -------------------------------------------------------------------------
    def _init_tab_bloom(self):
        tab = tb.Frame(self.nb, padding=10)
        self.bloom_canvas_frame = tb.Frame(tab)
        self.bloom_canvas_frame.pack(fill=BOTH, expand=YES)
        
        if not HAS_MATPLOTLIB:
            tb.Label(self.bloom_canvas_frame, text="Vui lòng cài đặt matplotlib", foreground='red').pack(pady=50)
        
        self.lbl_bloom_warn = tb.Label(tab, text="", font=('Arial', 10, 'bold'))
        self.lbl_bloom_warn.pack(pady=10)
        
        return tab

    # -------------------------------------------------------------------------
    # TAB 4: PHÂN BỔ I/R/M THEO PLO
    # -------------------------------------------------------------------------
    def _init_tab_irm_plo(self):
        tab = tb.Frame(self.nb, padding=10)
        self.irm_canvas_frame = tb.Frame(tab)
        self.irm_canvas_frame.pack(fill=BOTH, expand=YES)
        
        if not HAS_MATPLOTLIB:
            tb.Label(self.irm_canvas_frame, text="Vui lòng cài đặt matplotlib", foreground='red').pack(pady=50)
            
        self.lbl_irm_warn = tb.Label(tab, text="", font=('Arial', 10, 'bold'), foreground='red')
        self.lbl_irm_warn.pack(pady=10)
        
        return tab

    def _refresh_ctdt_combobox(self):
        try:
            rows = self.db.get_all_ctdt()
            self.ctdt_map = {r['ten']: r['id'] for r in rows}
            names = list(self.ctdt_map.keys())
            self.cbo_ctdt_m.config(values=names)
            if names: self.cbo_ctdt_m.current(0)
        except Exception as e:
            pass

    # -------------------------------------------------------------------------
    # LOGIC: FETCH & PROCESS DATA
    # -------------------------------------------------------------------------
    def refresh_all(self):
        self.lbl_status.config(text="Đang tải dữ liệu...", foreground='blue')
        threading.Thread(target=self._load_data_async, daemon=True).start()

    def _load_data_async(self):
        try:
            from services.stats_service import StatsService
            self.stats_svc = StatsService(self.db)
            summary = self.stats_svc.get_overall_dashboard_stats()
            
            self.after(0, lambda: self.meters["Số HP số hóa"].configure(amountused=100))
            if summary['total_hp'] > 0:
                self.after(0, lambda: self.meters["Đã Validate"].configure(amountused=int((summary['validated_hp']/summary['total_hp'])*100)))
            
            self._run_matrix_plo_internal()
            self._plot_bloom_chart_internal()
            self._plot_irm_chart_internal()
            
            self.after(0, lambda: self.lbl_status.config(text="Đã tải xong", foreground='green'))
        except Exception as e:
            self.after(0, lambda: self.lbl_status.config(text=f"Lỗi: {str(e)}", foreground='red'))

    def _run_matrix_plo(self):
        self.lbl_status.config(text="Đang chạy ma trận...", foreground='blue')
        threading.Thread(target=self._run_matrix_plo_internal, daemon=True).start()
        
    def _run_matrix_plo_internal(self):
        ctdt_name = self.cbo_ctdt_m.get()
        if not ctdt_name: return
        ctdt_id = self.ctdt_map.get(ctdt_name)
        if not ctdt_id: return

        # 1. Lấy danh sách PLO
        plos = self.db.conn.execute("SELECT ma FROM ctdt_plo WHERE ctdt_id = ? ORDER BY ma", (ctdt_id,)).fetchall()
        self.plo_list = [p[0] for p in plos]
        if not self.plo_list: self.plo_list = [f"PLO{i}" for i in range(1, 11)]

        # 2. Lấy dữ liệu học phần và CLO của CTĐT
        hps = self.db.conn.execute("""
            SELECT hp.id, hp.ma, hp.ten_viet 
            FROM hoc_phan hp 
            JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
            WHERE ch.ctdt_id = ?
            ORDER BY ch.thu_tu, hp.ma
        """, (ctdt_id,)).fetchall()

        self.matrix_data = []
        self.irm_stats = {plo: {'I':0, 'R':0, 'M':0} for plo in self.plo_list}

        for hp in hps:
            hp_id, hp_ma, hp_ten = hp
            clos_rows = self.db.conn.execute("""
                SELECT ma, mo_ta, cdr_ma, level_irm 
                FROM clo 
                WHERE hp_id = ? AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom = 0)
                ORDER BY id
            """, (hp_id,)).fetchall()

            for clo in clos_rows:
                clo_ma, clo_mota, cdr_ma, level = clo
                if not clo_ma: continue
                
                row_dict = {
                    'hp_ma': hp_ma,
                    'hp_ten': hp_ten,
                    'clo_ma': clo_ma,
                    'clo_mota': clo_mota,
                    'plos': {}
                }

                # Phân tích PLO mapping của CLO này
                mapped_plos = [p.strip().upper() for p in re.split(r'[,\s;]+', str(cdr_ma)) if p.strip()]
                lvl_val = str(level).strip().upper() if level else 'I'
                if lvl_val not in ['I', 'R', 'M']: lvl_val = 'I'
                
                for p_code in mapped_plos:
                    # Giả định mapping map trực tiếp với mã PLO
                    if p_code in self.plo_list:
                        row_dict['plos'][p_code] = lvl_val
                        self.irm_stats[p_code][lvl_val] += 1
                        
                self.matrix_data.append(row_dict)

        self.after(0, self._render_matrix_ui)

    def _render_matrix_ui(self):
        # Cập nhật cột
        cols = ["hp", "clo"] + self.plo_list
        self.tree_matrix["columns"] = cols
        self.tree_matrix.heading("hp", text="Học phần")
        self.tree_matrix.heading("clo", text="Mã CLO")
        self.tree_matrix.column("hp", width=250, anchor=W)
        self.tree_matrix.column("clo", width=80, anchor=CENTER)
        
        for p in self.plo_list:
            self.tree_matrix.heading(p, text=p)
            self.tree_matrix.column(p, width=60, anchor=CENTER)
            
        self.tree_matrix.delete(*self.tree_matrix.get_children())
        
        current_hp = None
        for data in self.matrix_data:
            hp_disp = f"{data['hp_ma']} - {data['hp_ten']}" if data['hp_ma'] != current_hp else ""
            current_hp = data['hp_ma']
            
            row = [hp_disp, data['clo_ma']]
            for p in self.plo_list:
                val = data['plos'].get(p, '')
                row.append(IRM_ICONS.get(val, val))
                
            self.tree_matrix.insert("", END, values=row)

        self.lbl_matrix_summary.config(text=f"Tổng số CLO phân tích: {len(self.matrix_data)}")
        self.lbl_status.config(text="Đã tải ma trận CLO-PLO", foreground='green')

    def _plot_bloom_chart_internal(self):
        if not HAS_MATPLOTLIB: return
        
        # Nhận diện mức Bloom qua động từ CLO
        self.bloom_counts = [0] * 6
        clos = self.db.conn.execute("SELECT mo_ta FROM clo WHERE la_tieu_de_nhom=0 OR la_tieu_de_nhom IS NULL").fetchall()
        from services.deccuong_service import DeCuongValidator
        val = DeCuongValidator(self.db)
        
        for clo in clos:
            desc = (clo[0] or "").lower()
            found = False
            for level, verbs in val.DONG_TU_BLOOM.items():
                if any(desc.startswith(v) for v in verbs):
                    self.bloom_counts[level-1] += 1
                    found = True
                    break
            if not found:
                self.bloom_counts[0] += 1 # Default L1 nếu không nhận diện được
                
        self.after(0, self._render_bloom_chart)

    def _render_bloom_chart(self):
        for child in self.bloom_canvas_frame.winfo_children(): child.destroy()
        
        fig, ax = plt.subplots(figsize=(8, 4))
        levels = ["Nhớ (L1)", "Hiểu (L2)", "Vận dụng (L3)", "Phân tích (L4)", "Đánh giá (L5)", "Sáng tạo (L6)"]
        colors = ['#ff9999','#ffcc99','#66b3ff','#99ff99','#ffb3e6','#c2c2f0']
        
        bars = ax.bar(levels, self.bloom_counts, color=colors)
        ax.set_title("Bao phủ mức độ Bloom toàn bộ CLO")
        ax.set_ylabel("Số lượng CLO")
        plt.xticks(rotation=15)
        
        # Thêm số liệu lên đỉnh cột
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, int(yval), ha='center', va='bottom')
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.bloom_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES)
        
        # Cảnh báo nếu thiếu mức
        missing = [levels[i] for i, v in enumerate(self.bloom_counts) if v == 0]
        if missing:
            self.lbl_bloom_warn.config(text=f"⚠️ Cảnh báo: Thiếu hoàn toàn các mức Bloom: {', '.join(missing)}", foreground='red')
        else:
            self.lbl_bloom_warn.config(text="✅ CTĐT bao phủ đầy đủ 6 mức độ Bloom.", foreground='green')

    def _plot_irm_chart_internal(self):
        if not HAS_MATPLOTLIB: return
        self.after(0, self._render_irm_chart)

    def _render_irm_chart(self):
        for child in self.irm_canvas_frame.winfo_children(): child.destroy()
        
        if not self.plo_list or not self.irm_stats:
            tb.Label(self.irm_canvas_frame, text="Vui lòng chạy Ma trận CLO-PLO trước", font=('Arial',10,'italic')).pack(pady=20)
            return

        plos = self.plo_list
        i_vals = [self.irm_stats[p]['I'] for p in plos]
        r_vals = [self.irm_stats[p]['R'] for p in plos]
        m_vals = [self.irm_stats[p]['M'] for p in plos]

        fig, ax = plt.subplots(figsize=(9, 4))
        
        ax.bar(plos, i_vals, label='I (Giới thiệu)', color='#f1c40f')
        ax.bar(plos, r_vals, bottom=i_vals, label='R (Củng cố)', color='#e67e22')
        bottom_m = [i+r for i,r in zip(i_vals, r_vals)]
        ax.bar(plos, m_vals, bottom=bottom_m, label='M (Thành thạo)', color='#2ecc71')

        ax.set_title("Phân bổ I/R/M theo PLO")
        ax.set_ylabel("Số lượng CLO")
        ax.legend()
        plt.xticks(rotation=45)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.irm_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES)

        # Cảnh báo thiếu M
        missing_m = [p for p in plos if self.irm_stats[p]['M'] == 0]
        if missing_m:
            self.lbl_irm_warn.config(text=f"⚠️ Cảnh báo nghiêm trọng: Các PLO sau thiếu CLO mức Thành thạo (M): {', '.join(missing_m)}")
        else:
            self.lbl_irm_warn.config(text="✅ Tất cả PLO đều có CLO hỗ trợ mức Thành thạo (M).", foreground='green')

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    def _export_matrix_excel(self):
        if not HAS_OPENPYXL:
            show_modern_error(self, "Lỗi", "Vui lòng cài đặt openpyxl (pip install openpyxl).")
            return
        
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="Xuất Ma trận CLO-PLO")
        if not path: return
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ma trận CLO-PLO (Rows=CLO)"
        
        # Header
        cols = ["Học phần", "Mã CLO"] + self.plo_list
        ws.append(cols)
        
        header_fill = PatternFill(start_color="D9EDF7", end_color="D9EDF7", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        fill_i = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        fill_r = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        fill_m = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

        # Data
        for data in self.matrix_data:
            row = [f"{data['hp_ma']} - {data['hp_ten']}", data['clo_ma']]
            for p in self.plo_list:
                val = data['plos'].get(p, '')
                row.append(val)
            ws.append(row)
            
            # Tô màu row vừa thêm
            current_row = ws.max_row
            for col_idx, p in enumerate(self.plo_list, start=3):
                val = data['plos'].get(p, '')
                cell = ws.cell(row=current_row, column=col_idx)
                cell.alignment = Alignment(horizontal="center")
                if val == 'I': cell.fill = fill_i
                elif val == 'R': cell.fill = fill_r
                elif val == 'M': cell.fill = fill_m

        ws.column_dimensions['A'].width = 40
        wb.save(path)
        show_modern_info(self, "Thành công", f"Đã xuất file Excel:\n{path}")

    def _export_word_report(self):
        if not HAS_DOCX:
            show_modern_error(self, "Lỗi", "Vui lòng cài đặt python-docx (pip install python-docx).")
            return
            
        if not self.matrix_data:
            show_modern_warning(self, "Thông báo", "Vui lòng 'Chạy Ma trận' trước khi xuất báo cáo.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word", "*.docx")], title="Xuất Báo cáo Kiểm định")
        if not path: return
        
        try:
            doc = docx.Document()
            
            # Header
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(f"BÁO CÁO KIỂM ĐỊNH CHẤT LƯỢNG CHƯƠNG TRÌNH ĐÀO TẠO\nCTĐT: {self.cbo_ctdt_m.get()}\nNgày xuất: {datetime.now().strftime('%d/%m/%Y')}")
            run.bold = True
            run.font.size = Pt(14)
            
            # 1. Ma trận CLO-PLO
            doc.add_heading('1. Ma trận CLO - PLO toàn khóa', level=1)
            doc.add_paragraph("Bảng thể hiện sự đóng góp của từng CLO thuộc các Học phần vào Chuẩn đầu ra CTĐT (PLO).")
            
            table = doc.add_table(rows=1, cols=len(self.plo_list) + 2)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Học phần'
            hdr_cells[1].text = 'CLO'
            for i, p_name in enumerate(self.plo_list):
                hdr_cells[i+2].text = p_name
                
            for data in self.matrix_data:
                row_cells = table.add_row().cells
                row_cells[0].text = f"{data['hp_ma']}"
                row_cells[1].text = data['clo_ma']
                for i, p_name in enumerate(self.plo_list):
                    val = data['plos'].get(p_name, '')
                    row_cells[i+2].text = val
            
            # 2. Tổng hợp I/R/M
            doc.add_heading('2. Thống kê phân bổ I/R/M theo PLO', level=1)
            stat_table = doc.add_table(rows=1, cols=4)
            stat_table.style = 'Table Grid'
            hcells = stat_table.rows[0].cells
            hcells[0].text = 'PLO'
            hcells[1].text = 'Giới thiệu (I)'
            hcells[2].text = 'Củng cố (R)'
            hcells[3].text = 'Thành thạo (M)'
            
            for p_name in self.plo_list:
                rcells = stat_table.add_row().cells
                rcells[0].text = p_name
                rcells[1].text = str(self.irm_stats[p_name]['I'])
                rcells[2].text = str(self.irm_stats[p_name]['R'])
                rcells[3].text = str(self.irm_stats[p_name]['M'])
                
            # Cảnh báo thiếu M
            missing_m = [p for p in self.plo_list if self.irm_stats[p]['M'] == 0]
            if missing_m:
                warn_p = doc.add_paragraph("Cảnh báo: Các PLO sau không có CLO hỗ trợ ở mức Thành thạo (M): ")
                warn_p.add_run(", ".join(missing_m)).font.color.rgb = docx.shared.RGBColor(255, 0, 0)

            # 3. Bloom
            doc.add_heading('3. Bao phủ mức độ nhận thức (Bloom)', level=1)
            b_table = doc.add_table(rows=1, cols=2)
            b_table.style = 'Table Grid'
            b_table.rows[0].cells[0].text = 'Mức độ Bloom'
            b_table.rows[0].cells[1].text = 'Số lượng CLO'
            
            levels = ["Nhớ (L1)", "Hiểu (L2)", "Vận dụng (L3)", "Phân tích (L4)", "Đánh giá (L5)", "Sáng tạo (L6)"]
            for i, lvl in enumerate(levels):
                rcells = b_table.add_row().cells
                rcells[0].text = lvl
                rcells[1].text = str(self.bloom_counts[i])
                
            missing_b = [levels[i] for i, v in enumerate(self.bloom_counts) if v == 0]
            if missing_b:
                warn_b = doc.add_paragraph("Cảnh báo: Thiếu hoàn toàn các mức Bloom: ")
                warn_b.add_run(", ".join(missing_b)).font.color.rgb = docx.shared.RGBColor(255, 0, 0)
                
            doc.save(path)
            show_modern_info(self, "Thành công", f"Đã xuất Báo cáo Kiểm định ra:\n{path}")
        except Exception as e:
            show_modern_error(self, "Lỗi", f"Không thể xuất file Word:\n{str(e)}")
