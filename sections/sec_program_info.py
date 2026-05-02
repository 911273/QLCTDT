# sections/sec_program_info.py — Thông tin Chương trình đào tạo
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection, ScrollableFrame, make_tree
from sections.registry import register_section

@register_section(order=0, label="0. Thông tin CTĐT")
class SecProgramInfo(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self.ctdt_id = None

    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        self.p = sf.inner
        self._extra_parent = self.p

        # 1. Header & Thông tin chung
        header_frm = tb.Frame(self.p, padding=(20, 20))
        header_frm.pack(fill='x')
        
        tb.Label(header_frm, text='📘 CHƯƠNG TRÌNH ĐÀO TẠO', font=('Arial', 10, 'bold'), foreground='#888').pack(anchor='w')
        self.lbl_title = tb.Label(header_frm, text='Tên chương trình đào tạo', font=('Arial', 20, 'bold'), wraplength=800)
        self.lbl_title.pack(anchor='w', pady=(5, 15))

        info_grid = tb.Frame(header_frm)
        info_grid.pack(fill='x')
        
        self.val_bac = self._create_info_item(info_grid, "🎓 Bậc đào tạo:", 0, 0)
        self.val_khoa = self._create_info_item(info_grid, "🏫 Khoa quản lý:", 0, 1)

        # 2. Thống kê nhanh (Cards)
        stats_frm = tb.Frame(self.p, padding=20)
        stats_frm.pack(fill='x')
        
        from sections.base_section import CLR_PRIMARY2
        self.card_hp = self._create_card(stats_frm, "📚 Số học phần", "0", 0, 'info')
        self.card_tc = self._create_card(stats_frm, "💎 Tổng tín chỉ", "0", 1, 'success')
        self.card_po = self._create_card(stats_frm, "🎯 Số PO", "0", 2, 'warning')
        self.card_plo = self._create_card(stats_frm, "🚀 Số PLO", "0", 3, 'danger')

        # 3. Danh sách PLO
        plo_lf = tb.Labelframe(self.p, text="Chuẩn đầu ra của Chương trình đào tạo (PLO)", padding=15)
        plo_lf.pack(fill='both', expand=True, padx=20, pady=(0, 20))

        cols = ("ma", "mo_ta")
        heads = ("Mã PLO", "Mô tả chuẩn đầu ra")
        widths = (100, 700)
        self.plo_tree_frm, self.plo_tree = make_tree(plo_lf, cols, heads, widths, height=12)
        self.plo_tree_frm.pack(fill='both', expand=True)

    def _create_info_item(self, parent, label, row, col):
        f = tb.Frame(parent)
        f.grid(row=row, column=col, sticky='w', padx=(0, 40))
        tb.Label(f, text=label, font=('Arial', 10, 'bold')).pack(side='left')
        val = tb.Label(f, text="-", font=('Arial', 10))
        val.pack(side='left', padx=5)
        return val

    def _create_card(self, parent, title, value, col, color):
        card = tb.Frame(parent, bootstyle=color, padding=15)
        card.grid(row=0, column=col, padx=10, sticky='nsew')
        parent.columnconfigure(col, weight=1)
        
        tb.Label(card, text=title, font=('Arial', 10), bootstyle=f'{color}-inverse').pack(anchor='w')
        v_lbl = tb.Label(card, text=value, font=('Arial', 24, 'bold'), bootstyle=f'{color}-inverse')
        v_lbl.pack(anchor='w')
        return v_lbl

    def load_ctdt(self, ctdt_id):
        """Phương thức chuyên biệt để load thông tin CTĐT."""
        self.ctdt_id = ctdt_id
        self.ensure_ui()
        
        ctdt = self.db.get_ctdt(ctdt_id)
        if not ctdt:
            self.clear_ui()
            return
            
        self.lbl_title.config(text=ctdt['ten'])
        self.val_bac.config(text=ctdt['bac'])
        self.val_khoa.config(text=ctdt['ten_khoa'] or "Không xác định")
        
        stats = self.db.get_ctdt_stats(ctdt_id)
        self.card_hp.config(text=str(stats['hp_count']))
        self.card_tc.config(text=str(stats['tc_sum']))
        self.card_po.config(text=str(stats['po_count']))
        self.card_plo.config(text=str(stats['plo_count']))
        
        # Load PLOs
        plos = self.db.get_plo_by_ctdt(ctdt_id)
        self.plo_tree.delete(*self.plo_tree.get_children())
        for i, p in enumerate(plos):
            tag = 'even' if i % 2 == 0 else 'odd'
            self.plo_tree.insert('', 'end', values=(p['ma'], p['mo_ta']), tags=(tag,))
            
        # Highlight this tab if possible? 
        # No, that's main.py's job.

    def load(self, hp_id):
        """Mặc định khi chuyển học phần: Hiện info CTĐT của nó."""
        self.ensure_ui()
        links = self.db.get_ctdt_of_hp(hp_id)
        if links:
            # Thường lất link đầu tiên làm context chính
            self.load_ctdt(links[0]['ctdt_id'])
        else:
            self.clear_ui()

    def clear_ui(self):
        self.lbl_title.config(text="Chưa chọn Chương trình đào tạo")
        self.val_bac.config(text="-")
        self.val_khoa.config(text="-")
        self.card_hp.config(text="0")
        self.card_tc.config(text="0")
        self.card_po.config(text="0")
        self.card_plo.config(text="0")
        self.plo_tree.delete(*self.plo_tree.get_children())
