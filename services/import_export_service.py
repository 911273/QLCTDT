import json
import os
import word_import
import word_export
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class ImportExportService:
    def __init__(self, db):
        self.db = db

    def export_word_builtin(self, hp_id, out_path):
        return word_export.export_builtin(self.db, hp_id, out_path)

    def export_word_template(self, hp_id, out_path, template_path):
        return word_export.export_template(self.db, hp_id, out_path, template_path)

    def export_batch(self, hp_ids, dir_path, template_path=None, progress_callback=None):
        results = word_export.export_batch(self.db, hp_ids, dir_path, template_path, progress_callback)
        # Log to DB
        self.db.add_import_export_log(
            type='EXPORT',
            total=len(hp_ids),
            success=results['success'],
            error=results['errors'],
            details_json=json.dumps(results['details'], ensure_ascii=False),
            user_action=f'Export {len(hp_ids)} học phần to {dir_path}'
        )
        return results

    def import_word_single(self, file_path):
        parsed = word_import.parse_docx(file_path)
        hp_id = word_import.import_single(self.db, parsed)
        # Log
        self.db.add_import_export_log(
            type='IMPORT',
            total=1,
            success=1 if hp_id else 0,
            error=0 if hp_id else 1,
            details_json=json.dumps([{'file': os.path.basename(file_path), 'status': 'ok' if hp_id else 'error'}], ensure_ascii=False),
            user_action=f'Import single file: {os.path.basename(file_path)}'
        )
        return hp_id, parsed

    def parse_for_preview(self, file_paths, progress_callback=None):
        """Parse files và xác định trạng thái (Mới/Cập nhật/Trùng)."""
        preview_results = []
        total = len(file_paths)
        
        def _parse_one(fpath):
            try:
                data = word_import.parse_docx(fpath)
                ma = data['thong_tin'].get('ma', '')
                status = 'NEW'
                existing_hp = None
                
                if ma:
                    # Check by MA
                    row = self.db.conn.execute("SELECT id, ten_viet FROM hoc_phan WHERE ma=?", (ma,)).fetchone()
                    if row:
                        status = 'UPDATE'
                        existing_hp = dict(row)
                else:
                    # Check by NAME if MA is missing
                    row = self.db.conn.execute("SELECT id, ma FROM hoc_phan WHERE ten_viet=?", (data['ten_viet'],)).fetchone()
                    if row:
                        status = 'UPDATE'
                        existing_hp = dict(row)
                
                return {
                    'file_path': fpath,
                    'file_name': os.path.basename(fpath),
                    'data': data,
                    'status': status,
                    'existing_hp': existing_hp,
                    'selected': True
                }
            except Exception as e:
                return {
                    'file_path': fpath,
                    'file_name': os.path.basename(fpath),
                    'error': str(e),
                    'status': 'ERROR',
                    'selected': False
                }

        counter = 0
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_parse_one, fp) for fp in file_paths]
            for future in as_completed(futures):
                res = future.result()
                counter += 1
                if progress_callback:
                    progress_callback(counter, total, res['file_name'], 'parsing')
                preview_results.append(res)
        
        return preview_results

    def execute_import(self, preview_items, khoa_id=None, progress_callback=None):
        """Thực hiện import các mục đã chọn."""
        selected_items = [item for item in preview_items if item.get('selected')]
        total = len(selected_items)
        results = {'success': 0, 'errors': 0, 'details': []}
        
        counter = 0
        for item in selected_items:
            try:
                hp_id = word_import.import_single(self.db, item['data'], khoa_id=khoa_id)
                results['success'] += 1
                results['details'].append({
                    'file': item['file_name'], 'status': 'ok', 'hp_id': hp_id,
                    'ten': item['data']['ten_viet'], 'ma': item['data']['thong_tin'].get('ma', '')
                })
            except Exception as e:
                results['errors'] += 1
                results['details'].append({
                    'file': item['file_name'], 'status': 'error', 'error': str(e)
                })
            
            counter += 1
            if progress_callback:
                progress_callback(counter, total, item['file_name'], 'importing')
        
        # Log to DB
        self.db.add_import_export_log(
            type='IMPORT',
            total=total,
            success=results['success'],
            error=results['errors'],
            details_json=json.dumps(results['details'], ensure_ascii=False),
            user_action=f'Batch import {total} files'
        )
        return results
