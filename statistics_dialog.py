# statistics_dialog.py — Thống kê và báo cáo đề cương
"""
Dialog thống kê tổng hợp, báo cáo theo trường dữ liệu, xuất CSV.
"""

import os
import csv
import tkinter as tk
from tkinter import filedialog
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk as tb
    HAS_TTKBOOTSTRAP = False

from sections.base_section import make_tree, recolor_tree, CLR_BG, CLR_TEXT, CLR_ROW1, set_window_icon


class StatisticsDialog(tb.Toplevel):
    """Dialog thống kê và báo cáo đề cương chi tiết."""

    def __init__(self, parent, db):
        super().__init__(parent)
        set_window_icon(self)
        self.title('📊 Thống kê & Báo cáo Đề cương')
        self.geometry('1050x700')
        self.db = db
        self.grab_set()
        self.transient(parent)
        self._build()

    def _build(self):
        # Notebook for different report types
        self.nb = tb.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=10, pady=10)

        # Tab 1: Tổng hợp
        self._build_tab_tong_hop()
        # Tab 2: Theo trường dữ liệu
        self._build_tab_theo_truong()
        # Tab 3: Ma trận CLO-PLO
        self._build_tab_clo_plo()

        # Bottom bar
        bf = tb.Frame(self)
        bf.pack(fill='x', padx=10, pady=(0, 10))
        tb.Button(bf, text='Đóng', command=self.destroy).pack(side='right', padx=4)

    # ── Tab 1: Tổng hợp ──────────────────────────────────────────────────────

    def _build_tab_tong_hop(self):
        tab = tb.Frame(self.nb)
        self.nb.add(tab, text='📋 Tổng hợp')

        # Info cards
        info_frm = tb.Labelframe(tab, text='Thông tin tổng hợp', padding=10)
        info_frm.pack(fill='x', padx=5, pady=5)

        # Fetch statistics
        stats = self._get_stats()

        cards = [
            ('📚 Tổng số HP', str(stats['total_hp'])),
            ('📝 Tổng tín chỉ', str(stats['total_tc'])),
            ('👨‍🏫 Giảng viên', str(stats['total_gv'])),
            ('📘 CTĐT', str(stats['total_ctdt'])),
            ('📕 Tài liệu', str(stats['total_tl'])),
        ]

        for i, (label, value) in enumerate(cards):
            card = tb.Labelframe(info_frm, text=label, padding=8)
            card.grid(row=0, column=i, padx=8, pady=4, sticky='nsew')
            tb.Label(card, text=value, font=('Arial', 20, 'bold'),
                     bootstyle='info').pack()
            info_frm.columnconfigure(i, weight=1)

        # Breakdown tables
        frm_bottom = tb.Frame(tab)
        frm_bottom.pack(fill='both', expand=True, padx=5, pady=5)

        # Left: Phân bổ theo loại
        left = tb.Labelframe(frm_bottom, text='Phân bổ theo Loại HP', padding=5)
        left.pack(side='left', fill='both', expand=True, padx=(0, 5))

        cols_l = ('loai', 'so_luong', 'ty_le')
        heads_l = ('Loại HP', 'Số lượng', 'Tỷ lệ %')
        widths_l = (150, 80, 80)
        tf_l, self.tree_loai = make_tree(left, cols_l, heads_l, widths_l, height=6, db=self.db, table_id='stats_by_loai')
        tf_l.pack(fill='both', expand=True)

        for loai, count in stats['by_loai']:
            pct = f"{count * 100 / max(stats['total_hp'], 1):.1f}%"
            self.tree_loai.insert('', 'end', values=(loai or 'Chưa xác định', count, pct))
        recolor_tree(self.tree_loai)

        # Right: Phân bổ theo tính chất
        right = tb.Labelframe(frm_bottom, text='Phân bổ theo Tính chất', padding=5)
        right.pack(side='left', fill='both', expand=True, padx=(5, 0))

        cols_r = ('tinh_chat', 'so_luong', 'ty_le')
        heads_r = ('Tính chất', 'Số lượng', 'Tỷ lệ %')
        widths_r = (150, 80, 80)
        tf_r, self.tree_tc = make_tree(right, cols_r, heads_r, widths_r, height=6, db=self.db, table_id='stats_by_nature')
        tf_r.pack(fill='both', expand=True)

        for tc, count in stats['by_tinh_chat']:
            pct = f"{count * 100 / max(stats['total_hp'], 1):.1f}%"
            self.tree_tc.insert('', 'end', values=(tc or 'Chưa xác định', count, pct))
        recolor_tree(self.tree_tc)

        # Export button
        tb.Button(tab, text='📥 Xuất CSV tổng hợp',
                  command=lambda: self._export_csv_summary(stats),
                  bootstyle='outline-success').pack(pady=5)

    # ── Tab 2: Theo trường dữ liệu ───────────────────────────────────────────

    def _build_tab_theo_truong(self):
        tab = tb.Frame(self.nb)
        self.nb.add(tab, text='🔍 Lọc theo trường')

        # Filter bar
        fbar = tb.Frame(tab, padding=5)
        fbar.pack(fill='x', padx=5, pady=5)

        tb.Label(fbar, text='CTĐT:').pack(side='left', padx=4)
        self.v_filter_ctdt = tk.StringVar(value='Tất cả')
        ctdt_list = ['Tất cả'] + [r['ten'] for r in self.db.get_all_ctdt()]
        cb_ctdt = tb.Combobox(fbar, textvariable=self.v_filter_ctdt,
                               values=ctdt_list, width=25, state='readonly')
        cb_ctdt.pack(side='left', padx=4)

        tb.Label(fbar, text='Trình độ:').pack(side='left', padx=4)
        self.v_filter_trinh_do = tk.StringVar(value='Tất cả')
        tb.Combobox(fbar, textvariable=self.v_filter_trinh_do,
                    values=['Tất cả', 'Đại học', 'Thạc sĩ', 'Tiến sĩ'],
                    width=12, state='readonly').pack(side='left', padx=4)

        tb.Label(fbar, text='Tính chất:').pack(side='left', padx=4)
        self.v_filter_tc = tk.StringVar(value='Tất cả')
        tb.Combobox(fbar, textvariable=self.v_filter_tc,
                    values=['Tất cả', 'Lý thuyết', 'Hỗn hợp', 'Thực hành', 'Đồ án', 'Thực tập'],
                    width=14, state='readonly').pack(side='left', padx=4)

        tb.Button(fbar, text='🔄 Lọc', command=self._apply_filter,
                  bootstyle='info').pack(side='left', padx=8)
        tb.Button(fbar, text='📥 Xuất CSV', command=self._export_csv_filtered,
                  bootstyle='outline-success').pack(side='right', padx=4)

        # Results table
        cols = ('ma', 'ten_viet', 'trinh_do', 'so_tin_chi', 'loai', 'tinh_chat',
                'gio_lt', 'gio_th_tn', 'gio_tu_hoc', 'tong_gio')
        heads = ('Mã HP', 'Tên học phần', 'Trình độ', 'TC', 'Loại', 'Tính chất',
                 'Giờ LT', 'Giờ TH', 'Tự học', 'Tổng giờ')
        widths = (80, 250, 70, 35, 70, 80, 50, 50, 50, 55)
        tf, self.tree_filter = make_tree(tab, cols, heads, widths, height=18, db=self.db, table_id='stats_filter')
        tf.pack(fill='both', expand=True, padx=5, pady=5)

        # Count label
        self.lbl_filter_count = tb.Label(tab, text='')
        self.lbl_filter_count.pack(anchor='w', padx=10)

        self._apply_filter()

    def _apply_filter(self):
        self.tree_filter.delete(*self.tree_filter.get_children())

        ctdt_name = self.v_filter_ctdt.get()
        trinh_do = self.v_filter_trinh_do.get()
        tinh_chat = self.v_filter_tc.get()

        # Build query
        conditions = []
        params = []

        if trinh_do != 'Tất cả':
            conditions.append("hp.trinh_do = ?")
            params.append(trinh_do)
        if tinh_chat != 'Tất cả':
            conditions.append("hp.tinh_chat = ?")
            params.append(tinh_chat)

        if ctdt_name != 'Tất cả':
            sql = """
                SELECT DISTINCT hp.* FROM hoc_phan hp
                JOIN ctdt_hoc_phan ch ON ch.hp_id = hp.id
                JOIN chuong_trinh_dao_tao c ON ch.ctdt_id = c.id
                WHERE c.ten = ?
            """
            params_q = [ctdt_name]
            if conditions:
                sql += " AND " + " AND ".join(conditions)
                params_q += params
            sql += " ORDER BY hp.ma, hp.ten_viet"
            rows = self.db.conn.execute(sql, params_q).fetchall()
        else:
            where = "WHERE " + " AND ".join(conditions) if conditions else ""
            sql = f"SELECT * FROM hoc_phan hp {where} ORDER BY hp.ma, hp.ten_viet"
            rows = self.db.conn.execute(sql, params).fetchall()

        total_tc = 0
        for i, r in enumerate(rows):
            tag = 'even' if i % 2 == 0 else 'odd'
            tc = r['so_tin_chi'] or 0
            total_tc += tc
            self.tree_filter.insert('', 'end', values=(
                r['ma'] or '', r['ten_viet'] or '', r['trinh_do'] or '',
                tc, r['loai'] or '', r['tinh_chat'] or '',
                r['gio_lt'] or 0, r['gio_th_tn'] or 0,
                r['gio_tu_hoc'] or 0, r['tong_gio'] or 0
            ), tags=(tag,))

        self.lbl_filter_count.config(
            text=f'Hiển thị {len(rows)} học phần — Tổng tín chỉ: {total_tc}')

    # ── Tab 3: Ma trận CLO-PLO ────────────────────────────────────────────────

    def _build_tab_clo_plo(self):
        tab = tb.Frame(self.nb)
        self.nb.add(tab, text='📐 Ma trận CLO-PLO')

        # Select HP
        fbar = tb.Frame(tab, padding=5)
        fbar.pack(fill='x', padx=5, pady=5)

        tb.Label(fbar, text='Học phần:').pack(side='left', padx=4)
        self._hp_list = self.db.get_all_hoc_phan()
        hp_names = [f"{r['ma'] or '???'} - {r['ten_viet']}" for r in self._hp_list]
        self.v_clo_hp = tk.StringVar()
        self.cb_clo_hp = tb.Combobox(fbar, textvariable=self.v_clo_hp,
                                      values=hp_names, width=50, state='readonly')
        self.cb_clo_hp.pack(side='left', padx=4)

        tb.Button(fbar, text='📊 Xem', command=self._show_clo_matrix,
                  bootstyle='info').pack(side='left', padx=8)

        # Results
        self.frm_clo_result = tb.Frame(tab)
        self.frm_clo_result.pack(fill='both', expand=True, padx=5, pady=5)

        tb.Label(self.frm_clo_result,
                 text='Chọn học phần và nhấn "Xem" để hiển thị ma trận CLO-PLO',
                 font=('Arial', 10)).pack(pady=20)

    def _show_clo_matrix(self):
        sel = self.cb_clo_hp.current()
        if sel < 0:
            return

        hp_id = self._hp_list[sel]['id']

        # Clear previous
        for child in self.frm_clo_result.winfo_children():
            child.destroy()

        clos = self.db.get_clo(hp_id)
        muc_tieu = self.db.get_muc_tieu(hp_id)

        if not clos:
            tb.Label(self.frm_clo_result, text='Học phần chưa có CLO nào.',
                     font=('Arial', 10)).pack(pady=20)
            return

        # Build display table
        cols = ('clo_ma', 'mo_ta', 'cdr_ctdt')
        heads = ('CLO', 'Mô tả', 'CĐR CTĐT (PI)')
        widths = (70, 500, 200)
        tf, tree = make_tree(self.frm_clo_result, cols, heads, widths, height=15, db=self.db, table_id='stats_clo_plo_matrix')
        tf.pack(fill='both', expand=True)

        for i, clo in enumerate(clos):
            if clo['la_tieu_de_nhom']:
                tree.insert('', 'end', values=(
                    '', clo['mo_ta'] or '', ''
                ), tags=('group',))
            else:
                tag = 'even' if i % 2 == 0 else 'odd'
                tree.insert('', 'end', values=(
                    clo['ma'] or '', clo['mo_ta'] or '', clo['cdr_ma'] or ''
                ), tags=(tag,))

        # Summary
        summary = tb.Labelframe(self.frm_clo_result, text='Tóm tắt', padding=5)
        summary.pack(fill='x', pady=5)
        clo_count = sum(1 for c in clos if not c['la_tieu_de_nhom'])
        mt_count = sum(1 for m in muc_tieu if not m['la_tieu_de_nhom'])
        tb.Label(summary,
                 text=f'Số CLO: {clo_count} | Số mục tiêu: {mt_count}',
                 font=('Arial', 10)).pack(anchor='w')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_stats(self):
        """Truy vấn tất cả thống kê."""
        db = self.db
        total_hp = db.conn.execute("SELECT COUNT(*) as c FROM hoc_phan").fetchone()['c']
        total_tc = db.conn.execute("SELECT COALESCE(SUM(so_tin_chi), 0) as c FROM hoc_phan").fetchone()['c']
        total_gv = db.conn.execute("SELECT COUNT(*) as c FROM giang_vien").fetchone()['c']
        total_ctdt = db.conn.execute("SELECT COUNT(*) as c FROM chuong_trinh_dao_tao").fetchone()['c']
        total_tl = db.conn.execute("SELECT COUNT(*) as c FROM tai_lieu").fetchone()['c']

        by_loai = db.conn.execute(
            "SELECT loai, COUNT(*) as c FROM hoc_phan GROUP BY loai ORDER BY c DESC"
        ).fetchall()
        by_tinh_chat = db.conn.execute(
            "SELECT tinh_chat, COUNT(*) as c FROM hoc_phan GROUP BY tinh_chat ORDER BY c DESC"
        ).fetchall()

        return {
            'total_hp': total_hp, 'total_tc': total_tc,
            'total_gv': total_gv, 'total_ctdt': total_ctdt,
            'total_tl': total_tl,
            'by_loai': [(r['loai'], r['c']) for r in by_loai],
            'by_tinh_chat': [(r['tinh_chat'], r['c']) for r in by_tinh_chat]
        }

    def _export_csv_summary(self, stats):
        """Xuất CSV tổng hợp."""
        path = filedialog.asksaveasfilename(
            title='Lưu báo cáo CSV', defaultextension='.csv',
            filetypes=[('CSV', '*.csv')])
        if not path:
            return

        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['BÁO CÁO THỐNG KÊ ĐỀ CƯƠNG CHI TIẾT HỌC PHẦN'])
            w.writerow([])
            w.writerow(['Tổng số học phần', stats['total_hp']])
            w.writerow(['Tổng tín chỉ', stats['total_tc']])
            w.writerow(['Số giảng viên', stats['total_gv']])
            w.writerow(['Số CTĐT', stats['total_ctdt']])
            w.writerow(['Số tài liệu', stats['total_tl']])
            w.writerow([])
            w.writerow(['PHÂN BỔ THEO LOẠI HP'])
            w.writerow(['Loại', 'Số lượng', 'Tỷ lệ %'])
            for loai, count in stats['by_loai']:
                pct = f"{count * 100 / max(stats['total_hp'], 1):.1f}"
                w.writerow([loai or 'N/A', count, pct])
            w.writerow([])
            w.writerow(['PHÂN BỔ THEO TÍNH CHẤT'])
            w.writerow(['Tính chất', 'Số lượng', 'Tỷ lệ %'])
            for tc, count in stats['by_tinh_chat']:
                pct = f"{count * 100 / max(stats['total_hp'], 1):.1f}"
                w.writerow([tc or 'N/A', count, pct])

        show_modern_info(self, 'Thành công', f'Đã xuất: {path}')

    def _export_csv_filtered(self):
        """Xuất CSV danh sách đã lọc."""
        children = self.tree_filter.get_children()
        if not children:
            show_modern_info(self, 'Thông báo', 'Không có dữ liệu để xuất.')
            return

        path = filedialog.asksaveasfilename(
            title='Lưu danh sách CSV', defaultextension='.csv',
            filetypes=[('CSV', '*.csv')])
        if not path:
            return

        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['Mã HP', 'Tên học phần', 'Trình độ', 'Tín chỉ',
                         'Loại', 'Tính chất', 'Giờ LT', 'Giờ TH', 'Tự học', 'Tổng giờ'])
            for iid in children:
                vals = self.tree_filter.item(iid, 'values')
                w.writerow(vals)

        show_modern_info(self, 'Thành công', f'Đã xuất {len(children)} dòng: {path}')
