import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional, List
from core.models import CommandResult, DeviceInfo, DeviceMode

class DeviceManager:
    """Manage device communication via ADB and Fastboot"""
    
    def __init__(self, adb_path: Path, fastboot_path: Path, logger):
        self.adb_path = str(adb_path)
        self.fastboot_path = str(fastboot_path)
        self.logger = logger
    
    def run_command(
        self, 
        args: List[str], 
        timeout: int = 30,
        check_return_code: bool = False
    ) -> CommandResult:
        """
        Run a command and return result
        
        Args:
            args: Command arguments as list
            timeout: Command timeout in seconds
            check_return_code: Raise exception on non-zero return code
            
        Returns:
            CommandResult object
        """
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            cmd_result = CommandResult(
                returncode=result.returncode,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip()
            )
            
            if check_return_code and not cmd_result.success:
                self.logger.error(f"Command failed: {' '.join(args)}")
                self.logger.error(f"Error: {cmd_result.error_message}")
            
            return cmd_result
            
        except subprocess.TimeoutExpired as e:
            self.logger.error(f"Command timeout: {' '.join(args)}")
            return CommandResult(returncode=124, stdout="", stderr="Command timeout")
        except Exception as e:
            self.logger.error(f"Command error: {str(e)}")
            return CommandResult(returncode=-1, stdout="", stderr=str(e))
    
    def fastboot_devices(self) -> List[str]:
        """Get list of fastboot devices"""
        result = self.run_command([self.fastboot_path, "devices"])
        if not result.success:
            return []
        
        devices = []
        for line in result.stdout.split('\n'):
            if 'fastboot' in line and not line.startswith('*'):
                parts = line.split()
                if len(parts) >= 2:
                    devices.append(parts[0])
        return devices
    
    def adb_devices(self) -> Tuple[List[str], dict]:
        """
        Get list of ADB devices with their status
        
        Returns:
            Tuple of (device_list, status_dict)
        """
        result = self.run_command([self.adb_path, "devices"])
        if not result.success:
            return [], {}
        
        devices = []
        status_dict = {}
        for line in result.stdout.split('\n'):
            if not line.strip() or 'attached' in line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                devices.append(serial)
                status_dict[serial] = status
        
        return devices, status_dict
    
    def get_device_mode(self) -> DeviceMode:
        """Detect current device connection mode"""
        # Check fastboot first
        fb_devices = self.fastboot_devices()
        if fb_devices:
            return DeviceMode.FASTBOOT
        
        # Check ADB
        adb_devs, status_dict = self.adb_devices()
        if adb_devs:
            for device in adb_devs:
                status = status_dict.get(device, "").lower()
                if "sideload" in status:
                    return DeviceMode.SIDELOAD
                elif status == "recovery":
                    return DeviceMode.RECOVERY
                elif status == "device":
                    return DeviceMode.ADB
                elif status == "offline":
                    return DeviceMode.OFFLINE
                elif status == "unauthorized":
                    return DeviceMode.UNAUTHORIZED
        
        return DeviceMode.UNKNOWN
    
    def fastboot_getvar(self, variable: str) -> Optional[str]:
        """Get fastboot variable value"""
        result = self.run_command([
            self.fastboot_path,
            "getvar",
            variable
        ])
        
        if not result.success:
            return None
        
        # Parse output like "variable: value"
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                if key.strip() == variable:
                    return value.strip()
        
        return None
    
    def get_device_info(self) -> DeviceInfo:
        """Get device information"""
        mode = self.get_device_mode()
        info = DeviceInfo(mode=mode)
        
        if mode == DeviceMode.FASTBOOT:
            # Get product
            product = self.fastboot_getvar("product")
            info.product = product
            
            # Get serial
            serial = self.fastboot_getvar("serialno")
            info.serial = serial
            
            # Get bootloader version
            bootloader = self.fastboot_getvar("version-bootloader")
            info.bootloader_version = bootloader
            
            # Try to get unlock status (some devices support this)
            try:
                is_unlocked = self.fastboot_getvar("flashing_lock")
                info.is_unlocked = is_unlocked == "unlocked"
            except:
                pass
        
        return info
    
    def flash_partition(
        self, 
        partition: str, 
        image_path: Path
    ) -> CommandResult:
        """Flash a partition with image"""
        if not image_path.exists():
            return CommandResult(
                returncode=1,
                stdout="",
                stderr=f"Image not found: {image_path}"
            )
        
        self.logger.info(f"Flashing {partition} from {image_path.name}")
        
        result = self.run_command([
            self.fastboot_path,
            "flash",
            partition,
            str(image_path)
        ])
        
        if result.success:
            self.logger.info(f"✓ {partition} flashed successfully")
        else:
            self.logger.error(f"✗ Failed to flash {partition}: {result.error_message}")
        
        return result
    
    def reboot_recovery(self) -> CommandResult:
        """Reboot device to recovery"""
        self.logger.info("Rebooting to recovery...")
        result = self.run_command([
            self.fastboot_path,
            "reboot",
            "recovery"
        ])
        
        if result.success:
            self.logger.info("✓ Reboot command sent")
        else:
            self.logger.error(f"Reboot failed: {result.error_message}")
        
        return result
    
    def adb_sideload(self, rom_path: Path) -> CommandResult:
        """Sideload ROM via ADB"""
        if not rom_path.exists():
            return CommandResult(
                returncode=1,
                stdout="",
                stderr=f"ROM not found: {rom_path}"
            )
        
        rom_size_mb = rom_path.stat().st_size / (1024 * 1024)
        self.logger.info(f"Sideloading {rom_path.name} ({rom_size_mb:.1f} MB)")
        self.logger.warning("Do not disconnect USB cable during sideload!")
        
        result = self.run_command([
            self.adb_path,
            "-d",
            "sideload",
            str(rom_path)
        ], timeout=300)  # 5 minute timeout for large ROMs
        
        if result.success:
            self.logger.info("✓ ROM sideloaded successfully")
        else:
            self.logger.error(f"Sideload failed: {result.error_message}")
        
        return result
    
    def wait_for_device(self, mode: DeviceMode, timeout: int = 30) -> bool:
        """Wait for device to appear in specified mode"""
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            current_mode = self.get_device_mode()
            if current_mode == mode:
                self.logger.info(f"✓ Device detected in {mode.value} mode")
                return True
            
            self.logger.debug(f"Waiting for device ({mode.value})... current: {current_mode.value}")
            time.sleep(1)
        
        self.logger.error(f"✗ Device not detected in {mode.value} mode after {timeout}s")
        return False
