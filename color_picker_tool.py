from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF, QPoint, QRectF
from PyQt6.QtGui import QCursor, QPixmap, QImage, QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication

import numpy as np
import threading
from functools import lru_cache

from tools import Tool
from color_popup import ColorPopup

try:
    from gpu_ops import GPUImageProcessor
    gpu_available = True
except ImportError:
    gpu_available = False

class ColorAnalysisThread(QThread):
    """Thread for analyzing color data around cursor position"""
    
    # Signal for when analysis is complete
    analysisComplete = pyqtSignal(object)
    
    def __init__(self, image, pos, use_gpu=False, gpu_processor=None):
        super().__init__()
        self.image = image
        self.pos = pos
        self.use_gpu = use_gpu
        self.gpu_processor = gpu_processor
        
        # Only create a new processor if one wasn't passed in and GPU is enabled
        if use_gpu and not self.gpu_processor:
            try:
                from gpu_ops import GPUImageProcessor
                self.gpu_processor = GPUImageProcessor()
            except:
                self.use_gpu = False
        
    def run(self):
        """Run color analysis"""
        try:
            if self.use_gpu:
                result = self._analyze_with_gpu()
            else:
                result = self._analyze_with_cpu()
                
            self.analysisComplete.emit(result)
        except Exception as e:
            print(f"Error in color analysis: {e}")
            self.analysisComplete.emit(None)
            
    def _analyze_with_cpu(self):
        """Analyze colors using CPU"""
        # Extract the color at the cursor position with exact coordinates
        x = max(0, min(int(self.pos.x()), self.image.width() - 1))
        y = max(0, min(int(self.pos.y()), self.image.height() - 1))
        color = self.image.pixelColor(x, y)
        
        # Simple result: just return the color and exact position
        return {
            'center_color': color,
            'pos': QPoint(x, y),
            'timestamp': QApplication.instance().processEvents()  # Add timestamp to prevent stale data
        }
        
    def _analyze_with_gpu(self):
        """Analyze colors using GPU acceleration if available"""
        # For now, just return the same as CPU version for exact pixel analysis
        return self._analyze_with_cpu()

class ColorPickerTool(Tool):
    """Tool for picking colors from the canvas with enhanced UI and features"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        
        # Create eyedropper cursor
        self._create_eyedropper_cursor()
        
        # Color popup window
        self.color_popup = ColorPopup()
        self.color_popup.hide()
        
        # Last analyzed position
        self.last_pos = QPoint(0, 0)
        
        # Track if we're currently analyzing
        self.analysis_in_progress = False
        self.analysis_thread = None
        
        # Use GPU if available
        self.use_gpu = gpu_available and hasattr(self.canvas, 'use_gpu') and self.canvas.use_gpu
        self.gpu_processor = None
        if self.use_gpu and hasattr(self.canvas, 'gpu_processor'):
            # Reuse the existing GPU processor instead of creating a new one
            self.gpu_processor = self.canvas.gpu_processor
        
        # Cache for color lookups (to avoid redundant processing)
        self._color_cache = {}
        self._cache_size = 100
        
        # Store original cursor to restore later
        self.original_cursor = None
        
        # Flag to track if popup should be shown (only when clicking)
        self.show_popup = False
        
        # Track last picked color for comparison
        self.last_picked_color = None
        
    def _create_eyedropper_cursor(self):
        """Create a custom eyedropper cursor"""
        # Create an eyedropper cursor
        cursor_pixmap = QPixmap(32, 32)
        cursor_pixmap.fill(Qt.GlobalColor.transparent)
        
        # Draw eyedropper icon
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw eyedropper shape with more contrast for better visibility
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawLine(8, 24, 16, 16)
        painter.drawLine(16, 16, 24, 8)
        
        # Draw white fill with black outline for better visibility
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(22, 6, 6, 6)
        
        # Draw crosshair at the tip for precise picking - make it more visible
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.drawLine(22, 8, 26, 8)  # Horizontal line
        painter.drawLine(24, 6, 24, 10) # Vertical line
        
        painter.end()
        
        # FIXED: Define hotspot precisely at the tip of the eyedropper (24,8)
        self.cursor = QCursor(cursor_pixmap, 24, 8)
        
    def activate(self):
        """Activate the color picker tool"""
        # First call parent method to set active flag
        self.active = True  # Set active manually first
        
        # Check if there's an active layer with an image
        if not self.canvas.active_layer or not self.canvas.active_layer.original_image:
            self.statusChanged.emit("No active layer with an image to pick colors from")
        
        # Store the original cursor to restore later
        self.original_cursor = self.canvas.cursor()
        
        # IMPORTANT: Force set the custom cursor directly on the canvas
        self.canvas.setCursor(self.cursor)
        
        # Also set the application cursor to ensure it changes
        QApplication.setOverrideCursor(self.cursor)
        
        # Hide popup when tool is activated
        self.color_popup.hide()
        self.show_popup = False
        
        # Clear the cache when activating to ensure fresh data
        self._color_cache.clear()
        
        self.statusChanged.emit("Color Picker: Click to sample color")
        
    def deactivate(self):
        """Deactivate the color picker tool"""
        # Hide color popup
        self.color_popup.hide()
        self.show_popup = False
        
        # Restore original cursor
        if self.original_cursor:
            self.canvas.setCursor(self.original_cursor)
            
        # Also restore override cursor if set
        QApplication.restoreOverrideCursor()
        
        # Stop any running thread before deactivating
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.quit()
            self.analysis_thread.wait(300)  # Wait with timeout
            
        self.active = False
        
    def mouse_press(self, event):
        """Handle mouse press event - pick color at cursor position"""
        if not self.active or event.button() != Qt.MouseButton.LeftButton:
            return
            
        # Fixed: Convert QPointF to QPoint for proper handling
        view_pos = event.position().toPoint()
        
        # Set flag to show popup when picking completes
        self.show_popup = True
        
        # Reset the last picked color to force update
        self.last_picked_color = None
        
        # Pick color at the exact position
        self._pick_color_at(view_pos)
        
        # Mark event as handled
        event.accept()
        
    def mouse_move(self, event):
        """Handle mouse move event - don't update color popup during movement"""
        if not self.active:
            return
        
        # We'll only update colors in the popup if it's already visible (from a click)
        # but we won't show the popup just by moving the mouse
        if self.color_popup.isVisible() and not self.analysis_in_progress:
            # Fixed: Convert QPointF to QPoint for proper handling
            view_pos = event.position().toPoint()
            self._pick_color_at(view_pos)
            event.accept()
        
    def _get_exact_image_pos(self, view_pos):
        """Get the exact image coordinates from view position, accounting for all transformations"""
        # Convert view position to scene coordinates
        scene_pos = self.canvas.mapToScene(view_pos)
        
        # Find item at scene position
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        if not item or not hasattr(item, 'original_image') or item.original_image is None:
            return None, None, None
            
        # Get item-local coordinates
        item_pos = item.mapFromScene(scene_pos)
        
        # Account for item scaling by dividing by scale factors
        if hasattr(item, 'scale_x') and hasattr(item, 'scale_y') and item.scale_x > 0 and item.scale_y > 0:
            # Dividing by scale factor converts from scaled coordinate space to original image space
            x = round(item_pos.x() / item.scale_x)
            y = round(item_pos.y() / item.scale_y)
        else:
            # Fallback to direct conversion if scale attributes aren't available
            x = round(item_pos.x())
            y = round(item_pos.y())
        
        # Clamp to valid image dimensions
        x = max(0, min(x, item.original_image.width() - 1))
        y = max(0, min(y, item.original_image.height() - 1))
        
        # Additional debugging to help identify issues
        if not (0 <= x < item.original_image.width() and 0 <= y < item.original_image.height()):
            print(f"Warning: Coordinates out of bounds - x:{x}, y:{y}, width:{item.original_image.width()}, height:{item.original_image.height()}")
            return None, None, None
            
        return item, x, y
    
    def _pick_color_at(self, pos):
        """Pick color at given view position with improved precision"""
        if self.analysis_in_progress:
            return
            
        # Get exact image position with all transformations accounted for
        item, x, y = self._get_exact_image_pos(pos)
        if item is None or x is None or y is None:
            return
            
        # Build a more comprehensive cache key that accounts for transformations
        item_transform = item.transform()
        cache_key = f"{x}_{y}_{item.pos().x()}_{item.pos().y()}_{item_transform.m11()}_{item_transform.m22()}"
        
        if cache_key in self._color_cache:
            self._update_popup_with_color(self._color_cache[cache_key])
            return
        
        # Mark analysis as in progress
        self.analysis_in_progress = True
        
        # Create and start a new thread for color analysis
        if self.analysis_thread and self.analysis_thread.isRunning():
            self.analysis_thread.quit()
            self.analysis_thread.wait(100)  # Quick wait with timeout
        
        # Create a new thread for color analysis with precise coordinates
        self.analysis_thread = ColorAnalysisThread(
            item.original_image, 
            QPoint(x, y),  # Use exact pixel coordinates
            self.use_gpu,
            self.gpu_processor
        )
        
        # Connect the signal from the thread to our handler
        self.analysis_thread.analysisComplete.connect(self._on_analysis_complete)
        
        # Start the thread
        self.analysis_thread.start()
        
        # Store the view position and item for the result callback
        self.last_pos = pos
        self.last_item = item
        
    def _on_analysis_complete(self, result):
        """Handle completion of color analysis"""
        self.analysis_in_progress = False
        
        if not result:
            return
            
        # Store view position information
        result['view_pos'] = self.last_pos
        
        # Add item transform information for a more precise cache key
        if hasattr(self, 'last_item') and self.last_item:
            item_transform = self.last_item.transform()
            item_pos = self.last_item.pos()
            cache_key = (f"{int(result['pos'].x())}_{int(result['pos'].y())}_"
                        f"{item_pos.x()}_{item_pos.y()}_"
                        f"{item_transform.m11()}_{item_transform.m22()}")
            
            # Update cache with comprehensive key
            self._color_cache[cache_key] = result
            
            # Trim cache if needed
            if len(self._color_cache) > self._cache_size:
                # Remove oldest entries
                for key in list(self._color_cache.keys())[:10]:
                    self._color_cache.pop(key, None)
        
        # Update UI
        self._update_popup_with_color(result)
            
    def _update_popup_with_color(self, result):
        """Update the color popup with the analyzed result"""
        # Get the color
        color = result['center_color']
        
        # Only update if the color has changed (to avoid unnecessary UI updates)
        if self.last_picked_color and self.last_picked_color.rgb() == color.rgb() and not self.show_popup:
            return
            
        # Update the popup data
        self.color_popup.update_color(color)
        self.last_picked_color = color
        
        # Only show popup if explicitly requested (on click)
        if not self.show_popup and not self.color_popup.isVisible():
            return
            
        # Position popup using screen-aware positioning
        self._position_popup_safely()
        
        # Reset flag after showing
        self.show_popup = False
        
    def _position_popup_safely(self):
        """Position the popup with enhanced edge detection to handle all screen edges"""
        # Get current cursor position and screen info
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        
        # Get popup dimensions
        popup_width = self.color_popup.width()
        popup_height = self.color_popup.height()
        
        # Get available screen geometry (accounts for taskbar and other system UI)
        available_geometry = screen.availableGeometry()
        
        # Default position: to the right and below cursor
        x = cursor_pos.x() + 20
        y = cursor_pos.y() + 20
        
        # Check right edge
        if x + popup_width > available_geometry.right():
            # Move to the left of cursor
            x = cursor_pos.x() - popup_width - 20
            
            # Additional safety check for multi-monitor setups
            # If placing left would put it outside the left edge
            if x < available_geometry.left():
                # Center on cursor X position instead
                x = max(available_geometry.left(), cursor_pos.x() - (popup_width // 2))
        
        # Check bottom edge
        if y + popup_height > available_geometry.bottom():
            # Move above cursor
            y = cursor_pos.y() - popup_height - 20
            
            # Additional safety check for multi-monitor setups
            # If placing above would put it outside the top edge
            if y < available_geometry.top():
                # Center on cursor Y position instead
                y = max(available_geometry.top(), cursor_pos.y() - (popup_height // 2))
        
        # Final safety check to ensure the popup is always visible within screen bounds
        x = max(available_geometry.left(), min(x, available_geometry.right() - popup_width))
        y = max(available_geometry.top(), min(y, available_geometry.bottom() - popup_height))
        
        # Move and show the popup
        self.color_popup.move(x, y)
        self.color_popup.show()
        self.color_popup.raise_()  # Bring to front
        self.color_popup.activateWindow()  # Ensure it's active

    def get_tooltip(self):
        """Return tooltip for toolbar button"""
        return "Color Picker (P)"
        
    def __del__(self):
        """Clean up resources when the tool is destroyed"""
        try:
            # Clean up analysis thread if it exists
            if hasattr(self, 'analysis_thread') and self.analysis_thread:
                if self.analysis_thread.isRunning():
                    self.analysis_thread.quit()
                    self.analysis_thread.wait(100)
                self.analysis_thread = None
                
            # Close the color popup
            if hasattr(self, 'color_popup') and self.color_popup:
                self.color_popup.hide()
                self.color_popup.close()
        except (RuntimeError, AttributeError, TypeError):
            # Catch any exceptions during cleanup
            pass
