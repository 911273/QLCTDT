# controllers/tree_controller.py
import tkinter as tk

class TreeController:
    def __init__(self, tree_widget, db, hp_id_map_callback=None):
        self.tree = tree_widget
        self.db = db
        self.hp_id_map_callback = hp_id_map_callback # Callback to update the map in MainApp
        self._hp_id_map = {}
        self._last_kw = ''
        self._last_nature = '-- Tất cả --'

    def load_list(self, keyword='', nature='-- Tất cả --'):
        self._last_kw = keyword
        self._last_nature = nature
        # 1. Lưu lại trạng thái các node đang mở
        expanded = [iid for iid in self._get_all_iids('') if self.tree.item(iid, 'open')]
        
        self.tree.delete(*self.tree.get_children())
        self._hp_id_map = {}
        
        if keyword:
            self._load_search_results(keyword, nature)
        else:
            self._load_root_nodes(nature)
            
        # 2. Khôi phục trạng thái mở (đệ quy vì lazy load)
        self._restore_expansion(expanded, nature)

        if self.hp_id_map_callback:
            self.hp_id_map_callback(self._hp_id_map)

    def _get_all_iids(self, parent):
        res = []
        for child in self.tree.get_children(parent):
            res.append(child)
            res.extend(self._get_all_iids(child))
        return res

    def _restore_expansion(self, expanded_list, nature):
        """Khôi phục trạng thái mở cho treeview (đệ quy)."""
        for iid in expanded_list:
            if self.tree.exists(iid):
                self.tree.item(iid, open=True)
                # Gọi load con cho iid này
                self.on_expand(None, nature_filter=nature, iid_override=iid)
                # Sau khi load xong tầng này, có thể các con của nó cũng cần restore tiếp
                # (Hàm _restore_expansion sẽ được gọi lặp lại bởi on_expand nếu ta cấu trúc lại)

    def _load_root_nodes(self, nature):
        bacs = self.db.conn.execute("SELECT DISTINCT bac FROM chuong_trinh_dao_tao ORDER BY bac").fetchall()
        for b in bacs:
            b_name = b['bac'] or 'Đại học'
            iid = f'lazy_bac_{b_name}'
            self.tree.insert('', 'end', iid=iid, text=f'🎓 Bậc: {b_name}', tags=('bac',))
            self.tree.insert(iid, 'end', text='dummy')
            
        u_iid = 'lazy_unassigned'
        self.tree.insert('', 'end', iid=u_iid, text='📂 Học phần chưa phân lớp', tags=('bac',))
        self.tree.insert(u_iid, 'end', text='dummy')

    def on_expand(self, event, nature_filter='-- Tất cả --', iid_override=None):
        iid = iid_override if iid_override else self.tree.focus()
        if not iid or not iid.startswith('lazy_'):
            return
            
        children = self.tree.get_children(iid)
        # Nếu có dummy con, xóa đi và load thật
        if len(children) == 1 and self.tree.item(children[0], 'text') == 'dummy':
            self.tree.delete(children[0])
            
            parts = iid.split('_')
            type = parts[1]
            nature = nature_filter
            nature_clause = " AND tinh_chat = ?" if nature != '-- Tất cả --' else ""
            params = [nature] if nature != '-- Tất cả --' else []

            if type == 'bac':
                bac_name = parts[2]
                ctdts = self.db.conn.execute(
                    "SELECT id, ten FROM chuong_trinh_dao_tao WHERE bac = ? ORDER BY ten", (bac_name,)
                ).fetchall()
                for c in ctdts:
                    c_iid = f'lazy_ctdt_{c["id"]}'
                    self.tree.insert(iid, 'end', iid=c_iid, text=f'📘 {c["ten"]}', tags=('ctdt',))
                    self.tree.insert(c_iid, 'end', text='dummy')
            
            elif type == 'ctdt':
                ctdt_id = parts[2]
                khois = self.db.conn.execute(
                    "SELECT DISTINCT khoi_kien_thuc FROM ctdt_hoc_phan WHERE ctdt_id = ? ORDER BY khoi_kien_thuc", (ctdt_id,)
                ).fetchall()
                for k in khois:
                    k_name = k['khoi_kien_thuc'] or 'Khác'
                    k_iid = f'lazy_khoi_{ctdt_id}_{k_name}'
                    self.tree.insert(iid, 'end', iid=k_iid, text=f'📚 {k_name}', tags=('khoi',))
                    self.tree.insert(k_iid, 'end', text='dummy')

            elif type == 'khoi':
                ctdt_id = parts[2]
                k_name = parts[3]
                cns = self.db.conn.execute(
                    "SELECT DISTINCT chuyen_nganh FROM ctdt_hoc_phan WHERE ctdt_id=? AND khoi_kien_thuc=? AND chuyen_nganh != ''",
                    (ctdt_id, k_name)
                ).fetchall()
                
                if cns:
                    for cn in cns:
                        cn_name = cn['chuyen_nganh']
                        cn_iid = f'lazy_cn_{ctdt_id}_{k_name}_{cn_name}'
                        self.tree.insert(iid, 'end', iid=cn_iid, text=f'🔸 Chuyên ngành: {cn_name}', tags=('cn',))
                        self.tree.insert(cn_iid, 'end', text='dummy')
                
                sql = f"""
                    SELECT hp.id, hp.ma, hp.ten_viet FROM hoc_phan hp
                    JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
                    WHERE ch.ctdt_id=? AND ch.khoi_kien_thuc=? AND (ch.chuyen_nganh IS NULL OR ch.chuyen_nganh = '')
                    {nature_clause} ORDER BY hp.ten_viet
                """
                hps = self.db.conn.execute(sql, [ctdt_id, k_name] + params).fetchall()
                for hp in hps:
                    hp_iid = f'hp_{hp["id"]}_{ctdt_id}'
                    self.tree.insert(iid, 'end', iid=hp_iid, text=f'📄 {hp["ma"] or "???"} - {hp["ten_viet"]}', tags=('hp',))
                    self._hp_id_map[hp_iid] = hp['id']

            elif type == 'cn':
                ctdt_id, k_name, cn_name = parts[2], parts[3], parts[4]
                sql = f"""
                    SELECT hp.id, hp.ma, hp.ten_viet FROM hoc_phan hp
                    JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
                    WHERE ch.ctdt_id=? AND ch.khoi_kien_thuc=? AND ch.chuyen_nganh=?
                    {nature_clause} ORDER BY hp.ten_viet
                """
                hps = self.db.conn.execute(sql, [ctdt_id, k_name, cn_name] + params).fetchall()
                for hp in hps:
                    hp_iid = f'hp_{hp["id"]}_{ctdt_id}'
                    self.tree.insert(iid, 'end', iid=hp_iid, text=f'📄 {hp["ma"] or "???"} - {hp["ten_viet"]}', tags=('hp',))
                    self._hp_id_map[hp_iid] = hp['id']

            elif type == 'unassigned':
                sql = f"""
                    SELECT hp.id, hp.ma, hp.ten_viet FROM hoc_phan hp
                    WHERE hp.id NOT IN (SELECT hp_id FROM ctdt_hoc_phan)
                    {nature_clause} ORDER BY hp.ten_viet
                """
                hps = self.db.conn.execute(sql, params).fetchall()
                for hp in hps:
                    hp_iid = f'hp_{hp["id"]}_none'
                    self.tree.insert(iid, 'end', iid=hp_iid, text=f'📄 {hp["ma"] or "???"} - {hp["ten_viet"]}', tags=('hp',))
                    self._hp_id_map[hp_iid] = hp['id']
            
            if self.hp_id_map_callback:
                self.hp_id_map_callback(self._hp_id_map)

    def _load_search_results(self, kw, nature):
        nature_clause = " AND hp.tinh_chat = ?" if nature != '-- Tất cả --' else ""
        
        # Tách từ khóa thành các cụm từ/từ đơn để tìm kiếm linh hoạt (AND logic)
        words = kw.split()
        if not words:
            return 0
            
        where_clauses = []
        params = []
        
        for word in words:
            w_param = f'%{word}%'
            # Sử dụng hàm unaccent (đã đăng ký trong db.py) để tìm kiếm không dấu
            clause = """(
                unaccent(hp.ten_viet) LIKE unaccent(?) 
                OR unaccent(hp.ma) LIKE unaccent(?) 
                OR unaccent(k.ten) LIKE unaccent(?) 
                OR unaccent(c.ten) LIKE unaccent(?) 
                OR unaccent(clo.ma) LIKE unaccent(?)
                OR unaccent(gv.ho_ten) LIKE unaccent(?)
            )"""
            where_clauses.append(clause)
            params.extend([w_param] * 6)
            
        if nature != '-- Tất cả --':
            params.append(nature)

        where_sql = " AND ".join(where_clauses)

        # Tìm kiếm mở rộng: Mã, Tên, Khoa, CTĐT, CLO, Giảng viên
        sql = f"""
            SELECT DISTINCT hp.id, hp.ma, hp.ten_viet, c.ten AS ctdt_ten
            FROM hoc_phan hp
            LEFT JOIN ctdt_hoc_phan ch ON hp.id = ch.hp_id
            LEFT JOIN chuong_trinh_dao_tao c ON ch.ctdt_id = c.id
            LEFT JOIN khoa k ON c.khoa_id = k.id
            LEFT JOIN clo ON hp.id = clo.hp_id
            LEFT JOIN hp_giang_vien gvhp ON hp.id = gvhp.hp_id
            LEFT JOIN giang_vien gv ON gvhp.gv_id = gv.id
            WHERE ({where_sql}) {nature_clause}
            ORDER BY hp.ten_viet LIMIT 500
        """
        rows = self.db.conn.execute(sql, params).fetchall()
        for r in rows:
            prefix = f"[{r['ctdt_ten']}] " if r['ctdt_ten'] else ""
            iid = f'hp_{r["id"]}_search'
            self.tree.insert('', 'end', iid=iid, text=f'📄 {prefix}{r["ma"] or "???"} - {r["ten_viet"]}', tags=('hp',))
            self._hp_id_map[iid] = r['id']
        
        return len(rows)

    # ── DRAG AND DROP ────────────────────────────────────────────────────────
    def setup_dnd(self):
        """Cấu hình kéo thả cho treeview."""
        self.tree.bind('<ButtonPress-1>', self._on_drag_start)
        self.tree.bind('<B1-Motion>', self._on_drag_motion)
        self.tree.bind('<ButtonRelease-1>', self._on_drag_drop)
        self._drag_data = None

    def _on_drag_start(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            self._drag_data = None
            return
            
        # Lấy danh sách đang chọn
        selection = self.tree.selection()
        
        # Chỉ kéo các node học phần
        if iid.startswith('hp_'):
            # Nếu item được click nằm trong vùng chọn, kéo tất cả các học phần đang chọn
            if iid in selection:
                self._drag_data = [s for s in selection if s.startswith('hp_')]
            else:
                self._drag_data = [iid]
                
            if self._drag_data:
                self.tree.config(cursor="fleur")
        else:
            self._drag_data = None

    def _on_drag_motion(self, event):
        # Có thể thêm hiệu ứng hover ở đây nếu cần
        pass

    def _on_drag_drop(self, event):
        self.tree.config(cursor="")
        if not self._drag_data:
            return
        
        drag_items = self._drag_data
        self._drag_data = None
        
        target_iid = self.tree.identify_row(event.y)
        if not target_iid:
            return
            
        # Không được thả lên chính nó hoặc lên con của chính mình (với folder)
        if target_iid in drag_items:
            return
            
        # 1. Phân tích đích
        if not target_iid.startswith('lazy_'):
            return 
            
        parts_t = target_iid.split('_')
        type_t = parts_t[1]
        
        new_ctdt_id = None
        new_khoi = None
        new_cn = None
        
        if type_t == 'ctdt':
            new_ctdt_id = int(parts_t[2])
        elif type_t == 'khoi':
            new_ctdt_id = int(parts_t[2])
            new_khoi = parts_t[3]
        elif type_t == 'cn':
            new_ctdt_id = int(parts_t[2])
            new_khoi = parts_t[3]
            new_cn = parts_t[4]
        elif type_t == 'unassigned':
            new_ctdt_id = None
        else:
            return 
        
        # 2. Thực hiện di chuyển cho tất cả các item trong group
        success_count = 0
        for source_iid in drag_items:
            try:
                parts_s = source_iid.split('_')
                hp_id = int(parts_s[1])
                old_ctdt_id = parts_s[2]
                if old_ctdt_id == 'none' or old_ctdt_id == 'search': old_ctdt_id = None
                else: old_ctdt_id = int(old_ctdt_id)
                
                self._perform_move(hp_id, old_ctdt_id, new_ctdt_id, new_khoi, new_cn)
                success_count += 1
            except:
                continue
        
        # 3. Refresh tree (giữ nguyên trạng thái mở)
        if success_count > 0:
            self.load_list(keyword=self._last_kw, nature=self._last_nature)

    def _perform_move(self, hp_id, old_ctdt_id, new_ctdt_id, new_khoi, new_cn):
        with self.db.transaction():
            # Xóa liên kết cũ
            if old_ctdt_id:
                self.db.conn.execute("DELETE FROM ctdt_hoc_phan WHERE hp_id=? AND ctdt_id=?", (hp_id, old_ctdt_id))
            
            # Thêm liên kết mới
            if new_ctdt_id:
                # Tránh trùng lặp nếu HP đã có trong CTĐT đích ở khối khác
                self.db.conn.execute("DELETE FROM ctdt_hoc_phan WHERE hp_id=? AND ctdt_id=?", (hp_id, new_ctdt_id))
                self.db.conn.execute(
                    "INSERT INTO ctdt_hoc_phan(ctdt_id, hp_id, khoi_kien_thuc, chuyen_nganh) VALUES(?,?,?,?)",
                    (new_ctdt_id, hp_id, new_khoi, new_cn)
                )
