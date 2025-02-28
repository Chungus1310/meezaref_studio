from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QApplication, QFrame)
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint, QSize

from style_utils import COLORS, apply_glass_effect

class ColorDisplay(QFrame):
    """Widget to display a color sample"""
    
    def __init__(self, color=Qt.GlobalColor.white, parent=None):
        super().__init__(parent)
        self.color = color
        self.setMinimumSize(100, 100)
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        
    def setColor(self, color):
        """Set color to display"""
        self.color = color
        self.update()
        
    def paintEvent(self, event):
        """Paint color sample with checkerboard for transparent colors"""
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw checkerboard for transparent colors
        if self.color.alpha() < 255:
            square_size = 10
            for x in range(0, self.width(), square_size):
                for y in range(0, self.height(), square_size):
                    if (x // square_size + y // square_size) % 2 == 0:
                        painter.fillRect(x, y, square_size, square_size, Qt.GlobalColor.lightGray)
                    else:
                        painter.fillRect(x, y, square_size, square_size, Qt.GlobalColor.white)
        
        # Draw the actual color
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        
        # Draw border
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width()-1, self.height()-1)

class MagnifierView(QFrame):
    """Widget to display magnified view of an area"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(150, 150)
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.pixmap = None
        self.center_pos = QPoint(0, 0)
        self.zoom_factor = 8  # How much to magnify
        
    def setPixmap(self, pixmap, center_pos):
        """Set pixmap to display and center position"""
        self.pixmap = pixmap
        self.center_pos = center_pos
        self.update()
        
    def paintEvent(self, event):
        """Paint magnified view"""
        super().paintEvent(event)
        if not self.pixmap:
            return
            
        painter = QPainter(self)
        
        # Draw zoomed image
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)  # Pixelated zoom
        
        # Calculate source rect (area around cursor) - FIXED to properly center on cursor
        src_size = QSize(self.width() // self.zoom_factor, self.height() // self.zoom_factor)
        src_rect = QRect(
            max(0, self.center_pos.x() - src_size.width() // 2),
            max(0, self.center_pos.y() - src_size.height() // 2),
            src_size.width(),
            src_size.height()
        )
        
        # Ensure source rect stays within pixmap bounds
        if src_rect.right() > self.pixmap.width():
            src_rect.moveLeft(max(0, self.pixmap.width() - src_size.width()))
        if src_rect.bottom() > self.pixmap.height():
            src_rect.moveTop(max(0, self.pixmap.height() - src_size.height()))
        
        # Draw the magnified area
        painter.drawPixmap(self.rect(), self.pixmap, src_rect)
        
        # Draw grid
        painter.setPen(QPen(QColor(0, 0, 0, 100)))
        
        # Draw horizontal grid lines
        cell_height = self.height() / src_size.height()
        for i in range(1, src_size.height()):
            y = int(i * cell_height)
            painter.drawLine(0, y, self.width(), y)
            
        # Draw vertical grid lines
        cell_width = self.width() / src_size.width()
        for i in range(1, src_size.width()):
            x = int(i * cell_width)
            painter.drawLine(x, 0, x, self.height())
            
        # Draw center pixel indicator
        center_rect = QRect(
            int((self.width() - cell_width) / 2),
            int((self.height() - cell_height) / 2),
            int(cell_width),
            int(cell_height)
        )
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(center_rect)

class ColorPopup(QWidget):
    """Popup window to display color information"""
    
    colorPicked = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setWindowTitle("Color Picker")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        
        # Set up UI
        self.setup_ui()
        
        # Apply glass effect
        apply_glass_effect(self, QColor(COLORS["primary_light"]), 0.9)
        
    def setup_ui(self):
        """Set up the UI elements"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Color display
        self.color_display = ColorDisplay()
        main_layout.addWidget(self.color_display)
        
        # Color information
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)  # Increase spacing between color info items
        
        # Hex value with improved layout
        hex_layout = QHBoxLayout()
        hex_label = QLabel("Hex:")
        hex_label.setMinimumWidth(40)
        hex_layout.addWidget(hex_label)
        
        self.hex_label = QLabel("#FFFFFF")
        self.hex_label.setFont(QFont("Consolas", 9))
        # Use a separate container for the value with opaque background
        self.hex_label.setStyleSheet("""
            font-family: monospace;
            font-weight: bold;
            background-color: rgba(40, 40, 40, 0.8);
            color: white;
            padding: 2px 5px;
            border-radius: 2px;
        """)
        self.hex_label.setMinimumWidth(100)
        self.hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hex_layout.addWidget(self.hex_label, 1)  # 1 = stretch factor
        info_layout.addLayout(hex_layout)
        
        # RGB values with improved layout
        rgb_layout = QHBoxLayout()
        rgb_tag = QLabel("RGB:")
        rgb_tag.setMinimumWidth(40)
        rgb_layout.addWidget(rgb_tag)
        
        self.rgb_label = QLabel("255, 255, 255")
        self.rgb_label.setFont(QFont("Consolas", 9))
        self.rgb_label.setStyleSheet("""
            font-family: monospace;
            font-weight: bold;
            background-color: rgba(40, 40, 40, 0.8);
            color: white;
            padding: 2px 5px;
            border-radius: 2px;
        """)
        self.rgb_label.setMinimumWidth(100)
        self.rgb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rgb_layout.addWidget(self.rgb_label, 1)  # 1 = stretch factor
        info_layout.addLayout(rgb_layout)
        
        # HSV values with improved layout
        hsv_layout = QHBoxLayout()
        hsv_tag = QLabel("HSV:")
        hsv_tag.setMinimumWidth(40)
        hsv_layout.addWidget(hsv_tag)
        
        self.hsv_label = QLabel("0°, 0%, 100%")
        self.hsv_label.setFont(QFont("Consolas", 9))
        self.hsv_label.setStyleSheet("""
            font-family: monospace;
            font-weight: bold;
            background-color: rgba(40, 40, 40, 0.8);
            color: white;
            padding: 2px 5px;
            border-radius: 2px;
        """)
        self.hsv_label.setMinimumWidth(100)
        self.hsv_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hsv_layout.addWidget(self.hsv_label, 1)  # 1 = stretch factor
        info_layout.addLayout(hsv_layout)
        
        main_layout.addLayout(info_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)  # Add space between buttons
        
        self.copy_button = QPushButton("Copy Hex")
        self.copy_button.clicked.connect(self.copy_hex_to_clipboard)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        button_layout.addWidget(self.copy_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        button_layout.addWidget(self.close_button)
        
        main_layout.addLayout(button_layout)
        
        # Style window with our modern theme
        self.setStyleSheet(f"""
            QLabel {{
                color: {COLORS["text"]};
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {COLORS["primary"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["text"]}40;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS["accent"]}60;
                border-color: {COLORS["accent"]};
            }}
        """)
        
        # Fixed size to prevent layout issues - smaller now that magnifier is removed
        self.setFixedSize(300, 280)
        
    def update_color(self, color, pixmap=None, pos=None):
        """Update the displayed color and information"""
        if not isinstance(color, QColor):
            color = QColor(color)
            
        # Update color display
        self.color_display.setColor(color)
        
        # Update color information
        self.hex_label.setText(color.name().upper())
        self.rgb_label.setText(f"{color.red()}, {color.green()}, {color.blue()}")
        
        # Calculate HSV
        hue = color.hue()
        saturation = int(color.saturationF() * 100)
        value = int(color.valueF() * 100)
        self.hsv_label.setText(f"{hue if hue >= 0 else 0}°, {saturation}%, {value}%")
        
        # Emit signal
        self.colorPicked.emit(color)
        
    def copy_hex_to_clipboard(self):
        """Copy hex color value to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hex_label.text())
