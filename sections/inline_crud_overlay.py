# sections/inline_crud_overlay.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb

class InlineCRUDOverlay:
    """
    Toolbar tùy biến nổi (không chiếm diện tích section).
    Kích hoạt khi user bật chế độ "Tùy biến giao diện".
    
    Hoạt động: nhúng 1 thin toolbar phía trên mỗi section.
    Mỗi trường có icon ⚙ nhỏ bên cạnh label để click chỉnh sửa inline.
    """

    def __init__(self, section, db):
        self._section = section
        self._db = db
        self._active = False
        self._gear_buttons = {}   # {field_key: btn_widget}
        self._toolbar = None

    # ── Bật/tắt chế độ tùy biến ──────────────────────────────────────────

    def toggle(self):
        if self._active:
            self.deactivate()
        else:
            self.activate()

    def activate(self):
        """
        Bật chế độ tùy biến:
          1. Hiện thanh toolbar ở top
          2. Thêm icon ⚙ cạnh mỗi label đã đăng ký
          3. Mỗi frame trường có highlight viền khi hover
        """
        self._active = True
        self._show_toolbar()
        self._add_gear_icons()
        self._highlight_fields(True)

    def deactivate(self):
        self._active = False
        self._hide_toolbar()
        self._remove_gear_icons()
        self._highlight_fields(False)

    # ── Toolbar ──────────────────────────────────────────────────────────

    def _show_toolbar(self):
        """
        Toolbar mỏng (30px) pack ở TOP của section.
        Hiện trên giao diện hiện tại, không che nội dung.
        """
        if self._toolbar:
            return
        self._toolbar = tb.Frame(self._section, bootstyle='warning', height=32)
        self._toolbar.pack(fill='x', side='top', before=self._get_first_child())
        self._toolbar.pack_propagate(False)

        tb.Label(
            self._toolbar,
            text='✏ CHẾ ĐỘ TÙY BIẾN ĐANG BẬT — click ⚙ cạnh trường để chỉnh',
            font=('Arial', 9, 'bold'), foreground='#664D00'
        ).pack(side='left', padx=8)

        tb.Button(
            self._toolbar, text='➕ Thêm trường',
            bootstyle='outline-success',
            command=self._add_extra_field_dialog
        ).pack(side='right', padx=4)

        tb.Button(
            self._toolbar, text='↕ Sắp xếp trường',
            bootstyle='outline-info',
            command=self._reorder_dialog
        ).pack(side='right', padx=2)

        tb.Button(
            self._toolbar, text='🔄 Reset mặc định',
            bootstyle='outline-secondary',
            command=self._reset_section
        ).pack(side='right', padx=2)

        tb.Button(
            self._toolbar, text='📋 Lịch sử thay đổi',
            bootstyle='outline-secondary',
            command=self._show_history
        ).pack(side='right', padx=2)

    def _get_first_child(self):
        """Lấy widget con đầu tiên của section để pack toolbar trước nó."""
        children = self._section.winfo_children()
        return children[0] if children else None

    def _hide_toolbar(self):
        if self._toolbar:
            self._toolbar.destroy()
            self._toolbar = None

    # ── Gear icons ────────────────────────────────────────────────────────

    def _add_gear_icons(self):
        """
        Với mỗi trường trong _field_registry, thêm button ⚙ nhỏ
        vào ngay sau label_widget (pack side='left', width=2).
        """
        for fkey, info in self._section._field_registry.items():
            if fkey in self._gear_buttons:
                continue
            frm = info.get('frame')
            lbl = info.get('label_widget')
            if not frm or not lbl:
                continue

            # Tạo button là anh em (sibling) của label_widget để place hợp lệ
            btn = tb.Button(
                lbl.master, text='⚙', width=2,
                bootstyle='link-secondary',
                command=lambda k=fkey: self._field_menu(k)
            )
            # Dùng place để thả nổi icon bên phải label, tránh xung đột grid/pack của frame
            try:
                btn.place(in_=lbl, relx=1.0, rely=0.5, anchor='w', x=4)
            except Exception as e:
                print(f"[InlineCRUD] Lỗi place gear icon cho {fkey}: {e}")
            self._gear_buttons[fkey] = btn

            # Tooltip
            self._attach_tooltip(btn, f"Tùy biến trường: {fkey}")

    def _remove_gear_icons(self):
        for btn in self._gear_buttons.values():
            try: btn.destroy()
            except: pass
        self._gear_buttons.clear()

    def _highlight_fields(self, on: bool):
        """Thêm viền màu vàng nhạt quanh mỗi frame trường khi bật."""
        for info in self._section._field_registry.values():
            frm = info.get('frame')
            if frm:
                try:
                    frm.config(
                        highlightbackground='#FFC107' if on else '',
                        highlightthickness=1 if on else 0
                    )
                except Exception:
                    pass

    # ── Field menu (click ⚙) ──────────────────────────────────────────────

    def _field_menu(self, field_key: str):
        """
        Menu popup khi click ⚙ cạnh một trường:
          ✏ Đổi tên nhãn
          👁 Ẩn trường này
          ↑↓ Di chuyển lên/xuống
          🔄 Reset về mặc định
        """
        info = self._section._field_registry.get(field_key, {})
        lbl  = info.get('label_widget')
        current_name = ''
        if lbl:
            try: current_name = lbl.cget('text')
            except: pass

        # Tạo popup menu
        menu = tk.Menu(self._section, tearoff=0)
        menu.add_command(
            label=f'✏  Đổi tên: "{current_name}"',
            command=lambda: self._rename_field(field_key, current_name)
        )
        menu.add_command(
            label='👁  Ẩn trường này',
            command=lambda: self._hide_field(field_key)
        )
        menu.add_separator()
        menu.add_command(
            label='↑  Di chuyển lên',
            command=lambda: self._move_field(field_key, -1)
        )
        menu.add_command(
            label='↓  Di chuyển xuống',
            command=lambda: self._move_field(field_key, 1)
        )
        menu.add_separator()
        menu.add_command(
            label='🔄 Reset trường này về mặc định',
            command=lambda: self._reset_field(field_key)
        )
        
        # Nếu là trường bổ sung thì cho phép xóa hoàn toàn
        if str(field_key).startswith('extra_'):
            menu.add_separator()
            placeholder = f"{{{{ {field_key} }}}}"
            menu.add_command(
                label=f'📋 Copy mã Placeholder: "{placeholder}"',
                command=lambda: self._copy_to_clipboard(placeholder)
            )
            menu.add_separator()
            menu.add_command(
                label='🗑 Xóa vĩnh viễn trường bổ sung này',
                command=lambda: self._delete_extra_field(field_key)
            )
            
        # Hiện menu tại vị trí button ⚙
        btn = self._gear_buttons.get(field_key)
        if btn:
            try:
                menu.tk_popup(btn.winfo_rootx(), btn.winfo_rooty() + 20)
            finally:
                menu.grab_release()

    def _copy_to_clipboard(self, text: str):
        self._section.clipboard_clear()
        self._section.clipboard_append(text)
        self._section.update()
        from ttkbootstrap.dialogs import Messagebox
        Messagebox.show_info(f"Đã copy placeholder:\n{text}", "Thông báo")

    # ── CRUD actions ──────────────────────────────────────────────────────

    def _rename_field(self, field_key: str, current: str):
        """
        Dialog đổi tên: 1 Entry đơn giản.
        Kết quả lưu vào ui_field_meta, apply ngay lên label_widget.
        """
        top = tk.Toplevel(self._section)
        top.title('Đổi tên nhãn')
        top.geometry('380x130')
        top.resizable(False, False)
        top.transient(self._section.winfo_toplevel())
        top.grab_set()

        tb.Label(top, text='Nhãn mới:', font=('Arial', 10)).pack(pady=(16,4))
        var = tk.StringVar(value=current)
        ent = tb.Entry(top, textvariable=var, width=40)
        ent.pack(padx=20)
        ent.select_range(0, 'end')
        ent.focus()

        def _save():
            new_name = var.get().strip()
            if not new_name:
                return
            self._db.set_field_label(self._section.section_key, field_key, new_name)
            # Apply ngay lên widget không cần refresh toàn bộ
            info = self._section._field_registry.get(field_key, {})
            lbl  = info.get('label_widget')
            if lbl:
                try: lbl.config(text=new_name)
                except: pass
            top.destroy()

        bf = tb.Frame(top)
        bf.pack(pady=8)
        tb.Button(bf, text='💾 Lưu', bootstyle='success',
                  command=_save, width=10).pack(side='left', padx=4)
        tb.Button(bf, text='Hủy', bootstyle='secondary',
                  command=top.destroy, width=8).pack(side='left')
        ent.bind('<Return>', lambda e: _save())

    def _hide_field(self, field_key: str):
        if not messagebox.askyesno(
            'Xác nhận ẩn',
            f'Ẩn trường "{field_key}"?\n'
            'Dữ liệu đã nhập vẫn được giữ nguyên trong DB.\n'
            'Có thể hiện lại bất kỳ lúc nào từ menu Tùy biến.'
        ):
            return
        self._db.set_field_visibility(
            self._section.section_key, field_key, True
        )
        info = self._section._field_registry.get(field_key, {})
        frm  = info.get('frame')
        if frm:
            try:
                frm.pack_forget()
                frm.grid_remove()
            except: pass
        # Xóa gear button của trường vừa ẩn
        btn = self._gear_buttons.pop(field_key, None)
        if btn:
            try: btn.destroy()
            except: pass

    def _move_field(self, field_key: str, direction: int):
        """Di chuyển trường lên (-1) hoặc xuống (+1) trong section."""
        keys = list(self._section._field_registry.keys())
        idx  = keys.index(field_key) if field_key in keys else -1
        if idx < 0: return
        new_idx = idx + direction
        if not (0 <= new_idx < len(keys)): return
        keys[idx], keys[new_idx] = keys[new_idx], keys[idx]
        self._db.set_field_order(self._section.section_key, keys)
        self._section.refresh_from_meta()
        self._refresh_gear_icons_for_extras()

    def _reset_field(self, field_key: str):
        self._db.reset_field_meta(self._section.section_key, field_key)
        self._section.refresh_from_meta()
        self._refresh_gear_icons_for_extras()

    def _reset_section(self):
        if not messagebox.askyesno(
            'Reset toàn bộ',
            'Reset toàn bộ tùy biến về mặc định ban đầu?\n'
            'Các trường bổ sung do bạn tạo sẽ bị xóa (dữ liệu đã nhập vẫn còn trong DB).'
        ):
            return
        self._db.reset_field_meta(self._section.section_key)
        self._section.refresh_from_meta()
        self._refresh_gear_icons_for_extras()

    def _delete_extra_field(self, field_key: str):
        if not messagebox.askyesno(
            'Xác nhận xóa',
            f'Xóa trường bổ sung "{field_key}"?\nThao tác này sẽ ẩn trường khỏi giao diện (dữ liệu cũ vẫn trong DB).'
        ):
            return
        self._db.delete_extra_field(self._section.section_key, field_key)
        self._section.refresh_from_meta()
        self._refresh_gear_icons_for_extras()

    def _refresh_gear_icons_for_extras(self):
        """Xóa các nút gear cũ của trường extra (do widget đã bị hủy) và vẽ lại."""
        keys_to_remove = [k for k in self._gear_buttons.keys() if str(k).startswith('extra_')]
        for k in keys_to_remove:
            btn = self._gear_buttons.pop(k, None)
            if btn:
                try: btn.destroy()
                except: pass
        
        # Gọi lại add_gear_icons, nó sẽ skip các key đã có trong _gear_buttons
        # và thêm gear cho các key mới sinh ra từ _field_registry
        self._add_gear_icons()
        self._highlight_fields(True)

    # ── Dialog thêm trường bổ sung ────────────────────────────────────────

    def _add_extra_field_dialog(self):
        """
        Dialog thêm trường hoàn toàn mới vào cuối section.
        Các kiểu: text (Entry) / textarea (Text) / number / dropdown
        """
        top = tk.Toplevel(self._section)
        top.title('➕ Thêm trường bổ sung')
        top.geometry('420x280')
        top.transient(self._section.winfo_toplevel())
        top.grab_set()

        form = tb.Frame(top, padding=12)
        form.pack(fill='both', expand=True)

        # Nhãn trường
        tb.Label(form, text='Nhãn hiển thị: *').grid(
            row=0, column=0, sticky='w', pady=4)
        var_nhan = tk.StringVar()
        tb.Entry(form, textvariable=var_nhan, width=35).grid(
            row=0, column=1, sticky='ew')

        # Kiểu dữ liệu
        tb.Label(form, text='Kiểu dữ liệu:').grid(
            row=1, column=0, sticky='w', pady=4)
        var_kieu = tk.StringVar(value='text')
        kieu_cb = tb.Combobox(form, textvariable=var_kieu, state='readonly',
            values=['text','textarea','number','dropdown','table'], width=20)
        kieu_cb.grid(row=1, column=1, sticky='w')

        # Options (chỉ hiện khi chọn dropdown hoặc table)
        lbl_opts = tb.Label(form, text='Giá trị (mỗi dòng 1 option):')
        txt_opts = tk.Text(form, height=4, width=35)
        def _toggle_opts(*a):
            k = var_kieu.get()
            if k == 'dropdown':
                lbl_opts.config(text='Giá trị (mỗi dòng 1 option):')
                lbl_opts.grid(row=2, column=0, sticky='nw', pady=4)
                txt_opts.grid(row=2, column=1, sticky='ew')
            elif k == 'table':
                lbl_opts.config(text='Các cột của bảng\n(mỗi dòng 1 tên cột):')
                lbl_opts.grid(row=2, column=0, sticky='nw', pady=4)
                txt_opts.grid(row=2, column=1, sticky='ew')
            else:
                lbl_opts.grid_remove()
                txt_opts.grid_remove()
        kieu_cb.bind('<<ComboboxSelected>>', _toggle_opts)

        # Bắt buộc
        var_bb = tk.BooleanVar()
        tb.Checkbutton(form, text='Trường bắt buộc',
                       variable=var_bb).grid(row=3, column=1, sticky='w')

        # Giá trị mặc định
        tb.Label(form, text='Giá trị mặc định:').grid(
            row=4, column=0, sticky='w', pady=4)
        var_mac_dinh = tk.StringVar()
        tb.Entry(form, textvariable=var_mac_dinh, width=35).grid(
            row=4, column=1, sticky='ew')

        form.columnconfigure(1, weight=1)

        def _save():
            nhan = var_nhan.get().strip()
            if not nhan:
                messagebox.showwarning('Thiếu nhãn', 'Vui lòng nhập nhãn hiển thị.')
                return
            import json
            kieu = var_kieu.get()
            opts = []
            if kieu in ('dropdown', 'table'):
                raw = txt_opts.get('1.0','end').strip()
                opts = [x.strip() for x in raw.splitlines() if x.strip()]

            self._db.add_extra_field(self._section.section_key, {
                'nhan': nhan,
                'kieu': kieu,
                'options_json': json.dumps(opts, ensure_ascii=False),
                'bat_buoc': var_bb.get(),
                'gia_tri_mac_dinh': var_mac_dinh.get(),
                'thu_tu': len(self._section._field_registry) + 1
            })
            self._section.refresh_from_meta()
            self._refresh_gear_icons_for_extras()
            top.destroy()

        bf = tb.Frame(top)
        bf.pack(pady=8)
        tb.Button(bf, text='➕ Thêm trường', bootstyle='success',
                  command=_save, width=14).pack(side='left', padx=4)
        tb.Button(bf, text='Hủy', command=top.destroy,
                  width=8).pack(side='left')

    # ── Dialog sắp xếp trường ─────────────────────────────────────────────

    def _reorder_dialog(self):
        """
        Dialog kéo-thả (dùng Listbox + ↑↓) để sắp xếp lại tất cả trường.
        """
        keys  = list(self._section._field_registry.keys())
        top = tk.Toplevel(self._section)
        top.title('↕ Sắp xếp trường trong mục này')
        top.geometry('400x400')
        top.transient(self._section.winfo_toplevel())
        top.grab_set()

        tb.Label(top, text='Dùng ↑ ↓ để thay đổi thứ tự hiển thị:',
                 font=('Arial', 9)).pack(pady=8)

        lf = tb.Frame(top)
        lf.pack(fill='both', expand=True, padx=12)
        lb = tk.Listbox(lf, font=('Arial', 10))
        lb.pack(side='left', fill='both', expand=True)
        vsb = tb.Scrollbar(lf, command=lb.yview)
        vsb.pack(side='right', fill='y')
        lb.config(yscrollcommand=vsb.set)

        # Điền tên nhãn hiện tại
        for k in keys:
            info = self._section._field_registry.get(k, {})
            lbl  = info.get('label_widget')
            name = k
            if lbl:
                try: name = lbl.cget('text')
                except: pass
            lb.insert('end', f"{name}  [{k}]")

        def _move(d):
            sel = lb.curselection()
            if not sel: return
            i = sel[0]
            ni = i + d
            if not (0 <= ni < lb.size()): return
            val = lb.get(i)
            lb.delete(i)
            lb.insert(ni, val)
            lb.selection_set(ni)
            keys[i], keys[ni] = keys[ni], keys[i]

        bf = tb.Frame(top)
        bf.pack(pady=4)
        tb.Button(bf, text='↑', width=4, command=lambda: _move(-1)).pack(side='left', padx=2)
        tb.Button(bf, text='↓', width=4, command=lambda: _move(1)).pack(side='left', padx=2)

        def _save():
            self._db.set_field_order(self._section.section_key, keys)
            self._section.refresh_from_meta()
            self._refresh_gear_icons_for_extras()
            top.destroy()

        bf2 = tb.Frame(top)
        bf2.pack(pady=4)
        tb.Button(bf2, text='💾 Lưu thứ tự', bootstyle='success',
                  command=_save).pack(side='left', padx=4)
        tb.Button(bf2, text='Hủy', command=top.destroy).pack(side='left')

    # ── Lịch sử thay đổi ─────────────────────────────────────────────────

    def _show_history(self):
        hist = self._db.get_custom_history(self._section.section_key, 30)
        top = tk.Toplevel(self._section)
        top.title('📋 Lịch sử tùy biến')
        top.geometry('520x320')
        top.transient(self._section.winfo_toplevel())

        cols = ('thoi_gian','field_key','hanh_dong','gia_tri_moi')
        heads = ('Thời gian', 'Trường', 'Hành động', 'Giá trị mới')
        tv = tb.Treeview(top, columns=cols, show='headings', height=12)
        for c,h in zip(cols,heads):
            tv.heading(c,text=h)
            tv.column(c, width=120)
        tv.pack(fill='both', expand=True, padx=8, pady=8)

        for h in hist:
            tv.insert('', 'end', values=(
                h['thoi_gian'][:16], h['field_key'],
                h['hanh_dong'], h['gia_tri_moi'][:40]
            ))

        tb.Button(top, text='Đóng', command=top.destroy).pack(pady=4)

    # ── Helper ────────────────────────────────────────────────────────────

    def _attach_tooltip(self, widget, text: str):
        def _enter(e):
            tip = tk.Toplevel()
            tip.wm_overrideredirect(True)
            tip.geometry(f'+{e.x_root+10}+{e.y_root+10}')
            tk.Label(tip, text=text, background='#ffffe0',
                     relief='solid', borderwidth=1,
                     font=('Arial', 8)).pack()
            widget._tooltip = tip
        def _leave(e):
            t = getattr(widget, '_tooltip', None)
            if t:
                try: t.destroy()
                except: pass
        widget.bind('<Enter>', _enter)
        widget.bind('<Leave>', _leave)
