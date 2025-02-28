from PyQt6.QtWidgets import (QToolBar, QLabel, QComboBox, QPushButton, QSlider, 
                           QButtonGroup, QToolButton, QGraphicsView, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtProperty, pyqtSignal

from color_picker_tool import ColorPickerTool
from style_utils import COLORS, STYLE_SHEETS, GlowEffect, ButtonAnimation

class AnimatedToolButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self._pressed = False
        self._base_color = QColor(COLORS["primary_light"])
        self._hover_color = QColor(COLORS["accent"] + "60")  # 60% opacity
        self._press_color = QColor(COLORS["accent"] + "A0")  # 60% opacity
        self._current_color = self._base_color
        
        # Add shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(8)
        self.shadow.setColor(QColor(COLORS["glass_shadow"]))
        self.shadow.setOffset(1, 1)
        self.setGraphicsEffect(self.shadow)
        
        # Size and styling
        self.setMinimumSize(36, 36)
        
    def enterEvent(self, event):
        self._hovered = True
        self._current_color = self._hover_color
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self._current_color = self._base_color
        self.update()
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._current_color = self._press_color
            self.update()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self._current_color = self._hover_color if self._hovered else self._base_color
            self.update()
        super().mouseReleaseEvent(event)
        
    def paintEvent(self, event):
        # Add custom painting before the standard paint
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw our custom background
        if self.isChecked():
            painter.setBrush(QColor(COLORS["accent"] + "80"))
        else:
            painter.setBrush(self._current_color)
            
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        
        # Let the standard painting happen
        painter.end()
        
        # Call standard painting
        super().paintEvent(event)

class ToolBar(QToolBar):
    """Main toolbar with common application tools"""
    
    statusChanged = pyqtSignal(str)
    
    def __init__(self, canvas):
        super().__init__("Main Toolbar")
        self.canvas = canvas
        self.active_tool = None
        self.tools = []
        
        # Create a button group for tools that are mutually exclusive
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_group.buttonClicked.connect(self.on_tool_clicked)
        
        # Add standard actions
        self.add_standard_actions()
        
        # Add tools
        self.add_tools()
        
    def add_standard_actions(self):
        """Add standard file/edit actions"""
        # Undo action
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setIcon(self.create_icon("↶", COLORS["text"]))
        undo_action.triggered.connect(self.canvas.undo)
        self.addAction(undo_action)
        
        # Redo action
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setIcon(self.create_icon("↷", COLORS["text"]))
        redo_action.triggered.connect(self.canvas.redo)
        self.addAction(redo_action)
        
        # Add separator
        self.addSeparator()
        
        # Import image action
        import_action = QAction("Import Image", self)
        import_action.setShortcut("Ctrl+I")
        import_action.setIcon(self.create_icon("⊕", COLORS["text"]))
        import_action.triggered.connect(self.import_image)
        self.addAction(import_action)
        
        # Add separator
        self.addSeparator()
    
    def add_tools(self):
        """Add standard editing tools"""
        # Add color picker
        self.add_tool(ColorPickerTool(self.canvas), self.create_icon("⦿", COLORS["accent_secondary"]))
        
    def add_tool(self, tool, icon=None):
        """Add a tool to the toolbar"""
        button = QToolButton()
        button.setCheckable(True)
        
        # Set a default icon if none provided
        if icon:
            button.setIcon(icon)
        else:
            # Create generic tool icon
            button.setIcon(self.create_icon("T", COLORS["text"]))
            
        # Set tooltip
        if hasattr(tool, 'get_tooltip'):
            button.setToolTip(tool.get_tooltip())
        elif hasattr(tool, 'get_name'):
            button.setToolTip(tool.get_name())
        else:
            button.setToolTip(tool.__class__.__name__)
            
        # Add button to group and toolbar
        self.tool_group.addButton(button)
        self.addWidget(button)
        
        # Store tool reference
        self.tools.append(tool)
        tool.statusChanged = self.statusChanged
        
        # Connect signal from tool if it exists
        if hasattr(tool, 'statusChanged'):
            tool.statusChanged.connect(self.on_status_changed)
        
    def create_icon(self, symbol, color):
        """Create a simple icon with text symbol"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw symbol centered in icon
        font = painter.font()
        font.setPointSize(18)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, symbol)
        painter.end()
        
        return QIcon(pixmap)
        
    def on_tool_clicked(self, button):
        """Handle tool button clicks"""
        tool_index = self.tool_group.buttons().index(button)
        
        # Deactivate current tool
        if self.active_tool:
            self.active_tool.deactivate()
            
        # Activate new tool
        if button.isChecked():
            self.active_tool = self.tools[tool_index]
            self.active_tool.activate()
            
            # Set status message
            if hasattr(self.active_tool, 'get_name'):
                self.on_status_changed(f"Tool: {self.active_tool.get_name()}")
        else:
            self.active_tool = None
            
    def on_status_changed(self, status):
        """Handle status change from tools"""
        if hasattr(self.canvas, 'main_window') and hasattr(self.canvas.main_window, 'statusBar'):
            self.canvas.main_window.statusBar.showMessage(status)
            
    def import_image(self):
        """Import an image"""
        if hasattr(self.canvas, 'main_window'):
            self.canvas.main_window.import_image()
