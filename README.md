# 🎨 Meeza Reference Studio

> A modern image reference and editing tool for artists and designers

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt-6.0%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Overview

Meeza Reference Studio is a powerful yet intuitive image reference tool designed for artists, illustrators, and designers. It provides a modern, layer-based workspace for importing, arranging, and manipulating reference images with professional-grade tools.

![Meeza Reference Studio Screenshot](https://github.com/user-attachments/assets/43a5b907-5d99-4754-b8ca-c3e1a3d0851c)

## 🚀 Features

- 🖼️ **Layer-Based Workflow**: Organize your references with a full-featured layer system
- 🎭 **Smart Selection Tool**: Select areas with rectangle or elliptical shapes to create new layers
- 🔍 **Advanced Color Picker**: Sample colors with precise information display and magnification
- 🌈 **GPU-Accelerated Image Processing**: Fast, high-quality image effects and adjustments
- 💨 **Smooth Performance**: Optimized rendering for large images and smooth zooming
- 🎛️ **Non-Destructive Editing**: Full undo/redo functionality for all operations
- 🌙 **Modern Dark Interface**: Sleek, eye-friendly design with glass effects
- 💾 **Project Saving**: Save and load your complete workspace including all layers and settings

## 🛠️ Image Editing Tools

- **Brightness & Contrast**: Adjust image luminosity and dynamic range
- **Sharpen & Blur**: Enhance details or smooth areas with precision controls
- **Color Balance**: Fine-tune RGB and temperature values for perfect color matching
- **Noise Reduction**: Clean up images with multiple noise reduction algorithms

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- PyQt6
- OpenCV (cv2)
- NumPy
- PyOpenCL (optional, for GPU acceleration)

### Quick Install

1. Clone the repository:
   ```
   git clone https://github.com/chungus1310/meezaref_studio.git
   cd meezaref_studio
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

### Building Windows Executable 🖥️

To create a standalone Windows executable (.exe) file:

1. Ensure you have the required icons:
   - `icon.ico` - Application icon file for Windows
   - `icon.png` - In-app icon displayed in the title bar

2. Make sure UPX is installed for compression (optional):
   - Download from [UPX GitHub](https://github.com/upx/upx/releases)
   - Extract to `C:\upx-4.2.4-win64`

3. Install PyInstaller:
   ```
   pip install pyinstaller
   ```

4. Run the build script:
   ```
   python build.py
   ```

5. The executable will be created at:
   ```
   dist/MeezaRefStudio/MeezaRefStudio.exe
   ```

The executable will include all necessary dependencies and can be distributed to users who don't have Python installed.

## 🔧 Usage

### Basic Controls

- **Mouse Wheel**: Zoom in/out
- **Middle Mouse Button**: Pan the canvas
- **Left Click + Drag**: Move layers or use active tool
- **Right Click**: Context menu for additional options

### Keyboard Shortcuts

- **Ctrl+Z**: Undo
- **Ctrl+Y**: Redo
- **Ctrl+S**: Save project
- **Ctrl+O**: Open project
- **Ctrl+I**: Import images

## 🧪 Technologies Used

- **PyQt6**: Modern UI framework
- **OpenCV**: Advanced image processing
- **NumPy**: Efficient array operations
- **PyOpenCL**: GPU acceleration (when available)

## 💡 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

Created with ❤️ by [Chun](https://github.com/chungus1310)

---

*Meeza Reference Studio - Elevating your creative workflow*
