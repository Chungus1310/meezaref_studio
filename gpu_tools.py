from PyQt6.QtCore import Qt, QThread, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtGui import QCursor, QImage, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMessageBox

import numpy as np
import cv2
from tools import Tool

try:
    from gpu_ops import GPUImageProcessor
    gpu_available = True
except ImportError:
    gpu_available = False

class GPUBasedTool(Tool):
    """Base class for GPU-accelerated tools"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.original_image = None
        self.parameters = {}
        self.work_thread = None
        
    def activate(self):
        """Store original image when tool is activated"""
        super().activate()
        # Make sure we get the active layer and its original image
        if self.canvas.active_layer and self.canvas.active_layer.original_image:
            self.original_image = self.canvas.active_layer.original_image.copy()
            # Process the image right away 
            self.process_image()
            
    def deactivate(self):
        """Reset to original image when tool is deactivated"""
        # Cancel any ongoing processing thread with proper timeout
        if self.work_thread and self.work_thread.isRunning():
            self.work_thread.requestInterruption()
            if not self.work_thread.wait(1000):  # Wait up to 1 second
                print("Warning: Processing thread did not terminate properly")
            
        # Reset image and call parent deactivate
        if self.canvas.active_layer and self.original_image:
            self.canvas.active_layer.set_image(self.original_image)
        super().deactivate()
        
    def update_parameter(self, name, value):
        """Update a parameter and reprocess the image"""
        # Update parameter value
        if isinstance(value, str) and name in self.parameters:
            self.parameters[name] = value
        else:
            try:
                self.parameters[name] = float(value)
            except (ValueError, TypeError):
                self.parameters[name] = value
                
        # Only process image when "apply" is triggered
        if name == "apply":
            self.process_image()
        
    def process_image(self, delay=False):
        """Process the image with current parameters"""
        if not self.canvas.active_layer or not self.original_image:
            return
            
        # Store original image when first used
        if not self.original_image and self.canvas.active_layer.original_image:
            self.original_image = self.canvas.active_layer.original_image
            
        # Cancel any ongoing processing
        if self.work_thread and self.work_thread.isRunning():
            self.work_thread.requestInterruption()
            self.work_thread.wait(100)  # Wait briefly for clean shutdown
            
        # Start new processing thread
        self.work_thread = ImageProcessingThread(
            self.original_image, 
            self.parameters,
            self.process_array
        )
        self.work_thread.resultReady.connect(self._on_processing_done)
        self.work_thread.start()
            
    def process_array(self, arr, params):
        """Override in subclasses to implement specific processing"""
        return arr
        
    def _on_processing_done(self, result):
        """Handle completion of image processing"""
        if result is None or not self.canvas.active_layer:
            return
            
        # Store the previous image state for undo/redo
        previous_image = None
        if self.canvas.active_layer.original_image:
            previous_image = self.canvas.active_layer.original_image.copy()
        
        # Update the image
        self.canvas.active_layer.set_image(result)
        
        # Add to history stack for undo/redo support
        if previous_image and hasattr(self.canvas, 'history'):
            self.canvas.history.add_command("filter", 
                                          self.canvas.active_layer,
                                          previous_image,  # Previous image
                                          result.copy())   # New image
        
    def get_name(self):
        """Return display name of the tool"""
        return self.__class__.__name__
        
    def get_tooltip(self):
        """Return tooltip for toolbar button"""
        return self.get_name()
        
    def get_controls(self):
        """Return control definitions for adjustment panel"""
        return {}
        
    def __del__(self):
        """Clean up resources when the tool is destroyed"""
        try:
            # Check if we have a work_thread attribute and if it exists
            if hasattr(self, 'work_thread') and self.work_thread is not None:
                # Check if the thread object is still valid and running
                if hasattr(self.work_thread, 'isRunning') and self.work_thread.isRunning():
                    self.work_thread.requestInterruption()
                    # Use a slightly longer wait time to ensure cleanup
                    if hasattr(self.work_thread, 'wait'):
                        if not self.work_thread.wait(500):
                            print("Warning: Thread did not terminate during cleanup")
        except (RuntimeError, AttributeError, TypeError):
            # Catch any exceptions during cleanup to prevent crashes
            pass

class ImageProcessingThread(QThread):
    """Thread for background image processing to keep UI responsive"""
    
    resultReady = pyqtSignal(object)
    
    def __init__(self, image, parameters, processing_func):
        super().__init__()
        self.image = image
        self.parameters = parameters.copy()  # Make a copy to prevent race conditions
        self.processing_func = processing_func

    def run(self):
        try:
            # Add more interruption checks throughout the method
            if self.isInterruptionRequested():
                self.resultReady.emit(None)
                return
                
            # Convert QImage to numpy array for processing
            if isinstance(self.image, QImage):
                # Fix for voidptr issues - create a copy and save to temp file
                temp_image = self.image.copy()
                
                # Get dimensions
                width = temp_image.width()
                height = temp_image.height()
                
                # Check for interruption before heavy processing
                if self.isInterruptionRequested():
                    self.resultReady.emit(None)
                    return
                
                # Create numpy array via safer method
                if hasattr(np, 'asarray'):
                    # Convert to RGBA format
                    if temp_image.format() != QImage.Format.Format_RGBA8888:
                        temp_image = temp_image.convertToFormat(QImage.Format.Format_RGBA8888)
                    
                    # Save to buffer and load with numpy
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                    temp_image.save(buffer, "PNG")
                    
                    from PIL import Image
                    import io
                    pil_img = Image.open(io.BytesIO(buffer.data().data()))
                    arr = np.array(pil_img)
                else:
                    # Fallback to simple shape creation
                    arr = np.zeros((height, width, 4), dtype=np.uint8)
            else:
                # Already a numpy array
                arr = self.image
                
            # Check for interruption before processing
            if self.isInterruptionRequested():
                self.resultReady.emit(None)
                return
                
            # Process the image
            result = self.processing_func(arr, self.parameters)
            
            if self.isInterruptionRequested():
                self.resultReady.emit(None)
                return
                
            # Convert back to QImage if needed
            if isinstance(result, np.ndarray):
                height, width = result.shape[:2]
                qimage_format = QImage.Format.Format_RGBA8888 if result.shape[2] == 4 else QImage.Format.Format_RGB888
                qimage = QImage(result.data, width, height, result.strides[0], qimage_format).copy()
                self.resultReady.emit(qimage)
            else:
                self.resultReady.emit(result)
                
        except Exception as e:
            print(f"Image processing error: {e}")
            self.resultReady.emit(None)

class BrightnessContrastTool(GPUBasedTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.parameters = {
            "brightness": 0,
            "contrast": 1.0
        }
        
    def process_array(self, arr, params):
        brightness = params.get("brightness", 0) * 50  # Scale effect for visibility
        contrast = params.get("contrast", 1.0)
        
        # Enhanced brightness/contrast algorithm for better visual effect
        result = np.clip(arr * contrast + brightness, 0, 255).astype(np.uint8)
        return result
        
    def get_name(self):
        return "Brightness/Contrast"
        
    def get_tooltip(self):
        return "Adjust image brightness and contrast"
        
    def get_controls(self):
        return {
            "title": "Brightness & Contrast",
            "params": [
                {
                    "name": "brightness",
                    "min": -5.0,
                    "max": 5.0,
                    "default": 0.0,
                    "step": 0.1
                },
                {
                    "name": "contrast",
                    "min": 0.1,
                    "max": 5.0,
                    "default": 1.0,
                    "step": 0.1
                }
            ]
        }

class SharpenBlurTool(GPUBasedTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.parameters = {
            "amount": 0  # -1 to 1 (negative for blur, positive for sharpen)
        }
        # Precalculate common kernels for efficiency
        self.kernels = {
            "sharpen_light": np.array([
                [0, -0.5, 0],
                [-0.5, 3, -0.5],
                [0, -0.5, 0]
            ]),
            "sharpen_medium": np.array([
                [-0.5, -1, -0.5],
                [-1, 7, -1],
                [-0.5, -1, -0.5]
            ]),
            "sharpen_strong": np.array([
                [-1, -1, -1],
                [-1, 9, -1],
                [-1, -1, -1]
            ])
        }
        
    def process_array(self, arr, params):
        amount = params.get("amount", 0)
        
        # Enhance effect for better visibility
        if abs(amount) < 0.05:
            return arr
        
        # Make a copy to avoid modifying original
        result = arr.copy()
        
        # Extract RGB channels (skip alpha)
        rgb = result[:, :, :3]
        
        if amount > 0:  # Sharpen (enhanced)
            # Use stronger kernel for better visibility
            kernel = np.array([
                [-amount, -amount, -amount],
                [-amount, 1 + 8 * amount, -amount],
                [-amount, -amount, -amount]
            ])
            rgb_filtered = cv2.filter2D(rgb, -1, kernel)
            result[:, :, :3] = np.clip(rgb_filtered, 0, 255)
        else:  # Blur (enhanced)
            blur_size = max(3, int(abs(amount * 20))) * 2 + 1  # Larger blur kernel
            result[:, :, :3] = cv2.GaussianBlur(rgb, (blur_size, blur_size), 0)
            
        return result
        
    def get_name(self):
        return "Sharpen/Blur"
        
    def get_tooltip(self):
        return "Sharpen or blur the image"
        
    def get_controls(self):
        return {
            "title": "Sharpen/Blur",
            "params": [
                {
                    "name": "amount",
                    "min": -3.0,  # Negative for blur
                    "max": 3.0,   # Positive for sharpen
                    "default": 0.0,
                    "step": 0.1
                }
            ]
        }

class ColorBalanceTool(GPUBasedTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.parameters = {
            "red": 1.0,
            "green": 1.0,
            "blue": 1.0,
            "temperature": 0  # Warm/cool adjustment
        }
        
    def process_array(self, arr, params):
        red = params.get("red", 1.0)
        green = params.get("green", 1.0)
        blue = params.get("blue", 1.0)
        temperature = params.get("temperature", 0) * 2  # Double the effect
        
        # Make a copy to avoid modifying original
        result = arr.copy()
        
        # Apply RGB adjustments with enhanced effect
        result[:, :, 0] = np.clip(result[:, :, 0] * blue, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * green, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] * red, 0, 255)
        
        # Apply temperature adjustment with enhanced effect
        if temperature != 0:
            if temperature > 0:  # Warmer
                result[:, :, 2] = np.clip(result[:, :, 2] * (1 + temperature * 0.4), 0, 255)
                result[:, :, 0] = np.clip(result[:, :, 0] * (1 - temperature * 0.2), 0, 255)
            else:  # Cooler
                result[:, :, 0] = np.clip(result[:, :, 0] * (1 - temperature * 0.4), 0, 255)
                result[:, :, 2] = np.clip(result[:, :, 2] * (1 + temperature * 0.2), 0, 255)
                
        return result
        
    def get_name(self):
        return "Color Balance"
        
    def get_tooltip(self):
        return "Adjust image color balance"
        
    def get_controls(self):
        return {
            "title": "Color Balance",
            "params": [
                {
                    "name": "red",
                    "min": 0.0,
                    "max": 4.0,
                    "default": 1.0,
                    "step": 0.1
                },
                {
                    "name": "green",
                    "min": 0.0,
                    "max": 4.0,
                    "default": 1.0,
                    "step": 0.1
                },
                {
                    "name": "blue",
                    "min": 0.0,
                    "max": 4.0,
                    "default": 1.0,
                    "step": 0.1
                },
                {
                    "name": "temperature",
                    "min": -2.0,
                    "max": 2.0,
                    "default": 0.0,
                    "step": 0.1
                }
            ]
        }

class NoiseReductionTool(GPUBasedTool):
    def __init__(self, canvas):
        super().__init__(canvas)
        self.parameters = {
            "strength": 0.5,
            "method": "nlm"  # nlm, bilateral, median
        }
        
    def process_array(self, arr, params):
        strength = params.get("strength", 0.5)
        method = params.get("method", "nlm")
        
        if strength < 0.05:  # Very small strength, just return original
            return arr
            
        # Make a copy to avoid modifying original
        result = arr.copy()
        
        # Extract RGB channels (skip alpha)
        rgb = result[:, :, :3]
        
        if method == "nlm":
            # Non-local means denoising (best quality but slow)
            h_value = int(strength * 10) + 5  # Convert strength to h-parameter
            result[:, :, :3] = cv2.fastNlMeansDenoisingColored(
                rgb, None, h_value, h_value, 7, 21
            )
        elif method == "bilateral":
            # Bilateral filtering (good edge preservation)
            d = int(strength * 10) + 3  # Filter size
            sigma_color = strength * 75 + 10
            sigma_space = strength * 75 + 10
            result[:, :, :3] = cv2.bilateralFilter(rgb, d, sigma_color, sigma_space)
        elif method == "median":
            # Median filtering (good for salt & pepper noise)
            k_size = int(strength * 10) * 2 + 1  # Must be odd
            result[:, :, :3] = cv2.medianBlur(rgb, k_size)
            
        return result
        
    def get_name(self):
        return "Noise Reduction"
        
    def get_tooltip(self):
        return "Reduce image noise"
        
    def get_controls(self):
        return {
            "title": "Noise Reduction",
            "params": [
                {
                    "name": "strength",
                    "min": 0.1,
                    "max": 5.0,
                    "default": 1.0,
                    "step": 0.1
                }
            ],
            "combos": [
                {
                    "name": "method",
                    "options": ["nlm", "bilateral", "median"]
                }
            ]
        }
