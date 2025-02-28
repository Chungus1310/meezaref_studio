from PyQt6.QtWidgets import QGraphicsPixmapItem, QGraphicsItem
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QTransform
from PyQt6.QtCore import Qt, QPointF, QRectF, QBuffer, QByteArray, QIODevice
import os
import base64
import io
from debug_util import debug_log

class Layer(QGraphicsPixmapItem):
    """Represents a layer in the image editor"""
    
    def __init__(self, image_path=None):
        super().__init__()
        
        # Layer properties
        self.name = "New Layer"
        self.is_visible = True
        self.is_locked = False
        self.opacity = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.original_image = None
        
        # Configure the item
        self.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable |
                     QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Load image if path is provided
        if image_path and os.path.exists(image_path):
            self.load_image(image_path)
            self.name = os.path.basename(image_path)
            
    def load_image(self, image_path):
        """Load an image from file"""
        self.original_image = QImage(image_path)
        if not self.original_image.isNull():
            self.update_pixmap()
            return True
        return False
    
    def set_image(self, image):
        """Set layer image from a QImage or numpy array"""
        if isinstance(image, QImage):
            self.original_image = image.copy()
        else:
            # Handle other types like numpy array
            if hasattr(image, 'shape'):
                # Assuming it's a numpy array
                # Convert to QImage using external function or library
                pass
                
        self.update_pixmap()
        
    def update_pixmap(self):
        """Update the pixmap from the original image with current transforms"""
        if self.original_image and not self.original_image.isNull():
            # Apply transformations to the pixmap
            pixmap = QPixmap.fromImage(self.original_image)
            
            # Create transform for scaling
            if self.scale_x != 1.0 or self.scale_y != 1.0:
                transform = QTransform().scale(self.scale_x, self.scale_y)
                pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
                
            # Set the pixmap
            self.setPixmap(pixmap)
            
            # Apply opacity
            self.setOpacity(self.opacity)
            
    def set_opacity(self, opacity):
        """Set layer opacity"""
        self.opacity = max(0.0, min(1.0, opacity))
        self.setOpacity(self.opacity)
        
    def set_visible(self, visible):
        """Set layer visibility"""
        self.is_visible = visible
        # Ensure the Qt visibility state matches our internal state
        self.setVisible(visible)
        # Force a redraw to ensure visibility change is applied
        self.update()
        
    def set_locked(self, locked):
        """Set layer locked state"""
        self.is_locked = locked
        if locked:
            self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False)
        else:
            self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
            
    def scale_image(self, scale_x, scale_y):
        """Scale the image (preserving the original)"""
        if self.original_image and not self.original_image.isNull():
            self.scale_x = max(0.1, scale_x)
            self.scale_y = max(0.1, scale_y)
            self.update_pixmap()
            
    def duplicate(self):
        """Create a duplicate of this layer"""
        new_layer = Layer()
        new_layer.name = self.name + " (Copy)"
        
        if self.original_image:
            new_layer.original_image = self.original_image.copy()
        
        new_layer.is_visible = self.is_visible
        new_layer.opacity = self.opacity
        new_layer.scale_x = self.scale_x
        new_layer.scale_y = self.scale_y
        
        # Update position
        new_layer.setPos(self.pos().x() + 20, self.pos().y() + 20)
        
        # Update the pixmap
        new_layer.update_pixmap()
        
        return new_layer
    
    def serialize(self):
        """Serialize the layer to a dict for saving"""
        layer_data = {
            "name": self.name,
            "visible": self.is_visible,
            "locked": self.is_locked,
            "opacity": self.opacity,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "pos_x": self.pos().x(),
            "pos_y": self.pos().y(),
        }
        
        # Serialize image data if available
        if self.original_image and not self.original_image.isNull():
            # Convert image to base64
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            self.original_image.save(buffer, "PNG")
            image_data = bytes(byte_array.data())
            layer_data["image"] = base64.b64encode(image_data).decode('ascii')
            
        return layer_data
    
    def deserialize(self, layer_data):
        """Load the layer from serialized data"""
        self.name = layer_data.get("name", "Layer")
        self.is_visible = layer_data.get("visible", True)
        self.is_locked = layer_data.get("locked", False)
        self.opacity = layer_data.get("opacity", 1.0)
        self.scale_x = layer_data.get("scale_x", 1.0)
        self.scale_y = layer_data.get("scale_y", 1.0)
        
        # Load position
        self.setPos(layer_data.get("pos_x", 0), layer_data.get("pos_y", 0))
        
        # Set flags based on locked state
        self.set_locked(self.is_locked)
        
        # Load image data if available
        if "image" in layer_data:
            try:
                # Decode base64 image data
                image_data = base64.b64decode(layer_data["image"])
                
                # Create QImage from raw data
                self.original_image = QImage()
                if self.original_image.loadFromData(image_data, "PNG"):
                    # Update pixmap with loaded image
                    self.update_pixmap()
                    return True
            except Exception as e:
                print(f"Error deserializing image data: {e}")
                return False
                
        return True
