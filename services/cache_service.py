# services/cache_service.py
"""TTL Cache đơn giản cho QLCTDT — tránh query DB lặp với dữ liệu tĩnh."""
import time
import threading
from typing import Any, Optional


class TTLCache:
    """
    Thread-safe in-memory cache với tự động expire theo TTL (giây).
    Không cần Redis — đủ dùng cho ứng dụng desktop SQLite.
    """

    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: Thời gian cache mặc định tính bằng giây (mặc định 5 phút)
        """
        self._store: dict = {}
        self._ttl = default_ttl
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Lấy giá trị từ cache. Trả về None nếu miss hoặc expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry and time.monotonic() < entry['expires']:
                return entry['value']
            if entry:
                del self._store[key]  # cleanup expired entry
            return None

    def set(self, key: str, value: Any, ttl: int = None):
        """Lưu giá trị vào cache với TTL tùy chỉnh."""
        with self._lock:
            self._store[key] = {
                'value': value,
                'expires': time.monotonic() + (ttl or self._ttl)
            }

    def invalidate(self, key: str):
        """Xóa 1 key khỏi cache."""
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str):
        """Xóa tất cả keys bắt đầu bằng prefix (dùng khi save/update HP)."""
        with self._lock:
            keys_to_del = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_del:
                del self._store[k]

    def clear(self):
        """Xóa toàn bộ cache."""
        with self._lock:
            self._store.clear()

    def cleanup_expired(self):
        """Dọn dẹp các entry đã expire — gọi định kỳ để tránh memory leak."""
        with self._lock:
            now = time.monotonic()
            keys = [k for k, v in self._store.items() if now >= v['expires']]
            for k in keys:
                del self._store[k]

    def stats(self) -> dict:
        """Thống kê trạng thái cache để debug."""
        with self._lock:
            now = time.monotonic()
            active = sum(1 for v in self._store.values() if now < v['expires'])
            return {
                'total': len(self._store),
                'active': active,
                'expired': len(self._store) - active,
            }


# Singleton instance dùng chung toàn app
_app_cache: Optional[TTLCache] = None


def get_app_cache() -> TTLCache:
    """Lấy instance cache singleton của app."""
    global _app_cache
    if _app_cache is None:
        _app_cache = TTLCache(default_ttl=120)  # 2 phút cho HP data
    return _app_cache
