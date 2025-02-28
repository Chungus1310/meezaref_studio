import inspect
import datetime
import os

# Global debug flag
DEBUG_ENABLED = True
LOG_FILE = "c:\\Users\\Administrator\\Desktop\\testing\\debug.log"
CONSOLE_OUTPUT = False  # Set to False to disable console output

def debug_log(message, level="INFO"):
    """Log a debug message to console and file"""
    if not DEBUG_ENABLED:
        return
        
    # Get caller info
    caller_frame = inspect.currentframe().f_back
    caller_info = inspect.getframeinfo(caller_frame)
    
    # Format message with timestamp and caller info
    # Fixed timestamp format with proper microsecond precision
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    file_name = os.path.basename(caller_info.filename)
    line_num = caller_info.lineno
    
    log_message = f"[{timestamp}] [{level}] {file_name}:{line_num} - {message}"
    
    # Print to console if enabled
    if CONSOLE_OUTPUT:
        print(log_message)
    
    # Write to file
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_message + "\n")
    except Exception as e:
        if CONSOLE_OUTPUT:
            print(f"Error writing to log file: {e}")
