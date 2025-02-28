import numpy as np
try:
    import pyopencl as cl
    OPENCL_AVAILABLE = True
except ImportError:
    OPENCL_AVAILABLE = False
    
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
from PIL import Image
import io
import os
import tempfile

class GPUImageProcessor:
    def __init__(self):
        self.initialized = False
        
        if not OPENCL_AVAILABLE:
            print("PyOpenCL not available. Using CPU processing.")
            return
            
        try:
            # Disable/Log compiler warnings
            os.environ['PYOPENCL_COMPILER_OUTPUT'] = '0'
            os.environ['PYOPENCL_NO_CACHE'] = '1'
            
            platforms = cl.get_platforms()
            if not platforms:
                print("No OpenCL platforms found")
                return
                
            platform = platforms[0]
            # Try to use CPU instead of GPU to prevent freezing
            devices = platform.get_devices(device_type=cl.device_type.CPU)
            if not devices:
                devices = platform.get_devices(device_type=cl.device_type.GPU)
                if not devices:
                    print("No OpenCL devices found")
                    return
            
            self.context = cl.Context(devices)
            self.queue = cl.CommandQueue(self.context)
            self.build_programs()
            
            self.initialized = True
            print(f"GPU acceleration initialized using: {devices[0].name}")
        except Exception as e:
            print(f"Failed to initialize GPU acceleration: {e}")
            self.initialized = False
    
    def build_programs(self):
        self.program = cl.Program(self.context, """
            __kernel void scale_image(__global const uchar4* input, 
                                    __global uchar4* output,
                                    const int src_width, 
                                    const int src_height,
                                    const int dst_width, 
                                    const int dst_height)
            {
                int dst_x = get_global_id(0);
                int dst_y = get_global_id(1);
                
                if (dst_x >= dst_width || dst_y >= dst_height)
                    return;
                
                float scale_x = (float)src_width / dst_width;
                float scale_y = (float)src_height / dst_height;
                
                int src_x = (int)(dst_x * scale_x);
                int src_y = (int)(dst_y * scale_y);
                
                src_x = min(src_x, src_width - 1);
                src_y = min(src_y, src_height - 1);
                
                int src_idx = src_y * src_width + src_x;
                int dst_idx = dst_y * dst_width + dst_x;
                
                output[dst_idx] = input[src_idx];
            }
        """).build()

    def scale_image(self, img, scale_x, scale_y):
        if not self.initialized:
            return None
            
        try:
            # Convert QImage to numpy array without using temporary files
            if isinstance(img, QImage):
                # Create in-memory buffer
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                img.save(buffer, "PNG")
                buffer.close()
                
                # Convert buffer data to numpy array using PIL
                from PIL import Image
                import io
                pil_img = Image.open(io.BytesIO(byte_array.data()))
                src_array = np.array(pil_img)
            else:
                src_array = img
                
            if len(src_array.shape) == 3:
                src_height, src_width, channels = src_array.shape
            else:
                src_height, src_width = src_array.shape
                channels = 1
                
            dst_width = max(1, int(src_width * scale_x))
            dst_height = max(1, int(src_height * scale_y))
            
            # Convert to RGBA if needed
            if channels != 4:
                if channels == 3:
                    rgba_array = np.zeros((src_height, src_width, 4), dtype=np.uint8)
                    rgba_array[:, :, :3] = src_array
                    rgba_array[:, :, 3] = 255
                    src_array = rgba_array
                elif channels == 1:
                    rgba_array = np.zeros((src_height, src_width, 4), dtype=np.uint8)
                    rgba_array[:, :, :3] = np.repeat(src_array[:, :, np.newaxis], 3, axis=2)
                    rgba_array[:, :, 3] = 255
                    src_array = rgba_array
            
            flat_src = src_array.reshape(-1).astype(np.uint8)
            
            src_buf = cl.Buffer(self.context, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, 
                               hostbuf=flat_src)
            dst_buf = cl.Buffer(self.context, cl.mem_flags.WRITE_ONLY, 
                               size=dst_width * dst_height * 4)
            
            self.program.scale_image(self.queue, (dst_width, dst_height), None,
                                   src_buf, dst_buf,
                                   np.int32(src_width), np.int32(src_height),
                                   np.int32(dst_width), np.int32(dst_height))
            
            result = np.empty(dst_width * dst_height * 4, dtype=np.uint8)
            cl.enqueue_copy(self.queue, result, dst_buf)
            
            result_img = result.reshape(dst_height, dst_width, 4)
            
            # Convert numpy array directly to QImage without temporary files
            height, width = result_img.shape[:2]
            bytes_per_line = width * 4
            qt_image = QImage(result_img.data, width, height, bytes_per_line, QImage.Format.Format_RGBA8888).copy()
            
            return qt_image
            
        except Exception as e:
            print(f"GPU scaling failed: {e}")
            return None
            
    def is_available(self):
        return self.initialized
