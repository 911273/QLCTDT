# utils/async_worker.py
"""
WorkerPool — Thread pool đơn giản cho tác vụ nặng (batch import/export).
Tốt hơn threading_utils.py hiện tại vì hỗ trợ nhiều task song song và
không block UI thread.
"""
import queue
import threading
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
import traceback


@dataclass
class Task:
    """Đại diện 1 tác vụ nền."""
    fn: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    on_success: Optional[Callable] = None   # callback(result)
    on_error: Optional[Callable] = None     # callback(exception)
    on_progress: Optional[Callable] = None  # callback(current, total, msg)
    task_id: str = ''
    description: str = ''


class WorkerPool:
    """
    Thread pool nhẹ, daemon threads.
    Dùng cho: batch export, batch import, validate nhiều HP.
    """

    def __init__(self, max_workers: int = 2):
        self._queue: queue.Queue = queue.Queue()
        self._active_count = 0
        self._lock = threading.Lock()
        self._workers = []
        self._running = True

        for _ in range(max_workers):
            w = threading.Thread(target=self._worker_loop, daemon=True)
            w.start()
            self._workers.append(w)

    def submit(self, task: Task):
        """Gửi task vào queue để xử lý."""
        if self._running:
            self._queue.put(task)

    def submit_fn(self, fn: Callable, *args,
                  on_success: Callable = None,
                  on_error: Callable = None,
                  description: str = '',
                  **kwargs):
        """Shortcut để submit 1 function nhanh."""
        self.submit(Task(
            fn=fn, args=args, kwargs=kwargs,
            on_success=on_success, on_error=on_error,
            description=description
        ))

    def _worker_loop(self):
        while True:
            try:
                task: Task = self._queue.get(timeout=1)
            except queue.Empty:
                if not self._running:
                    break
                continue

            with self._lock:
                self._active_count += 1

            try:
                # Inject progress_callback nếu function có nhận tham số này
                kwargs = dict(task.kwargs)
                if task.on_progress and 'progress_callback' not in kwargs:
                    try:
                        import inspect
                        sig = inspect.signature(task.fn)
                        if 'progress_callback' in sig.parameters:
                            kwargs['progress_callback'] = task.on_progress
                    except Exception:
                        pass

                result = task.fn(*task.args, **kwargs)

                if task.on_success:
                    try:
                        task.on_success(result)
                    except Exception as e:
                        print(f"[WorkerPool] on_success error: {e}")

            except Exception as e:
                tb_str = traceback.format_exc()
                print(f"[WorkerPool] Task '{task.description}' failed: {e}\n{tb_str}")
                if task.on_error:
                    try:
                        task.on_error(e)
                    except Exception as e2:
                        print(f"[WorkerPool] on_error callback error: {e2}")

            finally:
                with self._lock:
                    self._active_count -= 1
                self._queue.task_done()

    def wait_all(self, timeout: float = 30.0):
        """Đợi tất cả task completed."""
        self._queue.join()

    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    def shutdown(self):
        """Dừng worker pool."""
        self._running = False

    def queue_size(self) -> int:
        return self._queue.qsize()


# Singleton worker pool cho toàn app
_app_pool: Optional[WorkerPool] = None


def get_app_pool() -> WorkerPool:
    """Lấy singleton WorkerPool."""
    global _app_pool
    if _app_pool is None:
        _app_pool = WorkerPool(max_workers=2)
    return _app_pool
