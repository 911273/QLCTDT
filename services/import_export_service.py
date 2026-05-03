import json
import os
import word_import
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from services.template_service import TemplateEngine
from services.word_export_service import export_dccthp

class ImportExportService:
    def __init__(self, db):
        self.db = db
        self.tpl_engine = TemplateEngine(db)

    def export_word_builtin(self, hp_id, out_path):
        data = self.tpl_engine.build_context(hp_id)
        return export_dccthp(data, out_path)

    def export_word_template(self, hp_id, out_path, template_path):
        return self.tpl_engine.render(hp_id, template_path, out_path)

    def export_batch(self, hp_ids, dir_path, template_path=None, progress_callback=None):
        results = {'success': 0, 'errors': 0, 'details': []}
        for i, hp_id in enumerate(hp_ids):
            if progress_callback:
                progress_callback(i + 1, len(hp_ids), str(hp_id), 'exporting')
            try:
                out_path = os.path.join(dir_path, f"DCCTHP_{hp_id}.docx")
                if template_path:
                    self.export_word_template(hp_id, out_path, template_path)
                else:
                    self.export_word_builtin(hp_id, out_path)
                results['success'] += 1
                results['details'].append({'hp_id': hp_id, 'status': 'ok'})
            except Exception as e:
                results['errors'] += 1
                results['details'].append({'hp_id': hp_id, 'status': 'error', 'error': str(e)})

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
        hp_id, local_logs = self._save_imported_data(parsed['data'])
        # Log
        self.db.add_import_export_log(
            type='IMPORT',
            total=1,
            success=1 if hp_id else 0,
            error=0 if hp_id else 1,
            details_json=json.dumps([{
                'file': os.path.basename(file_path), 
                'status': 'ok' if hp_id else 'error',
                'logs': local_logs
            }], ensure_ascii=False),
            user_action=f'Import single file: {os.path.basename(file_path)}'
        )
        return hp_id, parsed

    def _save_imported_data(self, data, khoa_id=None):
        """P2 Unified Persistence Logic using Repositories."""
        hp_data = data.get('hp', {})
        if khoa_id: hp_data['khoa_id'] = khoa_id

        local_logs = []
        hp_id = None

        # 1. HP Info
        try:
            ma = hp_data.get('ma')
            if ma:
                existing = self.db.hp_repo.search(ma)
                # Find exact match by code
                match = next((h for h in existing if h['ma'] == ma), None)
                if match:
                    hp_id = match['id']
                    self.db.hp_repo.update(hp_id, hp_data)
                    local_logs.append(("success", "Thông tin chung", f"Cập nhật HP mã {ma}."))
            
            if not hp_id:
                hp_id = self.db.hp_repo.create(hp_data)
                local_logs.append(("success", "Thông tin chung", "Tạo mới học phần."))
        except Exception as e:
            local_logs.append(("error", "Thông tin chung", f"Lỗi HP: {e}"))
            return None, local_logs

        # 2. Related data
        sections = [
            ('giang_vien', self.db.hp_repo.set_gv, "Giảng viên"),
            ('muc_tieu', self.db.hp_repo.set_muc_tieu, "Mục tiêu"),
            ('clos', self.db.hp_repo.set_clo, "CLO"),
            ('hoc_lieu', self.db.hp_repo.set_hoc_lieu, "Học liệu"),
            ('noi_dung', lambda id_, items: self.db.hp_repo.set_noi_dung(id_, 'lt', items), "Nội dung"),
            ('danh_gia', self.db.hp_repo.set_ke_hoach_kt, "Kế hoạch đánh giá"),
            ('rubrics', self.db.hp_repo.set_rubric, "Rubrics")
        ]

        for key, func, label in sections:
            items = data.get(key, [])
            if items:
                try:
                    func(hp_id, items)
                    local_logs.append(("success", label, f"Đã nhập {len(items)} mục."))
                except Exception as e:
                    local_logs.append(("error", label, f"Lỗi: {e}"))

        return hp_id, local_logs


    def parse_for_preview(self, file_paths, progress_callback=None):
        """Parse files và xác định trạng thái (Mới/Cập nhật/Trùng)."""
        preview_results = []
        total = len(file_paths)
        
        def _parse_one(fpath):
            try:
                full_res = word_import.parse_docx(fpath)
                data = full_res.get('data', {})
                logs = full_res.get('logs', [])
                
                ma = data.get('hp', {}).get('ma', '')
                status = 'NEW'
                existing_hp = None
                
                if ma:
                    # Check by MA using repo
                    existing = self.db.hp_repo.search(ma)
                    match = next((h for h in existing if h['ma'] == ma), None)
                    if match:
                        status = 'UPDATE'
                        existing_hp = match

                
                return {
                    'file_path': fpath,
                    'file_name': os.path.basename(fpath),
                    'data': data,
                    'logs': logs,
                    'status': status,
                    'existing_hp': existing_hp,
                    'selected': True if status != 'ERROR' else False
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
            # P0 Stability: Transaction per file to prevent "all-or-nothing" failure
            try:
                with self.db.transaction():
                    hp_id, local_logs = self._save_imported_data(item['data'], khoa_id=khoa_id)
                    results['success'] += 1 if hp_id else 0
                    if not hp_id: results['errors'] += 1
                    
                    results['details'].append({
                        'file': item['file_name'], 
                        'status': 'ok' if hp_id else 'error', 
                        'hp_id': hp_id,
                        'ten': item['data'].get('hp', {}).get('ten_viet') or item['file_name'],
                        'ma': item['data'].get('hp', {}).get('ma', ''),
                        'logs': local_logs
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
