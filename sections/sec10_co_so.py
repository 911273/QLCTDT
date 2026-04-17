# sections/sec10_co_so.py — Cơ sở vật chất phục vụ học phần
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection
from utils.ui_utils import (show_modern_info, ask_modern_yesno)

class Sec10CoSo(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self.txt = None

    def _build_ui(self):
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='10. Cơ sở vật chất phục vụ học phần',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        frm = tb.Frame(self, padding=(16, 4, 16, 16))
        frm.pack(fill='both', expand=True)

        lbl_frm = tb.Frame(frm)
        lbl_frm.pack(fill='x')
        tb.Label(lbl_frm, text='Mô tả phòng học, thiết bị, phần mềm, ...',
                  font=('Arial', 10)).pack(side='left')
        tb.Button(lbl_frm, text='🪄 Điền mẫu chuẩn', bootstyle='outline-info', 
                   command=self._auto_fill, padding=2).pack(side='right')

        txt_frame = tb.Frame(frm)
        txt_frame.pack(fill='both', expand=True, pady=(4, 0))

        self.txt = tk.Text(txt_frame, font=('Times New Roman', 12), wrap='word',
                           relief='solid', bd=1, padx=6, pady=6, undo=True)
        vsb = tb.Scrollbar(txt_frame, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=vsb.set)
        self.txt.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        self.txt.delete('1.0', 'end')
        val = hp['co_so_vat_chat'] if hp and 'co_so_vat_chat' in hp and hp['co_so_vat_chat'] else ''
        self.txt.insert('1.0', val)

    def save(self):
        if self.hp_id is not None:
            self.db.update_hoc_phan(self.hp_id, self.get_data_dict())

    def get_data_dict(self):
        self.ensure_ui()
        return {'co_so_vat_chat': self.txt.get('1.0', 'end-1c').strip()}

    def _auto_fill(self):
        suggestion = (
            "- Phòng học lý thuyết có máy chiếu, âm thanh.\n"
            "- Phòng thực hành máy tính với cấu hình phù hợp.\n"
            "- Các phần mềm chuyên ngành: Visual Studio, SQL Server, ...\n"
            "- Hệ thống E-learning của Trường."
        )
        if self.txt.get('1.0', 'end-1c').strip():
            if not ask_modern_yesno(self, 'Xác nhận', 'Nội dung hiện tại sẽ bị ghi đè. Tiếp tục?'):
                return
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', suggestion)
