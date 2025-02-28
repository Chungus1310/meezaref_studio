class History:
    def __init__(self, max_history=50):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = max_history
        
    def add_command(self, action, *args):
        """Add a command to the history stack"""
        command = (action, *args)
        self.undo_stack.append(command)
        
        # Clear the redo stack when a new command is added
        self.redo_stack.clear()
        
        # Limit history size
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
            
    def undo(self):
        """Undo the last command and return it"""
        if self.undo_stack:
            command = self.undo_stack.pop()
            self.redo_stack.append(command)
            return command
        return None
        
    def redo(self):
        """Redo the last undone command and return it"""
        if self.redo_stack:
            command = self.redo_stack.pop()
            self.undo_stack.append(command)
            return command
        return None
        
    def clear(self):
        """Clear all history"""
        self.undo_stack.clear()
        self.redo_stack.clear()
