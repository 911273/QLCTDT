# core/event_bus.py
"""
EventBus — Singleton pub/sub dùng trong nội bộ app.

Dùng để SchemaManagerPanel notify DCEditorSection reload
mà không cần truyền callback lồng nhau.

Events được dùng trong hệ thống:
  'schema.changed'     — khi thêm/sửa/xóa schema       (kwargs: schema_id)
  'section.changed'    — khi thêm/sửa/xóa/reorder sec  (kwargs: schema_id)
  'field.changed'      — khi thêm/sửa/xóa field         (kwargs: section_id, schema_id)
  'field.col.changed'  — khi sửa cột của bảng           (kwargs: field_def_id)
  'de_cuong.saved'     — khi lưu dữ liệu đề cương       (kwargs: dc_id)
"""


class EventBus:
    """Singleton pub/sub EventBus."""

    _instance = None
    _listeners: dict = {}

    @classmethod
    def get(cls) -> 'EventBus':
        """Lấy singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._listeners = {}
        return cls._instance

    def subscribe(self, event: str, callback):
        """Đăng ký lắng nghe một event."""
        self._listeners.setdefault(event, [])
        if callback not in self._listeners[event]:
            self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback):
        """Hủy đăng ký lắng nghe một event."""
        if event in self._listeners:
            self._listeners[event] = [
                cb for cb in self._listeners[event] if cb != callback
            ]

    def emit(self, event: str, **kwargs):
        """Phát sự kiện đến tất cả subscribers."""
        for cb in list(self._listeners.get(event, [])):
            try:
                cb(**kwargs)
            except Exception as e:
                print(f"[EventBus] Error in '{event}' handler {cb}: {e}")

    def clear_all(self):
        """Xóa tất cả listeners (dùng khi test)."""
        self._listeners.clear()

    def list_events(self) -> list:
        """Liệt kê tất cả events đang có subscriber."""
        return [e for e, cbs in self._listeners.items() if cbs]
