import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_executable():
    """Build the Meeza Reference Studio executable using PyInstaller"""
    print("🔧 Building Meeza Reference Studio executable...")
    
    # Check for icon files
    if not os.path.exists("icon.ico"):
        print("❌ Error: icon.ico not found! Please create or provide this file.")
        return False
    
    if not os.path.exists("icon.png"):
        print("❌ Error: icon.png not found! Please create or provide this file.")
        return False
    
    # Verify UPX installation
    upx_path = "C:\\upx-4.2.4-win64"
    if not os.path.exists(upx_path) or not os.path.exists(os.path.join(upx_path, "upx.exe")):
        print(f"⚠️ Warning: UPX not found at {upx_path}. Compression will not be applied.")
        upx_arg = "--noupx"
    else:
        print(f"✅ Using UPX from {upx_path} for compression")
        upx_arg = f"--upx-dir={upx_path}"
    
    # Install PyInstaller if not already installed
    try:
        import PyInstaller
        print(f"✅ Using PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Ensure clean build directory
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"🧹 Cleaning {folder} directory...")
            shutil.rmtree(folder)
    
    # Run PyInstaller with the spec file
    print("🚀 Starting build process...")
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller",
        "meezaref_studio.spec",
        "--clean",
        upx_arg,
        "--log-level=INFO"
    ]
    
    try:
        subprocess.check_call(cmd)
        exe_path = Path("dist/MeezaRefStudio/MeezaRefStudio.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ Build completed successfully!")
            print(f"📦 Executable size: {size_mb:.2f} MB")
            print(f"📂 Location: {exe_path.absolute()}")
            return True
        else:
            print("❌ Build failed: Executable not found")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error: {e}")
        return False

if __name__ == "__main__":
    build_executable()
