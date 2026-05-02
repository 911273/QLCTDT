# sections/dynamic_section.py
import tkinter as tk
import ttkbootstrap as tb
from sections.base_section import BaseSection, ScrollableFrame

class DynamicSection(BaseSection):
    """
    Mục tùy biến động. Tự động vẽ giao diện dựa trên danh sách trường (ui_field_extra)
    được gán cho section_key này.
    """
    def __init__(self, parent, db, section_key, label, **kwargs):
        self._custom_section_key = section_key
        self._custom_label = label
        super().__init__(parent, db, **kwargs)

    @property
    def section_key(self) -> str:
        return self._custom_section_key

    def _build_ui(self):
        sf = ScrollableFrame(self)
        sf.pack(fill='both', expand=True)
        self._extra_parent = sf.inner
        
        # Header
        head = tb.Frame(self._extra_parent, padding=(16, 12, 16, 4))
        head.pack(fill='x')
        tb.Label(head, text=self._custom_label,
                  style='SectionHeader.TLabel').pack(anchor='w')
        tb.Separator(self._extra_parent, orient='horizontal').pack(fill='x', padx=16, pady=4)
        
        # Các trường dữ liệu sẽ được vẽ tự động bởi BaseSection.ensure_ui -> _render_extra_fields
        # nhờ vào việc self.section_key trả về key động.
