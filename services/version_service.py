# services/version_service.py
"""
Version Control nhẹ cho đề cương học phần.
Mỗi lần lưu hoặc theo yêu cầu người dùng, hệ thống:
1. Serialize toàn bộ đề cương thành JSON
2. Lưu vào bảng de_cuong_version với số phiên bản tự tăng
3. Cung cấp khả năng xem lại và khôi phục phiên bản cũ
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class VersionService:
    """Quản lý phiên bản đề cương (lightweight version control)."""

    # Số phiên bản tối đa giữ lại trên mỗi học phần
    MAX_VERSIONS = 20

    def __init__(self, db):
        self.db = db

    # ── Tạo phiên bản ─────────────────────────────────────────────────────────

    def create_snapshot(self, hp_id: int, ten_phien: str = '', ghi_chu: str = '',
                        nguoi_tao: str = '') -> int:
        """
        Lưu toàn bộ đề cương hiện tại thành 1 phiên bản.
        
        Args:
            hp_id: ID học phần
            ten_phien: Tên phiên bản (VD: "Trước hội đồng", "Draft 2")
            ghi_chu: Ghi chú thêm
            nguoi_tao: Người tạo phiên bản
        
        Returns:
            version_id (int) của phiên bản mới
        """
        data = self._collect_full_data(hp_id)
        data_json = json.dumps(data, ensure_ascii=False, indent=None)

        last_ver = self.db.conn.execute(
            "SELECT MAX(version_no) FROM de_cuong_version WHERE hp_id=?", (hp_id,)
        ).fetchone()[0] or 0

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not ten_phien:
            ten_phien = f"Phiên bản {last_ver + 1} — {now[:10]}"

        with self.db.transaction():
            cur = self.db.conn.execute("""
                INSERT INTO de_cuong_version(hp_id, version_no, ten_phien, data_json, nguoi_tao, ngay_tao, ghi_chu)
                VALUES (?,?,?,?,?,?,?)
            """, (hp_id, last_ver + 1, ten_phien, data_json, nguoi_tao, now, ghi_chu))
            version_id = cur.lastrowid

        # Dọn dẹp phiên bản cũ nếu vượt quá MAX_VERSIONS
        self._cleanup_old_versions(hp_id)

        return version_id

    def auto_snapshot(self, hp_id: int) -> int:
        """
        Tự động tạo snapshot trước mỗi lần lưu (đặt tên tự động).
        Dùng cho auto-save hoặc trước khi import đè dữ liệu.
        """
        return self.create_snapshot(hp_id, ten_phien='', ghi_chu='Auto-save')

    # ── Khôi phục ─────────────────────────────────────────────────────────────

    def restore_snapshot(self, hp_id: int, version_id: int) -> bool:
        """
        Khôi phục đề cương về phiên bản cụ thể.
        Tự động tạo snapshot hiện tại trước khi khôi phục (safety net).
        
        Returns:
            True nếu thành công
        """
        row = self.db.conn.execute(
            "SELECT data_json FROM de_cuong_version WHERE id=? AND hp_id=?",
            (version_id, hp_id)
        ).fetchone()

        if not row:
            raise ValueError(f"Phiên bản id={version_id} không tồn tại với hp_id={hp_id}")

        # Safety: tạo snapshot hiện tại trước khi restore
        self.create_snapshot(hp_id, ten_phien='(Trước khi khôi phục)', ghi_chu='Auto before restore')

        try:
            data = json.loads(row['data_json'])
            self._restore_full_data(hp_id, data)
            return True
        except Exception as e:
            raise RuntimeError(f"Lỗi khôi phục phiên bản: {e}") from e

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_versions(self, hp_id: int) -> List[dict]:
        """Lấy danh sách phiên bản của 1 học phần, mới nhất trước."""
        rows = self.db.conn.execute("""
            SELECT id, hp_id, version_no, ten_phien, nguoi_tao, ngay_tao, ghi_chu,
                   LENGTH(data_json) as data_size
            FROM de_cuong_version
            WHERE hp_id=? ORDER BY version_no DESC
        """, (hp_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_version_detail(self, version_id: int) -> Optional[dict]:
        """Lấy chi tiết 1 phiên bản (bao gồm data_json)."""
        row = self.db.conn.execute(
            "SELECT * FROM de_cuong_version WHERE id=?", (version_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d['data'] = json.loads(d['data_json'])
        except Exception:
            d['data'] = {}
        return d

    def delete_version(self, version_id: int):
        """Xóa 1 phiên bản cụ thể."""
        with self.db.transaction():
            self.db.conn.execute("DELETE FROM de_cuong_version WHERE id=?", (version_id,))

    def compare_versions(self, v1_id: int, v2_id: int) -> dict:
        """
        So sánh 2 phiên bản, trả về list các thay đổi đơn giản.
        Returns dict {'changes': [...], 'v1_date': ..., 'v2_date': ...}
        """
        v1 = self.get_version_detail(v1_id)
        v2 = self.get_version_detail(v2_id)
        if not v1 or not v2:
            return {'changes': [], 'error': 'Không tìm thấy phiên bản'}

        changes = []
        d1 = v1.get('data', {})
        d2 = v2.get('data', {})

        # So sánh các field cơ bản của HP
        hp1 = d1.get('hp', {})
        hp2 = d2.get('hp', {})
        for field in ('ten_viet', 'so_tin_chi', 'gio_lt', 'gio_bt', 'gio_th_tn', 'mo_ta'):
            if hp1.get(field) != hp2.get(field):
                changes.append({
                    'section': 'Thông tin chung',
                    'field': field,
                    'old': hp1.get(field),
                    'new': hp2.get(field)
                })

        # So sánh số lượng CLO
        c1 = len(d1.get('clos', []))
        c2 = len(d2.get('clos', []))
        if c1 != c2:
            changes.append({'section': 'CLO', 'field': 'Số lượng CLO', 'old': c1, 'new': c2})

        # So sánh số lượng nội dung
        n1 = len(d1.get('noi_dung', []))
        n2 = len(d2.get('noi_dung', []))
        if n1 != n2:
            changes.append({'section': 'Nội dung', 'field': 'Số mục nội dung', 'old': n1, 'new': n2})

        return {
            'changes': changes,
            'v1_date': v1.get('ngay_tao', ''),
            'v2_date': v2.get('ngay_tao', ''),
            'v1_name': v1.get('ten_phien', ''),
            'v2_name': v2.get('ten_phien', ''),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _collect_full_data(self, hp_id: int) -> dict:
        """Thu thập toàn bộ dữ liệu đề cương từ DB thành dict."""
        db = self.db

        hp_raw = db.get_hoc_phan(hp_id)
        hp = dict(hp_raw) if hp_raw else {}

        gv_rows = db.conn.execute(
            "SELECT * FROM hp_giang_vien WHERE hp_id=? ORDER BY thu_tu", (hp_id,)
        ).fetchall()

        clos = [dict(r) for r in db.get_clo(hp_id)]
        muc_tieu = [dict(r) for r in db.get_muc_tieu(hp_id)]
        hoc_lieu = [dict(r) for r in db.get_hoc_lieu(hp_id)]
        noi_dung_lt = [dict(r) for r in db.get_noi_dung(hp_id, 'lt')]
        noi_dung_th = [dict(r) for r in db.get_noi_dung(hp_id, 'th')]
        ke_hoach_kt = [dict(r) for r in db.get_ke_hoach_kt(hp_id)]

        # Rubric
        rubric_rows = db.get_rubric_by_hp(hp_id) or []
        rubrics = []
        for rb in rubric_rows:
            rb_d = dict(rb)
            try:
                tc = [dict(r) for r in db.conn.execute(
                    "SELECT * FROM rubric_tieu_chi WHERE rubric_id=? ORDER BY thu_tu",
                    (rb_d['id'],)
                ).fetchall()]
                rb_d['tieu_chi_list'] = tc
            except Exception:
                rb_d['tieu_chi_list'] = []
            rubrics.append(rb_d)

        # Lịch sử
        try:
            lich_su = [dict(r) for r in db.get_lich_su(hp_id)]
        except Exception:
            lich_su = []

        return {
            'snapshot_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hp': hp,
            'giang_vien': [dict(r) for r in gv_rows],
            'clos': clos,
            'muc_tieu': muc_tieu,
            'hoc_lieu': hoc_lieu,
            'noi_dung': noi_dung_lt + noi_dung_th,
            'ke_hoach_kt': ke_hoach_kt,
            'rubrics': rubrics,
            'lich_su': lich_su,
        }

    def _restore_full_data(self, hp_id: int, data: dict):
        """Khôi phục dữ liệu từ dict về DB."""
        db = self.db

        with db.transaction():
            # 1. HP info
            hp_data = data.get('hp', {})
            if hp_data:
                hp_data.pop('id', None)
                db.update_hoc_phan(hp_id, hp_data)

            # 2. CLO
            clos = data.get('clos', [])
            if clos:
                db.set_clo(hp_id, clos)

            # 3. Mục tiêu
            mts = data.get('muc_tieu', [])
            if mts:
                db.set_muc_tieu(hp_id, mts)

            # 4. Học liệu
            hls = data.get('hoc_lieu', [])
            if hls:
                db.set_hoc_lieu(hp_id, hls)

            # 5. Nội dung
            nds = data.get('noi_dung', [])
            if nds:
                db.conn.execute("DELETE FROM noi_dung WHERE hp_id=?", (hp_id,))
                for nd in nds:
                    nd_copy = {k: v for k, v in nd.items() if k != 'id'}
                    nd_copy['hp_id'] = hp_id
                    db._safe_fields('noi_dung', nd_copy)  # filter valid cols
                    cols = list(nd_copy.keys())
                    db.conn.execute(
                        f"INSERT INTO noi_dung({','.join(cols)}) VALUES({','.join(['?']*len(cols))})",
                        list(nd_copy.values())
                    )

            # 6. Kế hoạch KT
            kts = data.get('ke_hoach_kt', [])
            if kts:
                db.set_ke_hoach_kt(hp_id, kts)

            # 7. Rubric
            rubrics = data.get('rubrics', [])
            if rubrics:
                try:
                    db.set_rubric(hp_id, rubrics)
                except Exception as e:
                    print(f"[VersionService] restore rubric: {e}")

    def _cleanup_old_versions(self, hp_id: int):
        """Giữ lại tối đa MAX_VERSIONS phiên bản mới nhất."""
        rows = self.db.conn.execute(
            "SELECT id FROM de_cuong_version WHERE hp_id=? ORDER BY version_no DESC",
            (hp_id,)
        ).fetchall()
        if len(rows) > self.MAX_VERSIONS:
            ids_to_delete = [r['id'] for r in rows[self.MAX_VERSIONS:]]
            for id_ in ids_to_delete:
                self.db.conn.execute("DELETE FROM de_cuong_version WHERE id=?", (id_,))
