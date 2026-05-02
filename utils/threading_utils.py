import threading
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import queue
import time

class BackgroundTask:
    """
    Helper class to run a function in a background thread and update a progress dialog.
    """
    def __init__(self, parent, task_func, title="Đang xử lý...", args=(), kwargs=()):
        self.parent = parent
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.title = title
        
        self.queue = queue.Queue()
        self.is_running = True
        self.result = None
        self.exception = None
        
        # Create Progress Dialog
        self.dialog = tb.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x180")
        self.dialog.resizable(False, False)
        self.dialog.grab_set() # Modal
        self.dialog.transient(parent)
        
        # Center dialog
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        extra_x = (self.dialog.winfo_screenwidth() - w) // 2
        extra_y = (self.dialog.winfo_screenheight() - h) // 2
        self.dialog.geometry(f"+{extra_x}+{extra_y}")
        
        # UI Elements
        self.lbl_status = tb.Label(self.dialog, text="Đang chuẩn bị...", font=("Arial", 10))
        self.lbl_status.pack(pady=(20, 5), padx=20, anchor="w")
        
        self.progress = tb.Progressbar(self.dialog, mode='determinate', bootstyle="info-striped")
        self.progress.pack(fill="x", padx=20, pady=10)
        
        self.lbl_detail = tb.Label(self.dialog, text="", font=("Arial", 9), foreground="gray")
        self.lbl_detail.pack(padx=20, anchor="w")
        
        # Start thread
        self.thread = threading.Thread(target=self._run_task, daemon=True)
        self.thread.start()
        
        # Start checking queue
        self.dialog.after(100, self._check_queue)

    def _run_task(self):
        try:
            # Inject progress_callback if the function accepts it
            if 'progress_callback' in self.task_func.__code__.co_varnames or \
               'progress_callback' in getattr(self.task_func, '__annotations__', {}):
                def callback(current, total, filename, status):
                    self.queue.put(('progress', (current, total, filename, status)))
                
                self.kwargs['progress_callback'] = callback
            
            self.result = self.task_func(*self.args, **self.kwargs)
            self.queue.put(('done', self.result))
        except Exception as e:
            self.exception = e
            self.queue.put(('error', str(e)))

    def _check_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == 'progress':
                    current, total, filename, status = data
                    percent = (current / total) * 100 if total > 0 else 0
                    self.progress['value'] = percent
                    self.lbl_status.config(text=f"Tiến độ: {current}/{total}")
                    self.lbl_detail.config(text=f"Đang xử lý: {filename}")
                elif msg_type == 'done':
                    self.is_running = False
                    self.dialog.destroy()
                    return
                elif msg_type == 'error':
                    self.is_running = False
                    self.dialog.destroy()
                    # Error handling can be done by providing a finish_callback or just letting the user see result
                    return
        except queue.Empty:
            pass
        
        if self.is_running:
            self.dialog.after(50, self._check_queue)

def run_threaded_task(parent, task_func, title="Đang xử lý...", args=(), kwargs={}):
    """Tiện ích chạy tác vụ đa luồng có progress bar."""
    task = BackgroundTask(parent, task_func, title, args, kwargs)
    parent.wait_window(task.dialog)
    if task.exception:
        raise task.exception
    return task.result
