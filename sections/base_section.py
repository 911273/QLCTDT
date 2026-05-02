import tkinter as tk
from utils.ui_utils import (show_modern_info, show_modern_warning, 
                             show_modern_error, ask_modern_yesno)
try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *
    HAS_TTKBOOTSTRAP = True
except ImportError:
    from tkinter import ttk as tb
    HAS_TTKBOOTSTRAP = False
import os
import ctypes

def set_window_icon(window):
    """Thiết lập logo cho cửa sổ."""
    try:
        # AppUserModelID để hiện icon trên taskbar Windows
        myappid = 'epu.qlctdt.v1.4'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass
        
    try:
        # Đường dẫn icon
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(current_dir, 'assets', 'logo.ico')
        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
    except Exception as e:
        print(f"Không thể đặt icon: {e}")

# ─── Màu sắc chủ đề ───────────────────────────────────────────────────────────
# Các biến màu sắc sẽ được cập nhật động bởi ThemeManager
CLR_BG      = '#FAFAFA'
CLR_PRIMARY = '#0F172A'
CLR_PRIMARY2= '#334155'
CLR_ACCENT  = '#EF4444'
CLR_TEXT    = '#0F172A'
CLR_BORDER  = '#E2E8F0'
CLR_ROW1    = '#FFFFFF'
CLR_ROW2    = '#F8FAFC'
CLR_HDR     = '#365A7C'
CLR_SIDEBAR = '#F8FAFC'
CLR_SIDEBAR_FG = '#0F172A'
CLR_SIDEBAR_SEL = '#E2E8F0'

THEMES = {
    'light': {
        'BG': '#FFFFFF', 'PRIMARY': '#0F172A', 'PRIMARY2': '#334155',
        'ACCENT': '#EF4444', 'TEXT': '#1E293B', 'BORDER': '#E2E8F0',
        'ROW1': '#FFFFFF', 'ROW2': '#F1F5F9', 'HDR': '#334155',
        'SIDEBAR': '#F8FAFC', 'SIDEBAR_FG': '#334155', 'SIDEBAR_SEL': '#CBD5E1'
    },
    'dark': {
        'BG': '#1E1E1E', 'PRIMARY': '#337AB7', 'PRIMARY2': '#5BC0DE',
        'ACCENT': '#D9534F', 'TEXT': '#E0E0E0', 'BORDER': '#444444',
        'ROW1': '#2D2D2D', 'ROW2': '#252525', 'HDR': '#2B4B69',
        'SIDEBAR': '#1A1A1A', 'SIDEBAR_FG': '#E0E0E0', 'SIDEBAR_SEL': '#337AB7'
    }
}

CURRENT_THEME = 'light'

def apply_theme(theme_name):
    """Cập nhật các biến màu sắc toàn cục theo theme."""
    global CLR_BG, CLR_PRIMARY, CLR_PRIMARY2, CLR_ACCENT, CLR_TEXT, \
           CLR_BORDER, CLR_ROW1, CLR_ROW2, CLR_HDR, CURRENT_THEME, \
           CLR_SIDEBAR, CLR_SIDEBAR_FG, CLR_SIDEBAR_SEL
    
    if theme_name not in THEMES: theme_name = 'dark'
    CURRENT_THEME = theme_name
    colors = THEMES[theme_name]
    
    CLR_BG      = colors['BG']
    CLR_PRIMARY = colors['PRIMARY']
    CLR_PRIMARY2= colors['PRIMARY2']
    CLR_ACCENT  = colors['ACCENT']
    CLR_TEXT    = colors['TEXT']
    CLR_BORDER  = colors['BORDER']
    CLR_ROW1    = colors['ROW1']
    CLR_ROW2    = colors['ROW2']
    CLR_HDR     = colors['HDR']
    CLR_SIDEBAR = colors['SIDEBAR']
    CLR_SIDEBAR_FG = colors['SIDEBAR_FG']
    CLR_SIDEBAR_SEL = colors['SIDEBAR_SEL']
    
    # Cấu hình lại Style nếu không dùng ttkbootstrap Window trực tiếp
    style = tb.Style()
    if HAS_TTKBOOTSTRAP:
        # dark theme của ta tương ứng darkly, light tương ứng litera
        tb_theme = 'darkly' if theme_name == 'dark' else 'litera'
        style.theme_use(tb_theme)
        # Thiết lập font chữ Arial 10 đồng nhất toàn hệ thống
        style.configure('.', font=('Arial', 10))
    
    setup_treeview_style()


# ─── ScrollableFrame ──────────────────────────────────────────────────────────
class ScrollableFrame(tb.Frame):
    """Frame cuộn dọc."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0,
                                background=CLR_BG)
        sb = tb.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner = tb.Frame(self.canvas, style='Inner.TFrame')
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')

        self.inner.bind('<Configure>', self._on_inner_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=sb.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        
        # Chỉ kích hoạt cuộn khi chuột nằm trong canvas này
        self.canvas.bind('<Enter>', lambda _: self.canvas.bind_all('<MouseWheel>', self._on_mousewheel))
        self.canvas.bind('<Leave>', lambda _: self.canvas.unbind_all('<MouseWheel>'))

    def update_theme(self):
        """Cập nhật màu sắc cho canvas và frame bên trong."""
        self.canvas.configure(background=CLR_BG)
        self.inner.configure(style='Inner.TFrame')

    def _on_inner_configure(self, _e):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._win, width=e.width)

    def _on_mousewheel(self, e):
        try:
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
        except:
            pass


# ─── BaseSection ──────────────────────────────────────────────────────────────
class BaseSection(tb.Frame):
    """Base cho tất cả section tab."""
    def __init__(self, parent, db, lazy=False, modified_callback=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.db  = db
        self.hp_id = None
        self.modified_callback = modified_callback
        self.is_modified = False
        self.configure(padding=0)
        self._ui_built = False
        self._field_registry = {}  # Cho Inline CRUD

        if not lazy:
            self.ensure_ui()

    def ensure_ui(self):
        if not self._ui_built:
            self._build_ui()
            self._ui_built = True
            
            # Tự động nạp các trường bổ sung (Inline CRUD)
            self._render_extra_fields()
            
            # Gọi hàm áp dụng giao diện tùy biến (từ DB) sau khi build UI
            if hasattr(self, 'apply_customization'):
                try:
                    self.apply_customization()
                except Exception as e:
                    print(f"Lỗi apply_customization: {e}")

    def _build_ui(self):
        pass

    def mark_modified(self):
        """Đánh dấu section đã bị thay đổi dữ liệu."""
        if not self.is_modified:
            self.is_modified = True
            if self.modified_callback:
                self.modified_callback(self, True)

    def reset_modified(self):
        """Reset trạng thái sau khi lưu."""
        if self.is_modified:
            self.is_modified = False
            if self.modified_callback:
                self.modified_callback(self, False)

    def load(self, hp_id):
        self.ensure_ui()
        self.hp_id = hp_id
        self.is_modified = False # Reset flag on load
        
        # Tự động nạp dữ liệu cho các trường bổ sung
        if hasattr(self, 'db') and self.db:
            extra_vals = self.db.load_extra_data(hp_id, self.section_key)
            if extra_vals:
                self.load_extra_data_dict(extra_vals)

    def save(self):
        pass

    def get_data_dict(self) -> dict:
        """Trả về dictionary chứa dữ liệu của section này."""
        return {}

    def apply_data_dict(self, data: dict):
        """Nạp dữ liệu từ một dictionary (dùng cho recovery hoặc clone)."""
        self.ensure_ui() # FIXED: Ensure UI built before access

    def get_extra_data_dict(self) -> dict:
        """Trích xuất dữ liệu từ các trường bổ sung."""
        data = {}
        for fkey, info in self._field_registry.items():
            if str(fkey).startswith('extra_'):
                w = info.get('input_widget')
                if not w: continue
                import tkinter as tk
                if isinstance(w, tk.Text):
                    data[fkey] = w.get('1.0', 'end-1c').strip()
                elif hasattr(w, 'treeview'): # It's a table wrapper
                    rows = []
                    tv = w.treeview
                    cols = tv.cget('columns')
                    for item in tv.get_children():
                        rows.append(dict(zip(cols, tv.item(item, 'values'))))
                    data[fkey] = rows
                elif hasattr(w, 'get'):
                    data[fkey] = w.get()
        return data

    def load_extra_data_dict(self, data: dict):
        """Nạp dữ liệu vào các trường bổ sung."""
        self.ensure_ui()
        for fkey, val in data.items():
            info = self._field_registry.get(fkey)
            if not info: continue
            w = info.get('input_widget')
            if not w: continue
            import tkinter as tk
            import json
            if isinstance(w, tk.Text):
                w.delete('1.0', 'end')
                w.insert('1.0', str(val))
            elif hasattr(w, 'treeview'):
                tv = w.treeview
                for item in tv.get_children(): tv.delete(item)
                if isinstance(val, str):
                    try: val = json.loads(val)
                    except: val = []
                if isinstance(val, list):
                    for row_dict in val:
                        cols = tv.cget('columns')
                        vals = [row_dict.get(c, '') for c in cols]
                        tv.insert('', 'end', values=vals)
            elif hasattr(w, 'set'):
                w.set(str(val))
            elif hasattr(w, 'delete') and hasattr(w, 'insert'):
                w.delete(0, 'end')
                w.insert(0, str(val))

    def auto_track_vars(self, *vars):
        """Tự động gọi mark_modified khi bất kỳ biến nào thay đổi."""
        for v in vars:
            v.trace_add('write', lambda *_: self.mark_modified())

    def clear(self):
        self.hp_id = None
        self.is_modified = False

    def update_theme(self):
        """Tự động cập nhật theme cho các widget con có hỗ trợ."""
        if not self._ui_built: return # FIXED: Skip if UI not yet built (lazy load)
        for child in self.winfo_children():
            if hasattr(child, 'update_theme'):
                child.update_theme()

    # ── INLINE CRUD ───────────────────────────────────────────────────────

    def _register_field(self, field_key: str, label_widget=None, input_widget=None, frame=None):
        """Gọi từ các section con khi tạo widget."""
        self._field_registry[field_key] = {
            'label_widget': label_widget,
            'input_widget':  input_widget,
            'frame':         frame or (label_widget.master if label_widget else None)
        }
        if label_widget and not hasattr(label_widget, '_original_text'):
            try:
                label_widget._original_text = label_widget.cget('text')
            except Exception:
                label_widget._original_text = ''

    @property
    def section_key(self) -> str:
        return type(self).__module__.split('.')[-1]

    def apply_customization(self):
        """Áp dụng nhãn tùy biến, ẩn/hiện và thứ tự từ DB."""
        if not hasattr(self, 'db') or not self.db:
            return
        meta = self.db.get_field_meta(self.section_key)
        if not meta:
            return

        # 1. Thu thập và sắp xếp các trường theo thứ tự (thu_tu)
        items = []
        for fkey, info in self._field_registry.items():
            m = meta.get(fkey, {})
            order = m.get('thu_tu', 999)
            items.append((order, fkey, info, m))
        
        # Sắp xếp theo thu_tu
        items.sort(key=lambda x: x[0])

        # 2. Áp dụng thay đổi
        for _, fkey, info, m in items:
            # Đổi nhãn
            lbl = info.get('label_widget')
            if lbl:
                new_nhan = m.get('nhan_tuy_bien')
                if new_nhan:
                    try: lbl.config(text=new_nhan)
                    except: pass
                else:
                    # Reset về nhãn gốc nếu không có tùy biến
                    orig = getattr(lbl, '_original_text', None)
                    if orig:
                        try: lbl.config(text=orig)
                        except: pass

            # Ẩn/Hiện và Thứ tự
            frm = info.get('frame')
            if frm:
                if m.get('an_truong'):
                    try:
                        frm.pack_forget()
                        frm.grid_remove()
                    except: pass
                else:
                    # Đưa về hiển thị nếu đang bị ẩn (dùng pack mặc định)
                    try:
                        if frm.winfo_manager() == '':
                            frm.pack(side='top', fill='x', pady=2)
                        elif frm.winfo_manager() == 'pack':
                            # Re-pack để đảm bảo thứ tự
                            frm.pack(side='top', fill='x')
                    except: pass

    def refresh_from_meta(self):
        """Làm mới toàn bộ giao diện dựa trên cấu hình DB mới nhất."""
        self._render_extra_fields()
        self.apply_customization()

    def _render_extra_fields(self):
        """Vẽ các trường dữ liệu bổ sung."""
        if not hasattr(self, 'db'): return
        extras = self.db.list_extra_fields(self.section_key)
        
        # Dọn dẹp cũ
        for w in getattr(self, '_extra_widgets', []):
            try: w.destroy()
            except: pass
        self._extra_widgets = []
        
        # Xóa các trường extra cũ khỏi registry
        keys_to_remove = [k for k in self._field_registry.keys() if str(k).startswith('extra_')]
        for k in keys_to_remove:
            self._field_registry.pop(k, None)
        
        if not extras: 
            if hasattr(self, '_extra_container'):
                try: self._extra_container.pack_forget()
                except: pass
            return
            
        # Xác định container (ưu tiên self._extra_parent nếu có để hỗ trợ ScrollableFrame)
        parent = getattr(self, '_extra_parent', self)
        
        if not hasattr(self, '_extra_container') or not self._extra_container.winfo_exists():
            self._extra_container = tb.LabelFrame(parent, text='➕ Trường bổ sung')
            self._extra_container.pack(fill='x', padx=16, pady=8)
        else:
            self._extra_container.pack(fill='x', padx=16, pady=8)
            for w in self._extra_container.winfo_children():
                try: w.destroy()
                except: pass
                
        for ef in extras:
            self._render_one_extra(self._extra_container, ef)

    def _render_one_extra(self, parent, ef: dict):
        row = tb.Frame(parent)
        row.pack(fill='x', pady=2)
        lbl = tb.Label(row, text=ef['nhan'] + ('  *' if ef['bat_buoc'] else ''), width=28, anchor='w')
        lbl.pack(side='left')
        
        var = tk.StringVar(value=ef.get('gia_tri_mac_dinh',''))
        kieu = ef.get('kieu','text')
        
        if kieu == 'textarea':
            w = tk.Text(row, height=3, width=40)
            w.insert('1.0', var.get())
            w.pack(side='left', fill='x', expand=True)
        elif kieu == 'dropdown':
            import json
            try: opts = json.loads(ef.get('options_json','[]'))
            except: opts = []
            w = tb.Combobox(row, textvariable=var, values=opts, state='readonly')
            w.pack(side='left', fill='x', expand=True)
        elif kieu == 'table':
            import json
            try: cols = json.loads(ef.get('options_json','[]'))
            except: cols = []
            if not cols: cols = ['Cột 1', 'Cột 2']
            
            # Wrapper frame for the table so we can attach it to _field_registry
            w = tb.Frame(row)
            w.pack(side='left', fill='both', expand=True)
            
            # Treeview sử dụng hàm chuẩn của hệ thống để hỗ trợ căn lề
            table_id = f"ext_{ef['field_key']}"
            tfrm, tv = make_tree(w, columns=cols, headings=cols, height=4, db=self.db, table_id=table_id)
            tfrm.pack(side='left', fill='both', expand=True)
            
            # Nút chức năng
            btn_frm = tb.Frame(w)
            btn_frm.pack(side='left', fill='y', padx=4)
            
            def _add_row():
                top = tk.Toplevel(w)
                top.title("Nhập dữ liệu dòng mới")
                top.geometry("350x300")
                top.transient(w.winfo_toplevel())
                top.grab_set()
                
                entries = []
                for c in cols:
                    f = tb.Frame(top)
                    f.pack(fill='x', padx=10, pady=4)
                    tb.Label(f, text=c, width=15).pack(side='left')
                    e = tb.Entry(f)
                    e.pack(side='left', fill='x', expand=True)
                    entries.append(e)
                    
                def _save_row():
                    vals = [e.get() for e in entries]
                    tv.insert('', 'end', values=vals)
                    top.destroy()
                    
                tb.Button(top, text="Thêm dòng", command=_save_row, bootstyle='success').pack(pady=10)
                if entries: entries[0].focus()
                
            def _del_row():
                for item in tv.selection():
                    tv.delete(item)
                    
            tb.Button(btn_frm, text='+', width=3, command=_add_row, bootstyle='success').pack(pady=2)
            tb.Button(btn_frm, text='-', width=3, command=_del_row, bootstyle='danger').pack(pady=2)
            
            # Save a reference to the treeview inside the wrapper for data extraction later
            w.treeview = tv
        else:
            w = tb.Entry(row, textvariable=var)
            w.pack(side='left', fill='x', expand=True)
            
        self._extra_widgets.append(row)
        self._register_field(ef['field_key'], label_widget=lbl, input_widget=w, frame=row)

# ─── Helpers cho widget ───────────────────────────────────────────────────────
def lbl(parent, text, bold=False, fg=None, size=10, style=None):
    if style:
        return tb.Label(parent, text=text, style=style)
    
    s = 'SubHeader.TLabel' if bold else 'TLabel'
    l = tb.Label(parent, text=text, style=s)
    if fg:
        l.configure(foreground=fg)
    return l


def entry(parent, textvariable=None, width=30, **kw):
    e = tb.Entry(parent, textvariable=textvariable, width=width,
                  font=('Arial', 10), **kw)
    return e


def combo(parent, values, textvariable=None, width=20, **kw):
    c = tb.Combobox(parent, values=values, textvariable=textvariable,
                     width=width, font=('Arial', 10), state='readonly', **kw)
    return c


def btn(parent, text, cmd, style='Primary.TButton', **kw):
    return tb.Button(parent, text=text, command=cmd, style=style, **kw)


def setup_treeview_style():
    """Thiết lập style Treeview chung."""
    style = tb.Style()
    # ttkbootstrap đã có style sẵn cho Treeview, ta chỉ tinh chỉnh
    style.configure('MyTree.Treeview',
                    font=('Arial', 10),
                    rowheight=26)
    style.configure('MyTree.Treeview.Heading',
                    background=CLR_HDR, foreground='white',
                    font=('Arial', 10, 'bold'))
    style.map('MyTree.Treeview', 
              background=[('selected', CLR_PRIMARY)],
              foreground=[('selected', 'white')])


def make_tree(parent, columns, headings, widths=None, show='headings', height=12, column_aligns=None, db=None, table_id=None, undo_manager=None, on_change=None):
    """
    Tạo Treeview chuẩn với scrollbar và hỗ trợ căn lề linh hoạt.
    - undo_manager: Lớp UndoManager để lưu lịch sử.
    - on_change: Callback khi dữ liệu trong tree thay đổi.
    """
    frame = tb.Frame(parent)
    tree = tb.Treeview(frame, columns=columns, show=show,
                        style='MyTree.Treeview', height=height)
    
    # Binding for Undo/Redo
    if undo_manager:
        def _get_tree_state():
            state = []
            for iid in tree.get_children():
                state.append({
                    'iid': iid,
                    'values': tree.item(iid, 'values'),
                    'tags': tree.item(iid, 'tags'),
                    'text': tree.item(iid, 'text')
                })
            return state

        def _apply_tree_state(state):
            if state is None: return
            tree.delete(*tree.get_children())
            for item in state:
                tree.insert("", "end", iid=item['iid'], values=item['values'], tags=item['tags'], text=item['text'])
            if on_change: on_change()

        def _undo(e=None):
            state = undo_manager.undo()
            if state is not None: _apply_tree_state(state)
        
        def _redo(e=None):
            state = undo_manager.redo()
            if state is not None: _apply_tree_state(state)

        tree.bind("<Control-z>", _undo)
        tree.bind("<Control-y>", _redo)
        tree.bind("<Control-Shift-Z>", _redo) # Thêm phím tắt khác cho redo
        
        # Helper to save state before an action
        tree.snapshot = lambda: undo_manager.push(_get_tree_state())

    # Load saved alignments if possible
    saved_aligns = {}
    if db and table_id:
        import json
        cfg_key = f"table_align_{table_id}"
        val = db.get_config(cfg_key)
        if val:
            try: saved_aligns = json.loads(val)
            except: pass

    for i, col in enumerate(columns):
        # 1. Default alignment
        anchor = 'center'
        if column_aligns and i < len(column_aligns):
            anchor = column_aligns[i]
        elif i == 0:
            anchor = 'w'
        
        # 2. Override from saved config
        if col in saved_aligns:
            anchor = saved_aligns[col]
            
        tree.heading(col, text=headings[i], anchor=anchor)
        w = widths[i] if widths else 120
        tree.column(col, width=w, minwidth=50, anchor=anchor, stretch=False)

    # 3. Handle Tree column (#0) if it's shown
    if show == 'tree headings':
        tree.heading('#0', text='')
        if '#0' in saved_aligns:
            tree.column('#0', anchor=saved_aligns['#0'])
            tree.heading('#0', anchor=saved_aligns['#0'])

    def _on_right_click(event):
        region = tree.identify_region(event.x, event.y)
        if region == "heading":
            col_id = tree.identify_column(event.x)
            # col_id is like '#1', '#2'...
            try:
                idx = int(col_id.replace('#', ''))
                if show == 'tree headings':
                    if idx == 0: real_col = '#0'
                    else: real_col = columns[idx-1]
                else:
                    real_col = columns[idx-1]
            except: return

            menu = tk.Menu(tree, tearoff=0)
            def set_align(a):
                tree.column(real_col, anchor=a)
                # Save if we have table_id
                if db and table_id:
                    saved_aligns[real_col] = a
                    import json
                    db.set_config(f"table_align_{table_id}", json.dumps(saved_aligns))
            
            menu.add_command(label="⬅ Căn trái", command=lambda: set_align('w'))
            menu.add_command(label="↔ Căn giữa", command=lambda: set_align('center'))
            menu.add_command(label="➡ Căn phải", command=lambda: set_align('e'))
            menu.post(event.x_root, event.y_root)

    tree.bind("<Button-3>", _on_right_click)

    vsb = tb.Scrollbar(frame, orient='vertical', command=tree.yview)
    hsb = tb.Scrollbar(frame, orient='horizontal', command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    tree.tag_configure('odd',  background=CLR_ROW1, foreground=CLR_TEXT)
    tree.tag_configure('even', background=CLR_ROW2, foreground=CLR_TEXT)
    tree.tag_configure('group', background=CLR_HDR, foreground='white', font=('Arial', 10, 'bold'))
    tree.tag_configure('subgroup', background=CLR_PRIMARY2, foreground='white', font=('Arial', 10, 'bold'))
    tree.tag_configure('accent', foreground=CLR_ACCENT, font=('Arial', 10, 'bold'))
    
    return frame, tree


def recolor_tree(tree):
    """Tô màu xen kẽ sau khi thêm/xóa hàng."""
    for i, iid in enumerate(tree.get_children()):
        tree.item(iid, tags=('even' if i % 2 == 0 else 'odd',))


# ─── Dialog chỉnh sửa hàng bảng ──────────────────────────────────────────────
class RowEditDialog(tb.Toplevel):
    """Dialog nhập/sửa một hàng dữ liệu dạng label:entry."""
    def __init__(self, parent, title, fields, initial=None, on_build=None):
        """
        fields: list of (field_key, label_text, widget_type, opts)
            widget_type: 'entry' | 'text' | 'combo' | 'spin' | 'multi_picker'
            opts: dict (cho combo: values=[...], cho multi_picker: values=[...])
        initial: dict {field_key: value}
        on_build: callback(dlg) to add extra logic/widgets before wait_window
        """
        super().__init__(parent)
        set_window_icon(self)
        self.title(title)
        self.resizable(True, True)
        self.result = None
        self._vars = {}
        self._texts = {}
        self.entries = {}

        self.grab_set()
        self._build(fields, initial or {})
        if on_build:
            on_build(self)
        self.transient(parent)
        self.wait_window()

    def _build(self, fields, initial):
        pad = dict(padx=8, pady=4)
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)
        self.configure(background=CLR_BG)

        for r, (key, label, wtype, opts) in enumerate(fields):
            tb.Label(frm, text=label).grid(
                row=r, column=0, sticky='w', **pad)

            if wtype == 'text':
                txt = tk.Text(frm, width=45, height=4, font=('Arial', 10),
                               wrap='word', background=CLR_ROW1, foreground=CLR_TEXT,
                               insertbackground=CLR_TEXT, borderwidth=1, relief='solid')
                txt.grid(row=r, column=1, sticky='ew', **pad)
                if initial.get(key):
                    txt.insert('1.0', initial[key])
                self._texts[key] = txt
                self.entries[key] = txt
            elif wtype == 'combo':
                var = tk.StringVar(value=str(initial.get(key, '')))
                cb = tb.Combobox(frm, textvariable=var,
                                  values=opts.get('values', []),
                                  width=40, font=('Arial', 10),
                                  state=opts.get('state', 'readonly'))
                cb.grid(row=r, column=1, sticky='ew', **pad)
                self._vars[key] = var
                self.entries[key] = cb
            elif wtype == 'spin':
                var = tk.StringVar(value=str(initial.get(key, opts.get('from_', 0))))
                sp = tb.Spinbox(frm, textvariable=var,
                                 from_=opts.get('from_', 0),
                                 to=opts.get('to', 100),
                                 increment=opts.get('increment', 1),
                                 width=10, font=('Arial', 10))
                sp.grid(row=r, column=1, sticky='w', **pad)
                self._vars[key] = var
                self.entries[key] = sp
            elif wtype == 'multi_picker':
                var = tk.StringVar(value=str(initial.get(key, '')))
                f = tb.Frame(frm)
                f.grid(row=r, column=1, sticky='ew', **pad)
                e = tb.Entry(f, textvariable=var, width=35, font=('Arial', 10), state='readonly')
                e.pack(side='left', fill='x', expand=True)
                # Helper function for closure
                def _open_picker(v=var, ops=opts.get('values', [])):
                    dlg = MultiSelectDialog(self, "Chọn các mục", ops, initial=v.get())
                    if dlg.result is not None:
                        v.set(", ".join(dlg.result))
                
                tb.Button(f, text='...', width=3, command=_open_picker).pack(side='right', padx=(4,0))
                self._vars[key] = var
                self.entries[key] = e
            elif wtype == 'entry_with_btn':
                row_frm = tb.Frame(frm)
                row_frm.grid(row=r, column=1, sticky='ew', **pad)
                var = tk.StringVar(value=str(initial.get(key, '')))
                ent = tb.Entry(row_frm, textvariable=var, font=('Arial', 10))
                ent.pack(side='left', fill='x', expand=True)
                btn_txt = opts.get('btn_text', '...')
                # cmd_key dùng để callback về parent
                cmd_key = opts.get('btn_cmd_key', '')
                tb.Button(row_frm, text=btn_txt, bootstyle='outline-info', padding=2,
                          command=lambda v=var, k=cmd_key: self._handle_btn_cmd(k, v)
                          ).pack(side='left', padx=(4, 0))
                self._vars[key] = var
                self.entries[key] = ent
            else:  # entry
                var = tk.StringVar(value=str(initial.get(key, '')))
                e = tb.Entry(frm, textvariable=var, width=44,
                               font=('Arial', 10))
                e.grid(row=r, column=1, sticky='ew', **pad)
                self._vars[key] = var
                self.entries[key] = e

        frm.columnconfigure(1, weight=1)

        # Buttons
        self.btn_frame = tb.Frame(self, padding=(12, 4, 12, 12))
        self.btn_frame.pack(fill='x')
        tb.Button(self.btn_frame, text='✔ Lưu', command=self._ok).pack(side='right', padx=4)
        tb.Button(self.btn_frame, text='✘ Hủy', command=self.destroy).pack(side='right', padx=4)

    def _ok(self):
        self.result = {}
        for key, var in self._vars.items():
            self.result[key] = var.get().strip()
        for key, txt in self._texts.items():
            self.result[key] = txt.get('1.0', 'end-1c').strip()
        self.destroy()

    def _handle_btn_cmd(self, key, var):
        # Tự động gọi hàm _<key> trên master nếu tồn tại
        method_name = f"_{key}"
        if hasattr(self.master, method_name):
            # Pass cả var và dialog (self) để có thể update nhiều field
            getattr(self.master, method_name)(var, dialog=self)


# ─── Dialog chọn nhiều mục (Checkbox list) ──────────────────────────────────
class MultiSelectDialog(tb.Toplevel):
    def __init__(self, parent, title, options, initial=''):
        """
        options: list of str
        initial: str (comma separated)
        """
        super().__init__(parent)
        set_window_icon(self)
        self.title(title)
        self.geometry('700x600')
        self.grab_set()
        self.result = None
        self.options_list = options
        self._checked_vars = {} # map option -> BooleanVar
        
        # Parse initial
        init_list = [s.strip() for s in initial.split(',') if s.strip()]
        for opt in options:
            self._checked_vars[opt] = tk.BooleanVar(value=(opt in init_list))

        self._build()
        self.transient(parent)
        self.wait_window()

    def _build(self):
        self.configure(background=CLR_BG)
        frm = tb.Frame(self, padding=12)
        frm.pack(fill='both', expand=True)

        # Filter
        tb.Label(frm, text="Tìm kiếm:").pack(anchor='w')
        self.v_filter = tk.StringVar()
        self.v_filter.trace_add("write", lambda *_: self._refresh_list())
        tb.Entry(frm, textvariable=self.v_filter).pack(fill='x', pady=(0, 10))

        # Scrollable list of checkboxes
        self.scroll_frm = ScrollableFrame(frm)
        self.scroll_frm.pack(fill='both', expand=True)
        
        self.check_list_frm = self.scroll_frm.inner
        self._refresh_list()

        # Action bar
        bf = tb.Frame(self, padding=8)
        bf.pack(fill='x')
        tb.Button(bf, text="Chọn tất cả", command=self._select_all).pack(side='left', padx=4)
        tb.Button(bf, text="Bỏ chọn hết", command=self._deselect_all).pack(side='left', padx=4)
        
        tb.Button(bf, text="✔ OK", command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text="Hủy", command=self.destroy).pack(side='right', padx=4)

    def _refresh_list(self):
        # Clear inner frame
        for child in self.check_list_frm.winfo_children():
            child.destroy()
        
        kw = self.v_filter.get().lower()
        for opt in self.options_list:
            if kw in opt.lower():
                cb = tb.Checkbutton(self.check_list_frm, text=opt, variable=self._checked_vars[opt])
                cb.pack(anchor='w', pady=2)

    def _select_all(self):
        kw = self.v_filter.get().lower()
        for opt in self.options_list:
            if kw in opt.lower():
                self._checked_vars[opt].set(True)

    def _deselect_all(self):
        kw = self.v_filter.get().lower()
        for opt in self.options_list:
            if kw in opt.lower():
                self._checked_vars[opt].set(False)

    def _ok(self):
        self.result = [opt for opt in self.options_list if self._checked_vars[opt].get()]
        self.destroy()

def enable_inline_edit(tree, editable_cols, on_change_cb=None):
    """
    Cho phép inline edit các cột được chỉ định trong Treeview.
    
    Args:
        tree: ttk.Treeview widget
        editable_cols: list mã cột có thể sửa, VD: ['hinh_thuc', 'ty_trong']
        on_change_cb: callback(row_id, col_id, new_value) sau khi sửa xong
    """
    _active_editor = {'widget': None}

    def _close_editor(commit=True):
        ed = _active_editor.get('widget')
        if ed and ed.winfo_exists():
            if commit:
                row_id = _active_editor['row_id']
                col_id = _active_editor['col_id']
                new_val = _active_editor['var'].get()
                try:
                    tree.set(row_id, col_id, new_val)
                    if on_change_cb:
                        on_change_cb(row_id, col_id, new_val)
                except Exception:
                    pass
            ed.destroy()
        _active_editor['widget'] = None

    def _on_double_click(event):
        # Đóng editor cũ trước
        _close_editor(commit=True)
        
        region = tree.identify_region(event.x, event.y)
        if region != 'cell':
            return
        
        col = tree.identify_column(event.x)
        col_idx = int(col.replace('#', '')) - 1
        cols = tree['columns']
        if col_idx < 0 or col_idx >= len(cols):
            return
        col_id = cols[col_idx]
        
        if col_id not in editable_cols:
            return
        
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        
        # Lấy bounding box của cell
        bbox = tree.bbox(row_id, col)
        if not bbox:
            return
        x, y, w, h = bbox
        
        var = tk.StringVar(value=tree.set(row_id, col_id))
        
        # Tạo Entry overlay
        entry = tk.Entry(
            tree, textvariable=var,
            font=('Arial', 10),
            relief='flat',
            bd=1,
            highlightthickness=1,
            highlightcolor='#01696f'
        )
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, 'end')
        
        _active_editor.update({
            'widget': entry,
            'row_id': row_id,
            'col_id': col_id,
            'var': var
        })
        
        def _on_tab(e):
            _close_editor(commit=True)
            # Chuyển sang cột kế tiếp có thể edit
            cur_idx = list(cols).index(col_id)
            for next_col in cols[cur_idx+1:]:
                if next_col in editable_cols:
                    bbox2 = tree.bbox(row_id, f'#{list(cols).index(next_col)+1}')
                    if bbox2:
                        # Simulate double click ở vị trí đó
                        tree.event_generate('<Double-1>',
                            x=bbox2[0]+2, y=bbox2[1]+2)
                    break
            return 'break'
        
        entry.bind('<Return>',    lambda e: _close_editor(True))
        entry.bind('<Escape>',    lambda e: _close_editor(False))
        entry.bind('<Tab>',       _on_tab)
        entry.bind('<FocusOut>',  lambda e: _close_editor(True))
    
    def _on_click_outside(event):
        if _active_editor.get('widget'):
            _close_editor(commit=True)
    
    tree.bind('<Double-1>',   _on_double_click)
    tree.bind('<Button-1>',   _on_click_outside)

def enable_drag_reorder(tree, on_reorder_cb=None):
    """
    Cho phép kéo thả để thay đổi thứ tự rows trong Treeview.
    
    Args:
        tree: ttk.Treeview widget
        on_reorder_cb: callback(old_idx, new_idx) sau khi đổi thứ tự
    """
    state = {'drag_item': None, 'drag_start_y': 0}

    def _get_row_center_y(item_id):
        bbox = tree.bbox(item_id)
        if bbox:
            return bbox[1] + bbox[3] // 2
        return 0

    def _on_press(event):
        item = tree.identify_row(event.y)
        if item:
            state['drag_item'] = item
            state['drag_start_y'] = event.y
            tree.configure(cursor='fleur')

    def _on_motion(event):
        if not state['drag_item']:
            return
        target = tree.identify_row(event.y)
        if target and target != state['drag_item']:
            # Visual highlight target row
            tree.selection_set(target)

    def _on_release(event):
        drag_item = state['drag_item']
        if not drag_item:
            return
        tree.configure(cursor='')
        state['drag_item'] = None
        
        target = tree.identify_row(event.y)
        if not target or target == drag_item:
            tree.selection_set(drag_item)
            return
        
        # Lấy vị trí hiện tại
        all_items = tree.get_children()
        old_idx = list(all_items).index(drag_item)
        new_idx = list(all_items).index(target)
        
        # Di chuyển trong tree
        tree.move(drag_item, '', new_idx)
        tree.selection_set(drag_item)
        
        if on_reorder_cb:
            on_reorder_cb(old_idx, new_idx)

    # Thêm tooltip hướng dẫn
    tree._drag_tooltip = None
    
    def _show_drag_hint(event):
        if not tree._drag_tooltip and event.y < 20:
            pass  # Có thể thêm tooltip sau

    tree.bind('<ButtonPress-1>',   _on_press)
    tree.bind('<B1-Motion>',       _on_motion)
    tree.bind('<ButtonRelease-1>', _on_release)
