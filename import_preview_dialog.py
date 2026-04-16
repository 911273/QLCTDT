import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from sections.base_section import make_tree, set_window_icon

class ImportPreviewDialog(tb.Toplevel):
    def __init__(self, parent, preview_items):
        """
        Args:
            parent: Cửa sổ cha
            preview_items: List các dict {file_name, data, status, existing_hp, selected, error}
        """
        super().__init__(parent)
        set_window_icon(self)
        self.title("Xem trước dữ liệu Nhập từ Word")
        self.geometry("1000x650")
        self.preview_items = preview_items
        self.result = None # List of selected items if confirmed
        
        self.grab_set()
        self._build_ui()
        self._populate_tree()
        self.transient(parent)

    def _build_ui(self):
        main_frame = tb.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=YES)

        # Header info
        total = len(self.preview_items)
        errors = len([i for i in self.preview_items if i['status'] == 'ERROR'])
        updates = len([i for i in self.preview_items if i['status'] == 'UPDATE'])
        news = len([i for i in self.preview_items if i['status'] == 'NEW'])

        header_lbl = tb.Label(
            main_frame, 
            text=f"Tìm thấy {total} học phần. (Mới: {news}, Cập nhật: {updates}, Lỗi: {errors})",
            font=("Arial", 11, "bold")
        )
        header_lbl.pack(anchor=W, pady=(0, 10))

        # Explanation
        info_lbl = tb.Label(
            main_frame,
            text="Chọn các học phần bạn muốn lưu vào cơ sở dữ liệu. Lưu ý: 'Cập nhật' sẽ ghi đè dữ liệu cũ.",
            font=("Arial", 9, "italic"),
            foreground="gray"
        )
        info_lbl.pack(anchor=W, pady=(0, 5))

        # Treeview
        cols = ("select", "file_name", "ma_hp", "ten_hp", "status")
        heads = ("Chọn", "Tên file", "Mã học phần", "Tên học phần", "Trạng thái")
        widths = (60, 200, 120, 350, 120)

        # We use a custom tree for checkboxes or just text 'X' for now
        self.tree_frame, self.tree = make_tree(
            main_frame, cols, heads, widths, height=15
        )
        self.tree_frame.pack(fill=BOTH, expand=YES)

        # Setup tags for coloring
        self.tree.tag_configure("NEW", foreground="green")
        self.tree.tag_configure("UPDATE", foreground="orange")
        self.tree.tag_configure("ERROR", foreground="red")

        # Select all / Deselect all
        action_fm = tb.Frame(main_frame)
        action_fm.pack(fill=X, pady=10)
        
        tb.Button(action_fm, text="Chọn tất cả", bootstyle=OUTLINE, command=self._select_all).pack(side=LEFT, padx=5)
        tb.Button(action_fm, text="Bỏ chọn tất cả", bootstyle=OUTLINE, command=self._deselect_all).pack(side=LEFT, padx=5)

        # Bottom buttons
        btn_fm = tb.Frame(main_frame)
        btn_fm.pack(fill=X, side=BOTTOM, pady=(10, 0))

        self.btn_confirm = tb.Button(
            btn_fm, text="✔ Xác nhận Nhập", bootstyle=SUCCESS, command=self._on_confirm
        )
        self.btn_confirm.pack(side=RIGHT, padx=5)

        tb.Button(
            btn_fm, text="✖ Hủy bỏ", bootstyle=DANGER, command=self.destroy
        )
        self.btn_confirm.pack(side=RIGHT, padx=5) # wait, fix duplicate export logic later
        
        # Binding for selection
        self.tree.bind("<Button-1>", self._on_click)

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self.preview_items):
            status_text = item['status']
            if status_text == 'UPDATE':
                status_text = "Cập nhật"
            elif status_text == 'NEW':
                status_text = "Mới"
            elif status_text == 'ERROR':
                status_text = "Lỗi"
            
            check_mark = " [X] " if item.get('selected') else " [  ] "
            ma = item['data']['thong_tin'].get('ma', '') if 'data' in item else ''
            ten = item['data'].get('ten_viet', '') if 'data' in item else item.get('file_name', '')
            
            self.tree.insert(
                "", END, iid=str(i),
                values=(check_mark, item['file_name'], ma, ten, status_text),
                tags=(item['status'],)
            )

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1": # 'Select' column
                item_id = self.tree.identify_row(event.y)
                if item_id:
                    idx = int(item_id)
                    # Toggle selection
                    self.preview_items[idx]['selected'] = not self.preview_items[idx]['selected']
                    # Don't allow selecting errors
                    if self.preview_items[idx]['status'] == 'ERROR':
                        self.preview_items[idx]['selected'] = False
                    
                    self._populate_tree()

    def _select_all(self):
        for item in self.preview_items:
            if item['status'] != 'ERROR':
                item['selected'] = True
        self._populate_tree()

    def _deselect_all(self):
        for item in self.preview_items:
            item['selected'] = False
        self._populate_tree()

    def _on_confirm(self):
        # Filter only selected
        self.result = [item for item in self.preview_items if item.get('selected')]
        self.destroy()
