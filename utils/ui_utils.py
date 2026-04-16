import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *

class AutocompleteCombobox(tb.Combobox):
    """Combobox hỗ trợ tự động gợi ý (Fuzzy Search/Filter)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._all_values = kwargs.get('values', [])
        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<<ComboboxSelected>>', self._on_select)

    def set_completion_list(self, completion_list):
        self._all_values = completion_list
        self['values'] = completion_list

    def _on_keyrelease(self, event):
        if event.keysym in ('BackSpace', 'Left', 'Right', 'Up', 'Down', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R'):
            return
        
        value = self.get().lower()
        if value == '':
            self['values'] = self._all_values
        else:
            data = []
            for item in self._all_values:
                if value in item.lower():
                    data.append(item)
            self['values'] = data
            
        # Tự động mở list
        if self['values']:
            self.event_generate('<Down>')

    def _on_select(self, event):
        # Khi chọn xong, reset list về đầy đủ cho lần sau
        self.root = self.winfo_toplevel()
        self.root.after(100, lambda: self.configure(values=self._all_values))

class TreeviewDND:
    """Helper hỗ trợ kéo thả sắp xếp trong Treeview."""
    def __init__(self, tree, on_drop_callback=None):
        self.tree = tree
        self.on_drop = on_drop_callback
        self.tree.bind("<ButtonPress-1>", self._on_press)
        self.tree.bind("<B1-Motion>", self._on_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_release)
        self._drag_data = {"item": None, "y": 0}

    def _on_press(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item
            self._drag_data["y"] = event.y

    def _on_motion(self, event):
        # Có thể thêm hiệu ứng visual ở đây
        pass

    def _on_release(self, event):
        source = self._drag_data["item"]
        target = self.tree.identify_row(event.y)
        
        if source and target and source != target:
            # Sắp xếp lại trong Treeview
            target_index = self.tree.index(target)
            self.tree.move(source, '', target_index)
            if self.on_drop:
                self.on_drop(source, target)
        
        self._drag_data = {"item": None, "y": 0}

def show_modern_info(parent, title, message):
    from ttkbootstrap.dialogs import Messagebox
    Messagebox.show_info(message, title, parent=parent)

def show_modern_warning(parent, title, message):
    from ttkbootstrap.dialogs import Messagebox
    Messagebox.show_warning(message, title, parent=parent)

def show_modern_error(parent, title, message):
    from ttkbootstrap.dialogs import Messagebox
    Messagebox.show_error(message, title, parent=parent)

def ask_modern_yesno(parent, title, message):
    from ttkbootstrap.dialogs import Messagebox
    return Messagebox.yesno(message, title, parent=parent) == 'Yes'
