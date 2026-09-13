from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from PyQt5.QtCore import Qt

class LogTab(QWidget):
    """Log display tab"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 10px;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        
        layout.addWidget(self.log_text)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        
        copy_btn = QPushButton("Copy All")
        copy_btn.clicked.connect(self.copy_log)
        
        control_layout.addStretch()
        control_layout.addWidget(copy_btn)
        control_layout.addWidget(clear_btn)
        
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
    
    def append_log(self, message: str):
        """Append message to log"""
        self.log_text.append(message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Clear all log messages"""
        self.log_text.clear()
    
    def copy_log(self):
        """Copy all log text to clipboard"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
    
    def get_log_text(self) -> str:
        """Get all log text"""
        return self.log_text.toPlainText()
