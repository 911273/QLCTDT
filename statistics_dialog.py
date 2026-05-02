# statistics_dialog.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import sqlite3
import re
import pandas as pd
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

import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Meter
from ttkbootstrap.dialogs import Messagebox

class StatisticsDialog(tb.Toplevel):
    def __init__(self, parent, db):
        super().__init__(title="📊 Hệ thống Phân tích & Dashboard Chất lượng", size=(1200, 800))
        self.db = db
        self.parent = parent
        self.cache = {}
        
        self._build_ui()
        self.position_center()
        self.grab_set()

    def _build_ui(self):
        self.nb = tb.Notebook(self, bootstyle=PRIMARY)
        self.nb.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # 1. Dashboard Tab
        self.tab_dash = self._init_tab_dashboard()
        self.nb.add(self.tab_dash, text="🏠 Dashboard")
        
        # 2. Ma trận CLO-PLO Tab
        self.tab_matrix = self._init_tab_matrix()
        self.nb.add(self.tab_matrix, text="📐 Ma trận CLO-PLO")
        
        # 3. Phân tích Bloom Tab
        self.tab_bloom = self._init_tab_bloom()
        self.nb.add(self.tab_bloom, text="🌸 Phân tích Bloom")
        
        # 4. Tính nhất quán Tab
        self.tab_consistency = self._init_tab_consistency()
        self.nb.add(self.tab_consistency, text="🚦 Tính nhất quán")
        
        # 5. Phân bổ I/R/M
        self.tab_irm = self._init_tab_irm()
        self.nb.add(self.tab_irm, text="🔄 Phân bổ I/R/M")

        # Bottom Bar
        footer = tb.Frame(self, padding=10)
        footer.pack(fill=X)
        self.lbl_status = tb.Label(footer, text="Sẵn sàng", foreground='grey')
        self.lbl_status.pack(side=LEFT)
        tb.Button(footer, text="🔄 Làm mới dữ liệu", bootstyle=INFO, command=self.refresh_all).pack(side=RIGHT, padx=5)
        tb.Button(footer, text="❌ Đóng", bootstyle=SECONDARY, command=self.destroy).pack(side=RIGHT, padx=5)

    # -------------------------------------------------------------------------
    # TAB 1: DASHBOARD
    # -------------------------------------------------------------------------
    def _init_tab_dashboard(self):
        tab = tb.Frame(self.nb, padding=20)
        
        # KPI Row
        kpi_frame = tb.Frame(tab)
        kpi_frame.pack(fill=X, pady=(0, 20))
        
        self.meters = {}
        stats = [
            ("Số HP số hóa", "success", 0),
            ("Đã Validate", "info", 0),
            ("Chất lượng cao", "primary", 0),
        ]
        
        for label, color, val in stats:
            f = tb.Frame(kpi_frame)
            f.pack(side=LEFT, expand=YES)
            m = Meter(f, metersize=160, padding=5, amounttotal=100, amountused=val, 
                      subtext=label, bootstyle=color, textright="%")
            m.pack()
            self.meters[label] = m

        # Lists Row
        list_frame = tb.Frame(tab)
        list_frame.pack(fill=BOTH, expand=YES)
        
        # Outdated HP
        lt_frame = tb.Labelframe(list_frame, text="⚠️ Top 5 HP cần cập nhật (Lâu nhất)", padding=10)
        lt_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        
        self.tree_outdated = tb.Treeview(lt_frame, columns=("ma", "ten", "last"), show='headings', height=5)
        self.tree_outdated.pack(fill=BOTH, expand=YES)
        for c, t in zip(["ma", "ten", "last"], ["Mã HP", "Tên HP", "Ngày cuối"]):
            self.tree_outdated.heading(c, text=t)
        
        # Weak PLO
        rt_frame = tb.Labelframe(list_frame, text="📉 PLO đang được hỗ trợ ít nhất", padding=10)
        rt_frame.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.tree_weak_plo = tb.Treeview(rt_frame, columns=("plo", "count", "percent"), show='headings', height=5)
        self.tree_weak_plo.pack(fill=BOTH, expand=YES)
        for c, t in zip(["plo", "count", "percent"], ["PLO", "Số HP hỗ trợ", "% Phủ"]):
            self.tree_weak_plo.heading(c, text=t)
            
        return tab

    # -------------------------------------------------------------------------
    # TAB 2: MA TRẬN CLO-PLO TOÀN KHOA
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
        
        self.tree_matrix = tb.Treeview(tab, show='headings')
        # Dynamic columns based on PLO will be set in _run_matrix_plo
        self.tree_matrix.pack(fill=BOTH, expand=YES, pady=10)
        
        return tab

    # -------------------------------------------------------------------------
    # TAB 3: PHÂN TÍCH BLOOM
    # -------------------------------------------------------------------------
    def _init_tab_bloom(self):
        tab = tb.Frame(self.nb, padding=10)
        self.bloom_canvas_frame = tb.Frame(tab)
        self.bloom_canvas_frame.pack(fill=BOTH, expand=YES)
        
        if not HAS_MATPLOTLIB:
            tb.Label(self.bloom_canvas_frame, text="Vui lòng cài đặt matplotlib để xem biểu đồ", foreground='red').pack(pady=50)
        
        self.lbl_bloom_warn = tb.Label(tab, text="", font=('', 10, 'bold'))
        self.lbl_bloom_warn.pack(pady=10)
        
        return tab

    # -------------------------------------------------------------------------
    # TAB 4: TÍNH NHẤT QUÁN (TRAFFIC LIGHT)
    # -------------------------------------------------------------------------
    def _init_tab_consistency(self):
        tab = tb.Frame(self.nb, padding=10)
        cols = ("status", "ma", "ten", "nd", "dg")
        self.tree_consist = tb.Treeview(tab, columns=cols, show='headings')
        self.tree_consist.pack(fill=BOTH, expand=YES)
        
        for c, t in zip(cols, ["Trạng thái", "Mã HP", "Tên HP", "Nội dung", "Đánh giá"]):
            self.tree_consist.heading(c, text=t)
        
        self.tree_consist.column("status", width=100, anchor=CENTER)
        self.tree_consist.tag_configure('fail', foreground='red')
        self.tree_consist.tag_configure('warn', foreground='orange')
        self.tree_consist.tag_configure('pass', foreground='green')
        
        self.tree_consist.bind("<Double-1>", self._on_consistency_click)
        
        return tab

    # -------------------------------------------------------------------------
    # TAB 5: PHÂN BỔ I/R/M
    # -------------------------------------------------------------------------
    def _init_tab_irm(self):
        tab = tb.Frame(self.nb, padding=10)
        cols = ("ma", "ten", "total", "i", "r", "m", "pct")
        self.tree_irm = tb.Treeview(tab, columns=cols, show='headings')
        self.tree_irm.pack(fill=BOTH, expand=YES)
        for c, t in zip(cols, ["Mã HP", "Tên HP", "Tổng CLO", "I", "R", "M", "% Master"]):
            self.tree_irm.heading(c, text=t)
        return tab

    def _refresh_ctdt_combobox(self):
        """Tải danh sách CTĐT từ database vào combobox."""
        try:
            from db import Database
            rows = self.db.get_all_ctdt()
            self.ctdt_map = {r['ten']: r['id'] for r in rows}
            names = list(self.ctdt_map.keys())
            self.cbo_ctdt_m.config(values=names)
            if names:
                self.cbo_ctdt_m.current(0)
        except Exception as e:
            print(f"Error loading CTĐT: {e}")

    # -------------------------------------------------------------------------
    # LOGIC
    # -------------------------------------------------------------------------
    def refresh_all(self):
        self.lbl_status.config(text="Đang tải dữ liệu...", foreground='blue')
        from services.stats_service import StatsService
        self.stats_svc = StatsService(self.db)
        threading.Thread(target=self._load_data_async, daemon=True).start()

    def _load_data_async(self):
        # Heavy lifting here (Phase 3: Use StatsService)
        try:
            summary = self.stats_svc.get_overall_dashboard_stats()
            # summary contain: total_hp, digital_hp, validated_hp, outdated, weak_plos
            
            # Consistency Data
            consistency_rows = self.db.conn.execute("""
                SELECT hp.ma, hp.ten_viet, 
                (SELECT COUNT(*) FROM clo WHERE hp_id = hp.id) as clo_cnt,
                (SELECT COUNT(DISTINCT id) FROM noi_dung WHERE hp_id = hp.id AND phan='lt') as nd_cnt,
                (SELECT COUNT(DISTINCT id) FROM ke_hoach_kiem_tra WHERE hp_id = hp.id) as dg_cnt
                FROM hoc_phan hp LIMIT 20
            """).fetchall()
            
            # Update UI
            self.after(0, lambda: self._update_ui_full(
                summary['total_hp'], 
                summary['validated_hp'], 
                summary['outdated'], 
                summary['weak_plos'], 
                consistency_rows
            ))
            # Refresh CTDT list too
            self.after(0, self._refresh_ctdt_combobox)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self.lbl_status.config(text=f"Lỗi: {err_msg}", foreground='red'))

    def _update_ui_full(self, total, val, outdated_rows, weak_plos, consist_rows):
        self.meters["Số HP số hóa"].configure(amountused=100)
        self.meters["Đã Validate"].configure(amountused=int((val/total)*100))
        
        # Outdated
        for item in self.tree_outdated.get_children(): self.tree_outdated.delete(item)
        for row in outdated_rows: self.tree_outdated.insert("", END, values=tuple(row))
        
        # Weak PLO
        for item in self.tree_weak_plo.get_children(): self.tree_weak_plo.delete(item)
        for row in weak_plos: 
            pct = int((row[1]/total)*100)
            self.tree_weak_plo.insert("", END, values=(row[0], row[1], f"{pct}%"))

        # Consistency
        for item in self.tree_consist.get_children(): self.tree_consist.delete(item)
        for row in consist_rows:
            status = "pass"
            c_cnt = row[2] or 0
            if row[3] < c_cnt or row[4] < c_cnt: status = "warn"
            if row[3] == 0 or row[4] == 0: status = "fail"
            
            icon = "✅ Đủ" if status == "pass" else ("⚠️ Thiếu" if status == "warn" else "❌ Trống")
            self.tree_consist.insert("", END, values=(icon, row[0], row[1], f"{row[3]}/{c_cnt} CLO", f"{row[4]}/{c_cnt} CLO"), tags=(status,))

        self.lbl_status.config(text="Đã cập nhật dữ liệu học thuật", foreground='green')
        self._plot_bloom_chart()

    def _plot_bloom_chart(self):
        if not HAS_MATPLOTLIB: return
        for child in self.bloom_canvas_frame.winfo_children(): child.destroy()
        
        # Query thực tế mức Bloom
        counts = [0] * 6
        clos = self.db.conn.execute("SELECT mo_ta FROM clo").fetchall()
        from services.deccuong_service import DeCuongValidator
        val = DeCuongValidator(self.db)
        
        for clo in clos:
            desc = (clo[0] or "").lower()
            for level, verbs in val.DONG_TU_BLOOM.items():
                if any(desc.startswith(v) for v in verbs):
                    counts[level-1] += 1
                    break
        
        fig, ax = plt.subplots(figsize=(6, 4))
        levels = ["L1", "L2", "L3", "L4", "L5", "L6"]
        colors = ['#ff9999','#ffcc99','#66b3ff','#99ff99','#ffb3e6','#c2c2f0']
        ax.bar(levels, counts, color=colors)
        ax.set_title("Phân bổ mức độ Bloom (Toàn CTĐT)")
        ax.set_ylabel("Số lượng CLO")
        
        canvas = FigureCanvasTkAgg(fig, master=self.bloom_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=YES)
        
        total = sum(counts) or 1
        low_pct = (counts[0]+counts[1])/total*100
        if low_pct > 40:
            self.lbl_bloom_warn.config(text=f"⚠️ Cảnh báo Bloom: Tỷ lệ nhận thức thấp chiếm {low_pct:.1f}% (>40%).", foreground='red')
        else:
            self.lbl_bloom_warn.config(text=f"✅ Chỉ số Bloom đạt chuẩn ({low_pct:.1f}%).", foreground='green')

    def _run_matrix_plo(self):
        # Lấy CTĐT đang chọn
        ctdt_name = self.cbo_ctdt_m.get()
        ctdt_id = self.ctdt_map.get(ctdt_name)
        if not ctdt_id: return

        # Query PLOs của CTĐT này
        plos = self.db.conn.execute("""
            SELECT ma FROM ctdt_plo 
            WHERE ctdt_id = ? ORDER BY ma
        """, (ctdt_id,)).fetchall()
        
        plo_list = [p[0] for p in plos]
        if not plo_list: plo_list = [f"PLO{i}" for i in range(1, 11)]
        
        self.tree_matrix["columns"] = ["hp"] + plo_list
        for c in self.tree_matrix["columns"]:
            self.tree_matrix.heading(c, text=c)
            self.tree_matrix.column(c, width=60, anchor=CENTER)
        self.tree_matrix.column("hp", width=250, anchor=W)
        
        for item in self.tree_matrix.get_children(): self.tree_matrix.delete(item)
        
        # Query HP thuộc CTĐT
        hps = self.db.conn.execute("""
            SELECT hp.ma, hp.ten_viet 
            FROM hoc_phan hp 
            JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
            WHERE ch.ctdt_id = ?
            ORDER BY ch.thu_tu, hp.ma
        """, (ctdt_id,)).fetchall()
        
        for hp in hps:
            row = [f"{hp[0]} - {hp[1]}"]
            
            # Lấy tất cả mapping CLO-PLO của học phần này
            # cdr_ma có thể chứa nhiều PLO cách nhau bởi dấu phẩy hoặc khoảng trắng
            clos_rows = self.db.conn.execute("""
                SELECT cdr_ma, level_irm FROM clo 
                WHERE hp_id = (SELECT id FROM hoc_phan WHERE ma = ?)
                AND (la_tieu_de_nhom IS NULL OR la_tieu_de_nhom = 0)
            """, (hp[0],)).fetchall()
            
            # Xây dựng bản đồ PLO -> Level cao nhất cho HP này
            # (Vì 1 HP có nhiều CLO, nhiều CLO có thể cùng map vào 1 PLO)
            hp_plo_map = {}
            level_rank = {'I': 1, 'R': 2, 'M': 3}
            
            for cdr_ma, level in clos_rows:
                if not cdr_ma: continue
                # Tách các PLO nếu có nhiều (VD: "PLO1, PLO2")
                mapped_plos = [p.strip().upper() for p in re.split(r'[,\s;]+', str(cdr_ma)) if p.strip()]
                
                for p_code in mapped_plos:
                    # Cập nhật mức độ cao nhất (M > R > I)
                    current_lvl = hp_plo_map.get(p_code, '')
                    if level_rank.get(level, 0) > level_rank.get(current_lvl, 0):
                        hp_plo_map[p_code] = level
            
            for plo in plo_list:
                val = hp_plo_map.get(plo.upper(), "-")
                row.append(val)
            self.tree_matrix.insert("", END, values=row)

    def _export_matrix_excel(self):
        if not HAS_OPENPYXL:
            Messagebox.show_error("Lỗi", "Vui lòng cài đặt openpyxl.")
            return
        
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path: return
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ma trận CLO-PLO"
        
        cols = [self.tree_matrix.heading(c)['text'] for c in self.tree_matrix['columns']]
        ws.append(cols)
        
        # Style
        header_fill = PatternFill(start_color="D9EDF7", end_color="D9EDF7", fill_type="solid")
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for item in self.tree_matrix.get_children():
            vals = self.tree_matrix.item(item)['values']
            ws.append(vals)
            
        wb.save(path)
        
        # Phase 3: Also export professional version
        pro_path = path.replace('.xlsx', '_Professional_Report.xlsx')
        ctdt_name = self.cbo_ctdt_m.get()
        ctdt_id = self.ctdt_map.get(ctdt_name)
        if ctdt_id:
            self.stats_svc.export_ctdt_matrix_excel(ctdt_id, pro_path)
            msg = f"Đã xuất 2 báo cáo:\n1. {path}\n2. {pro_path}"
        else:
            msg = f"Đã xuất ma trận ra: {path}"
            
        Messagebox.show_info("Thành công", msg)

    def _on_consistency_click(self, event):
        item = self.tree_consist.focus()
        if not item: return
        vals = self.tree_consist.item(item)['values']
        ma_hp = vals[1]
        
        if ask_modern_yesno(self, "Điều hướng", f"Bạn có muốn mở Đề cương học phần {ma_hp} để chỉnh sửa không?"):
            # Gọi callback trên parent (MainApp) để chuyển tab
            if hasattr(self.parent, 'open_de_cuong'):
                self.parent.open_de_cuong(ma_hp)
                self.destroy()
