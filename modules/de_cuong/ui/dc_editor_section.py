# modules/de_cuong/ui/dc_editor_section.py
"""DCEditorSection — Giao diện soạn thảo đề cương động dựa trên schema."""
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from core.event_bus import EventBus


class DCEditorSection(tb.Frame):
    """Giao diện Editor tự render dựa trên schema config."""

    def __init__(self, master, db, lazy=False, modified_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self._db = db
        self.hp_id = None
        self._modified_callback = modified_callback
        
        self._bus = EventBus.get()
        self._bus.subscribe('schema.changed',  self._on_schema_event)
        self._bus.subscribe('section.changed', self._on_schema_event)
        self._bus.subscribe('field.changed',   self._on_field_event)
        
        self._active_schema = None
        self._sections = []
        self._panels = {}
        self._is_ui_built = False

    def ensure_ui(self):
        if self._is_ui_built:
            return
        self._build_ui()
        self._is_ui_built = True

    def _build_ui(self):
        paned = tb.Panedwindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=4, pady=4)
        
        # Sidebar: Navigation List
        left = tb.Frame(paned, width=200)
        paned.add(left, weight=0)
        self._nav_list = tk.Listbox(left, font=('Arial', 10), selectmode='single', 
                                    borderwidth=0, highlightthickness=1)
        vsb = tb.Scrollbar(left, orient='vertical', command=self._nav_list.yview)
        self._nav_list.configure(yscrollcommand=vsb.set)
        self._nav_list.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self._nav_list.bind('<<ListboxSelect>>', self._on_nav_select)
        
        # Right: Content Panel
        self._content_frm = tb.Frame(paned)
        paned.add(self._content_frm, weight=1)
        
        self._reload_from_db()

    def _on_schema_event(self, schema_id=None, **kwargs):
        """Reload toàn bộ nav khi schema/section thay đổi."""
        active = self._active_schema
        if schema_id is None or (active and active['id'] == schema_id):
            self._reload_from_db()

    def _on_field_event(self, section_id=None, schema_id=None, **kwargs):
        """Reload chỉ panel đang active nếu section của nó thay đổi."""
        if section_id and section_id in self._panels:
            if hasattr(self._panels[section_id], 'reload'):
                self._panels[section_id].reload()
        elif schema_id:
            self._on_schema_event(schema_id=schema_id)

    def _reload_from_db(self):
        if getattr(self._db, 'dc_bridge', None) is None:
            return

        prev_sel = self._nav_list.curselection()
        prev_idx = prev_sel[0] if prev_sel else 0

        for p in self._panels.values():
            try: p.destroy()
            except: pass
        self._panels.clear()
        
        self._active_schema = self._db.dc_bridge.get_default_schema()
        if not self._active_schema:
            self._show_no_schema_placeholder()
            return
            
        self._sections = self._db.dc_bridge.list_sections(self._active_schema['id'])
        self._render_nav()

        n = len(self._sections)
        restore_idx = min(prev_idx, n - 1) if n > 0 else None
        if restore_idx is not None:
            self._nav_list.selection_set(restore_idx)
            self._on_nav_select()

    def _render_nav(self):
        self._nav_list.delete(0, 'end')
        for sec in self._sections:
            self._nav_list.insert('end', f"{sec.get('icon', '📋')} {sec.get('tieu_de')}")

    def _show_no_schema_placeholder(self):
        self._nav_list.delete(0, 'end')
        for widget in self._content_frm.winfo_children():
            widget.destroy()
        tb.Label(self._content_frm, text="Chưa có mẫu đề cương mặc định.", font=('Arial', 12, 'italic')).pack(pady=50)

    def _on_nav_select(self, event=None):
        sel = self._nav_list.curselection()
        if not sel: return
        idx = sel[0]
        sec = self._sections[idx]
        
        for widget in self._content_frm.winfo_children():
            widget.pack_forget()
            
        sec_id = sec['id']
        if sec_id not in self._panels:
            # Placeholder for section panel rendering
            panel = tb.Frame(self._content_frm)
            tb.Label(panel, text=f"Rendering {sec['tieu_de']}", font=('Arial', 14)).pack(pady=20)
            self._panels[sec_id] = panel
            
        self._panels[sec_id].pack(fill='both', expand=True)

    def load(self, hp_id):
        self.ensure_ui()
        self.hp_id = hp_id
        # Reload panel data here based on hp_id

    def destroy(self):
        self._bus.unsubscribe('schema.changed',  self._on_schema_event)
        self._bus.unsubscribe('section.changed', self._on_schema_event)
        self._bus.unsubscribe('field.changed',   self._on_field_event)
        super().destroy()
