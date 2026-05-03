# repositories/hoc_phan_repository.py
from datetime import datetime
from .base_repository import BaseRepository
from typing import List, Optional, Dict, Any

class HocPhanRepository(BaseRepository):
    def get_all(self) -> List[dict]:
        """Lấy tất cả học phần kèm tên khoa."""
        return self._fetch_all("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            ORDER BY k.ten, hp.ten_viet
        """)

    def get_by_id(self, hp_id: int) -> Optional[dict]:
        """Lấy chi tiết 1 học phần."""
        return self._fetch_one("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            WHERE hp.id=?
        """, (hp_id,))

    def search(self, keyword: str) -> List[dict]:
        """Tìm kiếm học phần (hỗ trợ không dấu)."""
        k = f"%{keyword}%"
        return self._fetch_all("""
            SELECT hp.*, k.ten AS ten_khoa
            FROM hoc_phan hp
            LEFT JOIN khoa k ON hp.khoa_id = k.id
            WHERE unaccent(hp.ten_viet) LIKE unaccent(?) 
               OR unaccent(hp.ma) LIKE unaccent(?) 
               OR unaccent(hp.ten_anh) LIKE unaccent(?)
            ORDER BY k.ten, hp.ten_viet
        """, (k, k, k))

    def create(self, data: dict) -> int:
        """Tạo học phần mới."""
        with self.db.transaction():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data.setdefault('ngay_tao', now)
            data.setdefault('ngay_cap_nhat', now)
            return self._safe_insert('hoc_phan', data)

    def update(self, hp_id: int, data: dict):
        """Cập nhật học phần, tự động tính tổng giờ nếu có thay đổi."""
        with self.db.transaction():
            data['ngay_cap_nhat'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Tự động tính tổng giờ
            gio_fields = ['gio_lt', 'gio_bt', 'gio_tl', 'gio_th_tn', 'gio_th', 'gio_bt_th',
                          'gio_kt', 'gio_tieu_luan', 'gio_thuc_tap', 'gio_tu_hoc']
            
            if any(f in data for f in gio_fields):
                hp_current = self.get_by_id(hp_id)
                if hp_current:
                    merged = {**{f: hp_current.get(f, 0) or 0 for f in gio_fields}, 
                              **{k: v for k, v in data.items() if k in gio_fields}}
                    data['tong_gio'] = sum(float(merged[f]) for f in gio_fields)

            self._safe_update('hoc_phan', hp_id, data)

    def delete(self, hp_id: int):
        """Xóa học phần."""
        with self.db.transaction():
            self.conn.execute("DELETE FROM hoc_phan WHERE id=?", (hp_id,))

    def clone(self, hp_id: int) -> int:
        """Sao chép toàn bộ học phần (optimized)."""
        with self.db.transaction():
            old_hp = self.get_by_id(hp_id)
            if not old_hp: return None
            
            # 1. Tạo record HP mới
            data = dict(old_hp)
            data.pop('id', None)
            data.pop('ten_khoa', None)
            data['ten_viet'] += " (Bản sao)"
            if data.get('ma'): data['ma'] += "_copy"
            
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data['ngay_tao'] = now_str
            data['ngay_cap_nhat'] = now_str
            
            new_id = self._safe_insert('hoc_phan', data)
            
            # 2. Bulk copy các bảng phẳng (Optimized using INSERT INTO ... SELECT)
            tables = ['muc_tieu', 'clo', 'hoc_lieu', 'ke_hoach_kiem_tra', 'hp_giang_vien', 'lich_su_cap_nhat', 'ctdt_hoc_phan']
            for table in tables:
                cols = self._get_cols(table)
                # Lấy các cột trừ id và hp_id
                cols_to_copy = [f'"{c}"' for c in cols if c not in ('id', 'hp_id')]
                if not cols_to_copy: continue
                
                col_str = ", ".join(cols_to_copy)
                sql = f"INSERT INTO {table} ({col_str}, hp_id) SELECT {col_str}, ? FROM {table} WHERE hp_id=?"
                self.conn.execute(sql, (new_id, hp_id))
                
            # 3. Sao chép bảng NOI_DUNG (có phân cấp)
            old_nd_rows = self._fetch_all("SELECT * FROM noi_dung WHERE hp_id=? ORDER BY cap_do, id", (hp_id,))
            id_map = {None: None}
            
            for r in old_nd_rows:
                old_id = r.pop('id')
                old_parent = r.get('parent_id')
                r['hp_id'] = new_id
                r['parent_id'] = id_map.get(old_parent)
                
                new_nd_id = self._safe_insert('noi_dung', r)
                id_map[old_id] = new_nd_id
                
            return new_id

    def check_duplicates(self) -> List[str]:
        """Kiểm tra trùng lặp."""
        issues = []
        dup_ma = self._fetch_all("""
            SELECT ma, COUNT(*) as c FROM hoc_phan 
            WHERE ma IS NOT NULL AND ma != '' 
            GROUP BY ma HAVING c > 1
        """)
        for r in dup_ma:
            issues.append(f"• Trùng mã học phần: {r['ma']} ({r['c']} lần)")

        dup_ten = self._fetch_all("""
            SELECT ten_viet, COUNT(*) as c FROM hoc_phan 
            GROUP BY ten_viet HAVING c > 1
        """)
        for r in dup_ten:
            issues.append(f"• Trùng tên học phần: {r['ten_viet']} ({r['c']} bản ghi)")

        return issues

    def get_gv(self, hp_id: int) -> List[dict]:
        return self._fetch_all("""
            SELECT hpgv.*, gv.ho_ten AS gv_ten
            FROM hp_giang_vien hpgv
            LEFT JOIN giang_vien gv ON hpgv.gv_id = gv.id
            WHERE hpgv.hp_id=? ORDER BY hpgv.thu_tu
        """, (hp_id,))

    def set_gv(self, hp_id: int, gv_list: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM hp_giang_vien WHERE hp_id=?", (hp_id,))
            for i, gv in enumerate(gv_list):
                gv['hp_id'] = hp_id
                gv['thu_tu'] = i + 1
                self._safe_insert('hp_giang_vien', gv)

    def get_ctdt_links(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM ctdt_hoc_phan WHERE hp_id=?", (hp_id,))

    def update_ctdt_links(self, hp_id: int, ctdt_links: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM ctdt_hoc_phan WHERE hp_id=?", (hp_id,))
            for link in ctdt_links:
                link['hp_id'] = hp_id
                self._safe_insert('ctdt_hoc_phan', link)

    def set_muc_tieu(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM muc_tieu WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['so_thu_tu'] = i + 1
                self._safe_insert('muc_tieu', item)

    def set_clo(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM clo WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                self._safe_insert('clo', item)

    def set_hoc_lieu(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM hoc_lieu WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['so_thu_tu'] = i + 1
                self._safe_insert('hoc_lieu', item)

    def set_noi_dung(self, hp_id: int, phan: str, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM noi_dung WHERE hp_id=? AND phan=?", (hp_id, phan))
            # Vì items thường là list phẳng có parent_id mapping trong UI, 
            # nhưng tốt nhất là handle parent_id mapping nếu nó trỏ về ID cũ.
            # Tuy nhiên, UI hiện tại thường gửi dữ liệu đã được xử lý ID.
            for item in items:
                item['hp_id'] = hp_id
                item['phan'] = phan
                self._safe_insert('noi_dung', item)

    def get_ke_hoach_kt(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM ke_hoach_kiem_tra WHERE hp_id=? ORDER BY thu_tu", (hp_id,))

    def set_ke_hoach_kt(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM ke_hoach_kiem_tra WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['thu_tu'] = i + 1
                self._safe_insert('ke_hoach_kiem_tra', item)

    def get_lich_su(self, hp_id: int) -> List[dict]:
        return self._fetch_all("SELECT * FROM lich_su_cap_nhat WHERE hp_id=? ORDER BY lan DESC", (hp_id,))

    def set_lich_su(self, hp_id: int, items: List[dict]):
        with self.db.transaction():
            self.conn.execute("DELETE FROM lich_su_cap_nhat WHERE hp_id=?", (hp_id,))
            for i, item in enumerate(items):
                item['hp_id'] = hp_id
                item['lan'] = i + 1
                self._safe_insert('lich_su_cap_nhat', item)

    def add_lich_su_cap_nhat(self, data: dict):
        return self._safe_insert('lich_su_cap_nhat', data)

    def update_trang_thai(self, hp_id: int, trang_thai: str):
        self.conn.execute("UPDATE hoc_phan SET trang_thai=? WHERE id=?", (trang_thai, hp_id))

    def save_draft(self, hp_id: int, data_json: str):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute("""
            INSERT OR REPLACE INTO temp_draft (hp_id, data_json, updated_at)
            VALUES (?, ?, ?)
        """, (hp_id, data_json, now))

    def get_draft(self, hp_id: int) -> Optional[dict]:
        return self._fetch_one("SELECT * FROM temp_draft WHERE hp_id=?", (hp_id,))

    def delete_draft(self, hp_id: int):
        self.conn.execute("DELETE FROM temp_draft WHERE hp_id=?", (hp_id,))
