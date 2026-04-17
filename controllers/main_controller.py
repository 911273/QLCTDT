# controllers/main_controller.py

class MainController:
    def __init__(self, hp_service, import_export_service, validation_service, view):
        self.hp_service = hp_service
        self.ie_service = import_export_service
        self.val_service = validation_service
        self.view = view # This is the QLCTDTApp instance (UI)

    def save_current_hp(self, hp_id, full_data, modified_data):
        """
        Xử lý lưu học phần hiện tại - Chỉ lưu các phần bị thay đổi.
        """
        if hp_id is None:
            self.view.show_warning('Cảnh báo', 'Chưa chọn học phần nào.')
            return False

        # 1. Validation (Dùng full_data để check tính toàn vẹn)
        merged_full = {}
        for sec_data in full_data.values():
            if isinstance(sec_data, dict):
                merged_full.update(sec_data)

        sec1_full = full_data.get('sec1', {})
        issues = self.val_service.validate_hp_accuracy(sec1_full, merged_full)
        
        # Cập nhật kết quả vào Validation Panel thay vì hiện popup
        if hasattr(self.view, 'update_validation_results'):
            self.view.update_validation_results(issues)
        
        # Nếu có lỗi nghiêm trọng (type='error'), có thể chặn lưu. 
        # Cảnh báo (type='warning') thì vẫn cho lưu bình thường.
        has_errors = any(i['type'] == 'error' for i in issues)
        if has_errors:
            self.view.show_error('Lỗi quy chuẩn', 'Dữ liệu có lỗi nghiêm trọng không thể lưu. Vui lòng kiểm tra bảng Quy chuẩn.')
            return False

        # 2. Save via Service (Chỉ truyền modified_data)
        try:
            success = self.hp_service.save_hoc_phan_partial(hp_id, modified_data)
            if success:
                h_name = sec1_full.get('ten_viet') or full_data.get('sec1', {}).get('ten_viet', 'Học phần')
                self.view.set_status(f"✔ Đã lưu thành công: {h_name}")
                return True
        except Exception as e:
            self.view.show_error('Lỗi khi lưu', str(e))
            
        return False

    def clone_hp(self, hp_id):
        if not hp_id: return None
        if self.view.ask_yesno('Xác nhận', 'Bạn có chắc muốn sao chép học phần này thành một bản mới?'):
            new_id = self.hp_service.clone_hoc_phan(hp_id)
            self.view.set_status('Đã sao chép học phần thành công.')
            return new_id
        return None

    def delete_hp(self, hp_id, name):
        if not hp_id: return False
        if self.view.ask_yesno('Xác nhận xóa', 
                               f'Xóa học phần:\n"{name}"\n\nThao tác này không thể hoàn tác!'):
            self.hp_service.delete_hoc_phan(hp_id)
            self.view.set_status(f'Đã xóa: {name}')
            return True
        return False

    def export_word(self, hp_id, out_path, mode='builtin', template_path=None):
        try:
            if mode == 'builtin':
                self.ie_service.export_word_builtin(hp_id, out_path)
            else:
                self.ie_service.export_word_template(hp_id, out_path, template_path)
            return True
        except Exception as e:
            self.view.show_error('Lỗi xuất Word', str(e))
            return False

    def export_batch(self, hp_ids, dir_path, template_path=None):
        def _on_progress(cur, total, name, phase):
            self.view.update_progress(cur, total, f"Đang xuất: {name}")

        self.view.show_progress_dialog("Đang xuất hàng loạt...")
        try:
            results = self.ie_service.export_batch(hp_ids, dir_path, template_path, _on_progress)
            self.view.close_progress_dialog()
            self.view.show_info("Kết quả", f"Đã xuất xong {results['success']} file. Lỗi {results['errors']} file.")
            return results
        except Exception as e:
            self.view.close_progress_dialog()
            self.view.show_error("Lỗi xuất hàng loạt", str(e))
            return None

    def import_batch_with_preview(self, file_paths, khoa_id=None):
        if not file_paths: return

        # 1. Parse for preview
        def _on_parse_progress(cur, total, name, phase):
            self.view.update_progress(cur, total, f"Đang quét file: {name}")

        self.view.show_progress_dialog("Đang phân tích các file Word...")
        preview_items = self.ie_service.parse_for_preview(file_paths, _on_parse_progress)
        self.view.close_progress_dialog()

        # 2. Show Preview Dialog
        selected_items = self.view.show_import_preview_dialog(preview_items)
        if not selected_items:
            return

        # 3. Execute Import (Using existing thread utility)
        from utils.threading_utils import run_threaded_task
        try:
            results = run_threaded_task(
                self.view.root,
                self.ie_service.execute_import,
                title="Đang lưu dữ liệu vào Database...",
                args=(selected_items, khoa_id)
            )
            self._on_import_finish(results)
        except Exception as e:
            self.view.show_error("Lỗi khi lưu dữ liệu", str(e))

    def _on_import_finish(self, results):
        msg = f"Đã nhập xong!\nThành công: {results['success']}\nLỗi: {results['errors']}"
        self.view.show_info("Kết quả Nhập", msg)
        # Refresh current view if needed
        if hasattr(self.view, 'refresh_current_view'):
            self.view.refresh_current_view()
        elif hasattr(self.view, 'load_hp_list'):
            self.view.load_hp_list()

    def show_import_history(self):
        history = self.ie_service.db.get_import_export_history()
        self.view.show_history_dialog(history)
