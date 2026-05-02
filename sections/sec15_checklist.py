import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection, ScrollableFrame
from sections.registry import register_section

@register_section(order=15, label="15. Tự kiểm tra (Checklist)")
class Sec15Checklist(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self._initial_data = {}
        self.v_hinh_thuc = tk.IntVar()
        self.v_clo_bloom = tk.IntVar()
        self.v_gio_tu_hoc = tk.IntVar()
        self.v_rubric_match = tk.IntVar()
        self.v_giang_vien_xn = tk.IntVar()

    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        p = sf.inner

        tb.Label(p, text='Tiêu chí Tự kiểm tra / Wizard Touch', style='SectionHeader.TLabel').pack(anchor='w', padx=16, pady=(12, 4))
        tb.Separator(p, orient='horizontal').pack(fill='x', padx=16, pady=4)

        lf = tb.Labelframe(p, text='Đánh giá hoàn thành', padding=15)
        lf.pack(fill='both', expand=True, padx=16, pady=8)

        tb.Checkbutton(lf, text='[Hình thức] Thống nhất Font Times New Roman 12, cách dòng chuẩn, không lỗi bảng', 
                        variable=self.v_hinh_thuc).pack(anchor='w', pady=4)
        tb.Checkbutton(lf, text='[Chuẩn Bloom] Chuẩn đầu ra (CLO) đã sử dụng đúng động từ đo lường, không dùng Biết/Hiểu/Nắm vững', 
                        variable=self.v_clo_bloom).pack(anchor='w', pady=4)
        tb.Checkbutton(lf, text='[Thời lượng] Đảm bảo quy định 1 Tín chỉ = 50 giờ học tập (bao gồm Tự học)', 
                        variable=self.v_gio_tu_hoc).pack(anchor='w', pady=4)
        tb.Checkbutton(lf, text='[Đánh giá] 100% CLO được bao phủ bởi các bài đánh giá (Trọng số OK)', 
                        variable=self.v_rubric_match).pack(anchor='w', pady=4)
        tb.Checkbutton(lf, text='[Xác nhận] Giảng viên biên soạn đã ký và chịu trách nhiệm nội dung', 
                        variable=self.v_giang_vien_xn).pack(anchor='w', pady=4)

        self.auto_track_vars(self.v_hinh_thuc, self.v_clo_bloom, self.v_gio_tu_hoc, self.v_rubric_match, self.v_giang_vien_xn)

    def get_data_dict(self):
        self.ensure_ui()
        return {
            'hinh_thuc': self.v_hinh_thuc.get(),
            'clo_bloom': self.v_clo_bloom.get(),
            'gio_tu_hoc': self.v_gio_tu_hoc.get(),
            'rubric_match': self.v_rubric_match.get(),
            'giang_vien_xn': self.v_giang_vien_xn.get()
        }

    def apply_data_dict(self, data):
        self.ensure_ui()
        if not data: return
        self.v_hinh_thuc.set(data.get('hinh_thuc', 0))
        self.v_clo_bloom.set(data.get('clo_bloom', 0))
        self.v_gio_tu_hoc.set(data.get('gio_tu_hoc', 0))
        self.v_rubric_match.set(data.get('rubric_match', 0))
        self.v_giang_vien_xn.set(data.get('giang_vien_xn', 0))

    def load(self, hp_id):
        super().load(hp_id)
        self.ensure_ui()
        row = self.db.conn.execute("SELECT * FROM checklist_tu_kiem_tra WHERE hp_id=?", (hp_id,)).fetchone()
        data = dict(row) if row else {}
        self.apply_data_dict(data)
        self._initial_data = self.get_data_dict()

    def save(self):
        if not self.hp_id: return
        data = self.get_data_dict()
        with self.db.transaction():
            existing = self.db.conn.execute("SELECT id FROM checklist_tu_kiem_tra WHERE hp_id=?", (self.hp_id,)).fetchone()
            if existing:
                self.db.conn.execute("UPDATE checklist_tu_kiem_tra SET hinh_thuc=?, clo_bloom=?, gio_tu_hoc=?, rubric_match=?, giang_vien_xn=? WHERE hp_id=?", 
                                     (data['hinh_thuc'], data['clo_bloom'], data['gio_tu_hoc'], data['rubric_match'], data['giang_vien_xn'], self.hp_id))
            else:
                self.db.conn.execute("INSERT INTO checklist_tu_kiem_tra (hp_id, hinh_thuc, clo_bloom, gio_tu_hoc, rubric_match, giang_vien_xn) VALUES (?, ?, ?, ?, ?, ?)", 
                                     (self.hp_id, data['hinh_thuc'], data['clo_bloom'], data['gio_tu_hoc'], data['rubric_match'], data['giang_vien_xn']))
        self._initial_data = data

    def clear(self):
        super().clear()
        self.v_hinh_thuc.set(0)
        self.v_clo_bloom.set(0)
        self.v_gio_tu_hoc.set(0)
        self.v_rubric_match.set(0)
        self.v_giang_vien_xn.set(0)
