from PyQt6.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QMenu, QInputDialog, QFileDialog
from PyQt6.QtGui import QPainter, QImage, QPixmap, QTransform, QCursor, QColor
from PyQt6.QtCore import Qt, QPoint, QRectF, pyqtSignal, QPointF, QByteArray, QBuffer, QIODevice, QTimer
import json
import os
import base64

import multiprocessing as mp
from functools import partial

from layer import Layer
from history import History
from style_utils import COLORS, STYLE_SHEETS

try:
    from gpu_ops import GPUImageProcessor
    gpu_available = True
except ImportError:
    gpu_available = False

class Canvas(QGraphicsView):
    layerChanged = pyqtSignal()
    
    def __init__(self):
        self.scene = QGraphicsScene()
        super().__init__(self.scene)
        
        # Set scene rect to be very large for "infinite" canvas feel
        self.scene.setSceneRect(-100000, -100000, 200000, 200000)
        
        # Apply modern styling
        self.setStyleSheet(STYLE_SHEETS["canvas"])
        
        # Set a gradient background
        self.setBackgroundBrush(QColor(COLORS["primary"]))
        
        # Canvas settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add performance optimizations
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | 
                           QPainter.RenderHint.SmoothPixmapTransform)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        
        # Add caching for better performance
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        
        # Timer for throttling updates during movements
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(50)  # 50ms delay for smooth rendering
        self.update_timer.timeout.connect(self.delayed_update)
        
        # Flag to track if we're currently moving layers
        self.is_moving_layers = False
        
        # Layers and active layer
        self.layers = []
        self.active_layer = None
        
        # History for undo/redo
        self.history = History()
        
        # Store the current mouse position
        self.last_mouse_pos = QPoint()
        self.is_panning = False
        
        # Disable multiprocessing to prevent freezing
        # self.pool = mp.Pool(processes=mp.cpu_count())
        
        # Initialize GPU processor
        self.use_gpu = gpu_available
        if self.use_gpu:
            self.gpu_processor = GPUImageProcessor()
            self.use_gpu = self.gpu_processor.is_available()
            print(f"GPU acceleration: {'Enabled' if self.use_gpu else 'Disabled'}")
        
    def add_image_layer(self, image_path):
        """Add a new image layer to the canvas"""
        layer = Layer(image_path)
        self.layers.append(layer)
        self.scene.addItem(layer)
        
        # Set as active if it's the first layer
        if len(self.layers) == 1:
            self.set_active_layer(0)
            
        # Add to history
        self.history.add_command("add_layer", layer)
        self.layerChanged.emit()
        
        return layer
        
    def remove_layer(self, index):
        """Remove a layer at the specified index"""
        if 0 <= index < len(self.layers):
            layer = self.layers.pop(index)
            self.scene.removeItem(layer)
            
            # Update active layer if necessary
            if self.active_layer == layer:
                if self.layers:
                    self.set_active_layer(0)
                else:
                    self.active_layer = None
                    
            # Add to history
            self.history.add_command("remove_layer", layer, index)
            self.layerChanged.emit()
            
    def set_active_layer(self, index):
        """Set the active layer by index"""
        if 0 <= index < len(self.layers):
            # Deselect the current active layer
            if self.active_layer:
                self.active_layer.setSelected(False)
                
            self.active_layer = self.layers[index]
            self.active_layer.setSelected(True)
            
            # Don't change the Z-order when selecting - this breaks visibility state
            # Just use setSelected() to show selection state
            
            self.layerChanged.emit()
    
    def move_layer(self, from_index, to_index):
        """Move a layer from one position to another"""
        if 0 <= from_index < len(self.layers) and 0 <= to_index < len(self.layers):
            layer = self.layers.pop(from_index)
            self.layers.insert(to_index, layer)
            
            # Update z-order
            for i, layer in enumerate(self.layers):
                layer.setZValue(i)
                
            # Add to history
            self.history.add_command("move_layer", from_index, to_index)
            self.layerChanged.emit()
    
    def scale_layer(self, layer, scale_x, scale_y):
        """Scale a layer by the given factors"""
        if layer.is_locked:
            return
            
        old_scale = (layer.scale_x, layer.scale_y)
        
        # Use CPU scaling instead of GPU to prevent freezing
        layer.scale_image(scale_x, scale_y)
        
        # Add to history
        self.history.add_command("scale_layer", layer, old_scale, (scale_x, scale_y))
        self.layerChanged.emit()
    
    def show_context_menu(self, position):
        """Show context menu for layer operations"""
        if self.active_layer is None:
            return
            
        global_pos = self.mapToGlobal(position)
        menu = QMenu()
        
        # Scale action
        scale_action = menu.addAction("Scale Image...")
        scale_action.triggered.connect(lambda: self.show_scale_dialog(self.active_layer))
        scale_action.setEnabled(not self.active_layer.is_locked)
        
        # Reset scale action
        reset_scale_action = menu.addAction("Reset Scale")
        reset_scale_action.triggered.connect(lambda: self.scale_layer(self.active_layer, 1.0, 1.0))
        reset_scale_action.setEnabled(not self.active_layer.is_locked)
        
        menu.exec(global_pos)
    
    def show_scale_dialog(self, layer):
        """Show a dialog to input scale values"""
        # Get current scale as percentage
        current_scale_x = int(layer.scale_x * 100)
        current_scale_y = int(layer.scale_y * 100)
        
        # Get x scale
        scale_x, ok = QInputDialog.getInt(
            self, "Scale Width", "Enter width scale percentage:",
            current_scale_x, 1, 1000
        )
        if not ok:
            return
            
        # Get y scale
        scale_y, ok = QInputDialog.getInt(
            self, "Scale Height", "Enter height scale percentage:",
            current_scale_y, 1, 1000
        )
        if not ok:
            return
            
        # Apply scale
        self.scale_layer(layer, scale_x / 100.0, scale_y / 100.0)
    
    def save_canvas(self, filename):
        """Save the current canvas state to a file"""
        canvas_data = {
            "version": "1.0",
            "layers": []
        }
        
        # Save each layer's data
        for layer in self.layers:
            layer_data = layer.serialize()
            canvas_data["layers"].append(layer_data)
            
        # Save the JSON to file
        try:
            with open(filename, 'w') as f:
                json.dump(canvas_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving canvas: {e}")
            return False
    
    def load_canvas(self, filename):
        """Load a canvas state from a file"""
        try:
            with open(filename, 'r') as f:
                canvas_data = json.load(f)
                
            # Check version
            if "version" not in canvas_data or canvas_data["version"] != "1.0":
                print("Unsupported canvas file version")
                return False
                
            # Clear current layers
            for layer in list(self.layers):  # Create a copy to avoid modification during iteration
                self.scene.removeItem(layer)
            self.layers.clear()
            self.active_layer = None
            
            # Load each layer
            for layer_data in canvas_data["layers"]:
                layer = Layer()
                if layer.deserialize(layer_data):
                    self.layers.append(layer)
                    self.scene.addItem(layer)
            
            # Set active layer if there are layers
            if self.layers:
                self.set_active_layer(0)
                
            self.layerChanged.emit()
            return True
            
        except Exception as e:
            print(f"Error loading canvas: {e}")
            return False
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # Store current scene position under mouse before zoom
        old_pos = self.mapToScene(event.position().toPoint())
        
        # Apply zooming
        zoom_factor = 1.1
        
        if event.angleDelta().y() > 0:
            # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:
            # Zoom out
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
        
        # Update the view center explicitly to ensure it's centered on the mouse
        # By calculating the delta from the scene point under the mouse before and after zooming
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        
        # Adjust the view by the delta to maintain the position under the mouse
        self.translate(delta.x(), delta.y())
        
        # Mark as handled
        event.accept()
            
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        # Check if we might be starting a drag operation on a layer
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, Layer) and not item.is_locked:
                # Temporarily reduce rendering quality for smoother dragging
                # Fix: Use .setRenderHint() instead of .setRenderHints() with proper format
                self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        
        # Pass event to active tool if available
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'left_toolbar') and self.main_window.left_toolbar.active_tool:
            self.main_window.left_toolbar.active_tool.mouse_press(event)
            # If the tool handled the event, don't propagate it
            if event.isAccepted():
                return
        
        # Handle middle mouse button for panning
        if event.button() == Qt.MouseButton.MiddleButton:
            # Start panning with middle mouse button
            self.is_panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            # Check if we're clicking on a locked layer
            item = self.itemAt(event.pos())
            if isinstance(item, Layer) and item.is_locked:
                event.accept()
                return
                
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        """Handle mouse move events with optimized rendering"""
        # Pass event to active tool if available
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'left_toolbar') and self.main_window.left_toolbar.active_tool:
            self.main_window.left_toolbar.active_tool.mouse_move(event)
            # If the tool handled the event, don't propagate it
            if event.isAccepted():
                return
        
        if self.is_panning:
            # Calculate the distance moved since last position
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            
            # Pan the view
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            # If we're moving a layer, optimize updates
            if not self.is_panning and self.active_layer and self.active_layer.isSelected():
                self.is_moving_layers = True
                
                # Use more aggressive throttling by checking if timer is active
                if not self.update_timer.isActive():
                    # Use more conservative updates during continuous movement
                    self.update_timer.start(75)  # Slightly longer interval for smoother dragging
            
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        # Restore high-quality rendering when drag ends
        # Fix: Use .setRenderHint() instead of .setRenderHints() with proper format
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        
        # Pass event to active tool if available
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'left_toolbar') and self.main_window.left_toolbar.active_tool:
            self.main_window.left_toolbar.active_tool.mouse_release(event)
            # If the tool handled the event, don't propagate it
            if event.isAccepted():
                return
        
        if event.button() == Qt.MouseButton.MiddleButton:
            # Stop panning
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            # If we were moving layers, ensure we do a final update
            if self.is_moving_layers:
                self.is_moving_layers = False
                self.update_timer.stop()
                self.delayed_update()
            super().mouseReleaseEvent(event)
    
    def undo(self):
        """Undo the last action"""
        command = self.history.undo()
        if command:
            action = command[0]
            
            if action == "add_layer":
                layer = command[1]
                self.scene.removeItem(layer)
                self.layers.remove(layer)
                if self.active_layer == layer:
                    self.active_layer = None if not self.layers else self.layers[0]
                    
            elif action == "remove_layer":
                layer = command[1]
                index = command[2]
                if index < len(self.layers):
                    self.layers.insert(index, layer)
                else:
                    self.layers.append(layer)
                self.scene.addItem(layer)
                
            elif action == "move_layer":
                from_index = command[1]
                to_index = command[2]
                # Swap the indices for undo
                self.move_layer(to_index, from_index)
                return  # move_layer already emits layerChanged
                
            elif action == "scale_layer":
                layer = command[1]
                old_scale = command[2]
                
                # Use CPU scaling instead of GPU
                layer.scale_image(old_scale[0], old_scale[1])
                
            elif action == "visibility":
                layer = command[1]
                old_visibility = command[2]
                # Ensure we're using set_visible to properly update the model
                layer.set_visible(old_visibility)
                # Force UI refresh for visibility changes
                self.scene.update()
                
            elif action == "filter":
                # Restore the previous image state for filter operations
                layer = command[1]
                previous_image = command[2]
                if layer in self.layers and previous_image:
                    layer.set_image(previous_image)
                
            self.layerChanged.emit()
    
    def redo(self):
        """Redo the last undone action"""
        command = self.history.redo()
        if command:
            action = command[0]
            
            if action == "add_layer":
                layer = command[1]
                self.layers.append(layer)
                self.scene.addItem(layer)
                
            elif action == "remove_layer":
                layer = command[1]
                index = command[2]
                if layer in self.layers:
                    self.layers.remove(layer)
                    self.scene.removeItem(layer)
                    if self.active_layer == layer:
                        self.active_layer = None if not self.layers else self.layers[0]
                
            elif action == "move_layer":
                from_index = command[1]
                to_index = command[2]
                if from_index < len(self.layers) and to_index < len(self.layers):
                    self.move_layer(from_index, to_index)
                return  # move_layer already emits layerChanged
                
            elif action == "scale_layer":
                layer = command[1]
                new_scale = command[3]
                
                # Use CPU scaling instead of GPU
                layer.scale_image(new_scale[0], new_scale[1])
                
            elif action == "visibility":
                layer = command[1]
                new_visibility = command[3]
                # Ensure we're using set_visible to properly update the model
                layer.set_visible(new_visibility)
                # Force UI refresh for visibility changes
                self.scene.update()
                
            elif action == "filter":
                # Apply the filter again for redo
                layer = command[1]
                new_image = command[3]
                if layer in self.layers and new_image:
                    layer.set_image(new_image)
                
            self.layerChanged.emit()
            
    def process_image_task(self, func, layer, *args):
        """Process an image operation in a separate process"""
        if not layer or layer.is_locked:
            return
            
        # Create a partial function with the arguments
        task = partial(func, *args)
        
        # Execute the task in the pool
        self.pool.apply_async(task, callback=lambda result: self.update_layer_image(layer, result))
        
    def update_layer_image(self, layer, new_image):
        """Update a layer's image after processing"""
        layer.set_image(new_image)
        self.layerChanged.emit()
        
    def closeEvent(self, event):
        """Clean up resources when closing"""
        # Don't try to close the pool since we disabled it
        # self.pool.close()
        # self.pool.join()
        super().closeEvent(event)
    
    def toggle_layer_visibility(self, layer, is_visible):
        """Toggle layer visibility with history tracking"""
        if layer:
            old_visibility = layer.is_visible
            
            # Only update if the state actually changes
            if old_visibility != is_visible:
                # Update the layer visibility first
                layer.set_visible(is_visible)
                
                # Force refresh the layer to ensure visibility state is applied
                if layer.isVisible() != is_visible:
                    layer.update()
                
                # Then add to history
                self.history.add_command("visibility", layer, old_visibility, is_visible)
                
                # Notify UI to update
                self.layerChanged.emit()
    
    def delayed_update(self):
        """Perform delayed update for smoother rendering"""
        # Ensure full rendering quality is restored before final update
        # Fix: Use .setRenderHint() instead of .setRenderHints() with proper format
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # Complete update with full quality
        self.scene.update()
        self.layerChanged.emit()
    
    def paintEvent(self, event):
        """Custom paint event to support tool overlays"""
        # Call the parent class paintEvent first
        super().paintEvent(event)
        
        # Let active tools draw overlays if they need to
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'left_toolbar'):
            active_tool = self.main_window.left_toolbar.active_tool
            if active_tool and hasattr(active_tool, 'paintEvent'):
                # Create painter for the viewport
                painter = QPainter(self.viewport())
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                # Let tool draw its overlay
                active_tool.paintEvent(painter, event.rect())
                painter.end()
