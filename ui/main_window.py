from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from ui.rom_tab import ROMTab
from ui.log_tab import LogTab
from core.logger import LogCapture

class SignalEmitter(QObject):
    """Signals for workflow events"""
    state_changed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, project_root: Path, logger):
        super().__init__()
        self.project_root = project_root
        self.logger = logger
        self.signals = SignalEmitter()
        
        # Create log capture for UI
        self.log_capture = LogCapture(logger)
        
        self.init_ui()
        self.setup_connections()
        
        # Title and window settings
        self.setWindowTitle("POCO F7 ROM Flasher - V1")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(900, 600)
    
    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # ROM Tab
        self.rom_tab = ROMTab(self.project_root, self.logger)
        self.tabs.addTab(self.rom_tab, "ROM Selection & Flash")
        
        # Log Tab
        self.log_tab = LogTab()
        self.tabs.addTab(self.log_tab, "Logs")
        
        layout.addWidget(self.tabs)
        
        # Footer with info
        footer = self.create_footer()
        layout.addWidget(footer)
        
        central_widget.setLayout(layout)
    
    def create_header(self) -> QWidget:
        """Create header widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        title = QLabel("POCO F7 / Redmi Turbo 4 Pro ROM Flasher")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        
        version = QLabel("v1.0.0")
        version.setAlignment(Qt.AlignRight)
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(version)
        
        widget.setLayout(layout)
        return widget
    
    def create_footer(self) -> QWidget:
        """Create footer widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        info = QLabel(
            "⚠️ Backup your data before flashing | "
            "Ensure bootloader is unlocked | "
            "Keep USB cable connected"
        )
        info.setStyleSheet("color: #666; font-size: 10px;")
        
        layout.addWidget(info)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect ROM tab signals
        self.rom_tab.signals.log.connect(self.on_log)
        self.rom_tab.signals.error.connect(self.on_error)
        self.rom_tab.signals.success.connect(self.on_success)
        
        # Connect main signals
        self.signals.log_message.connect(self.log_tab.append_log)
        self.signals.error.connect(self.show_error)
        self.signals.success.connect(self.show_success)
    
    def on_log(self, message: str):
        """Handle log message"""
        self.log_tab.append_log(message)
    
    def on_error(self, message: str):
        """Handle error"""
        self.log_tab.append_log(f"❌ {message}")
        self.show_error(message)
    
    def on_success(self, message: str):
        """Handle success"""
        self.log_tab.append_log(f"✅ {message}")
        self.show_success(message)
    
    def show_error(self, message: str):
        """Show error dialog"""
        QMessageBox.critical(self, "Error", message)
    
    def show_success(self, message: str):
        """Show success dialog"""
        QMessageBox.information(self, "Success", message)
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.rom_tab.is_flashing:
            reply = QMessageBox.question(
                self,
                "Flashing in Progress",
                "Flashing is in progress. Close anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.rom_tab.stop_flashing()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
