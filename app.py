import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.main_window import MainWindow
from core.logger import setup_logger

def check_resources():
    """Verify bundled tools exist"""
    tools_dir = project_root / "tools"
    required_tools = ["adb.exe", "fastboot.exe", "payload-dumper-go.exe"]
    
    missing = []
    for tool in required_tools:
        tool_path = tools_dir / tool
        if not tool_path.exists():
            missing.append(tool)
    
    if missing:
        return False, f"Missing tools: {', '.join(missing)}"
    
    return True, "All tools present"

def setup_logs_directory():
    """Create logs directory if it doesn't exist"""
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir

def main():
    try:
        # Setup logging first
        logs_dir = setup_logs_directory()
        logger = setup_logger(logs_dir)
        
        logger.info("="*60)
        logger.info(f"POCO F7 ROM Flasher V1 - {datetime.now()}")
        logger.info("="*60)
        
        # Check resources
        ok, msg = check_resources()
        logger.info(f"Resource check: {msg}")
        
        if not ok:
            print(f"ERROR: {msg}")
            sys.exit(1)
        
        # Initialize Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("POCO F7 ROM Flasher")
        app.setApplicationVersion("1.0.0")
        
        # Create and show main window
        window = MainWindow(project_root, logger)
        window.show()
        
        logger.info("Application started successfully")
        sys.exit(app.exec_())
        
    except Exception as e:
        error_msg = f"Fatal error during startup: {str(e)}"
        print(error_msg)
        if 'logger' in locals():
            logger.critical(error_msg, exc_info=True)
        
        # Show error dialog if Qt is available
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            QMessageBox.critical(None, "Startup Error", error_msg)
        except:
            pass
        
        sys.exit(1)

if __name__ == "__main__":
    main()
