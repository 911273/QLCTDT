import pytest
import os
import docx

from services.word_export_service import export_dccthp
from services.word_import_service import import_dccthp
from services.word_validator import validate_data, DCCTValidationError

# Giả lập dữ liệu chuẩn
def valid_base_data():
    return {
        "trinh_do": "Đại học",
        "ten_tv": "HỌC PHẦN MẪU",
        "ten_ta": "SAMPLE COURSE",
        "don_vi": "KHOA ĐÀO TẠO ĐẠI CƯƠNG",
        "ma_hp": "DC101",
        "so_tc": 3,
        "loai_hp": "Bắt buộc",
        "tinh_chat": "Lý thuyết",
        "loai_hinh": "Trực tiếp",
        "phan_bo_gio": {"ly_thuyet": 30, "tu_hoc": 120},
        "giang_vien_chinh": [{"tt": 1, "hoc_ham_vi_ten": "TS. A"}],
        "clo": [{"ma": "CLO1", "mo_ta": "Phân tích được abc...", "muc_do": "R"}],
        "thanh_phan_dg": [
            {"thanh_phan": "Giữa kỳ", "trong_so": 30},
            {"thanh_phan": "Cuối kỳ", "trong_so": 70}
        ],
        "rubrics": [{"ma": "R1", "tieu_chi": [{"ten": "T1", "trong_so": 100}]}],
        "ai_policy_level": 1,
    }

def test_t5_validation_clo_hieu():
    data = valid_base_data()
    data['clo'][0]['mo_ta'] = "Hiểu các quy luật cơ bản"
    with pytest.raises(DCCTValidationError) as exc:
        export_dccthp(data, "test.docx")
    assert "Biết/Hiểu/Nắm vững" in str(exc.value)

def test_t6_validation_tong_gio():
    data = valid_base_data()
    data['phan_bo_gio']['tu_hoc'] = 100  # tổng = 130 != 150
    with pytest.raises(DCCTValidationError) as exc:
        export_dccthp(data, "test.docx")
    assert "Tổng giờ" in str(exc.value)

def test_t1_export_lt_dh(tmp_path):
    data = valid_base_data()
    output_path = tmp_path / "t1_lt.docx"
    export_dccthp(data, str(output_path))
    assert output_path.exists()
    assert output_path.stat().st_size > 10000  # > 10KB

def test_t2_export_hon_hop_dh(tmp_path):
    data = valid_base_data()
    data['tinh_chat'] = "Hỗn hợp"
    data['phan_bo_gio'] = {"ly_thuyet": 10, "thuc_hanh_tn": 10, "tu_hoc": 130}
    # Thêm content TH
    data['noi_dung_chi_tiet'] = [
        {"tuan": "1", "noi_dung": "LT Bài 1", "gio_lt": "(5/0/0/0)"},
        {"tuan": "2", "noi_dung": "TH Bài 1", "gio_lt": "(0/0/0/TH)"}
    ]
    output_path = tmp_path / "t2_hh.docx"
    export_dccthp(data, str(output_path))
    assert output_path.exists()
    
    # Check bảng 6A và 6B tồn tại
    doc = docx.Document(str(output_path))
    texts = [p.text for p in doc.paragraphs]
    assert any("6.1. Nội dung lý thuyết" in t for t in texts)
    assert any("6.2. Nội dung thực hành/thí nghiệm" in t for t in texts)

def test_t3_export_tieu_luan_ts(tmp_path):
    data = valid_base_data()
    data['trinh_do'] = "Tiến sĩ"
    data['tinh_chat'] = "Tiểu luận tổng quan"
    data['mo_ta_tieu_luan'] = "Review lý thuyết chuyên ngành"
    
    output_path = tmp_path / "t3_ts.docx"
    export_dccthp(data, str(output_path))
    
    doc = docx.Document(str(output_path))
    texts = [p.text for p in doc.paragraphs]
    assert any("Tiểu luận tổng quan" in t for t in texts)

def test_t4_export_chuyen_de_ts(tmp_path):
    data = valid_base_data()
    data['trinh_do'] = "Tiến sĩ"
    data['tinh_chat'] = "Chuyên đề Tiến sĩ"
    
    output_path = tmp_path / "t4_ts.docx"
    export_dccthp(data, str(output_path))
    assert output_path.exists()

def test_t7_import_sample_word(tmp_path):
    # Dùng output T1 sinh ra doc mẫu để parse
    data = valid_base_data()
    output_path = tmp_path / "sample.docx"
    export_dccthp(data, str(output_path))
    
    imported = import_dccthp(str(output_path))
    assert "trinh_do" in imported
    assert "mo_ta" in imported

def test_t8_export_import_diff(tmp_path):
    data = valid_base_data()
    output_path = tmp_path / "t8_diff.docx"
    export_dccthp(data, str(output_path))
    
    imported = import_dccthp(str(output_path))
    # Test Name parsing as basic check
    assert imported['ten_tv'].upper() == data['ten_tv']

def test_t9_rubric_table(tmp_path):
    data = valid_base_data()
    output_path = tmp_path / "t9_rubric.docx"
    export_dccthp(data, str(output_path))
    
    doc = docx.Document(str(output_path))
    headers = [c.text for t in doc.tables for r in t.rows for c in r.cells]
    assert "Xuất sắc (9–10)" in headers
    
def test_t10_checklist_page(tmp_path):
    data = valid_base_data()
    output_path = tmp_path / "t10_checklist.docx"
    export_dccthp(data, str(output_path))
    
    doc = docx.Document(str(output_path))
    texts = [p.text for p in doc.paragraphs]
    assert any("PHIẾU TỰ KIỂM TRA ĐỀ CƯƠNG" in t for t in texts)
    assert any("VI. XÁC NHẬN GV" in t for t in texts)
