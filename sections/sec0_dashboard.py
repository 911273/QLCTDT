# sections/sec0_dashboard.py — Màn hình tổng quan
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection, ScrollableFrame, CLR_PRIMARY2, CLR_HDR, CLR_TEXT, CLR_BG

class Sec0Dashboard(BaseSection):
    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        self.p = sf.inner
        
        # Tiêu đề chào mừng
        header_frm = tb.Frame(self.p, padding=(20, 30))
        header_frm.pack(fill='x')
        
        tb.Label(header_frm, text='👋 Chào mừng bạn đến với', font=('Arial', 14)).pack(anchor='w')
        tb.Label(header_frm, text='Hệ thống Quản lý Đề cương Chi tiết Học phần', 
                  font=('Arial', 24, 'bold'), foreground=CLR_PRIMARY2).pack(anchor='w')
        tb.Label(header_frm, text='EPU Syllabus Management System v1.0', 
                  font=('Arial', 10, 'italic'), foreground='#666').pack(anchor='w', pady=(0, 20))
        
        # Khu vực thống kê (Cards)
        stats_frm = tb.Frame(self.p, padding=20)
        stats_frm.pack(fill='x')
        
        self.card_total = self._create_card(stats_frm, "📚 Tổng số đề cương", "0", 0)
        self.card_khoa = self._create_card(stats_frm, "🏫 Đơn vị quản lý", "0", 1)
        
        # Danh sách gần đây
        recent_frm = tb.Frame(self.p, padding=20)
        recent_frm.pack(fill='both', expand=True)
        
        tb.Label(recent_frm, text='🕒 Đề cương cập nhật gần đây', 
                  style='SectionHeader.TLabel').pack(anchor='w', pady=(0, 10))
        
        # Treeview cho danh sách gần đây
        cols = ('ma', 'ten', 'ngay')
        self.tree = tb.Treeview(recent_frm, columns=cols, show='headings', height=8)
        self.tree.heading('ma', text='Mã HP')
        self.tree.heading('ten', text='Tên học phần')
        self.tree.heading('ngay', text='Ngày cập nhật')
        self.tree.column('ma', width=100, minwidth=50, stretch=True)
        self.tree.column('ten', width=400, minwidth=100, stretch=True)
        self.tree.column('ngay', width=150, minwidth=80, stretch=True)
        self.tree.pack(fill='x')
        
        # Footer
        footer = tb.Frame(self.p, padding=40)
        footer.pack(fill='x')
        tb.Label(footer, text='Mẹo: Bạn có thể nhấn chuột phải vào danh sách bên trái để Sao chép đề cương nhanh.',
                  font=('Arial', 9, 'italic'), foreground='#888').pack()

    def _create_card(self, parent, title, value, col):
        card = tb.Frame(parent, style='Card.TFrame', padding=20, relief='flat')
        card.grid(row=0, column=col, padx=10, sticky='nsew')
        parent.columnconfigure(col, weight=1)
        
        tb.Label(card, text=title, font=('Arial', 11)).pack(anchor='w')
        v_lbl = tb.Label(card, text=value, font=('Arial', 24, 'bold'), foreground=CLR_PRIMARY2)
        v_lbl.pack(anchor='w')
        
        # Background color for cards (custom style needed)
        # We can simulate with a style or just use the current theme
        return v_lbl

    def load(self, hp_id=None):
        """Dashboard không phụ thuộc vào hp_id, nó lấy stats tổng thể."""
        stats = self.db.get_dashboard_stats()
        
        # Cập nhật cards
        self.card_total.config(text=str(stats.get('total_hp', 0)))
        self.card_khoa.config(text=str(len(stats.get('by_khoa', []))))
        
        # Cập nhật tree
        self.tree.delete(*self.tree.get_children())
        for r in stats.get('recent', []):
            self.tree.insert('', 'end', values=(r['ma'], r['ten_viet'], r['ngay_cap_nhat']))

    def update_theme(self):
        if not self._ui_built: return
        super().update_theme()
        # Custom card styling logic can go here if needed
