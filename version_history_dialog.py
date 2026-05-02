# version_history_dialog.py
"""
Dialog xem lịch sử phiên bản đề cương.
Cho phép: Xem danh sách, Xem nội dung phiên bản, Khôi phục, Xóa phiên bản cũ.
"""

import os
import json
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *


class VersionHistoryDialog(tb.Toplevel):
    """
    Dialog xem và quản lý lịch sử phiên bản đề cương.
    
    Sử dụng:
        dlg = VersionHistoryDialog(parent, db, hp_id, on_restore_callback)
        parent.wait_window(dlg)
    """

    def __init__(self, parent, db, hp_id: int, on_restore=None):
        super().__init__(parent)
        self.db = db
        self.hp_id = hp_id
        self.on_restore = on_restore

        from services.version_service import VersionService
        self.svc = VersionService(db)

        self.title(f"📜 Lịch sử phiên bản — HP #{hp_id}")
        self.geometry("860x560")
        self.minsize(640, 400)
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)

        self._center()
        self._build_ui()
        self._refresh()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 860) // 2
        y = (self.winfo_screenheight() - 560) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Header
        hdr = tb.Frame(self, bootstyle='dark')
        hdr.pack(fill='x')
        hp = self.db.get_hoc_phan(self.hp_id)
        hp_name = hp['ten_viet'] if hp else f'HP #{self.hp_id}'
        tb.Label(hdr, text=f"  📜 Lịch sử phiên bản: {hp_name}",
                 font=('Segoe UI', 11, 'bold'), bootstyle='inverse-dark').pack(
                     side='left', pady=6, padx=4)

        # Split
        split = tb.Frame(self, padding=8)
        split.pack(fill='both', expand=True)

        # LEFT — danh sách phiên bản
        left = tb.Labelframe(split, text=" Danh sách phiên bản ", bootstyle='primary', padding=6)
        left.pack(side='left', fill='y', padx=(0, 8))
        left.configure(width=300)

        self.tree = tb.Treeview(
            left,
            columns=('ver', 'name', 'date'),
            show='headings', height=16, bootstyle='primary'
        )
        self.tree.heading('ver', text='#')
        self.tree.heading('name', text='Tên phiên bản')
        self.tree.heading('date', text='Ngày tạo')
        self.tree.column('ver', width=35, anchor='center')
        self.tree.column('name', width=140, anchor='w')
        self.tree.column('date', width=85, anchor='center')

        vsb = tb.Scrollbar(left, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self._on_select)

        # Action buttons
        btn_f = tb.Frame(left)
        btn_f.pack(fill='x', pady=(6, 0))
        tb.Button(btn_f, text="💾 Tạo phiên bản ngay", bootstyle='success',
                  command=self._create_now).pack(fill='x', pady=2)
        tb.Button(btn_f, text="🔄 Khôi phục phiên bản này", bootstyle='warning',
                  command=self._restore).pack(fill='x', pady=2)
        tb.Button(btn_f, text="🗑 Xóa phiên bản", bootstyle='danger-outline',
                  command=self._delete).pack(fill='x', pady=2)

        # RIGHT — chi tiết
        right = tb.Labelframe(split, text=" Chi tiết phiên bản ", bootstyle='info', padding=8)
        right.pack(side='left', fill='both', expand=True)

        # Metadata
        meta_frame = tb.Frame(right)
        meta_frame.pack(fill='x', pady=(0, 8))
        self.lbl_ver_name = tb.Label(meta_frame, text="(Chọn phiên bản)", font=('Segoe UI', 11, 'bold'))
        self.lbl_ver_name.pack(anchor='w')
        self.lbl_ver_date = tb.Label(meta_frame, text="", foreground='gray')
        self.lbl_ver_date.pack(anchor='w')
        self.lbl_ver_note = tb.Label(meta_frame, text="", foreground='#89b4fa',
                                     wraplength=400, justify='left')
        self.lbl_ver_note.pack(anchor='w')

        tb.Separator(right, orient='horizontal').pack(fill='x', pady=6)

        # Preview summary
        tb.Label(right, text="Tóm tắt nội dung:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.txt_preview = tk.Text(right, height=14, state='disabled', font=('Consolas', 9),
                                    bg='#1e1e2e', fg='#cdd6f4', relief='flat', wrap='word')
        self.txt_preview.pack(fill='both', expand=True, pady=(4, 0))

        # Bottom
        tb.Button(right, text="✖ Đóng", bootstyle='secondary-outline',
                  command=self.destroy).pack(anchor='e', pady=(8, 0))

    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._versions = self.svc.get_versions(self.hp_id)
        for v in self._versions:
            self.tree.insert('', 'end', iid=str(v['id']),
                             values=(v['version_no'], v['ten_phien'][:25], (v['ngay_tao'] or '')[:10]))

    def _get_selected_id(self) -> int:
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _on_select(self, event=None):
        vid = self._get_selected_id()
        if not vid:
            return

        ver = next((v for v in self._versions if v['id'] == vid), None)
        if not ver:
            return

        self.lbl_ver_name.config(text=f"Phiên bản #{ver['version_no']}: {ver['ten_phien']}")
        self.lbl_ver_date.config(text=f"Tạo lúc: {ver.get('ngay_tao', '')} | Người tạo: {ver.get('nguoi_tao', '(Auto)')}")
        self.lbl_ver_note.config(text=f"Ghi chú: {ver.get('ghi_chu', '')}")

        # Preview
        detail = self.svc.get_version_detail(vid)
        if not detail:
            return

        data = detail.get('data', {})
        hp = data.get('hp', {})
        clos = data.get('clos', [])
        nds = data.get('noi_dung', [])
        kts = data.get('ke_hoach_kt', [])

        preview_lines = [
            f"📘 HP: {hp.get('ten_viet', 'N/A')} — Mã: {hp.get('ma', 'N/A')}",
            f"   Tín chỉ: {hp.get('so_tin_chi', 0)} | Tổng giờ: {hp.get('tong_gio', 0)}",
            f"",
            f"📌 CLO: {len(clos)} chuẩn đầu ra",
        ]
        for clo in clos[:5]:
            preview_lines.append(f"   [{clo.get('ma', '')}] {(clo.get('mo_ta') or '')[:60]}")
        if len(clos) > 5:
            preview_lines.append(f"   ... và {len(clos)-5} CLO khác")

        preview_lines += [
            f"",
            f"📄 Nội dung: {len(nds)} mục",
            f"📊 Kế hoạch KT: {len(kts)} bài đánh giá",
            f"   Tổng trọng số: {sum(float(r.get('ty_trong_nhom') or 0) for r in kts if r.get('nhom') == 'cuoi_ky'):.0f}% (cuối kỳ)",
        ]

        self.txt_preview.config(state='normal')
        self.txt_preview.delete('1.0', 'end')
        self.txt_preview.insert('end', '\n'.join(preview_lines))
        self.txt_preview.config(state='disabled')

    def _create_now(self):
        """Tạo phiên bản ngay lập tức."""
        dlg = _InputDialog(self, "Tạo Phiên bản", 
                           "Tên phiên bản:", "Ghi chú (tùy chọn):")
        self.wait_window(dlg)
        if dlg.cancelled:
            return
        try:
            vid = self.svc.create_snapshot(self.hp_id, dlg.val1, dlg.val2)
            self._refresh()
            self.tree.selection_set(str(vid))
            self._on_select()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)

    def _restore(self):
        vid = self._get_selected_id()
        if not vid:
            messagebox.showwarning("Chưa chọn", "Hãy chọn phiên bản muốn khôi phục.", parent=self)
            return
        ver = next((v for v in self._versions if v['id'] == vid), {})
        if not messagebox.askyesno(
            "Xác nhận khôi phục",
            f"Khôi phục về phiên bản #{ver.get('version_no')}: '{ver.get('ten_phien')}'?\n"
            "Dữ liệu hiện tại sẽ được lưu thành 1 phiên bản safety backup.",
            parent=self
        ):
            return
        try:
            self.svc.restore_snapshot(self.hp_id, vid)
            messagebox.showinfo("Thành công", "Đã khôi phục phiên bản thành công!\n"
                                "Vui lòng tải lại học phần để xem thay đổi.", parent=self)
            self._refresh()
            if self.on_restore:
                self.on_restore(self.hp_id)
        except Exception as e:
            messagebox.showerror("Lỗi khôi phục", str(e), parent=self)

    def _delete(self):
        vid = self._get_selected_id()
        if not vid:
            messagebox.showwarning("Chưa chọn", "Hãy chọn phiên bản.", parent=self)
            return
        ver = next((v for v in self._versions if v['id'] == vid), {})
        if not messagebox.askyesno("Xác nhận xóa",
                                    f"Xóa phiên bản #{ver.get('version_no')}: '{ver.get('ten_phien')}'?",
                                    parent=self):
            return
        try:
            self.svc.delete_version(vid)
            self._refresh()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)


class _InputDialog(tb.Toplevel):
    def __init__(self, parent, title, label1, label2):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.cancelled = True
        self.val1 = ''
        self.val2 = ''

        tb.Label(self, text=label1, font=('Segoe UI', 9, 'bold')).pack(padx=16, pady=(14, 2), anchor='w')
        self.e1 = tb.Entry(self, width=46)
        self.e1.pack(padx=16, fill='x')
        self.e1.focus_set()

        tb.Label(self, text=label2).pack(padx=16, pady=(8, 2), anchor='w')
        self.e2 = tb.Entry(self, width=46)
        self.e2.pack(padx=16, fill='x')

        btn = tb.Frame(self)
        btn.pack(pady=12)
        tb.Button(btn, text="OK", bootstyle='success', width=10, command=self._ok).pack(side='left', padx=4)
        tb.Button(btn, text="Hủy", bootstyle='secondary-outline', width=10, command=self.destroy).pack(side='left', padx=4)
        self.bind('<Return>', lambda _: self._ok())
        self.bind('<Escape>', lambda _: self.destroy())

    def _ok(self):
        self.cancelled = False
        self.val1 = self.e1.get().strip()
        self.val2 = self.e2.get().strip()
        self.destroy()
