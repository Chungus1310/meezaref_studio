import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt
from app import ImageReferenceApp, resource_path
from debug_util import debug_log

def exception_hook(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    # Log the error
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    debug_log(f"Unhandled exception: {error_msg}", "ERROR")
    
    # Show error dialog
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Error")
    error_dialog.setText("An unexpected error occurred.")
    error_dialog.setDetailedText(error_msg)
    error_dialog.exec()

def main():
    # Enable high DPI support
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Create application
    app = QApplication(sys.argv)
    
    # Set application details for Windows
    app.setApplicationName("Meeza Reference Studio")
    app.setOrganizationName("Chun")
    
    # Set app icon for taskbar
    icon_path = resource_path("icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Set default font
    app.setFont(QFont("Segoe UI", 9))
    
    debug_log("Starting application")
    
    # Create and show the main window
    window = ImageReferenceApp()
    window._create_collapsible_dock_buttons()
    window.show()
    
    # Run the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    # Set custom exception handler
    sys.excepthook = exception_hook
    main()