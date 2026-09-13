import hashlib
import zipfile
from pathlib import Path
from typing import Tuple, Dict, Optional
from core.models import ROMPackage, REQUIRED_PARTITIONS

class PackageValidator:
    """Validate AOSP ROM packages"""
    
    PAYLOAD_FILENAME = "payload.bin"
    META_INF_PATH = "META-INF"
    ANDROID_MANIFEST = "META-INF/ANDROID.MF"
    BUILD_PROP_PATHS = [
        "system/build.prop",
        "vendor/build.prop"
    ]
    
    def __init__(self, logger):
        self.logger = logger
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file hash"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def validate_zip_structure(self, zip_path: Path) -> Tuple[bool, str]:
        """Validate basic ZIP file structure"""
        if not zip_path.exists():
            return False, f"File not found: {zip_path}"
        
        if not zip_path.suffix.lower() == ".zip":
            return False, f"Invalid file extension: {zip_path.suffix}"
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Check if ZIP is valid
                test_result = z.testzip()
                if test_result is not None:
                    return False, f"Corrupted ZIP file: {test_result}"
                
                # Check for payload.bin
                if self.PAYLOAD_FILENAME not in z.namelist():
                    return False, f"Missing {self.PAYLOAD_FILENAME}"
                
                # Check for META-INF
                meta_files = [f for f in z.namelist() if f.startswith(self.META_INF_PATH)]
                if not meta_files:
                    return False, "Missing META-INF directory"
                
                return True, "ZIP structure valid"
        
        except zipfile.BadZipFile:
            return False, "Invalid ZIP file"
        except Exception as e:
            return False, f"Error validating ZIP: {str(e)}"
    
    def extract_payload_info(self, zip_path: Path) -> Tuple[bool, Optional[Path]]:
        """Extract payload.bin from ZIP to temporary location"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                payload_info = z.getinfo(self.PAYLOAD_FILENAME)
                payload_size = payload_info.file_size / (1024*1024)
                
                self.logger.info(f"Found payload.bin ({payload_size:.1f} MB)")
                
                # Extract to temp directory
                extract_path = zip_path.parent / f".{zip_path.stem}_payload"
                extract_path.mkdir(exist_ok=True)
                
                extracted_file = extract_path / self.PAYLOAD_FILENAME
                
                with z.open(self.PAYLOAD_FILENAME) as source:
                    with open(extracted_file, 'wb') as target:
                        target.write(source.read())
                
                self.logger.info(f"✓ Extracted payload.bin to {extract_path}")
                return True, extracted_file
        
        except Exception as e:
            self.logger.error(f"Failed to extract payload.bin: {str(e)}")
            return False, None
    
    def validate_rom_package(self, zip_path: Path) -> ROMPackage:
        """Perform complete ROM package validation"""
        package = ROMPackage(zip_path=str(zip_path))
        
        self.logger.info(f"Validating ROM package: {zip_path.name}")
        
        # Check ZIP structure
        ok, msg = self.validate_zip_structure(zip_path)
        if not ok:
            self.logger.error(f"✗ ZIP validation failed: {msg}")
            package.is_valid = False
            return package
        
        self.logger.info(f"✓ {msg}")
        
        # Calculate file hash
        file_hash = self.calculate_file_hash(zip_path)
        package.file_hash = file_hash
        self.logger.info(f"SHA256: {file_hash[:16]}...")
        
        # Extract payload.bin
        ok, payload_path = self.extract_payload_info(zip_path)
        if not ok:
            self.logger.error("✗ Failed to extract payload.bin")
            package.is_valid = False
            return package
        
        package.has_payload = True
        
        # Extract required images (this will be done by payload-dumper)
        # For now, just mark as validated
        package.is_valid = True
        
        self.logger.info("✓ ROM package validation complete")
        return package
    
    def verify_extracted_images(
        self, 
        image_dir: Path,
        required_images: list = None
    ) -> Tuple[bool, Dict[str, Path]]:
        """Verify extracted images exist and are valid"""
        if required_images is None:
            required_images = REQUIRED_PARTITIONS
        
        found_images = {}
        missing = []
        
        for partition in required_images:
            image_path = image_dir / f"{partition}.img"
            
            if image_path.exists():
                size_mb = image_path.stat().st_size / (1024*1024)
                self.logger.info(f"✓ {partition}.img ({size_mb:.1f} MB)")
                found_images[partition] = image_path
            else:
                missing.append(f"{partition}.img")
        
        if missing:
            self.logger.error(f"✗ Missing images: {', '.join(missing)}")
            return False, found_images
        
        return True, found_images
    
    def extract_build_info(self, zip_path: Path) -> Dict[str, str]:
        """Extract build information from ROM"""
        build_info = {}
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for prop_path in self.BUILD_PROP_PATHS:
                    if prop_path in z.namelist():
                        content = z.read(prop_path).decode('utf-8', errors='ignore')
                        
                        for line in content.split('\n'):
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                build_info[key.strip()] = value.strip()
        
        except Exception as e:
            self.logger.debug(f"Could not extract build info: {str(e)}")
        
        return build_info
    
    def cleanup_extraction(self, zip_path: Path):
        """Clean up extracted payload directory"""
        extract_path = zip_path.parent / f".{zip_path.stem}_payload"
        
        if extract_path.exists():
            import shutil
            try:
                shutil.rmtree(extract_path)
                self.logger.debug(f"Cleaned up extraction directory")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup extraction: {str(e)}")
