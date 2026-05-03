# services/template_service.py
"""
Template Engine cho QLCTDT v2.0.
Dùng docxtpl (Jinja2 trong Word) để cho phép người dùng tự tạo/sửa template
mà không cần chỉnh sửa code.

Người dùng mở file .docx, gõ {{ CourseName }}, {% for clo in CLOs %}...{% endfor %}
rồi upload vào hệ thống — hệ thống tự render ra Word đầy đủ dữ liệu.
"""

import os
import re
import json
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any


# Thư mục lưu template
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word_templates')


def _ensure_template_dir():
    os.makedirs(TEMPLATE_DIR, exist_ok=True)


class TemplateEngine:
    """
    Render file Word từ template .docx chứa Jinja2 placeholder.
    Tự động build context từ database theo hp_id.
    """

    def __init__(self, db):
        self.db = db
        _ensure_template_dir()

    def render(self, hp_id: int, template_path: str, output_path: str) -> bool:
        """
        Render template với đầy đủ dữ liệu từ DB.
        
        Args:
            hp_id: ID học phần
            template_path: Đường dẫn file .docx template
            output_path: Đường dẫn file .docx output
        
        Returns:
            True nếu thành công
        
        Raises:
            RuntimeError nếu docxtpl chưa cài hoặc có lỗi render
        """
        try:
            from docxtpl import DocxTemplate
        except ImportError:
            raise RuntimeError(
                "Thư viện 'docxtpl' chưa được cài đặt.\n"
                "Chạy lệnh: pip install docxtpl"
            )

        try:
            tpl = DocxTemplate(template_path)
            context = self.build_context(hp_id)
            tpl.render(context)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            tpl.save(output_path)
            return True
        except Exception as e:
            raise RuntimeError(f"Lỗi render template '{os.path.basename(template_path)}': {e}") from e

    def get_template_context(self, hp_id: int) -> dict:
        """Alias for build_context to support word_export.py legacy calls."""
        return self.build_context(hp_id)

    def build_context(self, hp_id: int) -> dict:
        """
        Xây dựng context dict Jinja2 từ dữ liệu DB.
        Keys đặt tên theo convention PascalCase cho Jinja2.
        """
        db = self.db

        hp_raw = db.get_hoc_phan(hp_id)
        if not hp_raw:
            raise ValueError(f"Không tìm thấy học phần hp_id={hp_id}")
        hp = dict(hp_raw)

        # GV
        gv_rows = db.conn.execute("""
            SELECT hpgv.ho_ten, hpgv.hoc_ham_vi AS hoc_vi, hpgv.sdt, hpgv.email, hpgv.vai_tro, hpgv.don_vi,
                   gv.hoc_vi AS gv_hoc_vi, gv.sdt AS gv_sdt, gv.email AS gv_email,
                   gv.ma_can_bo, gv.gioi_tinh, gv.chuc_vu, gv.dia_chi
            FROM hp_giang_vien hpgv
            LEFT JOIN giang_vien gv ON hpgv.gv_id = gv.id
            WHERE hpgv.hp_id=? ORDER BY hpgv.thu_tu
        """, (hp_id,)).fetchall()

        lecturers = [
            {
                'Name'  : r['ho_ten'] or '',
                'Degree': r['hoc_vi'] or r['gv_hoc_vi'] or '',
                'Phone' : r['sdt'] or r['gv_sdt'] or '',
                'Email' : r['email'] or r['gv_email'] or '',
                'Unit'  : r['don_vi'] or '',
                'Role'  : 'Phụ trách chính' if r['vai_tro'] == 'phu_trach' else 'Tham gia giảng dạy',
                'RoleKey': r['vai_tro'] or '',
                'StaffCode': r['ma_can_bo'] or '',
                'Gender' : r['gioi_tinh'] or '',
                'Position': r['chuc_vu'] or '',
                'Address': r['dia_chi'] or '',
                # Compatibility for Word Builders
                'hoc_ham_vi_ten': f"{r['hoc_vi'] or r['gv_hoc_vi'] or ''} {r['ho_ten'] or ''}".strip(),
                'ma_can_bo': r['ma_can_bo'] or '',
                'chuc_vu': r['chuc_vu'] or '',
                'sdt': r['sdt'] or r['gv_sdt'] or '',
                'email': r['email'] or r['gv_email'] or '',
            }
            for r in gv_rows
        ]
        main_lect = next((l for l in lecturers if l['RoleKey'] == 'phu_trach'), {})

        # Tên khoa
        ten_khoa = ''
        if hp.get('khoa_id'):
            k = db.conn.execute("SELECT ten FROM khoa WHERE id=?", (hp['khoa_id'],)).fetchone()
            if k: ten_khoa = k['ten']

        # CLO
        clo_rows = [dict(r) for r in db.get_clo(hp_id)]
        clos = [
            {
                'Code'      : r.get('ma', ''),
                'Desc'      : r.get('mo_ta', ''),
                'PLO'       : r.get('cdr_ma', ''),
                'Level'     : r.get('level_irm', 'I'),
                'BloomLevel': r.get('cap_do_bloom', 1),
                'Group'     : r.get('nhom', ''),
            }
            for r in clo_rows
            if not r.get('la_tieu_de_nhom')
        ]

        # Mục tiêu
        mt_rows = [dict(r) for r in db.get_muc_tieu(hp_id)]
        objectives = [
            {
                'No'  : r.get('so_thu_tu', i + 1),
                'Desc': r.get('mo_ta', ''),
                'PLO' : r.get('cdr_ma', ''),
            }
            for i, r in enumerate(mt_rows)
            if not r.get('la_tieu_de_nhom')
        ]

        # Học liệu
        hl_rows = [dict(r) for r in db.get_hoc_lieu(hp_id)]
        main_refs  = [r for r in hl_rows if r.get('loai') == '5.1']
        sup_refs   = [r for r in hl_rows if r.get('loai') == '5.2']
        other_refs = [r for r in hl_rows if r.get('loai') == '5.3']
        phong_hoc  = [r for r in hl_rows if r.get('loai') == '5.4']
        thiet_bi_ho_tro = [r for r in hl_rows if r.get('loai') == '5.5']
        tb_thuc_hanh = [r for r in hl_rows if r.get('loai') == '5.6']
        ngoai_khoa = [r for r in hl_rows if r.get('loai') == '5.7']

        # Nội dung
        nd_lt = [dict(r) for r in db.get_noi_dung(hp_id, 'lt')]
        nd_th = [dict(r) for r in db.get_noi_dung(hp_id, 'th')]

        # Kế hoạch kiểm tra
        kt_rows = [dict(r) for r in db.get_ke_hoach_kt(hp_id)]
        assessment_groups = {}
        for r in kt_rows:
            nhom = r.get('nhom', 'khac')
            if nhom not in assessment_groups:
                assessment_groups[nhom] = {
                    'Label' : 'Thường xuyên' if nhom == 'thuong_xuyen' else
                              'Giữa kỳ' if nhom == 'giua_ky' else
                              'Cuối kỳ' if nhom == 'cuoi_ky' else nhom,
                    'Weight': float(r.get('ty_trong_nhom') or 0),
                    'Items' : []
                }
            assessment_groups[nhom]['Items'].append(r)

        # Rubric
        rubric_rows = db.get_rubric_by_hp(hp_id) or []
        rubrics = []
        for rb in rubric_rows:
            rb_dict = dict(rb)
            try:
                tc_rows = db.conn.execute(
                    "SELECT * FROM rubric_tieu_chi WHERE rubric_id=? ORDER BY thu_tu",
                    (rb_dict['id'],)
                ).fetchall()
                rb_dict['Criteria'] = [dict(r) for r in tc_rows]
            except Exception:
                rb_dict['Criteria'] = []
            rubrics.append(rb_dict)

        # Lịch sử
        try:
            lich_su = [dict(r) for r in db.get_lich_su(hp_id)]
        except Exception:
            lich_su = []

        # Chính sách
        try:
            cs_row = db.conn.execute("SELECT * FROM chinh_sach_hoc_phan WHERE hp_id=?", (hp_id,)).fetchone()
            if cs_row:
                cs_rows = [
                    {'loai_chinh_sach': 'Liêm chính học thuật', 'noi_dung': cs_row['liem_chinh_ht']},
                    {'loai_chinh_sach': 'Sử dụng AI', 'noi_dung': cs_row['su_dung_ai']}
                ]
            else:
                cs_rows = []
        except Exception:
            cs_rows = []

        # Checklist
        try:
            cl_row = db.conn.execute("SELECT * FROM checklist_tu_kiem_tra WHERE hp_id=?", (hp_id,)).fetchone()
            if cl_row:
                cl_rows = [
                    {'hang_muc': 'Hình thức format', 'trang_thai': 'Đạt' if cl_row['hinh_thuc'] else 'Cần chú ý'},
                    {'hang_muc': 'Chuẩn CLO Bloom', 'trang_thai': 'Đạt' if cl_row['clo_bloom'] else 'Cần chú ý'},
                    {'hang_muc': 'Giờ tự học (1TC=50h)', 'trang_thai': 'Đạt' if cl_row['gio_tu_hoc'] else 'Cần chú ý'},
                    {'hang_muc': 'Rubric khớp CLO', 'trang_thai': 'Đạt' if cl_row['rubric_match'] else 'Cần chú ý'},
                    {'hang_muc': 'Giảng viên xác nhận', 'trang_thai': 'Đạt' if cl_row['giang_vien_xn'] else 'Cần chú ý'}
                ]
            else:
                cl_rows = []
        except Exception:
            cl_rows = []

        # CTĐT (Các chương trình đào tạo áp dụng môn này)
        try:
            ctdt_rows = [dict(r) for r in db.get_ctdt_of_hp(hp_id)]
        except Exception:
            ctdt_rows = []

        def parse_courses(course_list_str):
            if not course_list_str or course_list_str.strip().lower() == 'không có':
                return {
                    'Raw': course_list_str or 'Không có',
                    'Code': '',
                    'Name': course_list_str or 'Không có',
                    'List': []
                }
            course_list_str = course_list_str.strip()
            raw_items = [item.strip() for item in re.split(r'[,;]', course_list_str) if item.strip()]
            
            parsed_list = []
            codes = []
            names = []
            for item in raw_items:
                parsed_item = {'Code': '', 'Name': item, 'Raw': item}
                if '-' in item:
                    parts = item.split('-', 1)
                    parsed_item['Code'] = parts[0].strip()
                    parsed_item['Name'] = parts[1].strip()
                else:
                    parts = item.split(' ', 1)
                    if len(parts) == 2 and len(parts[0]) <= 10 and parts[0].isalnum():
                        parsed_item['Code'] = parts[0].strip()
                        parsed_item['Name'] = parts[1].strip()
                
                parsed_list.append(parsed_item)
                if parsed_item['Code']:
                    codes.append(parsed_item['Code'])
                names.append(parsed_item['Name'])
                
            return {
                'Raw': course_list_str,
                'Code': ', '.join(codes) if codes else '',
                'Name': ', '.join(names) if names else course_list_str,
                'List': parsed_list
            }

        tq = parse_courses(hp.get('hp_tien_quyet'))
        sh = parse_courses(hp.get('hp_song_hanh'))
        tt = parse_courses(hp.get('hp_thay_the'))

        return {
            # ── Thông tin chung ──────────────────────────────────────────────
            'CourseName'        : hp.get('ten_viet') or '',
            'CourseNameEN'      : hp.get('ten_anh') or '',
            'CourseCode'        : hp.get('ma') or '',
            'Credits'           : hp.get('so_tin_chi') or 0,
            'Department'        : ten_khoa,
            'ManageUnit'        : hp.get('don_vi_ql') or '',
            'Level'             : hp.get('trinh_do') or 'Đại học',
            'CourseType'        : hp.get('loai') or '',
            'CourseNature'      : hp.get('tinh_chat') or '',
            'TotalHours'        : hp.get('tong_gio') or 0,
            'HoursLT'           : hp.get('gio_lt') or 0,
            'HoursBT'           : hp.get('gio_bt') or 0,
            'HoursTH'           : hp.get('gio_th_tn') or 0,
            'HoursBTTH'         : hp.get('gio_bt_th') or 0,
            'HoursTL'           : hp.get('gio_tl') or 0,
            'HoursTuHoc'        : hp.get('gio_tu_hoc') or 0,
            'HoursKT'           : hp.get('gio_kt') or 0,
            'HoursTieuLuan'     : hp.get('gio_tieu_luan') or 0,
            'HoursThucTap'      : hp.get('gio_thuc_tap') or 0,
            'PrereqCourse'      : tq['Raw'],
            'PrereqCourseName'  : tq['Name'],
            'PrereqCourseCode'  : tq['Code'],
            'PrereqCourses'     : tq['List'],
            'CoReqCourse'       : sh['Raw'],
            'CoReqCourseName'   : sh['Name'],
            'CoReqCourseCode'   : sh['Code'],
            'CoReqCourses'      : sh['List'],
            'SubstituteCourse'  : tt['Raw'],
            'SubstituteCourseName': tt['Name'],
            'SubstituteCourseCode': tt['Code'],
            'SubstituteCourses' : tt['List'],
            'Description'       : hp.get('mo_ta') or '',
            'Status'            : hp.get('trang_thai') or 'nhap',
            'Major'             : hp.get('nganh') or '',
            'Specialization'    : hp.get('chuyen_nganh') or '',
            'KnowledgeBlock'    : hp.get('khoi_kien_thuc') or '',
            'TeachingMethods'   : hp.get('pp_day_hoc') or '',

            # ── Nhiệm vụ sinh viên & Quy định ────────────────────────────────
            'TaskInClass'       : hp.get('nhiem_vu_sv_len_lop') or '',
            'TaskHomework'      : hp.get('nhiem_vu_sv_bai_tap') or '',
            'TaskEquipment'     : hp.get('nhiem_vu_sv_dung_cu') or '',
            'TaskOther'         : hp.get('nhiem_vu_sv_khac') or '',
            'CourseRules'       : hp.get('quy_dinh_hp') or '',

            # ── Thông tin Ký duyệt ───────────────────────────────────────────
            'SignPlace'         : hp.get('dia_diem_ky') or 'Hà Nội',
            'SignDate'          : hp.get('ngay_ky') or '',
            'SignTitleLeft'     : hp.get('chuc_danh_ky_trai') or 'TRƯỞNG BỘ MÔN',
            'SignNameLeft'      : hp.get('ho_ten_ky_trai') or '',
            'SignTitleRight'    : hp.get('chuc_danh_ky_phai') or 'TRƯỞNG KHOA',
            'SignNameRight'     : hp.get('ho_ten_ky_phai') or '',

            # ── Giảng viên ───────────────────────────────────────────────────
            'Lecturers'         : lecturers,
            'MainLecturer'      : main_lect,
            'LecturerMain'      : [l for l in lecturers if l['RoleKey'] == 'phu_trach'],
            'LecturerTeam'      : [l for l in lecturers if l['RoleKey'] != 'phu_trach'],
            'giang_vien_chinh'   : [l for l in lecturers if l['RoleKey'] == 'phu_trach'],
            'giang_vien_tham_gia': [l for l in lecturers if l['RoleKey'] != 'phu_trach'],

            # ── Mục tiêu ─────────────────────────────────────────────────────
            'Objectives'        : objectives,

            # ── CLO ──────────────────────────────────────────────────────────
            'CLOs'              : clos,
            'CLOCount'          : len(clos),

            # ── CTĐT & Lịch sử & Khác ─────────────────────────────────────────
            'Programs'          : ctdt_rows,

            # ── Học liệu & Cơ sở vật chất (Mục 5) ────────────────────────────
            'MainRefs'          : main_refs,          # 5.1
            'SupRefs'           : sup_refs,           # 5.2
            'OtherRefs'         : other_refs,         # 5.3
            'PhongHoc'          : phong_hoc,          # 5.4
            'ThietBiHoTro'      : thiet_bi_ho_tro,    # 5.5
            'ThietBiThucHanh'   : tb_thuc_hanh,       # 5.6
            'NgoaiKhoa'         : ngoai_khoa,         # 5.7
            'AllRefs'           : hl_rows,

            # ── Nội dung ─────────────────────────────────────────────────────
            'ContentLT'         : nd_lt,
            'ContentTH'         : nd_th,
            'TotalLTHours'      : sum(r.get('gio_lt') or 0 for r in nd_lt),
            'TotalBTHours'      : sum(r.get('gio_bt') or 0 for r in nd_lt),
            'TotalTHHours'      : sum(r.get('gio_th_tn') or 0 for r in nd_lt + nd_th),

            # ── Kế hoạch đánh giá ────────────────────────────────────────────
            'AssessmentRows'    : kt_rows,
            'AssessmentGroups'  : assessment_groups,
            'TaskAttend'        : hp.get('nhiem_vu_sv_len_lop') or '',
            'TaskHomework'      : hp.get('nhiem_vu_sv_bai_tap') or '',
            'TaskTools'         : hp.get('nhiem_vu_sv_dung_cu') or '',
            'TaskOther'         : hp.get('nhiem_vu_sv_khac') or '',

            # ── Rubric ───────────────────────────────────────────────────────
            'Rubrics'           : rubrics,

            # ── Quy định / CSVC ──────────────────────────────────────────────
            'CourseRules'       : hp.get('quy_dinh_hp') or '',
            'Facilities'        : hp.get('co_so_vat_chat') or '',
            'Appendix'          : hp.get('phu_luc') or '',

            # ── Ký tên ───────────────────────────────────────────────────────
            'SignPlace'         : hp.get('dia_diem_ky') or 'Hà Nội',
            'SignDate'          : hp.get('ngay_ky') or datetime.now().strftime('%d/%m/%Y'),
            'SignerLeftTitle'   : hp.get('chuc_danh_ky_trai') or 'Giảng viên phụ trách',
            'SignerLeftName'    : hp.get('ho_ten_ky_trai') or (main_lect.get('Name') or ''),
            'SignerRightTitle'  : hp.get('chuc_danh_ky_phai') or 'Trưởng Bộ môn',
            'SignerRightName'   : hp.get('ho_ten_ky_phai') or '',

            # ── Lịch sử & Khác ───────────────────────────────────────────────
            'History'           : lich_su,
            'Policies'          : cs_rows,
            'Checklists'        : cl_rows,
            'IsPhD'             : hp.get('nhom_hp_dac_thu') == 'Chuyên đề Tiến sĩ',

            # ── Metadata ─────────────────────────────────────────────────────
            'Today'             : datetime.now().strftime('%d/%m/%Y'),
            'Year'              : datetime.now().year,
            'HpId'              : hp_id,
        }

        # ── Extra Fields (Inline CRUD) ───────────────────────────────────────
        try:
            extra_rows = db.conn.execute("""
                SELECT section_key, field_key, gia_tri FROM ui_field_data WHERE hp_id=?
            """, (hp_id,)).fetchall()
            for r in extra_rows:
                fkey = r['field_key']
                val = r['gia_tri']
                # Tự động parse JSON nếu là list/dict (cho trường Bảng)
                if val and isinstance(val, str) and (val.startswith('[') or val.startswith('{')):
                    try: val = json.loads(val)
                    except: pass
                # Đưa vào context với key gốc (ví dụ: extra_abc123)
                context[fkey] = val
        except Exception as ex:
            print(f"[Template] Error loading extra fields: {ex}")

        return context

    def get_available_placeholders(self) -> List[Dict]:
        """
        Trả về danh sách toàn bộ placeholder có thể dùng trong template,
        kèm loại dữ liệu và ví dụ.
        Dùng để hiển thị trong UI quản lý template.
        """
        return [
            # Scalar fields
            {'key': 'CourseName',      'type': 'text',    'example': '{{ CourseName }}', 'group': '1. Thông tin chung'},
            {'key': 'CourseNameEN',    'type': 'text',    'example': '{{ CourseNameEN }}', 'group': '1. Thông tin chung'},
            {'key': 'CourseCode',      'type': 'text',    'example': '{{ CourseCode }}', 'group': '1. Thông tin chung'},
            {'key': 'Credits',         'type': 'number',  'example': '{{ Credits }}', 'group': '1. Thông tin chung'},
            {'key': 'Department',      'type': 'text',    'example': '{{ Department }}', 'group': '1. Thông tin chung'},
            {'key': 'ManageUnit',      'type': 'text',    'example': '{{ ManageUnit }}', 'group': '1. Thông tin chung'},
            {'key': 'Level',           'type': 'text',    'example': '{{ Level }}', 'group': '1. Thông tin chung'},
            {'key': 'CourseType',      'type': 'text',    'example': '{{ CourseType }}', 'group': '1. Thông tin chung'},
            {'key': 'CourseNature',    'type': 'text',    'example': '{{ CourseNature }}', 'group': '1. Thông tin chung'},
            {'key': 'TotalHours',      'type': 'number',  'example': '{{ TotalHours }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursLT',         'type': 'number',  'example': '{{ HoursLT }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursBT',         'type': 'number',  'example': '{{ HoursBT }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursTH',         'type': 'number',  'example': '{{ HoursTH }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursBTTH',       'type': 'number',  'example': '{{ HoursBTTH }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursTL',         'type': 'number',  'example': '{{ HoursTL }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursTuHoc',      'type': 'number',  'example': '{{ HoursTuHoc }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursKT',         'type': 'number',  'example': '{{ HoursKT }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursTieuLuan',   'type': 'number',  'example': '{{ HoursTieuLuan }}', 'group': '1. Thông tin chung'},
            {'key': 'HoursThucTap',    'type': 'number',  'example': '{{ HoursThucTap }}', 'group': '1. Thông tin chung'},
            {'key': 'TotalLTHours',    'type': 'number',  'example': '{{ TotalLTHours }}', 'group': '1. Thông tin chung'},
            {'key': 'TotalBTHours',    'type': 'number',  'example': '{{ TotalBTHours }}', 'group': '1. Thông tin chung'},
            {'key': 'TotalTHHours',    'type': 'number',  'example': '{{ TotalTHHours }}', 'group': '1. Thông tin chung'},
            {'key': 'Description',     'type': 'text',    'example': '{{ Description }}', 'group': '2. Mô tả & Mục tiêu'},
            {'key': 'Status',          'type': 'text',    'example': '{{ Status }}', 'group': 'Hệ thống'},
            {'key': 'Major',           'type': 'text',    'example': '{{ Major }}', 'group': '1. Thông tin chung'},
            {'key': 'Specialization',  'type': 'text',    'example': '{{ Specialization }}', 'group': '1. Thông tin chung'},
            {'key': 'KnowledgeBlock',  'type': 'text',    'example': '{{ KnowledgeBlock }}', 'group': '1. Thông tin chung'},
            {'key': 'TeachingMethods', 'type': 'text',    'example': '{{ TeachingMethods }}', 'group': '1. Thông tin chung'},
            
            {'key': 'TaskInClass',     'type': 'text',    'example': '{{ TaskInClass }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'TaskAttend',      'type': 'text',    'example': '{{ TaskAttend }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'TaskHomework',    'type': 'text',    'example': '{{ TaskHomework }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'TaskEquipment',   'type': 'text',    'example': '{{ TaskEquipment }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'TaskTools',       'type': 'text',    'example': '{{ TaskTools }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'TaskOther',       'type': 'text',    'example': '{{ TaskOther }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'CourseRules',     'type': 'text',    'example': '{{ CourseRules }}', 'group': 'Nhiệm vụ & Quy định'},
            {'key': 'Facilities',      'type': 'text',    'example': '{{ Facilities }}', 'group': '5. Cơ sở vật chất'},
            {'key': 'Appendix',        'type': 'text',    'example': '{{ Appendix }}', 'group': '9. Khác'},
            
            {'key': 'SignPlace',       'type': 'text',    'example': '{{ SignPlace }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignDate',        'type': 'date',    'example': '{{ SignDate }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignTitleLeft',   'type': 'text',    'example': '{{ SignTitleLeft }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignNameLeft',    'type': 'text',    'example': '{{ SignNameLeft }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignTitleRight',  'type': 'text',    'example': '{{ SignTitleRight }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignNameRight',   'type': 'text',    'example': '{{ SignNameRight }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignerLeftTitle', 'type': 'text',    'example': '{{ SignerLeftTitle }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignerLeftName',  'type': 'text',    'example': '{{ SignerLeftName }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignerRightTitle','type': 'text',    'example': '{{ SignerRightTitle }}', 'group': 'Hệ thống - Ký duyệt'},
            {'key': 'SignerRightName', 'type': 'text',    'example': '{{ SignerRightName }}', 'group': 'Hệ thống - Ký duyệt'},
            
            {'key': 'Today',           'type': 'date',    'example': '{{ Today }}', 'group': 'Hệ thống'},
            {'key': 'Year',            'type': 'number',  'example': '{{ Year }}', 'group': 'Hệ thống'},
            {'key': 'HpId',            'type': 'number',  'example': '{{ HpId }}', 'group': 'Hệ thống'},
            
            {'key': 'PrereqCourse',    'type': 'text',    'example': '{{ PrereqCourse }}', 'group': '1. Thông tin chung'},
            {'key': 'PrereqCourseCode','type': 'text',    'example': '{{ PrereqCourseCode }}', 'group': '1. Thông tin chung'},
            {'key': 'PrereqCourseName','type': 'text',    'example': '{{ PrereqCourseName }}', 'group': '1. Thông tin chung'},
            {'key': 'CoReqCourse',     'type': 'text',    'example': '{{ CoReqCourse }}', 'group': '1. Thông tin chung'},
            {'key': 'CoReqCourseCode', 'type': 'text',    'example': '{{ CoReqCourseCode }}', 'group': '1. Thông tin chung'},
            {'key': 'CoReqCourseName', 'type': 'text',    'example': '{{ CoReqCourseName }}', 'group': '1. Thông tin chung'},
            {'key': 'SubstituteCourse','type': 'text',    'example': '{{ SubstituteCourse }}', 'group': '1. Thông tin chung'},
            {'key': 'SubstituteCourseCode','type': 'text', 'example': '{{ SubstituteCourseCode }}', 'group': '1. Thông tin chung'},
            {'key': 'SubstituteCourseName','type': 'text', 'example': '{{ SubstituteCourseName }}', 'group': '1. Thông tin chung'},
            
            # Lists
            {'key': 'Lecturers',       'type': 'list',    'example': '{{ Name, Degree, Role, StaffCode, Phone, Email }}', 'group': '1. Thông tin chung'},
            {'key': 'MainLecturer',    'type': 'dict',    'example': '{{ MainLecturer.Name }}', 'group': '1. Thông tin chung'},
            {'key': 'LecturerMain',    'type': 'list',    'example': '{% for l in LecturerMain %}', 'group': '1. Thông tin chung'},
            {'key': 'LecturerTeam',    'type': 'list',    'example': '{% for l in LecturerTeam %}', 'group': '1. Thông tin chung'},
            
            {'key': 'CLOs',            'type': 'list',    'example': '{{ Code, Desc, PLO, Level }}', 'group': '3. CLO'},
            {'key': 'CLOCount',        'type': 'number',  'example': '{{ CLOCount }}', 'group': '3. CLO'},
            {'key': 'Objectives',      'type': 'list',    'example': '{{ No, Desc, PLO }}', 'group': '2. Mô tả & Mục tiêu'},
            
            {'key': 'MainRefs',        'type': 'list',    'example': '{{ noi_dung }}', 'group': '5. Cơ sở vật chất'},
            {'key': 'SupRefs',         'type': 'list',    'example': '{{ noi_dung }}', 'group': '5. Cơ sở vật chất'},
            {'key': 'OtherRefs',       'type': 'list',    'example': '{{ noi_dung }}', 'group': '5. Cơ sở vật chất'},
            {'key': 'AllRefs',         'type': 'list',    'example': '{{ noi_dung, loai }}', 'group': '5. Cơ sở vật chất'},
            
            {'key': 'ContentLT',       'type': 'list',    'example': '{{ ten, gio_lt, pp_day }}', 'group': '5. Nội dung học phần'},
            {'key': 'ContentTH',       'type': 'list',    'example': '{{ ten, gio_th, pp_day }}', 'group': '5. Nội dung học phần'},
            
            {'key': 'AssessmentRows',  'type': 'list',    'example': '{{ nhom, noi_dung, hinh_thuc, ty_trong }}', 'group': '6. Đánh giá'},
            {'key': 'AssessmentGroups','type': 'dict',    'example': '{% for k, g in AssessmentGroups.items() %}', 'group': '6. Đánh giá'},
            {'key': 'Rubrics',         'type': 'list',    'example': '{{ ten, ky_hieu, Criteria }}', 'group': '6. Đánh giá'},
            
            {'key': 'History',         'type': 'list',    'example': '{{ lan, noi_dung, ngay_cap_nhat }}', 'group': '7. Lịch sử'},
            {'key': 'Policies',        'type': 'list',    'example': '{{ loai_chinh_sach, noi_dung }}', 'group': '8. Chính sách'},
            {'key': 'Checklists',      'type': 'list',    'example': '{{ hang_muc, trang_thai }}', 'group': '9. Tự kiểm tra'},
            {'key': 'IsPhD',           'type': 'boolean', 'example': '{% if IsPhD %}', 'group': '1. Thông tin chung'},
            
            # Note for dynamic fields
            {'key': 'extra_*',         'type': 'dynamic', 'example': 'Tùy biến theo Schema ĐCCTHP', 'group': '10. Trường mở rộng'},
        ]




    def validate_template(self, template_path: str) -> dict:
        """
        Kiểm tra template: liệt kê placeholder, phát hiện key không hợp lệ.
        Returns dict {'placeholders': [...], 'errors': [...], 'valid': bool}
        """
        try:
            from docxtpl import DocxTemplate
        except ImportError:
            return {'valid': False, 'errors': ['docxtpl chưa được cài đặt'], 'placeholders': []}

        try:
            tpl = DocxTemplate(template_path)
            # Lấy toàn bộ text một cách an toàn
            full_text = ""
            doc = tpl.get_docx()
            if doc:
                if getattr(doc, 'paragraphs', None):
                    full_text = ' '.join(p.text for p in doc.paragraphs if p)
                if getattr(doc, 'tables', None):
                    for table in doc.tables:
                        if getattr(table, 'rows', None):
                            for row in table.rows:
                                if getattr(row, 'cells', None):
                                    for cell in row.cells:
                                        if cell and getattr(cell, 'paragraphs', None):
                                            full_text += ' ' + ' '.join(p.text for p in cell.paragraphs if p)

            # Tìm tất cả {{ key }} và {% ... %}
            jinja_vars = re.findall(r'\{\{\s*([\w.]+)\s*(?:\|[^}]*)?\}\}', full_text)
            jinja_vars += re.findall(r'\{%\s*for\s+\w+\s+in\s+(\w+)\s*%\}', full_text)
            found_keys = sorted(set(jinja_vars))

            valid_keys = {p['key'] for p in self.get_available_placeholders()}
            errors = []
            ph_status = []

            for key in found_keys:
                root = key.split('.')[0]  # Lấy root key (ví dụ: "clo" từ "clo.Code")
                is_valid = root in valid_keys
                ph_status.append({'key': key, 'valid': is_valid})
                if not is_valid:
                    errors.append(f"Key '{key}' không tìm thấy trong danh sách placeholder hợp lệ.")

            return {
                'valid': len(errors) == 0,
                'placeholders': ph_status,
                'errors': errors,
                'total_keys': len(found_keys),
            }
        except Exception as e:
            return {'valid': False, 'errors': [str(e)], 'placeholders': []}


class TemplateService:
    """
    CRUD cho word_template_v2 trong database.
    + Upload/delete template files từ word_templates/.
    """

    def __init__(self, db):
        self.db = db
        self.engine = TemplateEngine(db)
        _ensure_template_dir()

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def get_all(self) -> List[dict]:
        rows = self.db.conn.execute(
            "SELECT * FROM word_template_v2 ORDER BY la_mac_dinh DESC, ten"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_default(self) -> Optional[dict]:
        row = self.db.conn.execute(
            "SELECT * FROM word_template_v2 WHERE la_mac_dinh=1 LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def get_by_id(self, tpl_id: int) -> Optional[dict]:
        row = self.db.conn.execute(
            "SELECT * FROM word_template_v2 WHERE id=?", (tpl_id,)
        ).fetchone()
        return dict(row) if row else None

    def upload(self, source_path: str, ten: str, mo_ta: str = '') -> int:
        """
        Upload template file vào thư mục word_templates/ và lưu metadata vào DB.
        Returns: id của template mới
        """
        _ensure_template_dir()
        filename = os.path.basename(source_path)
        dest = os.path.join(TEMPLATE_DIR, filename)

        # Validate trước khi upload
        validation = self.engine.validate_template(source_path)

        # Copy file
        shutil.copy2(source_path, dest)

        placeholders_json = json.dumps(
            [p['key'] for p in validation['placeholders']],
            ensure_ascii=False
        )

        with self.db.transaction():
            cur = self.db.conn.execute("""
                INSERT INTO word_template_v2(ten, mo_ta, file_path, placeholders, ngay_tao)
                VALUES(?,?,?,?,?)
            """, (ten, mo_ta, dest, placeholders_json, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        return cur.lastrowid

    def set_default(self, tpl_id: int):
        """Đặt 1 template làm mặc định."""
        with self.db.transaction():
            self.db.conn.execute("UPDATE word_template_v2 SET la_mac_dinh=0")
            self.db.conn.execute("UPDATE word_template_v2 SET la_mac_dinh=1 WHERE id=?", (tpl_id,))

    def delete(self, tpl_id: int):
        """Xóa template (record + file nếu không bị tham chiếu)."""
        tpl = self.get_by_id(tpl_id)
        if not tpl:
            return
        with self.db.transaction():
            self.db.conn.execute("DELETE FROM word_template_v2 WHERE id=?", (tpl_id,))
        # Xóa file nếu có và không còn template khác dùng
        if tpl.get('file_path') and os.path.exists(tpl['file_path']):
            still_used = self.db.conn.execute(
                "SELECT id FROM word_template_v2 WHERE file_path=?", (tpl['file_path'],)
            ).fetchone()
            if not still_used:
                try:
                    os.remove(tpl['file_path'])
                except OSError:
                    pass

    def update_name(self, tpl_id: int, ten: str, mo_ta: str = ''):
        with self.db.transaction():
            self.db.conn.execute(
                "UPDATE word_template_v2 SET ten=?, mo_ta=?, ngay_cap_nhat=? WHERE id=?",
                (ten, mo_ta, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tpl_id)
            )

    # ── Export ───────────────────────────────────────────────────────────────

    def export_with_template(self, hp_id: int, tpl_id: int, output_path: str) -> bool:
        """Export đề cương dùng template đã chọn."""
        tpl = self.get_by_id(tpl_id)
        if not tpl:
            raise ValueError(f"Template id={tpl_id} không tồn tại")
        if not tpl.get('file_path') or not os.path.exists(tpl['file_path']):
            raise FileNotFoundError(f"File template không tồn tại: {tpl.get('file_path')}")
        return self.engine.render(hp_id, tpl['file_path'], output_path)

    def export_with_default(self, hp_id: int, output_path: str) -> bool:
        """Export dùng template mặc định (fallback về builtin nếu không có)."""
        default = self.get_default()
        if default:
            return self.export_with_template(hp_id, default['id'], output_path)
        # Fallback về engine builtin (word_export_service)
        from services.word_export_service import export_dccthp
        data = self.engine.build_context(hp_id)
        return export_dccthp(data, output_path)

    def validate_template_file(self, template_path: str) -> dict:
        """Validate trực tiếp từ đường dẫn."""
        return self.engine.validate_template(template_path)

    def get_placeholders_help(self) -> List[dict]:
        """Trả về danh sách placeholder để hiển thị trong UI."""
        return self.engine.get_available_placeholders()
