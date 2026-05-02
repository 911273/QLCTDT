import sqlite3
import os
from datetime import datetime

DB_PATH = "qlctdt.db"

def seed_templates():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Template 1
    t1 = ("Template Hiện Đại (Blue Accent)", "Mẫu trình bày chuyên nghiệp, màu xanh chủ đạo, tiêu đề rõ ràng.", 
          "word_templates/Template_Hien_Dai.docx")
    
    # Template 2
    t2 = ("Template Nhanh Gọn (Minimalist)", "Mẫu tối giản, không dùng bảng nhiều, font Arial hiện đại.", 
          "word_templates/Template_Nhanh_Gon.docx")
    
    # Template 3
    t3 = ("Template Kiểm Định (Quality Focus)", "Tập trung vào ma trận CLO/PLO và bảng đánh giá chất lượng.", 
          "word_templates/Template_Kiem_Dinh_Chat_Luong.docx")
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for ten, mo_ta, path in [t1, t2, t3]:
        # Check if exists
        cur.execute("SELECT id FROM word_template_v2 WHERE ten=?", (ten,))
        if not cur.fetchone():
            full_path = os.path.join(os.getcwd(), path).replace("\\", "/")
            cur.execute("""
                INSERT INTO word_template_v2 (ten, mo_ta, file_path, ngay_tao, la_mac_dinh)
                VALUES (?, ?, ?, ?, 0)
            """, (ten, mo_ta, full_path, now))
            print(f"Added template to DB: {ten}")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_templates()
