from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QTextEdit, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QFont

from core.device import DeviceManager
from core.package_validator import PackageValidator
from core.payload import PayloadExtractor
from core.workflow import FlashWorkflow

class FlashSignals(QObject):
    """Signals for flashing workflow"""
    log = pyqtSignal(str)
    error = pyqtSignal(str)
    success = pyqtSignal(str)
    state_changed = pyqtSignal(str)
    progress = pyqtSignal(int)

class FlashWorker(QThread):
    """Worker thread for flashing"""
    signals = FlashSignals()
    
    def __init__(self, workflow: FlashWorkflow, rom_path: Path):
        super().__init__()
        self.workflow = workflow
        self.rom_path = rom_path
    
    def run(self):
        """Execute flashing workflow"""
        try:
            # Step 1: Validate package
            self.signals.state_changed.emit("Validating ROM package...")
            if not self.workflow.validate_package():
                self.signals.error.emit("ROM package validation failed")
                return
            self.signals.progress.emit(10)
            
            # Step 2: Extract images
            self.signals.state_changed.emit("Extracting images from payload...")
            if not self.workflow.extract_images():
                self.signals.error.emit("Failed to extract images")
                return
            self.signals.progress.emit(25)
            
            # Step 3: Wait for fastboot
            self.signals.state_changed.emit("Waiting for device in fastboot mode...")
            if not self.workflow.wait_fastboot(timeout=60):
                self.signals.error.emit(
                    "Device not found in fastboot mode.\n\n"
                    "Steps:\n"
                    "1. Power off device\n"
                    "2. Connect USB cable\n"
                    "3. Hold Volume Down + Power for 3 seconds\n"
                    "4. Device should enter fastboot mode"
                )
                return
            self.signals.progress.emit(35)
            
            # Step 4: Verify device
            self.signals.state_changed.emit("Verifying device...")
            if not self.workflow.verify_device():
                self.signals.error.emit("Device verification failed")
                return
            self.signals.progress.emit(40)
            
            # Step 5: Flash images
            self.signals.state_changed.emit("Flashing images...")
            if not self.workflow.flash_images():
                if self.workflow._is_stopped():
                    self.signals.log.emit("Flashing cancelled by user")
                else:
                    self.signals.error.emit("Image flashing failed")
                return
            self.signals.progress.emit(70)
            
            # Step 6: Reboot to recovery
            self.signals.state_changed.emit("Rebooting to recovery...")
            if not self.workflow.reboot_recovery():
                self.signals.error.emit("Failed to reboot to recovery")
                return
            self.signals.progress.emit(75)
            
            # Step 7: Wait for sideload
            self.signals.state_changed.emit("Waiting for sideload mode...")
            if not self.workflow.wait_sideload_mode(timeout=120):
                if self.workflow._is_stopped():
                    self.signals.log.emit("Flashing cancelled by user")
                else:
                    self.signals.error.emit("Device did not enter sideload mode")
                return
            self.signals.progress.emit(80)
            
            # Step 8: Sideload ROM
            self.signals.state_changed.emit("Sideloading ROM...")
            if not self.workflow.sideload_rom():
                self.signals.error.emit("ROM sideload failed")
                return
            self.signals.progress.emit(95)
            
            # Cleanup
            self.workflow.cleanup()
            self.signals.progress.emit(100)
            
            self.signals.success.emit(
                "ROM flashing completed!\n\n"
                "On the device:\n"
                "1. Select 'Reboot System Now'\n"
                "2. Device will boot with new ROM\n\n"
                "First boot may take a few minutes."
            )
        
        except Exception as e:
            self.signals.error.emit(f"Unexpected error: {str(e)}")
        
        finally:
            self.workflow.cleanup()

class ROMTab(QWidget):
    """ROM selection and flashing tab"""
    
    signals = FlashSignals()
    
    def __init__(self, project_root: Path, logger):
        super().__init__()
        self.project_root = project_root
        self.logger = logger
        self.is_flashing = False
        
        # Initialize components
        self.device = DeviceManager(
            project_root / "tools" / "adb.exe",
            project_root / "tools" / "fastboot.exe",
            logger
        )
        self.validator = PackageValidator(logger)
        self.extractor = PayloadExtractor(
            project_root / "tools" / "payload-dumper-go.exe",
            logger
        )
        self.workflow = None
        self.flash_worker = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        
        # ROM Selection Group
        rom_group = self.create_rom_group()
        layout.addWidget(rom_group)
        
        # Status Group
        status_group = self.create_status_group()
        layout.addWidget(status_group)
        
        # Progress Group
        progress_group = self.create_progress_group()
        layout.addWidget(progress_group)
        
        # Device Info Group
        device_group = self.create_device_group()
        layout.addWidget(device_group)
        
        # Control Group
        control_group = self.create_control_group()
        layout.addWidget(control_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def create_rom_group(self) -> QGroupBox:
        """Create ROM selection group"""
        group = QGroupBox("Step 1: Select ROM")
        layout = QHBoxLayout()
        
        self.rom_label = QLabel("No ROM selected")
        self.rom_label.setStyleSheet("color: #999;")
        
        self.select_btn = QPushButton("Select AOSP ROM ZIP")
        self.select_btn.clicked.connect(self.select_rom)
        
        layout.addWidget(self.rom_label)
        layout.addStretch()
        layout.addWidget(self.select_btn)
        
        group.setLayout(layout)
        return group
    
    def create_status_group(self) -> QGroupBox:
        """Create status display group"""
        group = QGroupBox("Status")
        layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(100)
        self.status_text.setStyleSheet("font-family: monospace; font-size: 10px;")
        
        layout.addWidget(self.status_text)
        group.setLayout(layout)
        return group
    
    def create_progress_group(self) -> QGroupBox:
        """Create progress display group"""
        group = QGroupBox("Progress")
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        
        layout.addWidget(self.progress_bar)
        group.setLayout(layout)
        return group
    
    def create_device_group(self) -> QGroupBox:
        """Create device info group"""
        group = QGroupBox("Step 2: Device Connection")
        layout = QVBoxLayout()
        
        info_layout = QHBoxLayout()
        
        self.device_status = QLabel("Checking device...")
        self.device_status.setStyleSheet("color: #666;")
        
        self.refresh_btn = QPushButton("Refresh Device Status")
        self.refresh_btn.clicked.connect(self.check_device)
        
        info_layout.addWidget(self.device_status)
        info_layout.addStretch()
        info_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(info_layout)
        group.setLayout(layout)
        return group
    
    def create_control_group(self) -> QGroupBox:
        """Create control buttons group"""
        group = QGroupBox("Actions")
        layout = QHBoxLayout()
        
        self.flash_btn = QPushButton("Start Flashing")
        self.flash_btn.clicked.connect(self.start_flashing)
        self.flash_btn.setEnabled(False)
        self.flash_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:!pressed {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        self.stop_btn = QPushButton("Stop Flashing")
        self.stop_btn.clicked.connect(self.stop_flashing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:!pressed {
                background-color: #da190b;
            }
        """)
        
        layout.addWidget(self.flash_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        
        group.setLayout(layout)
        return group
    
    def select_rom(self):
        """Select ROM file"""
        rom_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select AOSP ROM ZIP",
            "",
            "ZIP Files (*.zip);;All Files (*)"
        )
        
        if rom_path:
            rom_path = Path(rom_path)
            
            # Validate selection
            if self.workflow is None:
                self.workflow = FlashWorkflow(
                    self.device,
                    self.validator,
                    self.extractor,
                    self.logger
                )
            
            if self.workflow.select_rom(rom_path):
                self.rom_label.setText(f"Selected: {rom_path.name}")
                self.rom_label.setStyleSheet("color: #333;")
                self.update_status(f"Selected: {rom_path.name}")
                self.flash_btn.setEnabled(True)
                self.signals.log.emit(f"ROM selected: {rom_path.name}")
    
    def check_device(self):
        """Check device connection"""
        if self.workflow is None:
            self.workflow = FlashWorkflow(
                self.device,
                self.validator,
                self.extractor,
                self.logger
            )
        
        device_info = self.device.get_device_info()
        self.update_device_status(device_info)
    
    def update_device_status(self, info):
        """Update device status display"""
        status_text = f"Mode: {info.mode.value}"
        
        if info.product:
            status_text += f" | Product: {info.product}"
        
        if info.serial:
            status_text += f" | Serial: {info.serial}"
        
        if info.mode.value == "fastboot":
            self.device_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif info.mode.value == "sideload":
            self.device_status.setStyleSheet("color: #FF9800; font-weight: bold;")
        elif info.mode.value == "recovery":
            self.device_status.setStyleSheet("color: #2196F3; font-weight: bold;")
        else:
            self.device_status.setStyleSheet("color: #f44336;")
        
        self.device_status.setText(status_text)
    
    def update_status(self, message: str):
        """Update status text"""
        self.status_text.append(message)
        # Scroll to bottom
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )
    
    def start_flashing(self):
        """Start flashing process"""
        if not self.workflow or not self.workflow.rom_path:
            QMessageBox.warning(self, "No ROM Selected", "Please select a ROM first")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Flashing",
            "This will erase recovery and flash images.\n\n"
            "Ensure:\n"
            "- Device bootloader is unlocked\n"
            "- USB cable is properly connected\n"
            "- All data is backed up\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.is_flashing = True
        self.flash_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.select_btn.setEnabled(False)
        
        # Create and start worker thread
        self.flash_worker = FlashWorker(self.workflow, self.workflow.rom_path)
        self.flash_worker.signals.log.connect(self.update_status)
        self.flash_worker.signals.error.connect(self.on_flash_error)
        self.flash_worker.signals.success.connect(self.on_flash_success)
        self.flash_worker.signals.state_changed.connect(self.update_status)
        self.flash_worker.signals.progress.connect(self.progress_bar.setValue)
        self.flash_worker.finished.connect(self.on_flash_finished)
        
        self.update_status("Starting flashing process...")
        self.flash_worker.start()
    
    def stop_flashing(self):
        """Stop flashing process"""
        if self.workflow:
            self.workflow.request_stop()
            self.update_status("Stop requested...")
    
    def on_flash_error(self, error: str):
        """Handle flash error"""
        self.signals.error.emit(error)
        self.update_status(f"❌ Error: {error}")
    
    def on_flash_success(self, message: str):
        """Handle flash success"""
        self.signals.success.emit(message)
        self.update_status(f"✅ {message}")
    
    def on_flash_finished(self):
        """Handle flash worker finished"""
        self.is_flashing = False
        self.flash_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.select_btn.setEnabled(True)
        
        # Update device status
        self.check_device()
