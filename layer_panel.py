from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QPushButton, QHBoxLayout, QSlider, QCheckBox, 
                           QLabel, QMenu, QAbstractItemView, QDoubleSpinBox,
                           QFrame, QScrollArea)
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter, QPixmap, QLinearGradient, QFont
from PyQt6.QtCore import Qt, pyqtSlot, QSize

from style_utils import COLORS, STYLE_SHEETS, apply_glass_effect

class LayerItemWidget(QFrame):
    """Custom widget for layer items with modern design"""
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setObjectName("layerItem")
        self.setStyleSheet(f"""
            #layerItem {{
                background-color: {COLORS["primary_light"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                margin: 2px;
                padding: 4px;
            }}
        """)
        
        self.setFixedHeight(40)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Visibility toggle
        self.visibility_btn = QPushButton()
        self.visibility_btn.setFixedSize(24, 24)
        self.visibility_btn.setCheckable(True)
        self.visibility_btn.setChecked(layer.is_visible)
        self.visibility_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:checked {{
                background-color: {COLORS["accent"]}40;
                border: 1px solid {COLORS["accent"]};
            }}
        """)
        # Create eye icon
        eye_icon = QPixmap(24, 24)
        eye_icon.fill(Qt.GlobalColor.transparent)
        painter = QPainter(eye_icon)
        painter.setPen(QColor(COLORS["text"]))
        painter.setBrush(QColor(COLORS["text"]))
        painter.drawEllipse(8, 10, 8, 8)
        painter.setBrush(QColor(COLORS["primary_light"]))
        painter.drawEllipse(10, 12, 4, 4)
        painter.end()
        self.visibility_btn.setIcon(QIcon(eye_icon))
        layout.addWidget(self.visibility_btn)
        
        # Layer name
        self.name_label = QLabel(layer.name)
        self.name_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        layout.addWidget(self.name_label, 1)  # 1 = stretch factor
        
        # Lock toggle
        self.lock_btn = QPushButton()
        self.lock_btn.setFixedSize(24, 24)
        self.lock_btn.setCheckable(True)
        self.lock_btn.setChecked(layer.is_locked)
        self.lock_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 12px;
            }}
            QPushButton:checked {{
                background-color: {COLORS["accent_secondary"]}40;
                border: 1px solid {COLORS["accent_secondary"]};
            }}
        """)
        # Create lock icon
        lock_icon = QPixmap(24, 24)
        lock_icon.fill(Qt.GlobalColor.transparent)
        painter = QPainter(lock_icon)
        painter.setPen(QColor(COLORS["text"]))
        painter.drawRoundedRect(7, 12, 10, 8, 2, 2)
        painter.drawRect(9, 8, 6, 4)
        painter.end()
        self.lock_btn.setIcon(QIcon(lock_icon))
        layout.addWidget(self.lock_btn)

class LayerPanel(QWidget):
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.updating_ui = False  # Flag to prevent recursive signal handling
        self.collapsed = False
        
        # Connect to canvas layer changes
        self.canvas.layerChanged.connect(self.update_layers)
        
        # Main layout with modern look
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Title and collapse button
        header_layout = QHBoxLayout()
        title = QLabel("Layers")
        title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {COLORS["text"]};
            padding-bottom: 8px;
        """)
        header_layout.addWidget(title, 1)  # 1 = stretch factor
        
        # Collapse button
        self.collapse_btn = QPushButton("<<")
        self.collapse_btn.setStyleSheet(f"""
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
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.collapse_btn)
        
        main_layout.addLayout(header_layout)
        
        # Content container (for easy showing/hiding when collapsed)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        
        # Layer list with modern scrollable area
        list_container = QFrame()
        list_container.setObjectName("listContainer")
        list_container.setStyleSheet(f"""
            #listContainer {{
                background-color: {COLORS["primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
            }}
        """)
        # Set minimum width to prevent collapse when empty
        list_container.setMinimumWidth(200)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(1, 1, 1, 1)
        
        self.layer_list = QListWidget()
        self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.layer_list.setStyleSheet(STYLE_SHEETS["layer_panel"])
        self.layer_list.setIconSize(QSize(32, 32))
        self.layer_list.itemClicked.connect(self.on_layer_selected)
        self.layer_list.model().rowsMoved.connect(self.on_rows_moved)
        self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layer_list.setUniformItemSizes(True)
        
        list_layout.addWidget(self.layer_list)
        content_layout.addWidget(list_container, 1)  # 1 = stretch factor
        
        # Layer controls
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_frame.setStyleSheet(f"""
            #controlsFrame {{
                background-color: {COLORS["primary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(8)
        
        # Layer action buttons
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        
        # Add layer button
        self.add_btn = self._create_button("Add", "➕")
        self.add_btn.setToolTip("Add a new empty layer")
        self.add_btn.clicked.connect(self.add_empty_layer)
        actions_layout.addWidget(self.add_btn)
        
        # Remove layer button
        self.remove_btn = self._create_button("Remove", "➖")
        self.remove_btn.setToolTip("Remove selected layer")
        self.remove_btn.clicked.connect(self.remove_selected_layer)
        actions_layout.addWidget(self.remove_btn)
        
        # Duplicate layer button
        self.duplicate_btn = self._create_button("Duplicate", "📋")
        self.duplicate_btn.setToolTip("Duplicate selected layer")
        self.duplicate_btn.clicked.connect(self.duplicate_selected_layer)
        actions_layout.addWidget(self.duplicate_btn)
        
        controls_layout.addLayout(actions_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        separator.setMaximumHeight(1)
        controls_layout.addWidget(separator)
        
        # Layer properties
        # Opacity control
        opacity_header = self._create_property_header("Opacity")
        controls_layout.addWidget(opacity_header)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        self.opacity_label.setStyleSheet(f"color: {COLORS['text']}; min-width: 40px;")
        opacity_layout.addWidget(self.opacity_label)
        
        controls_layout.addLayout(opacity_layout)
        
        # Scale controls
        scale_header = self._create_property_header("Scale")
        controls_layout.addWidget(scale_header)
        
        scale_layout = QHBoxLayout()
        scale_layout.setContentsMargins(0, 0, 0, 0)
        
        scale_layout.addWidget(QLabel("X:"))
        self.scale_x_spin = QDoubleSpinBox()
        self.scale_x_spin.setRange(0.1, 10.0)
        self.scale_x_spin.setSingleStep(0.1)
        self.scale_x_spin.setValue(1.0)
        self.scale_x_spin.valueChanged.connect(self.on_scale_x_changed)
        scale_layout.addWidget(self.scale_x_spin)
        
        scale_layout.addWidget(QLabel("Y:"))
        self.scale_y_spin = QDoubleSpinBox()
        self.scale_y_spin.setRange(0.1, 10.0)
        self.scale_y_spin.setSingleStep(0.1)
        self.scale_y_spin.setValue(1.0)
        self.scale_y_spin.valueChanged.connect(self.on_scale_y_changed)
        scale_layout.addWidget(self.scale_y_spin)
        
        controls_layout.addLayout(scale_layout)
        
        # Visibility checkbox
        visibility_layout = QHBoxLayout()
        visibility_layout.addWidget(QLabel("Visible:"))
        self.visible_cb = QCheckBox()
        self.visible_cb.setChecked(True)
        self.visible_cb.stateChanged.connect(self.on_visibility_changed)
        visibility_layout.addWidget(self.visible_cb)
        controls_layout.addLayout(visibility_layout)
        
        # Lock layer checkbox
        lock_layout = QHBoxLayout()
        lock_layout.addWidget(QLabel("Lock:"))
        self.lock_cb = QCheckBox()
        self.lock_cb.stateChanged.connect(self.on_lock_changed)
        lock_layout.addWidget(self.lock_cb)
        controls_layout.addLayout(lock_layout)
        
        content_layout.addWidget(controls_frame)
        
        # Add content widget to main layout
        main_layout.addWidget(self.content_widget, 1)
        
        # Initialize the UI
        self.update_layers()
    
    def toggle_collapse(self):
        """Toggle between collapsed and expanded states"""
        if not self.collapsed:
            # Collapse
            self.content_widget.hide()
            self.collapse_btn.setText(">>")
            self.collapsed = True
        else:
            # Expand
            self.content_widget.show()
            self.collapse_btn.setText("<<")
            self.collapsed = False
            
    def _create_button(self, text, icon):
        """Helper to create styled buttons"""
        btn = QPushButton(text)
        btn.setIcon(QIcon(icon))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["primary_light"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 4px 8px;
                color: {COLORS["text"]};
            }}
            QPushButton:hover {{
                background-color: {COLORS["primary_dark"]};
            }}
        """)
        return btn
    
    def _create_property_header(self, text):
        """Helper to create property headers"""
        header = QLabel(text)
        header.setStyleSheet(f"""
            font-size: 12px;
            font-weight: bold;
            color: {COLORS["text"]};
            padding-bottom: 4px;
        """)
        return header
    
    def update_layers(self):
        """Update the layer list UI from the canvas layers"""
        self.updating_ui = True  # Flag to prevent signals during UI update
        
        try:
            self.layer_list.clear()
            
            # Add layers in reverse order (top to bottom)
            for i, layer in enumerate(reversed(self.canvas.layers)):
                item = QListWidgetItem()
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                
                # Update item text with appropriate icons
                self._update_layer_item_text(item, layer)
                
                self.layer_list.addItem(item)
            
            # Select and update UI for active layer
            if self.canvas.active_layer:
                # Set current row
                index = len(self.canvas.layers) - 1 - self.canvas.layers.index(self.canvas.active_layer)
                self.layer_list.setCurrentRow(index)
                
                # Update controls with signal blocking
                self.visible_cb.blockSignals(True)
                self.visible_cb.setChecked(self.canvas.active_layer.is_visible)
                self.visible_cb.blockSignals(False)
                
                # Update lock checkbox
                self.lock_cb.blockSignals(True)
                self.lock_cb.setChecked(self.canvas.active_layer.is_locked)
                self.lock_cb.blockSignals(False)
                
                # Update scale controls
                self.scale_x_spin.setValue(self.canvas.active_layer.scale_x)
                self.scale_y_spin.setValue(self.canvas.active_layer.scale_y)
                
                # Disable scale controls if layer is locked
                self.scale_x_spin.setEnabled(not self.canvas.active_layer.is_locked)
                self.scale_y_spin.setEnabled(not self.canvas.active_layer.is_locked)
        finally:
            self.updating_ui = False  # Reset flag when done
            
    def on_layer_selected(self, item):
        """Handle layer selection in the list"""
        if self.updating_ui:
            return  # Ignore if we're in the middle of updating the UI
            
        index = self.layer_list.row(item)
        # Convert to reverse index for canvas.layers (top to bottom vs bottom to top)
        canvas_index = len(self.canvas.layers) - 1 - index
        
        # Set active layer - this will call layerChanged signal which updates the UI
        self.canvas.set_active_layer(canvas_index)
        
    def on_rows_moved(self, parent, start, end, dest, row):
        """Handle layer reordering via drag and drop"""
        # Convert UI indices to canvas indices
        from_index = len(self.canvas.layers) - 1 - start
        to_index = len(self.canvas.layers) - 1 - row
        
        # Adjust if moving downward
        if start < row:
            to_index += 1
            
        self.canvas.move_layer(from_index, to_index)
        
    def on_opacity_changed(self, value):
        """Handle opacity slider changes"""
        if self.canvas.active_layer and not self.canvas.active_layer.is_locked:
            self.canvas.active_layer.set_opacity(value / 100.0)
            
    def on_scale_x_changed(self, value):
        """Handle X scale spin box changes"""
        if self.canvas.active_layer and not self.canvas.active_layer.is_locked:
            # Keep the Y scale the same
            self.canvas.scale_layer(self.canvas.active_layer, value, self.canvas.active_layer.scale_y)
            
    def on_scale_y_changed(self, value):
        """Handle Y scale spin box changes"""
        if self.canvas.active_layer and not self.canvas.active_layer.is_locked:
            # Keep the X scale the same
            self.canvas.scale_layer(self.canvas.active_layer, self.canvas.active_layer.scale_x, value)
            
    def on_visibility_changed(self, state):
        """Handle visibility checkbox changes"""
        if self.updating_ui:
            return  # Ignore if we're in the middle of updating the UI
        
        if not self.canvas.active_layer:
            return
            
        # Get the desired visibility state from checkbox
        is_visible = state == Qt.CheckState.Checked
        
        # Only proceed if the state actually needs to change
        if is_visible == self.canvas.active_layer.is_visible:
            return
        
        # Store previous opacity if making visible and opacity is too low
        if is_visible and self.canvas.active_layer.opacity < 0.05:
            self.canvas.active_layer.set_opacity(0.5)
            self.opacity_slider.setValue(50)  # 50%
        
        # Use the canvas's method to toggle visibility (includes history)
        self.canvas.toggle_layer_visibility(self.canvas.active_layer, is_visible)
        
        # Update UI item text
        self._update_layer_item_text(self.layer_list.currentItem(), self.canvas.active_layer)

    def _update_layer_item_text(self, item, layer):
        """Update layer item text with appropriate icons"""
        if not item or not layer:
            return
            
        # Start with base name
        name = layer.name
        
        # Add prefixes based on state
        prefix = ""
        if layer.is_locked:
            prefix += "🔒 "
        if not layer.is_visible:
            prefix += "👁️ "
            
        # Update item text
        item.setText(f"{prefix}{name}")
    
    def on_lock_changed(self, state):
        """Handle lock checkbox changes"""
        if self.canvas.active_layer:
            is_locked = state == Qt.CheckState.Checked
            self.canvas.active_layer.set_locked(is_locked)
            
            # Update UI to reflect locked status
            if is_locked:
                item = self.layer_list.currentItem()
                if item:
                    item.setText(f"🔒 {self.canvas.active_layer.name}")
            else:
                item = self.layer_list.currentItem()
                if item:
                    item.setText(self.canvas.active_layer.name)
                    
            # Disable/enable scale controls
            self.scale_x_spin.setEnabled(not is_locked)
            self.scale_y_spin.setEnabled(not is_locked)
            
    def add_empty_layer(self):
        """Add a new empty layer"""
        # Not implemented - would need to create an empty transparent image
        
    def remove_selected_layer(self):
        """Remove the selected layer"""
        current_row = self.layer_list.currentRow()
        if current_row >= 0:
            # Convert to canvas index
            canvas_index = len(self.canvas.layers) - 1 - current_row
            if canvas_index < len(self.canvas.layers):
                layer = self.canvas.layers[canvas_index]
                if not layer.is_locked:
                    self.canvas.remove_layer(canvas_index)
            
    def duplicate_selected_layer(self):
        """Duplicate the selected layer"""
        if self.canvas.active_layer and not self.canvas.active_layer.is_locked:
            new_layer = self.canvas.active_layer.duplicate()
            self.canvas.layers.append(new_layer)
            self.canvas.scene.addItem(new_layer)
            self.canvas.set_active_layer(len(self.canvas.layers) - 1)
            self.update_layers()
