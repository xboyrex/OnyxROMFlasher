import subprocess
from pathlib import Path
from typing import Tuple, Optional
from core.models import CommandResult, REQUIRED_PARTITIONS

class PayloadExtractor:
    """Extract images from A/B OTA payload.bin"""
    
    def __init__(self, dumper_path: Path, logger):
        self.dumper_path = str(dumper_path)
        self.logger = logger
        self._verify_dumper()
    
    def _verify_dumper(self) -> bool:
        """Verify payload-dumper-go executable exists and works"""
        dumper = Path(self.dumper_path)
        if not dumper.exists():
            self.logger.error(f"payload-dumper-go not found: {self.dumper_path}")
            return False
        
        self.logger.debug(f"payload-dumper-go: {self.dumper_path}")
        return True
    
    def extract_images(
        self,
        payload_path: Path,
        output_dir: Path,
        partitions: list = None
    ) -> Tuple[bool, str]:
        """
        Extract images from payload.bin
        
        Args:
            payload_path: Path to payload.bin
            output_dir: Directory to extract images to
            partitions: List of partitions to extract (default: REQUIRED_PARTITIONS)
            
        Returns:
            Tuple of (success, message)
        """
        if partitions is None:
            partitions = REQUIRED_PARTITIONS
        
        if not payload_path.exists():
            msg = f"payload.bin not found: {payload_path}"
            self.logger.error(f"✗ {msg}")
            return False, msg
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build partition list
        partition_list = ",".join(partitions)
        
        self.logger.info(f"Extracting images: {partition_list}")
        self.logger.info(f"Output directory: {output_dir}")
        
        try:
            # Run payload-dumper-go
            cmd = [
                self.dumper_path,
                "-o", str(output_dir),
                "--partitions", partition_list,
                str(payload_path)
            ]
            
            self.logger.debug(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # Log output
            if result.stdout:
                self.logger.debug(result.stdout)
            if result.stderr:
                self.logger.debug(result.stderr)
            
            if result.returncode != 0:
                msg = f"Extraction failed with code {result.returncode}"
                self.logger.error(f"✗ {msg}")
                return False, msg
            
            self.logger.info("✓ Images extracted successfully")
            return True, "Images extracted"
        
        except subprocess.TimeoutExpired:
            msg = "Extraction timeout (>5 minutes)"
            self.logger.error(f"✗ {msg}")
            return False, msg
        except Exception as e:
            msg = f"Extraction error: {str(e)}"
            self.logger.error(f"✗ {msg}")
            return False, msg
    
    def verify_extraction(
        self,
        output_dir: Path,
        partitions: list = None
    ) -> Tuple[bool, dict]:
        """
        Verify all required images were extracted
        
        Args:
            output_dir: Directory where images were extracted
            partitions: List of expected partitions
            
        Returns:
            Tuple of (all_found, image_dict)
        """
        if partitions is None:
            partitions = REQUIRED_PARTITIONS
        
        images = {}
        missing = []
        
        for partition in partitions:
            image_path = output_dir / f"{partition}.img"
            
            if image_path.exists():
                size_mb = image_path.stat().st_size / (1024*1024)
                self.logger.info(f"✓ {partition}.img ({size_mb:.1f} MB)")
                images[partition] = image_path
            else:
                missing.append(partition)
        
        if missing:
            self.logger.error(f"✗ Missing: {', '.join(missing)}")
            return False, images
        
        self.logger.info("✓ All required images present")
        return True, images
