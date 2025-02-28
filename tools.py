from PyQt6.QtCore import QObject, pyqtSignal, Qt, QPoint, QEvent
from PyQt6.QtGui import QCursor, QPixmap

class Tool(QObject):
    """Base class for all drawing and editing tools"""
    
    # Signal to emit when the tool status changes (for status bar)
    statusChanged = pyqtSignal(str)
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.active = False
        self.cursor = QCursor(Qt.CursorShape.PointingHandCursor)  # Default cursor as pointing hand
        
    def activate(self):
        """Activate the tool"""
        self.active = True
        self.canvas.setCursor(self.cursor)
        
    def deactivate(self):
        """Deactivate the tool"""
        self.active = False
        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
        
    def mouse_press(self, event):
        """Handle mouse press events"""
        # Base implementation does nothing
        pass
        
    def mouse_move(self, event):
        """Handle mouse move events"""
        # Base implementation does nothing
        pass
        
    def mouse_release(self, event):
        """Handle mouse release events"""
        # Base implementation does nothing
        pass
        
    def get_name(self):
        """Return the name of the tool"""
        return self.__class__.__name__
        
    def get_tooltip(self):
        """Return tooltip for toolbar button"""
        return self.get_name()
        
    def get_icon(self):
        """Return icon for toolbar button"""
        return None
