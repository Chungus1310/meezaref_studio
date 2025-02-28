from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPen, QColor, QCursor, QPixmap, QPainter, QBrush, QTransform, QPainterPath
from PyQt6.QtWidgets import QApplication, QComboBox, QLabel, QVBoxLayout, QWidget

import numpy as np

from tools import Tool
from layer import Layer

class SelectionTool(Tool):
    """Tool for selecting an area to duplicate as a new layer"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.start_point = None
        self.current_point = None
        self.selection_active = False
        self.selection_shape = "Rectangle"  # Default shape
        self.selection_shapes = ["Rectangle", "Ellipse"]
        
        # Set up cursor
        self._create_selection_cursor()

    def _create_selection_cursor(self):
        """Create a custom selection cursor"""
        cursor_pixmap = QPixmap(32, 32)
        cursor_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw crosshair
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(14, 16, 18, 16)  # Horizontal line
        painter.drawLine(16, 14, 16, 18)  # Vertical line
        
        # Draw selection icon
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawRect(6, 6, 20, 20)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawRect(7, 7, 18, 18)
        
        painter.end()
        
        self.cursor = QCursor(cursor_pixmap, 16, 16)  # Center hotspot

    def activate(self):
        """Activate the selection tool"""
        super().activate()
        # Store original cursor
        self.original_cursor = self.canvas.cursor()
        # Set selection cursor
        self.canvas.setCursor(self.cursor)
        # Reset state - vital for reactivation
        self.start_point = None
        self.current_point = None
        self.selection_active = False
        self.statusChanged.emit("Selection Tool: Click and drag to select an area, then click again to create new layer")

    def deactivate(self):
        """Deactivate the selection tool"""
        if self.original_cursor:
            self.canvas.setCursor(self.original_cursor)
        # Reset selection state on deactivation
        self.start_point = None
        self.current_point = None
        self.selection_active = False
        super().deactivate()

    def mouse_press(self, event):
        """Handle mouse press to start or complete selection"""
        if not self.active or event.button() != Qt.MouseButton.LeftButton:
            return
            
        view_pos = event.position().toPoint()
        scene_pos = self.canvas.mapToScene(view_pos)
        
        if not self.selection_active:
            # Start selection
            self.start_point = scene_pos
            self.current_point = scene_pos
            self.selection_active = True
            self.statusChanged.emit("Drag to adjust selection, click to complete")
        else:
            # Complete selection
            success = self.create_layer_from_selection()
            # Only reset selection if creation was successful
            if success:
                # Properly reset selection state
                self.start_point = None
                self.current_point = None
                self.selection_active = False
                self.statusChanged.emit("Selection completed. Click and drag for new selection")
            
        event.accept()
        self.canvas.viewport().update()
        
    def mouse_move(self, event):
        """Update selection preview during mouse move"""
        if not self.active or not self.selection_active:
            return
            
        # Update current point
        view_pos = event.position().toPoint()
        self.current_point = self.canvas.mapToScene(view_pos)
        
        # Update display
        self.canvas.viewport().update()
        event.accept()
        
    def mouse_release(self, event):
        """Handle mouse release - we don't finish on release, only on second click"""
        pass  # Selection completes on second click, not on release
    
    def get_selection_rect(self):
        """Get QRectF from selection points"""
        if not self.start_point or not self.current_point:
            return None
            
        x = min(self.start_point.x(), self.current_point.x())
        y = min(self.start_point.y(), self.current_point.y())
        width = abs(self.current_point.x() - self.start_point.x())
        height = abs(self.current_point.y() - self.start_point.y())
        
        return QRectF(x, y, width, height)
    
    def create_layer_from_selection(self):
        """Create a new layer from the selected area"""
        if not self.canvas.active_layer or not self.canvas.active_layer.original_image:
            self.statusChanged.emit("No active layer to select from")
            return False
        
        selection_rect = self.get_selection_rect()
        if not selection_rect or selection_rect.width() < 5 or selection_rect.height() < 5:
            self.statusChanged.emit("Selection too small")
            return False
            
        # Get item-local coordinates
        active_layer = self.canvas.active_layer
        item_rect = active_layer.mapFromScene(selection_rect).boundingRect()
        
        # Account for layer scaling by dividing by scale factors
        if hasattr(active_layer, 'scale_x') and hasattr(active_layer, 'scale_y') and active_layer.scale_x > 0 and active_layer.scale_y > 0:
            adjusted_rect = QRectF(
                item_rect.x() / active_layer.scale_x,
                item_rect.y() / active_layer.scale_y,
                item_rect.width() / active_layer.scale_x,
                item_rect.height() / active_layer.scale_y
            )
            item_rect = adjusted_rect
        
        # Convert QRect to QRectF for proper intersection
        image_rect = QRectF(active_layer.original_image.rect())
        
        # Intersect the rects and convert back to integer coordinates for copying
        intersected_rect = item_rect.intersected(image_rect)
        
        if intersected_rect.isEmpty():
            self.statusChanged.emit("Selection outside image bounds")
            return False
            
        # Convert floating point coordinates to integers for image copying
        x = max(0, int(round(intersected_rect.x())))
        y = max(0, int(round(intersected_rect.y())))
        width = min(active_layer.original_image.width() - x, int(round(intersected_rect.width())))
        height = min(active_layer.original_image.height() - y, int(round(intersected_rect.height())))
        
        # Use copy method to create a new image from selection
        selected_image = active_layer.original_image.copy(x, y, width, height)
        
        # Apply elliptical mask if using ellipse shape
        if self.selection_shape == "Ellipse":
            # Create a transparent image of the same size
            mask = QPixmap(width, height)
            mask.fill(Qt.GlobalColor.transparent)
            
            # Create elliptical mask
            mask_painter = QPainter(mask)
            mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            mask_painter.setPen(Qt.PenStyle.NoPen)
            mask_painter.setBrush(QColor(255, 255, 255, 255))
            mask_painter.drawEllipse(0, 0, width, height)
            mask_painter.end()
            
            # Apply mask to image
            result = QPixmap.fromImage(selected_image)
            masked_result = QPixmap(width, height)
            masked_result.fill(Qt.GlobalColor.transparent)
            
            masked_painter = QPainter(masked_result)
            masked_painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            masked_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            masked_painter.drawPixmap(0, 0, mask)
            masked_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            masked_painter.drawPixmap(0, 0, result)
            masked_painter.end()
            
            # Convert back to QImage
            selected_image = masked_result.toImage()
        
        # Create a new layer with selected image
        new_layer = Layer()
        new_layer.name = f"{active_layer.name} Selection"
        new_layer.set_image(selected_image)
        
        # Position at the scene coordinates, using the original selection position
        new_layer.setPos(selection_rect.x(), selection_rect.y())
        
        # Add to canvas
        self.canvas.layers.append(new_layer)
        self.canvas.scene.addItem(new_layer)
        self.canvas.set_active_layer(len(self.canvas.layers) - 1)
        
        # Add to history
        if hasattr(self.canvas, 'history'):
            self.canvas.history.add_command("add_layer", new_layer)
            
        self.canvas.layerChanged.emit()
        self.statusChanged.emit(f"Created new layer from selection")
        return True
    
    def get_controls(self):
        """Return control definitions for adjustment panel"""
        return {
            "title": "Selection Tool",
            "combos": [
                {
                    "name": "shape",
                    "options": self.selection_shapes
                }
            ]
        }
    
    def update_parameter(self, name, value):
        """Handle parameter updates from the adjustment panel"""
        if name == "shape":
            self.selection_shape = value
    
    def paintEvent(self, painter, rect):
        """Draw the selection overlay"""
        if self.selection_active and self.start_point and self.current_point:
            selection_rect = self.get_selection_rect()
            if selection_rect:
                # Convert scene rectangle to view coordinates
                view_rect = self.canvas.mapFromScene(selection_rect).boundingRect()
                
                # Draw selection based on selected shape
                painter.save()
                
                # Semi-transparent fill
                painter.setBrush(QBrush(QColor(100, 150, 255, 40)))
                
                # Dotted outline
                pen = QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                
                if self.selection_shape == "Rectangle":
                    painter.drawRect(view_rect)
                elif self.selection_shape == "Ellipse":
                    painter.drawEllipse(view_rect)
                
                # Draw size info
                pen.setStyle(Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                width = int(selection_rect.width())
                height = int(selection_rect.height())
                size_text = f"{width} × {height}"
                
                # Convert text position to view coordinates
                text_pos = QPointF(selection_rect.x() + 5, selection_rect.y() + selection_rect.height() - 20)
                view_text_pos = self.canvas.mapFromScene(text_pos)
                
                text_rect = QRectF(
                    view_text_pos.x(),
                    view_text_pos.y(),
                    100, 20
                )
                painter.drawText(text_rect, size_text)
                
                painter.restore()
                
    def get_tooltip(self):
        """Return tooltip for toolbar button"""
        return "Selection Tool (S)"
