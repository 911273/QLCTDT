# modules/de_cuong/ui/system_menu/form_dialogs.py
"""Form dialogs cho Schema, Section, Field CRUD."""
import tkinter as tk
from tkinter import messagebox, colorchooser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import json
import re


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

ICON_PALETTE = ['📋', '📝', '📊', '📎', '🔬', '🎯', '📅', '📌', '⚙', '🔗', '📄', '⊞', '✍']


def _make_slug(text: str) -> str:
    """Tạo ma_truong slug từ tên tiếng Việt."""
    replacements = {
        'à':'a','á':'a','ả':'a','ã':'a','ạ':'a','â':'a','ấ':'a','ầ':'a','ẩ':'a','ẫ':'a','ậ':'a',
        'ă':'a','ắ':'a','ằ':'a','ẳ':'a','ẵ':'a','ặ':'a','è':'e','é':'e','ẻ':'e','ẽ':'e','ẹ':'e',
        'ê':'e','ế':'e','ề':'e','ể':'e','ễ':'e','ệ':'e','ì':'i','í':'i','ỉ':'i','ĩ':'i','ị':'i',
        'ò':'o','ó':'o','ỏ':'o','õ':'o','ọ':'o','ô':'o','ố':'o','ồ':'o','ổ':'o','ỗ':'o','ộ':'o',
        'ơ':'o','ớ':'o','ờ':'o','ở':'o','ỡ':'o','ợ':'o','ù':'u','ú':'u','ủ':'u','ũ':'u','ụ':'u',
        'ư':'u','ứ':'u','ừ':'u','ử':'u','ữ':'u','ự':'u','ý':'y','ỳ':'y','ỷ':'y','ỹ':'y','ỵ':'y',
        'đ':'d'
    }
    s = text.lower()
    for v, a in replacements.items():
        s = s.replace(v, a)
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s[:40]


class _BaseDialog(tb.Toplevel):
    """Base dialog với result."""
    def __init__(self, parent, title, width=480, height=420):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(True, True)
        self.result = None
        self.grab_set()
        self.transient(parent)

    def _ok(self):
        self.result = self._collect()
        if self.result is not None:
            self.destroy()

    def _collect(self):
        raise NotImplementedError

    def _cancel(self):
        self.result = None
        self.destroy()

    def _buttons(self, parent):
        bf = tb.Frame(parent)
        bf.pack(fill='x', pady=(10, 0))
        tb.Button(bf, text='✓ Lưu', bootstyle='success', command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='Hủy', bootstyle='outline-secondary', command=self._cancel).pack(side='right', padx=4)


class SchemaFormDialog(_BaseDialog):
    def __init__(self, parent, existing=None):
        super().__init__(parent, '📐 Thêm/Sửa Mẫu đề cương', 480, 380)
        self._existing = existing or {}
        self._build()
        self.wait_window()

    def _build(self):
        frm = tb.Frame(self, padding=16)
        frm.pack(fill='both', expand=True)

        rows = [
            ('ten_mau',      'Tên mẫu *',          'entry',   ''),
            ('trinh_do',     'Trình độ',             'combo',   ['dai_hoc','cao_dang','sau_dh','khac']),
            ('nam_ban_hanh', 'Năm ban hành',         'spin',    (2020, 2035)),
            ('phien_ban',    'Phiên bản',            'entry',   '1.0'),
            ('mo_ta',        'Mô tả',                'text',    3),
        ]
        self._vars = {}
        for key, lbl, wtype, opts in rows:
            tb.Label(frm, text=lbl).pack(anchor='w', pady=(6, 0))
            default = self._existing.get(key, opts if wtype == 'entry' else '')
            if wtype == 'entry':
                v = tk.StringVar(value=str(default))
                tb.Entry(frm, textvariable=v).pack(fill='x')
                self._vars[key] = v
            elif wtype == 'combo':
                v = tk.StringVar(value=str(self._existing.get(key, opts[0])))
                tb.Combobox(frm, textvariable=v, values=opts, state='readonly').pack(fill='x')
                self._vars[key] = v
            elif wtype == 'spin':
                v = tk.IntVar(value=int(self._existing.get(key, opts[0])))
                tb.Spinbox(frm, textvariable=v, from_=opts[0], to=opts[1]).pack(fill='x')
                self._vars[key] = v
            elif wtype == 'text':
                t = tk.Text(frm, height=opts, wrap='word')
                t.insert('1.0', self._existing.get(key, ''))
                t.pack(fill='x')
                self._vars[key] = t

        self._buttons(frm)

    def _collect(self):
        ten = self._vars['ten_mau'].get().strip()
        if not ten:
            messagebox.showwarning('Thiếu thông tin', 'Tên mẫu không được để trống.', parent=self)
            return None
        mo_ta_w = self._vars['mo_ta']
        mo_ta = mo_ta_w.get('1.0', 'end').strip() if isinstance(mo_ta_w, tk.Text) else ''
        return {
            'ten_mau':      ten,
            'trinh_do':     self._vars['trinh_do'].get(),
            'nam_ban_hanh': self._vars['nam_ban_hanh'].get(),
            'phien_ban':    self._vars['phien_ban'].get().strip() or '1.0',
            'mo_ta':        mo_ta,
        }


class SectionFormDialog(_BaseDialog):
    def __init__(self, parent, existing=None):
        super().__init__(parent, '📑 Thêm/Sửa Mục (Section)', 500, 460)
        self._existing = existing or {}
        self._build()
        self.wait_window()

    def _build(self):
        frm = tb.Frame(self, padding=16)
        frm.pack(fill='both', expand=True)

        tb.Label(frm, text='Tiêu đề mục *').pack(anchor='w', pady=(4, 0))
        self._v_tieu_de = tk.StringVar(value=self._existing.get('tieu_de', ''))
        ent_td = tb.Entry(frm, textvariable=self._v_tieu_de)
        ent_td.pack(fill='x')
        ent_td.bind('<FocusOut>', self._suggest_ma)

        tb.Label(frm, text='Mã mục (ma_muc)').pack(anchor='w', pady=(6, 0))
        self._v_ma = tk.StringVar(value=self._existing.get('ma_muc', ''))
        tb.Entry(frm, textvariable=self._v_ma).pack(fill='x')

        # Icon
        tb.Label(frm, text='Icon').pack(anchor='w', pady=(6, 0))
        icon_frm = tb.Frame(frm)
        icon_frm.pack(fill='x')
        self._v_icon = tk.StringVar(value=self._existing.get('icon', '📋'))
        tb.Entry(icon_frm, textvariable=self._v_icon, width=6).pack(side='left')
        for ic in ICON_PALETTE:
            tb.Button(icon_frm, text=ic, width=3,
                      command=lambda i=ic: self._v_icon.set(i)).pack(side='left', padx=1)

        tb.Label(frm, text='Loại').pack(anchor='w', pady=(6, 0))
        self._v_loai = tk.StringVar(value=self._existing.get('loai', 'standard'))
        tb.Combobox(frm, textvariable=self._v_loai,
                    values=['standard', 'table', 'repeatable', 'conditional'],
                    state='readonly').pack(fill='x')

        tb.Label(frm, text='Màu nhãn').pack(anchor='w', pady=(6, 0))
        self._color = self._existing.get('color_tag', '#4A90D9')
        color_frm = tb.Frame(frm)
        color_frm.pack(fill='x')
        self._color_lbl = tk.Label(color_frm, bg=self._color, width=6, relief='solid')
        self._color_lbl.pack(side='left', padx=(0, 6))
        tb.Button(color_frm, text='Chọn màu', command=self._pick_color).pack(side='left')

        chk_frm = tb.Frame(frm)
        chk_frm.pack(fill='x', pady=(8, 0))
        self._v_required = tk.BooleanVar(value=bool(self._existing.get('is_required', 1)))
        self._v_visible  = tk.BooleanVar(value=bool(self._existing.get('is_visible', 1)))
        tb.Checkbutton(chk_frm, text='Bắt buộc', variable=self._v_required).pack(side='left', padx=6)
        tb.Checkbutton(chk_frm, text='Hiển thị', variable=self._v_visible).pack(side='left', padx=6)

        tb.Label(frm, text='Mô tả').pack(anchor='w', pady=(6, 0))
        self._txt_mo_ta = tk.Text(frm, height=2, wrap='word')
        self._txt_mo_ta.insert('1.0', self._existing.get('mo_ta', ''))
        self._txt_mo_ta.pack(fill='x')

        self._buttons(frm)

    def _suggest_ma(self, event=None):
        if not self._v_ma.get():
            self._v_ma.set('muc_' + _make_slug(self._v_tieu_de.get()))

    def _pick_color(self):
        c = colorchooser.askcolor(color=self._color, parent=self)
        if c and c[1]:
            self._color = c[1]
            self._color_lbl.config(bg=self._color)

    def _collect(self):
        tieu_de = self._v_tieu_de.get().strip()
        if not tieu_de:
            messagebox.showwarning('Thiếu thông tin', 'Tiêu đề mục không được để trống.', parent=self)
            return None
        ma = self._v_ma.get().strip() or 'muc_' + _make_slug(tieu_de)
        return {
            'tieu_de':   tieu_de,
            'ma_muc':    ma,
            'icon':      self._v_icon.get(),
            'loai':      self._v_loai.get(),
            'color_tag': self._color,
            'is_required': int(self._v_required.get()),
            'is_visible':  int(self._v_visible.get()),
            'mo_ta':     self._txt_mo_ta.get('1.0', 'end').strip(),
        }


class FieldFormDialog(_BaseDialog):
    """Dialog đa tab cho Field definition."""

    def __init__(self, parent, db=None, existing=None):
        super().__init__(parent, '📝 Thêm/Sửa Trường dữ liệu', 620, 560)
        self._db = db
        self._existing = existing or {}
        self._build()
        self.wait_window()

    def _build(self):
        nb = tb.Notebook(self)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        # Tab 1: Cơ bản
        t1 = tb.Frame(nb, padding=12)
        nb.add(t1, text='📋 Cơ bản')
        self._build_tab1(t1)

        # Tab 2: Nâng cao
        t2 = tb.Frame(nb, padding=12)
        nb.add(t2, text='⚙ Nâng cao')
        self._build_tab2(t2)

        # Tab 3: Word mapping
        t3 = tb.Frame(nb, padding=12)
        nb.add(t3, text='📄 Word')
        self._build_tab3(t3)

        bf = tb.Frame(self)
        bf.pack(fill='x', padx=8, pady=(0, 8))
        tb.Button(bf, text='✓ Lưu', bootstyle='success', command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='Hủy', bootstyle='outline-secondary', command=self._cancel).pack(side='right', padx=4)

    def _build_tab1(self, parent):
        ex = self._existing
        rows = [
            ('nhan',             'Nhãn hiển thị *',   'entry', ex.get('nhan', '')),
            ('ma_truong',        'Tên trường DB',      'entry', ex.get('ma_truong', '')),
            ('nhom_hien_thi',    'Nhóm hiển thị',      'entry', ex.get('nhom_hien_thi', '')),
            ('placeholder',      'Placeholder',         'entry', ex.get('placeholder', '')),
            ('tooltip',          'Tooltip',             'entry', ex.get('tooltip', '')),
            ('gia_tri_mac_dinh', 'Giá trị mặc định',   'entry', ex.get('gia_tri_mac_dinh', '')),
        ]
        self._f1_vars = {}

        tb.Label(parent, text='Kiểu dữ liệu *').pack(anchor='w')
        self._v_kieu = tk.StringVar(value=ex.get('kieu_du_lieu', 'text'))
        kieu_vals = [f"{v}  {l}" for v, l in FIELD_TYPES]
        kieu_raw  = [v for v, _ in FIELD_TYPES]
        cbo_kieu  = tb.Combobox(parent, textvariable=self._v_kieu,
                                values=kieu_raw, state='readonly')
        cbo_kieu.pack(fill='x', pady=(0, 4))

        for key, lbl, _, default in rows:
            tb.Label(parent, text=lbl).pack(anchor='w', pady=(4, 0))
            v = tk.StringVar(value=str(default))
            ent = tb.Entry(parent, textvariable=v)
            ent.pack(fill='x')
            self._f1_vars[key] = v
            if key == 'nhan':
                ent.bind('<FocusOut>', self._suggest_ma_truong)

        chk_frm = tb.Frame(parent)
        chk_frm.pack(fill='x', pady=(8, 0))
        self._v_bat_buoc  = tk.BooleanVar(value=bool(ex.get('bat_buoc', 0)))
        self._v_is_visible = tk.BooleanVar(value=bool(ex.get('is_visible', 1)))
        tb.Checkbutton(chk_frm, text='Bắt buộc', variable=self._v_bat_buoc).pack(side='left', padx=6)
        tb.Checkbutton(chk_frm, text='Hiển thị', variable=self._v_is_visible).pack(side='left', padx=6)

        tb.Label(parent, text='Độ rộng (%)').pack(anchor='w', pady=(6, 0))
        self._v_width = tk.IntVar(value=int(ex.get('width_hint', 100)))
        tb.Spinbox(parent, textvariable=self._v_width, from_=10, to=100).pack(fill='x')

    def _suggest_ma_truong(self, event=None):
        if not self._f1_vars.get('ma_truong') or not self._f1_vars['ma_truong'].get():
            nhan = self._f1_vars['nhan'].get()
            self._f1_vars['ma_truong'].set(_make_slug(nhan))

    def _build_tab2(self, parent):
        ex = self._existing
        tb.Label(parent, text='Options (dropdown/multiselect) — mỗi dòng 1 giá trị:').pack(anchor='w')
        self._txt_options = tk.Text(parent, height=5, wrap='word')
        opts = ex.get('options_json', [])
        if isinstance(opts, list):
            self._txt_options.insert('1.0', '\n'.join(opts))
        elif isinstance(opts, str):
            try:
                self._txt_options.insert('1.0', '\n'.join(json.loads(opts)))
            except Exception:
                self._txt_options.insert('1.0', opts)
        self._txt_options.pack(fill='x', pady=(0, 8))

        tb.Label(parent, text='Validation JSON (min/max/min_length/max_length/regex):').pack(anchor='w')
        self._txt_valid = tk.Text(parent, height=3, wrap='word')
        vj = ex.get('validation_json', {})
        self._txt_valid.insert('1.0', json.dumps(vj, ensure_ascii=False) if isinstance(vj, dict) else str(vj))
        self._txt_valid.pack(fill='x', pady=(0, 8))

        tb.Label(parent, text='Điều kiện hiện trường JSON:').pack(anchor='w')
        self._txt_dkien = tk.Text(parent, height=3, wrap='word')
        dkj = ex.get('dieu_kien_json', {})
        self._txt_dkien.insert('1.0', json.dumps(dkj, ensure_ascii=False) if isinstance(dkj, dict) else str(dkj))
        self._txt_dkien.pack(fill='x')

    def _build_tab3(self, parent):
        ex = self._existing
        for key, lbl in [('word_bookmark', 'Word Bookmark'),
                          ('word_style',    'Word Style'),
                          ('help_url',      'Help URL')]:
            tb.Label(parent, text=lbl).pack(anchor='w', pady=(6, 0))
            v = tk.StringVar(value=ex.get(key, ''))
            tb.Entry(parent, textvariable=v).pack(fill='x')
            setattr(self, f'_v_{key}', v)

    def _collect(self):
        nhan = self._f1_vars['nhan'].get().strip()
        if not nhan:
            messagebox.showwarning('Thiếu thông tin', 'Nhãn hiển thị không được để trống.', parent=self)
            return None
        ma = self._f1_vars['ma_truong'].get().strip() or _make_slug(nhan)

        # Parse options
        opts_raw = self._txt_options.get('1.0', 'end').strip()
        options = [o.strip() for o in opts_raw.splitlines() if o.strip()] if opts_raw else []

        # Parse validation JSON
        try:
            valid = json.loads(self._txt_valid.get('1.0', 'end').strip() or '{}')
        except Exception:
            valid = {}

        try:
            dkien = json.loads(self._txt_dkien.get('1.0', 'end').strip() or '{}')
        except Exception:
            dkien = {}

        return {
            'nhan':             nhan,
            'ma_truong':        ma,
            'kieu_du_lieu':     self._v_kieu.get(),
            'nhom_hien_thi':    self._f1_vars['nhom_hien_thi'].get(),
            'placeholder':      self._f1_vars['placeholder'].get(),
            'tooltip':          self._f1_vars['tooltip'].get(),
            'gia_tri_mac_dinh': self._f1_vars['gia_tri_mac_dinh'].get(),
            'bat_buoc':         int(self._v_bat_buoc.get()),
            'is_visible':       int(self._v_is_visible.get()),
            'width_hint':       self._v_width.get(),
            'options_json':     json.dumps(options, ensure_ascii=False),
            'validation_json':  json.dumps(valid, ensure_ascii=False),
            'dieu_kien_json':   json.dumps(dkien, ensure_ascii=False),
            'word_bookmark':    self._v_word_bookmark.get(),
            'word_style':       self._v_word_style.get(),
            'help_url':         self._v_help_url.get(),
        }


class _SimpleInputDialog(tb.Toplevel):
    """Dialog nhập 1 giá trị text đơn giản."""
    def __init__(self, parent, title, prompt, default=''):
        super().__init__(parent)
        self.title(title)
        self.geometry('380x160')
        self.resizable(False, False)
        self.result = None
        self.grab_set()
        self.transient(parent)

        frm = tb.Frame(self, padding=16)
        frm.pack(fill='both', expand=True)
        tb.Label(frm, text=prompt).pack(anchor='w')
        self._v = tk.StringVar(value=default)
        tb.Entry(frm, textvariable=self._v).pack(fill='x', pady=6)
        bf = tb.Frame(frm)
        bf.pack(fill='x')
        tb.Button(bf, text='OK', bootstyle='success',
                  command=self._ok).pack(side='right', padx=4)
        tb.Button(bf, text='Hủy', bootstyle='outline-secondary',
                  command=self.destroy).pack(side='right', padx=4)
        self.wait_window()

    def _ok(self):
        self.result = self._v.get().strip()
        self.destroy()
