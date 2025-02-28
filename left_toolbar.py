from PyQt6.QtWidgets import (QToolBar, QToolButton, QLabel, QSlider, 
                            QVBoxLayout, QWidget, QHBoxLayout, QComboBox, QDoubleSpinBox, QPushButton,
                            QDockWidget, QFrame, QSizePolicy, QButtonGroup)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QAction, QBrush, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from gpu_tools import (BrightnessContrastTool, SharpenBlurTool,
                     ColorBalanceTool, NoiseReductionTool)
from color_picker_tool import ColorPickerTool
from selection_tool import SelectionTool  # Import the new tool
from style_utils import COLORS, apply_glass_effect

class AdjustmentPanel(QWidget):
    """Widget to display adjustment controls for the active tool"""
    
    valueChanged = pyqtSignal(str, object)  # Use 'object' instead of 'float'
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setStyleSheet("""
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
            }
            QDoubleSpinBox, QComboBox {
                background-color: #444444;
                color: #f0f0f0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QPushButton {
                background-color: #444444;
                color: #f0f0f0;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        # Title label
        self.title_label = QLabel("Adjustments")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.layout.addWidget(self.title_label)
        # No controls by default
        self.clear()
        
    def clear(self):
        """Clear all adjustment controls"""
        # Remove all widgets except title
        for i in reversed(range(1, self.layout.count())):
            item = self.layout.itemAt(i)
            if item is None:
                continue
                
            # Remove widgets
            if item.widget():
                item.widget().deleteLater()
            # Remove layouts recursively
            elif item.layout():
                self.clear_layout(item.layout())
                
        # Add empty label
        self.layout.addWidget(QLabel("Select a tool to see controls"))
        self.layout.addStretch(1)
        
    def clear_layout(self, layout):
        """Clear all items from a layout"""
        if layout is None:
            return
            
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
        
    def set_controls(self, controls_data):
        """Set the adjustment controls based on the tool"""
        self.clear()
        if not controls_data:
            return
        # Update title
        self.title_label.setText(controls_data.get("title", "Adjustments"))
        # Add all parameter inputs (replacing sliders)
        params = controls_data.get("params", [])
        for param_data in params:
            name = param_data.get("name", "")
            min_val = param_data.get("min", -10.0)
            max_val = param_data.get("max", 10.0)
            default_val = param_data.get("default", 0.0)
            step = param_data.get("step", 0.1)
            
            # Create input layout
            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(f"{name}:"))
            
            # Use QDoubleSpinBox instead of slider
            spin_box = QDoubleSpinBox()
            spin_box.setRange(min_val, max_val)
            spin_box.setValue(default_val)
            spin_box.setSingleStep(step)
            spin_box.setDecimals(2)  # Show 2 decimal places
            spin_box.setMinimumWidth(80)
            
            # Add reset button
            reset_btn = QPushButton("Reset")
            reset_btn.setFixedWidth(50)
            reset_btn.clicked.connect(lambda checked=False, sb=spin_box, dv=default_val: sb.setValue(dv))
            
            # Connect spin box to emit value changes
            spin_box.valueChanged.connect(lambda value, n=name: self.valueChanged.emit(n, value))
            
            param_layout.addWidget(spin_box)
            param_layout.addWidget(reset_btn)
            self.layout.addLayout(param_layout)
            
        # Add combo boxes
        combos = controls_data.get("combos", [])
        for combo_data in combos:
            name = combo_data.get("name", "")
            options = combo_data.get("options", [])
            
            # Create combo layout
            combo_layout = QHBoxLayout()
            combo_layout.addWidget(QLabel(f"{name}:"))
            
            # Create combo box
            combo = QComboBox()
            for option in options:
                combo.addItem(option)
                
            # Connect combo to emit signal
            combo.currentTextChanged.connect(
                lambda text, n=name: self.valueChanged.emit(n, text)
            )
            
            combo_layout.addWidget(combo)
            self.layout.addLayout(combo_layout)
            
        # Add apply button
        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(lambda: self.valueChanged.emit("apply", True))
        self.layout.addWidget(apply_button)
        
        # Add stretch at the end
        self.layout.addStretch(1)

class LeftToolbar(QToolBar):
    """Left toolbar for GPU-accelerated image editing tools"""
    
    statusChanged = pyqtSignal(str)
    
    def __init__(self, canvas):
        super().__init__("Image Effects")
        self.canvas = canvas
        self.active_tool = None
        self.tools = []
        self.adjustment_dock = None
        
        # Create a button group so only one tool is active at a time
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_group.buttonClicked.connect(self.on_tool_clicked)
        
        # Set orientation
        self.setOrientation(Qt.Orientation.Vertical)
        
        # Add standard edit actions first (undo/redo)
        self.add_standard_actions()
        
        # Add a separator
        self.addSeparator()
        
        # Add image processing tools
        self.add_tools()
        
        # Add collapse button
        self.collapse_action = QAction("<<", self)
        self.collapse_action.setToolTip("Collapse toolbar")
        self.collapse_action.triggered.connect(self.toggle_collapse)
        self.addAction(self.collapse_action)
        
        # State for collapsed mode
        self.collapsed = False
        self.original_size = None
    
    def add_standard_actions(self):
        """Add standard undo/redo actions at the top of toolbar"""
        # Undo action
        undo_action = QAction("Undo", self)
        undo_action.setIcon(self.create_icon("↶", COLORS["text"]))
        undo_action.setToolTip("Undo (Ctrl+Z)")
        undo_action.triggered.connect(self.canvas.undo)
        self.addAction(undo_action)
        
        # Redo action
        redo_action = QAction("Redo", self)
        redo_action.setIcon(self.create_icon("↷", COLORS["text"]))
        redo_action.setToolTip("Redo (Ctrl+Y)")
        redo_action.triggered.connect(self.canvas.redo)
        self.addAction(redo_action)

    def add_tools(self):
        """Add available image editing tools"""
        # Add GPU-based tools
        self.add_tool(BrightnessContrastTool(self.canvas), self.create_icon("⟐", COLORS["accent"]))
        self.add_tool(SharpenBlurTool(self.canvas), self.create_icon("✦", COLORS["accent"]))
        self.add_tool(ColorBalanceTool(self.canvas), self.create_icon("◑", COLORS["accent"]))
        self.add_tool(NoiseReductionTool(self.canvas), self.create_icon("❄", COLORS["accent"]))
        
        # Add selection tool with "◫" (boxed rectangle) icon
        self.add_tool(SelectionTool(self.canvas), self.create_icon("◫", COLORS["accent_secondary"]))
        
        # Add color picker tool 
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
    
    def toggle_collapse(self):
        """Toggle collapsed state of the toolbar"""
        if not self.collapsed:
            # Save original size before collapsing
            self.original_size = self.sizeHint()
            self.setMaximumWidth(40)  # Collapse to only show icons
            self.collapse_action.setText(">>")
            self.collapse_action.setToolTip("Expand toolbar")
            self.collapsed = True
        else:
            # Restore original size
            self.setMaximumWidth(16777215)  # Default maximum
            self.collapse_action.setText("<<")
            self.collapse_action.setToolTip("Collapse toolbar")
            self.collapsed = False
            
            # Show adjustment panel for active tool if applicable
            if self.active_tool:
                self.show_adjustment_panel(self.active_tool)
                
    def create_adjustment_panel(self):
        """Create or get the existing adjustment dock widget"""
        if self.adjustment_dock is None and hasattr(self.canvas, 'main_window'):
            # Create the panel
            self.adjustment_panel = AdjustmentPanel()
            self.adjustment_panel.valueChanged.connect(self.on_adjustment_value_changed)
            
            # Create a dock widget to contain it
            self.adjustment_dock = QDockWidget("Tool Settings", self.canvas.main_window)
            self.adjustment_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                                           QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                           QDockWidget.DockWidgetFeature.DockWidgetClosable)
            self.adjustment_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | 
                                               Qt.DockWidgetArea.RightDockWidgetArea)
            
            # Create a container widget with styled frame
            container = QFrame()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(self.adjustment_panel)
            
            # Set container as dock widget content
            self.adjustment_dock.setWidget(container)
            
            # Apply glass effect
            apply_glass_effect(container, QColor(COLORS["primary"]), 0.95)
            
            # Add to main window
            self.canvas.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.adjustment_dock)
            
        return self.adjustment_dock
        
    def on_tool_clicked(self, button):
        """Handle tool button clicks"""
        tool_index = self.tool_group.buttons().index(button)
        
        # Check if the same tool is being clicked again (toggle off behavior)
        if self.active_tool and self.active_tool == self.tools[tool_index] and button.isChecked():
            # Uncheck the button to deactivate the tool
            button.setChecked(False)
            self.active_tool.deactivate()
            self.active_tool = None
            
            # Hide adjustment panel
            if self.adjustment_dock:
                self.adjustment_dock.hide()
                
            self.on_status_changed("Tool deactivated")
            return
        
        # Deactivate current tool
        if self.active_tool:
            self.active_tool.deactivate()
            
        # Activate new tool
        if button.isChecked():
            self.active_tool = self.tools[tool_index]
            self.active_tool.activate()
            
            # Show adjustment panel for this tool
            self.show_adjustment_panel(self.active_tool)
            
            # Set status message
            if hasattr(self.active_tool, 'get_name'):
                self.on_status_changed(f"Tool: {self.active_tool.get_name()}")
        else:
            self.active_tool = None
            
            # Hide adjustment panel
            if self.adjustment_dock:
                self.adjustment_dock.hide()
            
    def show_adjustment_panel(self, tool):
        """Show adjustment panel for the selected tool"""
        # Only proceed if tool has controls to display
        if not hasattr(tool, 'get_controls'):
            return
            
        # Get tool controls
        controls = tool.get_controls()
        if not controls:
            return
            
        # Create/get the adjustment dock
        dock = self.create_adjustment_panel()
        
        # Set the controls in the panel
        self.adjustment_panel.set_controls(controls)
        
        # Show the dock
        dock.show()
        dock.raise_()
            
    def on_adjustment_value_changed(self, name, value):
        """Handle adjustment panel value changes"""
        if self.active_tool and hasattr(self.active_tool, 'update_parameter'):
            self.active_tool.update_parameter(name, value)
            
    def on_status_changed(self, status):
        """Handle status change from tools"""
        if hasattr(self.canvas, 'main_window') and hasattr(self.canvas.main_window, 'statusBar'):
            self.canvas.main_window.statusBar.showMessage(status)
