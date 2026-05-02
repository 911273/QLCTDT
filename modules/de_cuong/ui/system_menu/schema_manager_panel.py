# modules/de_cuong/ui/system_menu/schema_manager_panel.py
import tkinter as tk
from tkinter import messagebox, colorchooser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json

from core.event_bus import EventBus
from modules.de_cuong.ui.system_menu.form_dialogs import _SimpleInputDialog

FIELD_TYPES = [
    ('text',        '📝 Văn bản 1 dòng'),
    ('textarea',    '📄 Văn bản nhiều dòng'),
    ('number',      '🔢 Số'),
    ('dropdown',    '▼ Danh sách chọn 1'),
    ('multiselect', '☰ Danh sách chọn nhiều'),
    ('date',        '📅 Ngày tháng'),
    ('table',       '⊞ Bảng dữ liệu'),
    ('relation',    '🔗 Liên kết bảng khác'),
    ('calculated',  '⚡ Tính tự động'),
    ('richtext',    '✍ Văn bản rich text'),
    ('file',        '📎 Đính kèm file'),
]

class SchemaManagerPanel(tb.Frame):
    """Panel quản trị Schema với Treeview bên trái và Property Grid bên phải."""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self._db = db.dc_bridge
        self._bus = EventBus.get()
        
        self._schemas = []
        self._sections_map = {}
        self._fields_map = {}
        
        self._current_node = None
        self._prop_vars = {}
        
        self._build_ui()
        self.reload_tree()

    def _build_ui(self):
        # Toolbar
        toolbar = tb.Frame(self, padding=(4, 4))
        toolbar.pack(fill='x')
        
        tb.Button(toolbar, text='➕ Mẫu mới', bootstyle='success', command=self._cmd_add_schema).pack(side='left', padx=2)
        tb.Button(toolbar, text='➕ Mục (Section)', bootstyle='primary-outline', command=self._cmd_add_section).pack(side='left', padx=2)
        tb.Button(toolbar, text='➕ Trường (Field)', bootstyle='primary-outline', command=self._cmd_add_field).pack(side='left', padx=2)
        tb.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=6)
        tb.Button(toolbar, text='⭐ Set Default', bootstyle='warning-outline', command=self._cmd_set_default).pack(side='left', padx=2)
        tb.Button(toolbar, text='📋 Copy Mẫu', bootstyle='info-outline', command=self._cmd_clone_schema).pack(side='left', padx=2)
        tb.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=6)
        tb.Button(toolbar, text='🗑 Xóa', bootstyle='danger-outline', command=self._cmd_delete).pack(side='left', padx=2)
        
        # PanedWindow
        paned = tb.Panedwindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True, pady=(4,0))
        
        # Left: Tree
        left = tb.Frame(paned, width=350)
        paned.add(left, weight=1)
        
        self._tree = tb.Treeview(left, show='tree', selectmode='browse')
        vsb = tb.Scrollbar(left, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        
        self._tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        
        # Right: Property Grid
        self._right = tb.Frame(paned)
        paned.add(self._right, weight=2)
        
        self._lbl_prop_title = tb.Label(self._right, text='Chọn một mục trong cây để xem đặc tính', font=('Arial', 12, 'bold'))
        self._lbl_prop_title.pack(anchor='w', pady=(0, 10))
        
        # Canvas + Scrollbar for properties
        sf = tb.Frame(self._right)
        sf.pack(fill='both', expand=True)
        self._prop_canvas = tk.Canvas(sf, highlightthickness=0)
        self._prop_vsb = tb.Scrollbar(sf, orient="vertical", command=self._prop_canvas.yview)
        self._prop_frame = tb.Frame(self._prop_canvas)
        
        self._prop_frame.bind("<Configure>", lambda e: self._prop_canvas.configure(scrollregion=self._prop_canvas.bbox("all")))
        self._prop_canvas.create_window((0, 0), window=self._prop_frame, anchor="nw", width=self._prop_canvas.winfo_reqwidth())
        self._prop_canvas.bind("<Configure>", lambda e: self._prop_canvas.itemconfig(self._prop_canvas.find_withtag("all")[0], width=e.width))
        
        self._prop_canvas.configure(yscrollcommand=self._prop_vsb.set)
        self._prop_canvas.pack(side="left", fill="both", expand=True)
        self._prop_vsb.pack(side="right", fill="y")
        
        # Save button for properties
        bf = tb.Frame(self._right)
        bf.pack(fill='x', pady=10)
        tb.Button(bf, text='💾 Lưu Thay Đổi', bootstyle='success', command=self._save_properties).pack(side='right')

    def reload_tree(self):
        sel = self._tree.selection()
        sel_id = sel[0] if sel else None
        
        self._tree.delete(*self._tree.get_children())
        self._schemas = self._db.list_schemas()
        
        for s in self._schemas:
            sid = s['id']
            s_node = f"schema_{sid}"
            star = "⭐ " if s.get('is_default') else ""
            lock = " 🔒" if s.get('is_locked') else ""
            text = f"📐 {star}{s['ten_mau']} (v{s.get('phien_ban', '1.0')}){lock}"
            
            self._tree.insert('', 'end', iid=s_node, text=text, open=True)
            
            sections = self._db.list_sections_all(sid)
            self._sections_map[sid] = sections
            for sec in sections:
                sec_id = sec['id']
                sec_node = f"section_{sec_id}"
                vis = "" if sec.get('is_visible') else " [ẩn]"
                icon = sec.get('icon', '📋')
                text_sec = f"{icon} {sec['tieu_de']}{vis}"
                
                self._tree.insert(s_node, 'end', iid=sec_node, text=text_sec, open=False)
                
                fields = self._db.list_field_defs_all(sec_id)
                self._fields_map[sec_id] = fields
                for f in fields:
                    f_id = f['id']
                    f_node = f"field_{f_id}"
                    bb = "*" if f.get('bat_buoc') else ""
                    del_ = " [đã xóa]" if f.get('deleted_at') else ""
                    f_icon = '📝'
                    for v, l in FIELD_TYPES:
                        if v == f.get('kieu_du_lieu'):
                            f_icon = l.split()[0]
                            break
                    text_f = f"{f_icon} {f['nhan']}{bb}{del_}"
                    self._tree.insert(sec_node, 'end', iid=f_node, text=text_f)
                    
        if sel_id and self._tree.exists(sel_id):
            self._tree.selection_set(sel_id)
            self._tree.see(sel_id)
            
    def _on_tree_select(self, event):
        sel = self._tree.selection()
        if not sel: return
        node_id = sel[0]
        self._current_node = node_id
        
        for widget in self._prop_frame.winfo_children():
            widget.destroy()
        self._prop_vars.clear()
            
        parts = node_id.split('_')
        ntype = parts[0]
        real_id = int(parts[1])
        
        if ntype == 'schema':
            schema = next((s for s in self._schemas if s['id'] == real_id), None)
            if schema:
                self._lbl_prop_title.config(text=f"Thuộc tính Mẫu: {schema['ten_mau']}")
                self._render_schema_props(schema)
        elif ntype == 'section':
            # find section
            section = None
            for slist in self._sections_map.values():
                for s in slist:
                    if s['id'] == real_id:
                        section = s
                        break
            if section:
                self._lbl_prop_title.config(text=f"Thuộc tính Mục: {section['tieu_de']}")
                self._render_section_props(section)
        elif ntype == 'field':
            field = None
            for flist in self._fields_map.values():
                for f in flist:
                    if f['id'] == real_id:
                        field = f
                        break
            if field:
                self._lbl_prop_title.config(text=f"Thuộc tính Trường: {field['nhan']}")
                self._render_field_props(field)

    def _add_prop_row(self, label_text, widget_type, key, default_val, options=None):
        row = tb.Frame(self._prop_frame)
        row.pack(fill='x', pady=4)
        tb.Label(row, text=label_text, width=20, anchor='w').pack(side='left', padx=(0,10))
        
        if widget_type == 'entry':
            v = tk.StringVar(value=str(default_val))
            tb.Entry(row, textvariable=v).pack(side='left', fill='x', expand=True)
            self._prop_vars[key] = ('entry', v)
        elif widget_type == 'check':
            v = tk.BooleanVar(value=bool(default_val))
            tb.Checkbutton(row, variable=v, bootstyle='round-toggle').pack(side='left')
            self._prop_vars[key] = ('check', v)
        elif widget_type == 'combo':
            v = tk.StringVar(value=str(default_val))
            tb.Combobox(row, textvariable=v, values=options, state='readonly').pack(side='left', fill='x', expand=True)
            self._prop_vars[key] = ('combo', v)
        elif widget_type == 'text':
            t = tk.Text(row, height=4, wrap='word')
            if isinstance(default_val, (dict, list)):
                t.insert('1.0', json.dumps(default_val, ensure_ascii=False))
            else:
                t.insert('1.0', str(default_val))
            t.pack(side='left', fill='x', expand=True)
            self._prop_vars[key] = ('text', t)
        elif widget_type == 'color':
            v = tk.StringVar(value=str(default_val))
            ent = tb.Entry(row, textvariable=v, width=12)
            ent.pack(side='left')
            lbl = tk.Label(row, bg=default_val, width=4)
            lbl.pack(side='left', padx=4)
            def pick():
                c = colorchooser.askcolor(color=v.get() or '#4A90D9', parent=self)
                if c and c[1]:
                    v.set(c[1])
                    lbl.config(bg=c[1])
            tb.Button(row, text='...', command=pick).pack(side='left')
            self._prop_vars[key] = ('entry', v)

    def _render_schema_props(self, s):
        self._add_prop_row('Tên mẫu (*)', 'entry', 'ten_mau', s.get('ten_mau',''))
        self._add_prop_row('Trình độ', 'combo', 'trinh_do', s.get('trinh_do','dai_hoc'), ['dai_hoc','cao_dang','sau_dh','khac'])
        self._add_prop_row('Năm ban hành', 'entry', 'nam_ban_hanh', s.get('nam_ban_hanh','2026'))
        self._add_prop_row('Phiên bản', 'entry', 'phien_ban', s.get('phien_ban','1.0'))
        self._add_prop_row('Thứ tự hiển thị', 'entry', 'thu_tu', s.get('thu_tu',0))
        self._add_prop_row('Khóa (Locked)', 'check', 'is_locked', s.get('is_locked',0))
        self._add_prop_row('Mô tả', 'text', 'mo_ta', s.get('mo_ta',''))

    def _render_section_props(self, sec):
        self._add_prop_row('Tiêu đề (*)', 'entry', 'tieu_de', sec.get('tieu_de',''))
        self._add_prop_row('Mã mục DB (*)', 'entry', 'ma_muc', sec.get('ma_muc',''))
        self._add_prop_row('Icon', 'entry', 'icon', sec.get('icon','📋'))
        self._add_prop_row('Color Tag', 'color', 'color_tag', sec.get('color_tag','#4A90D9'))
        self._add_prop_row('Loại mục', 'combo', 'loai', sec.get('loai','standard'), ['standard','table','repeatable'])
        self._add_prop_row('Bắt buộc', 'check', 'is_required', sec.get('is_required',1))
        self._add_prop_row('Hiển thị', 'check', 'is_visible', sec.get('is_visible',1))
        self._add_prop_row('Khóa (Locked)', 'check', 'is_locked', sec.get('is_locked',0))
        self._add_prop_row('Thứ tự hiển thị', 'entry', 'so_thu_tu', sec.get('so_thu_tu',0))
        self._add_prop_row('Mô tả', 'text', 'mo_ta', sec.get('mo_ta',''))

    def _render_field_props(self, f):
        self._add_prop_row('Nhãn hiển thị (*)', 'entry', 'nhan', f.get('nhan',''))
        self._add_prop_row('Tên trường DB (*)', 'entry', 'ma_truong', f.get('ma_truong',''))
        self._add_prop_row('Kiểu dữ liệu', 'combo', 'kieu_du_lieu', f.get('kieu_du_lieu','text'), [k for k,_ in FIELD_TYPES])
        self._add_prop_row('Placeholder', 'entry', 'placeholder', f.get('placeholder',''))
        self._add_prop_row('Giá trị mặc định', 'entry', 'gia_tri_mac_dinh', f.get('gia_tri_mac_dinh',''))
        self._add_prop_row('Nhóm hiển thị', 'entry', 'nhom_hien_thi', f.get('nhom_hien_thi',''))
        self._add_prop_row('Tooltip', 'entry', 'tooltip', f.get('tooltip',''))
        self._add_prop_row('Độ rộng (%)', 'entry', 'width_hint', f.get('width_hint',100))
        self._add_prop_row('Bắt buộc', 'check', 'bat_buoc', f.get('bat_buoc',0))
        self._add_prop_row('Hiển thị', 'check', 'is_visible', f.get('is_visible',1))
        self._add_prop_row('Thứ tự hiển thị', 'entry', 'so_thu_tu', f.get('so_thu_tu',0))
        self._add_prop_row('Options JSON\n(Mỗi dòng 1 giá trị)', 'text', 'options_json', '\n'.join(json.loads(f.get('options_json','[]'))) if isinstance(f.get('options_json'), str) and f.get('options_json').startswith('[') else f.get('options_json',''))
        self._add_prop_row('Validation JSON', 'text', 'validation_json', f.get('validation_json','{}'))
        self._add_prop_row('Điều kiện hiển thị JSON', 'text', 'dieu_kien_json', f.get('dieu_kien_json','{}'))

    def _save_properties(self):
        if not self._current_node: return
        
        parts = self._current_node.split('_')
        ntype = parts[0]
        real_id = int(parts[1])
        
        data = {}
        for key, (wtype, var) in self._prop_vars.items():
            if wtype == 'text':
                val = var.get('1.0', 'end').strip()
                if key == 'options_json':
                    if val and not val.startswith('['):
                        opts = [v.strip() for v in val.splitlines() if v.strip()]
                        val = json.dumps(opts, ensure_ascii=False)
                elif key.endswith('_json'):
                    if not val: val = '{}'
                data[key] = val
            elif wtype == 'check':
                data[key] = int(var.get())
            else:
                data[key] = var.get()
                
        if ntype == 'schema':
            self._db.update_schema(real_id, data)
            self._bus.emit('schema.changed', schema_id=real_id)
        elif ntype == 'section':
            self._db.update_section(real_id, data)
            schema_id = None
            for s in self._schemas:
                if any(x['id'] == real_id for x in self._sections_map.get(s['id'], [])):
                    schema_id = s['id']
                    break
            self._bus.emit('section.changed', schema_id=schema_id)
        elif ntype == 'field':
            self._db.update_field_def(real_id, data)
            sec_id = None
            schema_id = None
            for sid, flist in self._fields_map.items():
                if any(x['id'] == real_id for x in flist):
                    sec_id = sid
                    break
            if sec_id:
                for s in self._schemas:
                    if any(x['id'] == sec_id for x in self._sections_map.get(s['id'], [])):
                        schema_id = s['id']
                        break
            self._bus.emit('field.changed', section_id=sec_id, schema_id=schema_id)
            
        messagebox.showinfo('Thành công', 'Đã lưu thay đổi!')
        self.reload_tree()

    # --- Actions ---
    def _cmd_add_schema(self):
        new_id = self._db.create_schema({'ten_mau': 'Mẫu mới'})
        self.reload_tree()
        self._bus.emit('schema.changed', schema_id=new_id)
        
    def _cmd_add_section(self):
        if not self._current_node or not self._current_node.startswith('schema_'):
            messagebox.showwarning('Chú ý', 'Vui lòng chọn một Mẫu (Schema) trên cây để thêm Mục.')
            return
        schema_id = int(self._current_node.split('_')[1])
        new_id = self._db.create_section(schema_id, {'tieu_de': 'Mục mới', 'ma_muc': 'muc_moi'})
        self.reload_tree()
        self._bus.emit('section.changed', schema_id=schema_id)
        
    def _cmd_add_field(self):
        if not self._current_node or not self._current_node.startswith('section_'):
            messagebox.showwarning('Chú ý', 'Vui lòng chọn một Mục (Section) trên cây để thêm Trường.')
            return
        sec_id = int(self._current_node.split('_')[1])
        new_id = self._db.create_field_def(sec_id, {'nhan': 'Trường mới', 'ma_truong': 'truong_moi', 'kieu_du_lieu': 'text'})
        self.reload_tree()
        self._bus.emit('field.changed', section_id=sec_id)
        
    def _cmd_set_default(self):
        if not self._current_node or not self._current_node.startswith('schema_'):
            messagebox.showwarning('Chú ý', 'Vui lòng chọn một Mẫu (Schema).')
            return
        schema_id = int(self._current_node.split('_')[1])
        self._db.set_default_schema(schema_id)
        self.reload_tree()
        self._bus.emit('schema.changed', schema_id=schema_id)
        messagebox.showinfo('Thành công', 'Đã đặt làm mẫu mặc định!')
        
    def _cmd_clone_schema(self):
        if not self._current_node or not self._current_node.startswith('schema_'):
            messagebox.showwarning('Chú ý', 'Vui lòng chọn một Mẫu (Schema).')
            return
        schema_id = int(self._current_node.split('_')[1])
        dlg = _SimpleInputDialog(self, 'Copy Mẫu', 'Tên mẫu mới:', 'Mẫu copy')
        if dlg.result:
            new_id = self._db.clone_schema(schema_id, dlg.result)
            self.reload_tree()
            self._bus.emit('schema.changed', schema_id=new_id)

    def _cmd_delete(self):
        if not self._current_node: return
        parts = self._current_node.split('_')
        ntype = parts[0]
        real_id = int(parts[1])
        
        if not messagebox.askyesno('Xác nhận', f"Bạn có chắc muốn xóa {ntype} này?"):
            return
            
        if ntype == 'schema':
            self._db.delete_schema(real_id)
            self._bus.emit('schema.changed', schema_id=None)
        elif ntype == 'section':
            self._db.delete_section(real_id)
            self._bus.emit('section.changed', schema_id=None)
        elif ntype == 'field':
            self._db.soft_delete_field_def(real_id)
            self._bus.emit('field.changed', section_id=None)
            
        self._current_node = None
        for widget in self._prop_frame.winfo_children(): widget.destroy()
        self._lbl_prop_title.config(text="Chọn một mục trong cây để xem đặc tính")
        self.reload_tree()

class SchemaManagerDialog(tb.Toplevel):
    """Cửa sổ độc lập (Toplevel) bọc SchemaManagerPanel."""
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("📐 Quản lý Mẫu đề cương (Schema)")
        self.geometry("1100x650")
        self.minsize(900, 500)
        self.transient(parent)
        self.grab_set()

        panel = SchemaManagerPanel(self, db)
        panel.pack(fill='both', expand=True, padx=10, pady=10)
