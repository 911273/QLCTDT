import collections

class UndoManager:
    """Quản lý hoàn tác/làm lại cho các tập dữ liệu."""
    def __init__(self, maxlen=50):
        self.undo_stack = collections.deque(maxlen=maxlen)
        self.redo_stack = collections.deque(maxlen=maxlen)
        self._current_state = None

    def push(self, state):
        """Lưu một trạng thái mới."""
        if self._current_state is not None:
            if self._current_state == state:
                return # Trùng trạng thái hiện tại
            self.undo_stack.append(self._current_state)
        
        self._current_state = state
        self.redo_stack.clear()

    def undo(self):
        """Hoàn tác: trả về trạng thái trước đó."""
        if not self.undo_stack:
            return None
        
        state = self.undo_stack.pop()
        self.redo_stack.append(self._current_state)
        self._current_state = state
        return state

    def redo(self):
        """Làm lại: trả về trạng thái sau đó."""
        if not self.redo_stack:
            return None
        
        state = self.redo_stack.pop()
        self.undo_stack.append(self._current_state)
        self._current_state = state
        return state

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._current_state = None
