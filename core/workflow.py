import time
import shutil
from pathlib import Path
from typing import Callable, Optional
from core.models import FlashState, DeviceMode, REQUIRED_PARTITIONS, EXPECTED_DEVICE_CODENAME
from core.device import DeviceManager
from core.package_validator import PackageValidator
from core.payload import PayloadExtractor

class FlashWorkflow:
    """Orchestrate ROM flashing workflow with state machine"""
    
    def __init__(
        self,
        device: DeviceManager,
        validator: PackageValidator,
        extractor: PayloadExtractor,
        logger
    ):
        self.device = device
        self.validator = validator
        self.extractor = extractor
        self.logger = logger
        
        self.state = FlashState.IDLE
        self.rom_path: Optional[Path] = None
        self.extract_dir: Optional[Path] = None
        self.images: dict = {}
        self._stop_requested = False
    
    def set_state(self, state: FlashState):
        """Update workflow state"""
        self.state = state
        self.logger.debug(f"State: {state.value}")
    
    def request_stop(self):
        """Request workflow to stop"""
        self._stop_requested = True
        self.logger.warning("Stop requested")
    
    def _is_stopped(self) -> bool:
        """Check if stop was requested"""
        return self._stop_requested
    
    def select_rom(self, rom_path: Path) -> bool:
        """Select ROM file for flashing"""
        self.set_state(FlashState.ROM_SELECTED)
        self.rom_path = rom_path
        self.logger.info(f"Selected ROM: {rom_path.name}")
        return True
    
    def validate_package(self) -> bool:
        """Validate ROM package"""
        self.set_state(FlashState.PACKAGE_VALIDATED)
        
        if not self.rom_path:
            self.set_state(FlashState.PACKAGE_INVALID)
            self.logger.error("No ROM selected")
            return False
        
        # Validate ZIP structure and extract payload
        package = self.validator.validate_rom_package(self.rom_path)
        
        if not package.is_valid:
            self.set_state(FlashState.PACKAGE_INVALID)
            return False
        
        return True
    
    def extract_images(self) -> bool:
        """Extract images from payload.bin"""
        self.set_state(FlashState.IMAGES_EXTRACTED)
        
        if not self.rom_path:
            self.logger.error("No ROM selected")
            return False
        
        # Create extraction directory
        self.extract_dir = self.rom_path.parent / f".{self.rom_path.stem}_extract"
        self.extract_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Extracting to: {self.extract_dir}")
        
        # Find payload.bin
        payload_path = None
        temp_payload = self.rom_path.parent / f".{self.rom_path.stem}_payload" / "payload.bin"
        
        if temp_payload.exists():
            payload_path = temp_payload
        else:
            # Try to extract from ZIP
            ok, path = self.validator.extract_payload_info(self.rom_path)
            if ok:
                payload_path = path
        
        if not payload_path:
            self.set_state(FlashState.EXTRACTION_ERROR)
            self.logger.error("Could not find or extract payload.bin")
            return False
        
        # Extract images
        ok, msg = self.extractor.extract_images(payload_path, self.extract_dir)
        if not ok:
            self.set_state(FlashState.EXTRACTION_ERROR)
            return False
        
        # Verify extraction
        ok, images = self.extractor.verify_extraction(self.extract_dir)
        if not ok:
            self.set_state(FlashState.MISSING_IMAGE)
            return False
        
        self.images = images
        return True
    
    def wait_fastboot(self, timeout: int = 30) -> bool:
        """Wait for device in fastboot mode"""
        self.set_state(FlashState.FASTBOOT_DETECTED)
        self.logger.info("Waiting for device in fastboot mode...")
        
        return self.device.wait_for_device(DeviceMode.FASTBOOT, timeout)
    
    def verify_device(self) -> bool:
        """Verify device is correct model"""
        self.set_state(FlashState.DEVICE_VERIFIED)
        
        device_info = self.device.get_device_info()
        self.logger.info(f"Device mode: {device_info.mode.value}")
        
        if device_info.mode != DeviceMode.FASTBOOT:
            self.set_state(FlashState.WRONG_DEVICE)
            self.logger.error("Device is not in fastboot mode")
            return False
        
        if not device_info.product:
            self.set_state(FlashState.WRONG_DEVICE)
            self.logger.error("Could not determine device model")
            return False
        
        self.logger.info(f"Device product: {device_info.product}")
        self.logger.info(f"Device serial: {device_info.serial}")
        
        if device_info.product != EXPECTED_DEVICE_CODENAME:
            self.set_state(FlashState.WRONG_DEVICE)
            self.logger.error(
                f"✗ Wrong device! Expected '{EXPECTED_DEVICE_CODENAME}' "
                f"but device reports '{device_info.product}'"
            )
            self.logger.error("This tool only supports POCO F7 (onyx)")
            return False
        
        self.logger.info(f"✓ Device verified as {EXPECTED_DEVICE_CODENAME}")
        return True
    
    def flash_images(self) -> bool:
        """Flash images to device"""
        self.set_state(FlashState.FLASHING_IMAGES)
        
        if not self.images:
            self.set_state(FlashState.MISSING_IMAGE)
            self.logger.error("No images extracted")
            return False
        
        self.logger.info(f"Flashing {len(self.images)} images...")
        
        for partition in REQUIRED_PARTITIONS:
            if self._is_stopped():
                self.set_state(FlashState.USER_ABORTED)
                return False
            
            if partition not in self.images:
                self.set_state(FlashState.MISSING_IMAGE)
                self.logger.error(f"Missing image for partition: {partition}")
                return False
            
            result = self.device.flash_partition(
                partition,
                self.images[partition]
            )
            
            if not result.success:
                self.set_state(FlashState.FASTBOOT_ERROR)
                self.logger.error(f"Failed to flash {partition}")
                return False
        
        self.logger.info("✓ All images flashed successfully")
        return True
    
    def reboot_recovery(self) -> bool:
        """Reboot device to recovery"""
        self.set_state(FlashState.REBOOTING_RECOVERY)
        
        result = self.device.reboot_recovery()
        if not result.success:
            self.set_state(FlashState.FASTBOOT_ERROR)
            return False
        
        # Wait for recovery
        self.set_state(FlashState.RECOVERY_DETECTED)
        if not self.device.wait_for_device(DeviceMode.RECOVERY, timeout=30):
            self.set_state(FlashState.RECOVERY_TIMEOUT)
            return False
        
        return True
    
    def wait_sideload_mode(self, timeout: int = 60) -> bool:
        """Wait for device in sideload mode"""
        self.set_state(FlashState.WAITING_FOR_SIDELOAD)
        
        self.logger.info("Waiting for device in sideload mode...")
        self.logger.info("On the phone:")
        self.logger.info("  1. Select 'Apply Update'")
        self.logger.info("  2. Select 'Apply from ADB'")
        self.logger.info("  3. Keep USB cable connected")
        
        start = time.time()
        while time.time() - start < timeout:
            if self._is_stopped():
                self.set_state(FlashState.USER_ABORTED)
                return False
            
            mode = self.device.get_device_mode()
            if mode == DeviceMode.SIDELOAD:
                self.set_state(FlashState.SIDELOAD_MODE_DETECTED)
                self.logger.info("✓ Device in sideload mode")
                return True
            
            self.logger.debug(f"Current mode: {mode.value}")
            time.sleep(2)
        
        self.set_state(FlashState.RECOVERY_TIMEOUT)
        self.logger.error("Sideload mode not detected (timeout)")
        return False
    
    def sideload_rom(self) -> bool:
        """Sideload ROM to device"""
        self.set_state(FlashState.SIDELOADING_ROM)
        
        if not self.rom_path:
            self.logger.error("No ROM selected")
            return False
        
        result = self.device.adb_sideload(self.rom_path)
        if not result.success:
            self.set_state(FlashState.SIDELOAD_ERROR)
            return False
        
        self.set_state(FlashState.COMPLETED)
        self.logger.info("✓ ROM sideload completed")
        return True
    
    def cleanup(self):
        """Clean up temporary files"""
        self.logger.info("Cleaning up temporary files...")
        
        # Clean extraction directory
        if self.extract_dir and self.extract_dir.exists():
            try:
                shutil.rmtree(self.extract_dir)
                self.logger.debug(f"Removed {self.extract_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup extraction dir: {str(e)}")
        
        # Clean payload extraction directory
        if self.rom_path:
            payload_dir = self.rom_path.parent / f".{self.rom_path.stem}_payload"
            if payload_dir.exists():
                try:
                    shutil.rmtree(payload_dir)
                    self.logger.debug(f"Removed {payload_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup payload dir: {str(e)}")
