# sections/sec12_phu_luc.py — Phụ lục
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection

class Sec12PhuLuc(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self.txt = None

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='12. Phụ lục',
                  style='SectionHeader.TLabel').pack(anchor='w', side='left')
        tb.Button(head, text='🪄 Điền mẫu chuẩn', bootstyle='outline-info', 
                   command=self._auto_fill, padding=2).pack(side='right')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        frm = tb.Frame(self, padding=(16, 4, 16, 16))
        frm.pack(fill='both', expand=True)

        self.txt = tk.Text(frm, font=('Times New Roman', 12), wrap='word',
                           relief='solid', bd=1, padx=6, pady=6, undo=True)
        vsb = tb.Scrollbar(frm, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=vsb.set)
        self.txt.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        self.txt.delete('1.0', 'end')
        val = hp['phu_luc'] if hp and 'phu_luc' in hp and hp['phu_luc'] else ''
        self.txt.insert('1.0', val)

    def save(self):
        if self.hp_id is not None:
            self.db.update_hoc_phan(self.hp_id, self.get_data_dict())

    def get_data_dict(self):
        self.ensure_ui()
        return {'phu_luc': self.txt.get('1.0', 'end-1c').strip()}

    def _auto_fill(self):
        suggestion = (
            "- Danh mục các từ viết tắt.\n"
            "- Các bảng tra cứu bổ trợ.\n"
            "- Hướng dẫn cài đặt phần mềm chuyên ngành.\n"
            "- Quy trình thực hiện thí nghiệm chi tiết."
        )
        if self.txt.get('1.0', 'end-1c').strip():
            from utils.ui_utils import ask_modern_yesno
            if not ask_modern_yesno(self, 'Xác nhận', 'Nội dung hiện tại sẽ bị ghi đè. Tiếp tục?'):
                return
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', suggestion)
