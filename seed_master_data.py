# seed_master_data.py
from db import Database
import os

def seed():
    db = Database()
    
    # 1. KHOA / BỘ MÔN
    khoas = [
        ('NLM', 'Khoa Năng lượng mới'),
        ('KHCT', 'Bộ môn Khoa học chính trị'),
        ('KHTN', 'Bộ môn Khoa học tự nhiên'),
        ('NN', 'Bộ môn Ngoại ngữ'),
        ('CNTT', 'Khoa Công nghệ thông tin'),
        ('GDTC', 'Bộ môn Giáo dục thể chất'),
        ('CK&ĐL', 'Khoa Cơ khí & Động lực'),
        ('ĐK&TĐH', 'Khoa Điều khiển & Tự động hóa'),
        ('KTĐ', 'Khoa Kỹ thuật điện'),
        ('XD', 'Khoa Xây dựng'),
        ('QLCN&NL', 'Khoa Quản lý công nghiệp & Năng lượng')
    ]
    khoa_map = {}
    for ma, ten in khoas:
        kid = db.add_khoa(ma, ten)
        khoa_map[ma] = kid

    # 2. CDR CTĐT (PLO & PI)
    pis = [
        ('PI1.1', 'Hiểu và vận dụng tốt các kiến thức khoa học cơ bản, cơ sở ngành để giải quyết bài toán kỹ thuật.'),
        ('PI1.2', 'Vận dụng các kiến thức khoa học cơ bản để giải quyết các vấn đề thuộc lĩnh vực công nghệ kỹ thuật nhiệt - lạnh.'),
        ('PI1.3', 'Khả năng phát hiện, phân tích và giải quyết các vấn đề kỹ thuật mới trong lĩnh vực nhiệt - lạnh.'),
        ('PI1.4', 'Vận dụng các kiến thức chuyên môn vào việc tính toán thiết kế, lắp đặt, vận hành... trong các nhà máy nhiệt điện.'),
        ('PI1.5', 'Vận dụng chuyên môn vào tính toán thiết kế, lắp đặt... hệ thống làm lạnh, đông, ĐHKK.'),
        ('PI1.6', 'Vận dụng chuyên môn vào tính toán thiết kế, lắp đặt... hệ thống sấy, lò công nghiệp.'),
        ('PI1.7', 'Khả năng nghiên cứu, phân tích, dự báo đánh giá kinh tế năng lượng, quản lý hệ thống.'),
        ('PI2.1', 'Năng lực thực hiện các thí nghiệm, đo lường; phân tích diễn giải kết quả cải tiến quy trình.'),
        ('PI2.2', 'Năng lực thiết kế chuyên nghiệp về các thiết bị, hệ thống trong lĩnh vực nhiệt - lạnh.'),
        ('PI2.3', 'Làm việc hiệu quả với vai trò thành viên hoặc trưởng nhóm kỹ thuật.'),
        ('PI2.4', 'Khả năng viết, thuyết trình, sử dụng công cụ biểu đồ, hình ảnh trao đổi thông tin.'),
        ('PI2.5', 'Sử dụng thành thạo ít nhất 01 ngoại ngữ trong công việc.'),
        ('PI3.1', 'Có đạo đức và trách nhiệm nghề nghiệp cao, tôn trọng sự khác biệt.'),
        ('PI3.2', 'Có hiểu biết và hành động phù hợp để bảo vệ môi trường và xã hội.'),
        ('PI3.3', 'Có ý thức về đảm bảo chất lượng, tiến độ và liên tục cải tiến.'),
        ('PI3.4', 'Có ý thức không ngừng học hỏi và tự định hướng phát triển sự nghiệp.')
    ]
    for ma, mo_ta in pis:
        db.add_cdr_ctdt(ma, mo_ta)

    # 3. GIẢNG VIÊN CHI TIẾT
    gvs = [
        {
            'ho_ten': 'Nguyễn Quốc Uy', 'ngay_sinh': '27/09/1974', 'cmnd_cccd': '033074000121',
            'trinh_do_chuyen_mon': 'TS', 'co_so_dao_tao': 'Việt Nam', 'nam_tot_nghiep': 2019,
            'nganh_dao_tao': 'Kỹ thuật nhiệt', 'ngay_tuyen_dung': '01/04/2011', 'ma_so_bao_hiem': 'HC 0104039579',
            'so_nam_kinh_nghiem': 12, 'khoa_id': khoa_map['NLM']
        },
        {
            'ho_ten': 'Vũ Duy Thuận', 'ngay_sinh': '15/05/1981', 'cmnd_cccd': '013365837',
            'trinh_do_chuyen_mon': 'Tiến sĩ', 'co_so_dao_tao': 'Việt Nam', 'nam_tot_nghiep': 2018,
            'nganh_dao_tao': 'Kỹ thuật điều khiển và tự động hóa', 'ngay_tuyen_dung': '01/09/2004', 'ma_so_bao_hiem': 'HC 0112081688',
            'so_nam_kinh_nghiem': 19, 'khoa_id': khoa_map['NLM']
        },
        {
            'ho_ten': 'Nguyễn Đăng Toản', 'ngay_sinh': '05/04/1978', 'cmnd_cccd': '013220823',
            'trinh_do_chuyen_mon': 'Tiến sĩ', 'co_so_dao_tao': 'Pháp', 'nam_tot_nghiep': 2010,
            'nganh_dao_tao': 'Điện và tự động hóa', 'ngay_tuyen_dung': '05/09/2001', 'ma_so_bao_hiem': 'HC 0102001624',
            'so_nam_kinh_nghiem': 22, 'khoa_id': khoa_map['NLM']
        },
        {
            'ho_ten': 'Phạm Quang Vũ', 'ngay_sinh': '19/10/1988', 'cmnd_cccd': '038088014652',
            'trinh_do_chuyen_mon': 'Tiến sĩ', 'co_so_dao_tao': 'Hàn Quốc', 'nam_tot_nghiep': 2019,
            'nganh_dao_tao': 'Kỹ thuật nhiệt lạnh và điều hòa không khí', 'ngay_tuyen_dung': '05/09/2019', 'ma_so_bao_hiem': 'HC 0131675451',
            'so_nam_kinh_nghiem': 4, 'khoa_id': khoa_map['NLM']
        },
        {
            'ho_ten': 'Nguyễn Công Hân', 'ngay_sinh': '25/06/1948', 'cmnd_cccd': '010410592',
            'trinh_do_chuyen_mon': 'Tiến sĩ', 'co_so_dao_tao': 'Séc', 'nam_tot_nghiep': 1986,
            'nganh_dao_tao': 'Kỹ thuật điều khiển và tự động hóa', 'ngay_tuyen_dung': '02/05/2012',
            'so_nam_kinh_nghiem': 11, 'khoa_id': khoa_map['NLM']
        },
        {
            'ho_ten': 'Trần Văn Phú', 'ngay_sinh': '19/04/1941', 'cmnd_cccd': '010410637', 'chuc_danh': 'Giáo sư',
            'nam_phong_chuc_danh': '2002', 'trinh_do_chuyen_mon': 'Tiến sĩ', 'co_so_dao_tao': 'Ucraina',
            'nam_tot_nghiep': 1975, 'nganh_dao_tao': 'Kỹ thuật nhiệt', 'ngay_tuyen_dung': '01/02/2018',
            'so_nam_kinh_nghiem': 5, 'khoa_id': khoa_map['NLM']
        }
    ]
    gv_map = {}
    for gv_data in gvs:
        gid = db.add_giang_vien(gv_data)
        gv_map[gv_data['ho_ten']] = gid

    # 4. HỌC PHẦN (Căn bản & chuyên ngành)
    hps = [
        # Kỳ 1 - Đại cương
        ('003923', 'Triết học Mác - Lênin', 3, 45, 0, 'KHCT', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('004545', 'Toán cao cấp 1', 3, 45, 0, 'KHTN', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('004547', 'Ứng dụng CNTT cơ bản', 3, 39, 12, 'CNTT', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('002018', 'Pháp luật đại cương', 2, 30, 0, 'KHCT', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('004552', 'Năng lượng cho phát triển bền vững', 2, 30, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', None, 'Cơ sở ngành'),
        # Kỳ 2 - Đại cương
        ('003137', 'Tiếng Anh 1', 4, 60, 0, 'NN', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('004546', 'Toán cao cấp 2', 3, 45, 0, 'KHTN', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('003612', 'Vật lý đại cương', 3, 45, 0, 'KHTN', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        ('003925', 'Kinh tế chính trị Mác - Lênin', 2, 30, 0, 'KHCT', 'Công nghệ kỹ thuật nhiệt', None, 'Đại cương'),
        # Cơ sở ngành
        ('003773', 'Nhiệt động kỹ thuật', 4, 60, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', None, 'Cơ sở ngành'),
        ('003777', 'Truyền nhiệt', 4, 60, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', None, 'Cơ sở ngành'),
        # Chuyên ngành Điện lạnh
        ('004836', 'Điều hòa không khí và thông gió', 3, 45, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', 'Điện lạnh', 'Chuyên ngành'),
        ('001337', 'Kỹ thuật lạnh', 3, 45, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', 'Điện lạnh', 'Chuyên ngành'),
        # Chuyên ngành Nhiệt điện
        ('001873', 'Nhà máy nhiệt điện', 3, 45, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', 'Nhiệt điện', 'Chuyên ngành'),
        ('004838', 'Lò hơi', 3, 45, 0, 'NLM', 'Công nghệ kỹ thuật nhiệt', 'Nhiệt điện', 'Chuyên ngành'),
    ]
    hp_map = {}
    for ma, ten, tc, lt, th, kma, nganh, cn, khoi in hps:
        hp_id = db.add_hoc_phan({
            'ma': ma, 'ten_viet': ten, 'so_tin_chi': tc,
            'gio_lt': lt, 'gio_th_tn': th, 'khoa_id': khoa_map[kma]
        })
        hp_map[ma] = hp_id

    # 5. CHƯƠNG TRÌNH ĐÀO TẠO (CTĐT)
    ctdt_id = db.add_ctdt('Công nghệ kỹ thuật nhiệt', 'Đại học', khoa_map['NLM'])
    
    # 6. GÁN HỌC PHẦN VÀO CTĐT (ctdt_hoc_phan)
    ctdt_links = []
    for ma, ten, tc, lt, th, kma, nganh, cn, khoi in hps:
        ctdt_links.append({
            'hp_id': hp_map[ma],
            'khoi_kien_thuc': khoi or 'Khác',
            'chuyen_nganh': cn,
            'thu_tu': 1
        })
    db.set_hp_to_ctdt(ctdt_id, ctdt_links)

    # 5. HỌC LIỆU (TÀI LIỆU BANK)
    tls = [
        ('Nhiệt động kỹ thuật', 'Phạm Lê Dần', 2005, 'Nxb Khoa học và Kỹ thuật', 14, '003773'),
        ('Truyền nhiệt', 'Bùi Hải, Trương Nam Hưng', 2010, 'Nxb Khoa học và Kỹ thuật', 1, '003777'),
        ('Thiết bị đo lường nhiệt', 'Võ Huy Toàn', 2008, 'Nxb Khoa học và Kỹ thuật', 5, '004860'),
        ('Máy nhiệt Tập 1+2', 'Nguyễn Công Hân', 2002, 'Nxb Khoa học và Kỹ thuật', 11, '001873'),
        ('Lò hơi Tập 1+2', 'Nguyễn Sỹ Mão', 2006, 'Nxb Khoa học và Kỹ thuật', 9, '004838'),
        ('Lò công nghiệp', 'Phạm Văn Trí', 2008, 'Nxb Khoa học và Kỹ thuật', 2, '001477'),
        ('Nhà máy nhiệt điện Tập 1+2', 'Nguyễn Công Hân', 2002, 'Nxb Khoa học và Kỹ thuật', 11, '001873'),
        ('Xử lý nước & làm sạch hơi', 'Nguyễn Sỹ Mão', 2011, 'Nxb Khoa học và Kỹ thuật', 1, '003672')
    ]
    for ten, tac_gia, nam, nha_xb, sl, ma_hp in tls:
        tl_id = db.add_tai_lieu({
            'ten': ten, 'tac_gia': tac_gia, 'nam_xb': nam, 'nha_xb': nha_xb,
            'so_luong_thu_vien': sl, 'loai': 'Giáo trình'
        })
        # If the course exists in our seed, link it
        if ma_hp in hp_map:
            db.set_hoc_lieu(hp_map[ma_hp], [{'loai': 'chinh', 'so_thu_tu': 1, 'noi_dung': f"{ten} - {tac_gia}", 'tai_lieu_id': tl_id}])

    # 6. PHÂN CÔNG GIẢNG DẠY (SAMPLES)
    # TS Nguyễn Quốc Uy dạy các môn chuyên ngành
    uy_môn = ['004836', '000885', '001477', '002575', '003773']
    for ma in uy_môn:
        if ma in hp_map:
            db.set_gv_of_hp(hp_map[ma], [{'gv_id': gv_map['Nguyễn Quốc Uy'], 'vai_tro': 'chinh', 'thu_tu': 1}])

            db.set_gv_of_hp(hp_map[ma], [{'gv_id': gv_map['Nguyễn Quốc Uy'], 'vai_tro': 'chinh', 'thu_tu': 1}])

    print("Success: Master data seeded with CTDT mappings.")

if __name__ == "__main__":
    seed()
