from enum import Enum
from dataclasses import dataclass
from typing import Optional

class DeviceMode(Enum):
    """Device connection modes"""
    UNKNOWN = "unknown"
    FASTBOOT = "fastboot"
    ADB = "adb"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"

class FlashState(Enum):
    """Flash workflow states"""
    IDLE = "idle"
    ROM_SELECTED = "rom_selected"
    PACKAGE_VALIDATED = "package_validated"
    IMAGES_EXTRACTED = "images_extracted"
    FASTBOOT_DETECTED = "fastboot_detected"
    DEVICE_VERIFIED = "device_verified"
    FLASHING_IMAGES = "flashing_images"
    REBOOTING_RECOVERY = "rebooting_recovery"
    RECOVERY_DETECTED = "recovery_detected"
    WAITING_FOR_SIDELOAD = "waiting_for_sideload"
    SIDELOAD_MODE_DETECTED = "sideload_mode_detected"
    SIDELOADING_ROM = "sideloading_rom"
    COMPLETED = "completed"
    
    # Failure states
    PACKAGE_INVALID = "package_invalid"
    WRONG_DEVICE = "wrong_device"
    MISSING_IMAGE = "missing_image"
    FASTBOOT_ERROR = "fastboot_error"
    RECOVERY_TIMEOUT = "recovery_timeout"
    SIDELOAD_ERROR = "sideload_error"
    USER_ABORTED = "user_aborted"
    EXTRACTION_ERROR = "extraction_error"

@dataclass
class DeviceInfo:
    """Device information"""
    mode: DeviceMode
    product: Optional[str] = None
    serial: Optional[str] = None
    bootloader_version: Optional[str] = None
    is_unlocked: Optional[bool] = None
    
    def is_valid_for_flashing(self) -> bool:
        """Check if device is ready for flashing"""
        return (
            self.mode == DeviceMode.FASTBOOT and
            self.product == "onyx" and
            self.serial is not None
        )

@dataclass
class ROMPackage:
    """ROM package information"""
    zip_path: str
    is_valid: bool = False
    has_payload: bool = False
    extracted_path: Optional[str] = None
    required_images: dict = None  # {partition: (exists, path, hash)}
    build_info: dict = None
    file_hash: Optional[str] = None
    
    def __post_init__(self):
        if self.required_images is None:
            self.required_images = {}
        if self.build_info is None:
            self.build_info = {}

@dataclass
class CommandResult:
    """Result of a command execution"""
    returncode: int
    stdout: str
    stderr: str
    
    @property
    def success(self) -> bool:
        return self.returncode == 0
    
    @property
    def error_message(self) -> str:
        return self.stderr or self.stdout

# Partition configuration for onyx
REQUIRED_PARTITIONS = [
    "boot",
    "dtbo",
    "init_boot",
    "recovery",
    "vendor_boot",
]

EXPECTED_DEVICE_CODENAME = "onyx"
