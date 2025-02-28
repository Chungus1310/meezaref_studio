from PyQt6.QtWidgets import (QMainWindow, QFileDialog, QDockWidget, QVBoxLayout, QWidget, QToolBar, QStatusBar, QGraphicsDropShadowEffect, QLabel, QFrame, QHBoxLayout, QPushButton)
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPainter, QColor, QFontDatabase, QFont
from PyQt6.QtCore import Qt, QSize, QEvent, QPoint, QPropertyAnimation, QEasingCurve
import os
import sys

from canvas import Canvas
from layer_panel import LayerPanel
from left_toolbar import LeftToolbar
from style_utils import COLORS, STYLE_SHEETS, FadeAnimation, apply_glass_effect

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class ImageReferenceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meeza Reference Studio")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set application icon - this is the in-app icon shown in the title bar
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Setup fonts
        self._setup_fonts()
        
        # Apply modern theme
        self.setStyleSheet(STYLE_SHEETS["main_window"])
        
        # Create canvas (central widget)
        self.central_container = QWidget()
        main_layout = QVBoxLayout(self.central_container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)
        
        # Canvas with decorative frame
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("canvasFrame")
        self.canvas_frame.setStyleSheet(f"""
            #canvasFrame {{
                background-color: {COLORS["primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
            }}
        """)
        canvas_layout = QVBoxLayout(self.canvas_frame)
        canvas_layout.setContentsMargins(1, 1, 1, 1)
        canvas_layout.setSpacing(0)
        
        self.canvas = Canvas()
        canvas_layout.addWidget(self.canvas)
        
        main_layout.addWidget(self.canvas_frame, 1)  # 1 = stretch factor
        
        self.setCentralWidget(self.central_container)
        
        # Create layer panel dock widget with styling
        self.layer_panel = LayerPanel(self.canvas)
        self.layers_dock = QDockWidget("Layers")
        self.layers_dock.setWidget(self.layer_panel)
        self.layers_dock.setStyleSheet(STYLE_SHEETS["dock_widget"])
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.layers_dock)
        
        # Apply glass effect to dock widget
        apply_glass_effect(self.layers_dock, QColor(COLORS["primary"]), 0.95)
        
        # Apply fade-in animation
        self.fade_animation = FadeAnimation(self.central_container)
        self.fade_animation.fade_in(0.0, 1.0, 400)  # Smoother, slower fade-in
        
        # Create left toolbar with GPU tools and standard actions
        self.create_left_toolbar()
        
        # Create menus
        self.create_menus()
        
        # Create status bar
        self.statusBar = self._create_status_bar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Enable the paintEvent for glass border effect
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Create collapsible dock buttons
        self._create_collapsible_dock_buttons()
        
    def _setup_fonts(self):
        """Set up custom fonts for the application"""
        # Using system fonts that are likely to exist
        self.header_font = QFont("Segoe UI", 16)
        self.header_font.setBold(True)
        self.normal_font = QFont("Segoe UI", 9)
        
    def _create_status_bar(self):
        """Create a modern status bar"""
        status_bar = QStatusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {COLORS["primary"]};
                color: {COLORS["text_dark"]};
                border-top: 1px solid {COLORS["border"]};
                padding: 4px;
            }}
        """)
        # Apply glass effect
        apply_glass_effect(status_bar, QColor(COLORS["primary"]), 0.95)
        return status_bar
        
    def create_left_toolbar(self):
        """Create the left toolbar with GPU-accelerated tools"""
        self.left_toolbar = LeftToolbar(self.canvas)
        self.left_toolbar.setStyleSheet(STYLE_SHEETS["toolbar"])
        self.left_toolbar.setMovable(False)  # Lock toolbar position
        self.left_toolbar.setIconSize(QSize(28, 28))  # Larger icons
        
        # Add glass effect to toolbar
        apply_glass_effect(self.left_toolbar, QColor(COLORS["primary"]), 0.95)
        
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.left_toolbar)
        
        # Store a direct reference to the window in the canvas
        self.canvas.main_window = self

    def create_menus(self):
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        # Import image action
        import_action = QAction("Import Image", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self.import_image)
        file_menu.addAction(import_action)
        
        # Save canvas action
        save_action = QAction("Save Canvas", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_canvas)
        file_menu.addAction(save_action)
        
        # Load canvas action
        load_action = QAction("Load Canvas", self)
        load_action.setShortcut(QKeySequence("Ctrl+O"))
        load_action.triggered.connect(self.load_canvas)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("Edit")
        
        # Undo action
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self.canvas.undo)
        edit_menu.addAction(undo_action)
        
        # Redo action
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.triggered.connect(self.canvas.redo)
        edit_menu.addAction(redo_action)
        
    def _create_collapsible_dock_buttons(self):
        """Add collapse/expand buttons to dock widgets"""
        # Make right dock widget collapsible
        if hasattr(self, 'layers_dock'):
            # Add a collapse button to the dock title bar
            collapse_btn = QPushButton("<<")
            collapse_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS["primary_light"]};
                    color: {COLORS["text"]};
                    border: 1px solid {COLORS["border"]};
                    border-radius: 3px;
                    max-width: 24px;
                    max-height: 18px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS["accent"]}40;
                }}
            """)
            
            # Store original width
            self.layers_dock_width = self.layers_dock.width()
            
            # Connect to toggle function
            collapse_btn.clicked.connect(self._toggle_layer_dock)
            
            # Add to dock title bar
            self.layers_dock.setTitleBarWidget(collapse_btn)
            
    def _toggle_layer_dock(self):
        """Toggle the layers dock visibility"""
        if self.layers_dock.width() > 50:  # If expanded
            # Save width before collapsing
            self.layers_dock_width = self.layers_dock.width()
            # Collapse
            self.layers_dock.setMaximumWidth(24)
            self.layers_dock.titleBarWidget().setText(">>")
        else:  # If collapsed
            # Expand
            self.layers_dock.setMaximumWidth(16777215)  # Default maximum
            self.layers_dock.resize(self.layers_dock_width, self.layers_dock.height())
            self.layers_dock.titleBarWidget().setText("<<")
            
    def import_image(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Images",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        
        if file_paths:
            for path in file_paths:
                self.canvas.add_image_layer(path)
                self.layer_panel.update_layers()
            self.statusBar.showMessage(f"Imported {len(file_paths)} image(s)")
            
    def save_canvas(self):
        """Save the current canvas state to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Canvas",
            "",
            "Canvas Files (*.canvas)"
        )
        
        if file_path:
            # Ensure the file has the correct extension
            if not file_path.endswith(".canvas"):
                file_path += ".canvas"
                
            if self.canvas.save_canvas(file_path):
                self.statusBar.showMessage(f"Canvas saved to {file_path}")
            else:
                self.statusBar.showMessage("Failed to save canvas")
                
    def load_canvas(self):
        """Load a canvas from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Canvas",
            "",
            "Canvas Files (*.canvas)"
        )
        
        if file_path:
            if self.canvas.load_canvas(file_path):
                self.layer_panel.update_layers()
                self.statusBar.showMessage(f"Canvas loaded from {file_path}")
            else:
                self.statusBar.showMessage("Failed to load canvas")
                
    def closeEvent(self, event):
        """Clean up resources when closing the application"""
        # Deactivate any active tools to clean up threads
        if hasattr(self, 'left_toolbar') and self.left_toolbar.active_tool:
            self.left_toolbar.active_tool.deactivate()
        
        # Clean up canvas resources
        if hasattr(self, 'canvas'):
            self.canvas.closeEvent(event)
            
        # Call parent closeEvent
        super().closeEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event to draw glass-effect borders"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Let the original painting happen
        painter.end()
