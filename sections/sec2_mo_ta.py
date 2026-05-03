# sections/sec2_mo_ta.py — Mô tả tóm tắt nội dung học phần
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection, CLR_BG, CLR_PRIMARY2
from sections.registry import register_section


@register_section(order=2, label="2. Mô tả")
class Sec2MoTa(BaseSection):
    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, db, **kwargs)
        self.txt = None

    def _build_ui(self):
        self.configure(style='TFrame')
        
        head = tb.Frame(self, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text='2. Mô tả vắn tắt nội dung học phần',
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self, orient='horizontal').pack(fill='x', padx=16, pady=4)

        frm = tb.Frame(self, padding=(16, 4, 16, 16))
        frm.pack(fill='both', expand=True)
        self._extra_parent = frm

        lbl = tb.Label(frm, text='Nội dung mô tả:', font=('Arial', 10))
        lbl.pack(anchor='w')

        txt_frame = tb.Frame(frm)
        txt_frame.pack(fill='both', expand=True, pady=(4, 0))

        self.txt = tk.Text(txt_frame, font=('Times New Roman', 12), wrap='word',
                           relief='solid', bd=1, padx=6, pady=6,
                           undo=True)
        vsb = tb.Scrollbar(txt_frame, orient='vertical', command=self.txt.yview)
        self.txt.configure(yscrollcommand=vsb.set)
        self.txt.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.txt.bind('<KeyRelease>', lambda _: self.mark_modified())

        self._register_field('mo_ta', label_widget=lbl, input_widget=self.txt, frame=txt_frame)

    def load(self, hp_id):
        super().load(hp_id)
        hp = self.db.get_hoc_phan(hp_id)
        self.txt.delete('1.0', 'end')
        val = hp['mo_ta'] if hp and hp['mo_ta'] else ''
        self.txt.insert('1.0', val)
        self._loading = False

    def save(self):
        if self.hp_id is not None:
            self.db.update_hoc_phan(self.hp_id, self.get_data_dict())

    def get_data_dict(self):
        self.ensure_ui()
        return {'mo_ta': self.txt.get('1.0', 'end-1c').strip()}

    def clear(self):
        super().clear()
        self.txt.delete('1.0', 'end')
