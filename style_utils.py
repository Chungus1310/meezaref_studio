from PyQt6.QtWidgets import QGraphicsOpacityEffect, QToolButton, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPainter, QColor, QBrush, QPalette
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QSize, Qt, QTimer, pyqtProperty, QObject, QRect

# Modern color scheme
COLORS = {
    "primary": "#1e1e1e",
    "primary_light": "#2d2d2d",
    "primary_dark": "#1a1a1a",  # Add missing primary_dark color
    "secondary": "#252526",
    "accent": "#007acc",
    "accent_secondary": "#0098ff",  # Add missing accent_secondary color
    "text": "#ffffff",
    "text_dark": "#cccccc",
    "border": "#3f3f3f",
    "canvas_bg": "#1e1e1e",  # Add missing color definition
    "success": "#4ec9b0",
    "warning": "#ce9178",
    "error": "#f44747"
}

# Define style sheets for various components
STYLE_SHEETS = {
    "main_window": f"""
        QMainWindow {{
            background-color: {COLORS["primary"]};
            border: 1px solid {COLORS["border"]};
        }}
    """,
    
    "dock_widget": f"""
        QDockWidget {{
            background-color: {COLORS["primary"]};
            border: 1px solid {COLORS["border"]};
            color: {COLORS["text"]};
        }}
        
        QDockWidget::title {{
            background-color: {COLORS["primary_light"]};
            padding: 5px;
            border-bottom: 1px solid {COLORS["border"]};
        }}
        
        QDockWidget::close-button, QDockWidget::float-button {{
            border: none;
            background: {COLORS["primary_light"]};
            padding: 0px;
        }}
        
        QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
            background: {COLORS["accent"]}40;
        }}
    """,
    
    "toolbar": f"""
        QToolBar {{
            background-color: {COLORS["primary"]};
            border: none;
            spacing: 5px;
            padding: 5px;
        }}
        
        QToolButton {{
            background-color: {COLORS["primary_light"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QToolButton:hover {{
            background-color: {COLORS["accent"]}40;
            border-color: {COLORS["accent"]};
        }}
        
        QToolButton:checked {{
            background-color: {COLORS["accent"]};
            border-color: {COLORS["accent"]};
        }}
    """,
    
    "canvas": f"""
        QGraphicsView {{
            background-color: {COLORS["canvas_bg"]};
            border: none;
            border-radius: 8px;
        }}
    """,
    
    "layer_panel": f"""
        QListWidget {{
            background-color: {COLORS["primary"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 6px;
            outline: none;
        }}
        QListWidget::item {{
            background-color: {COLORS["primary_light"]};
            color: {COLORS["text"]};
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 4px 8px;
            margin: 2px;
        }}
        QListWidget::item:selected {{
            background-color: {COLORS["accent"]}40;
            border: 1px solid {COLORS["accent"]};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {COLORS["primary_light"]}90;
            border: 1px solid {COLORS["border"]};
        }}
        
        QDoubleSpinBox, QSpinBox, QCheckBox {{
            background-color: {COLORS["primary_light"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 4px;
            padding: 2px 4px;
        }}
        
        QPushButton {{
            background-color: {COLORS["primary_light"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: 6px;
            padding: 6px 12px;
        }}
        QPushButton:hover {{
            background-color: {COLORS["accent"]}40;
            border: 1px solid {COLORS["accent"]};
        }}
        
        QLabel {{
            color: {COLORS["text"]};
        }}
        
        QSlider {{
            height: 20px;
        }}
        QSlider::groove:horizontal {{
            border: 1px solid {COLORS["border"]};
            height: 6px;
            background-color: {COLORS["primary_light"]};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background-color: {COLORS["accent"]};
            border: none;
            width: 12px;
            height: 12px;
            margin: -3px 0;
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            background-color: {COLORS["accent_secondary"]};
            transform: scale(1.1);
        }}
    """
}

# Animation classes
class GlowEffect(QGraphicsOpacityEffect):
    def __init__(self, parent):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.7)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setOpacity(0.7)
    
    def start(self):
        self.animation.start()

class ButtonAnimation:
    def __init__(self, button):
        self.button = button
        self.hover_animation = QPropertyAnimation(button, b"styleSheet")
        self.hover_animation.setDuration(150)
        self.pressed_animation = QPropertyAnimation(button, b"styleSheet")
        self.pressed_animation.setDuration(100)
        
    def on_hover(self, hovered):
        if hovered:
            self.hover_animation.setStartValue(self.button.styleSheet())
            self.hover_animation.setEndValue(f"""
                background-color: {COLORS["accent"]}40;
                border: 1px solid {COLORS["accent"]};
                border-radius: 6px;
                padding: 6px;
            """)
            self.hover_animation.start()
        else:
            self.hover_animation.setStartValue(self.button.styleSheet())
            self.hover_animation.setEndValue(f"""
                background-color: {COLORS["primary_light"]};
                border: 1px solid {COLORS["text"]}40;
                border-radius: 6px;
                padding: 6px;
            """)
            self.hover_animation.start()

class FadeAnimation(QObject):
    def __init__(self, target_widget):
        super().__init__()
        self.target = target_widget
        self.opacity = 0.0
        self.target.setStyleSheet(f"opacity: {self.opacity};")

    def get_opacity(self):
        return self.opacity

    def set_opacity(self, opacity):
        self.opacity = opacity
        self.target.setStyleSheet(f"opacity: {self.opacity};")
        self.target.update()

    opacity_prop = pyqtProperty(float, get_opacity, set_opacity)

    def fade_in(self, start=0.0, end=1.0, duration=250):
        self.animation = QPropertyAnimation(self, b"opacity_prop")
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def fade_out(self, start=1.0, end=0.0, duration=250):
        self.animation = QPropertyAnimation(self, b"opacity_prop")
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

# Helper function to apply glass effect stylesheet to any widget
def apply_glass_effect(widget, bg_color=QColor(40, 40, 48), opacity=0.9):
    """Apply a modern glass effect to a widget"""
    # Set background opacity
    color = QColor(bg_color)
    color.setAlphaF(opacity)
    
    # Set stylesheet for glass-like appearance
    widget.setStyleSheet(widget.styleSheet() + f"""
        background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {int(opacity * 255)});
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
    """)
    
    # Add drop shadow for depth
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setColor(QColor(0, 0, 0, 70))
    shadow.setOffset(0, 2)
    widget.setGraphicsEffect(shadow)

# Add AnimatedToolButton to the exports
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
