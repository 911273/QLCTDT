# utils/event_bus.py
"""
EventBus (Observer Pattern) — thay thế dirty flag rải rác khắp sections.
Dùng để thông báo thay đổi dữ liệu mà không cần coupling trực tiếp.
"""
import threading
from typing import Callable, Dict, List, Any


class EventBus:
    """
    Lightweight publish-subscribe message bus.
    Thread-safe. Callbacks được gọi trong thread gọi publish().
    
    Sử dụng:
        # Subscribe
        EventBus.subscribe('data_changed', my_callback)
        EventBus.subscribe('hp_selected', lambda hp_id: ...)
        
        # Publish (từ section khi có thay đổi)
        EventBus.publish('data_changed', hp_id=1, section='CLO')
        
        # Unsubscribe
        EventBus.unsubscribe('data_changed', my_callback)
    """

    _listeners: Dict[str, List[Callable]] = {}
    _lock = threading.RLock()

    @classmethod
    def subscribe(cls, event: str, callback: Callable):
        """Đăng ký lắng nghe 1 event."""
        with cls._lock:
            if event not in cls._listeners:
                cls._listeners[event] = []
            if callback not in cls._listeners[event]:
                cls._listeners[event].append(callback)

    @classmethod
    def unsubscribe(cls, event: str, callback: Callable):
        """Hủy đăng ký."""
        with cls._lock:
            if event in cls._listeners:
                try:
                    cls._listeners[event].remove(callback)
                except ValueError:
                    pass

    @classmethod
    def publish(cls, event: str, **kwargs):
        """
        Phát sự kiện tới tất cả subscribers.
        Lỗi trong 1 callback sẽ được log nhưng không dừng các callback khác.
        """
        with cls._lock:
            callbacks = list(cls._listeners.get(event, []))

        for cb in callbacks:
            try:
                cb(**kwargs)
            except Exception as e:
                print(f"[EventBus] Error in '{event}' callback {cb.__name__}: {e}")

    @classmethod
    def clear(cls, event: str = None):
        """Xóa tất cả listeners của 1 event (hoặc toàn bộ nếu event=None)."""
        with cls._lock:
            if event:
                cls._listeners.pop(event, None)
            else:
                cls._listeners.clear()

    @classmethod
    def list_events(cls) -> List[str]:
        """Liệt kê các event đang có subscriber — dùng để debug."""
        with cls._lock:
            return list(cls._listeners.keys())


# ── Các event chuẩn trong ứng dụng ──────────────────────────────────────────

class AppEvents:
    """Hằng số tên event để tránh lỗi typo."""
    HP_SELECTED         = 'hp_selected'         # hp_id: int
    HP_SAVED            = 'hp_saved'             # hp_id: int
    HP_DELETED          = 'hp_deleted'           # hp_id: int
    DATA_CHANGED        = 'data_changed'         # hp_id: int, section: str
    VALIDATION_DONE     = 'validation_done'      # hp_id: int, result: dict
    IMPORT_DONE         = 'import_done'          # hp_id: int, logs: list
    EXPORT_DONE         = 'export_done'          # hp_id: int, path: str
    VERSION_CREATED     = 'version_created'      # hp_id: int, version_id: int
    STATUS_MESSAGE      = 'status_message'       # msg: str, level: str
    PROGRESS_UPDATE     = 'progress_update'      # current: int, total: int, msg: str
