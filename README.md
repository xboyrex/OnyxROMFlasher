# POCO F7 / Redmi Turbo 4 Pro ROM Flasher v1.0

Professional Windows ROM flashing tool for POCO F7 (codename: `onyx`) with intelligent payload extraction and safe fastboot operations.

## ⚠️ Important Warnings

- **Backup your data** before flashing
- **Ensure bootloader is unlocked** (cannot be undone for all devices)
- **Keep USB cable connected** throughout the process
- This tool only works with **onyx** devices
- **First-time users**: Test on a non-critical device first

## Features

### V1 (Current)
- ✅ AOSP ROM ZIP validation
- ✅ Automatic payload.bin extraction
- ✅ Device verification (onyx codename check)
- ✅ Safe fastboot flashing sequence
- ✅ Automatic recovery reboot
- ✅ ADB sideload detection and ROM transfer
- ✅ Detailed real-time logs
- ✅ Error handling and rollback protection

### Planned (V2+)
- HyperOS fastboot packages
- Bootloader version checking
- Anti-rollback inspection
- Regional settings validation

## System Requirements

- **Windows**: Windows 10/11 x64
- **Python**: 3.8+
- **USB**: USB 2.0+ cable
- **Device**: POCO F7 with unlocked bootloader

## Installation

### 1. Download Project

```bash
git clone https://github.com/yourusername/onyx-rom-flasher.git
cd onyx-rom-flasher
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify Bundled Tools

Ensure these executables exist in `tools/`:
- `adb.exe` (Android Debug Bridge)
- `fastboot.exe` (Fastboot protocol)
- `payload-dumper-go.exe` (Payload extractor)

[Download ADB/Fastboot](https://developer.android.com/studio/releases/platform-tools)

### 4. Run Application

```bash
python app.py
```

## Device Preparation

### Unlock Bootloader

1. Power off device
2. Open Settings → About Phone
3. Tap "Build Number" 7 times
4. Go to Developer Options
5. Enable "OEM Unlocking"
6. Reboot to bootloader:
   ```bash
   adb reboot bootloader
   ```
7. Unlock bootloader:
   ```bash
   fastboot flashing unlock
   ```
8. Confirm on device (Volume Up to confirm)

### Enter Fastboot Mode

1. Power off device completely
2. Connect USB cable
3. Hold **Volume Down + Power** for 3 seconds
4. Device enters fastboot mode (fastboot logo appears)
5. Release buttons

## Usage Workflow

### Step 1: Prepare ROM
- Download AOSP ROM for onyx
- Ensure ROM contains `payload.bin`
- Verify ROM build number in ZIP

### Step 2: Select ROM
1. Click "Select AOSP ROM ZIP"
2. Choose ROM file
3. Tool validates and extracts payload

### Step 3: Connect Device
1. Boot device into Fastboot mode
2. Connect USB cable
3. Tool automatically detects device
4. Verifies device is "onyx"

### Step 4: Start Flashing
1. Click "Start Flashing"
2. Tool flashes 5 boot partitions:
   - `boot.img`
   - `dtbo.img`
   - `init_boot.img`
   - `recovery.img`
   - `vendor_boot.img`
3. Device automatically reboots to recovery

### Step 5: Sideload ROM
On the device recovery screen:
1. Select "Apply Update"
2. Select "Apply from ADB"
3. Keep USB cable connected
4. Tool automatically detects sideload mode
5. Transfers ROM via sideload

### Step 6: Complete
1. Device boots with new ROM
2. **First boot takes 5-10 minutes** - do not interrupt
3. Setup wizard appears

## ROM Requirements

**Valid AOSP ROM must have:**
```
ROM.zip
├── payload.bin (50-1000 MB)
├── META-INF/
│   ├── ANDROID.MF
│   └── MANIFEST.MF
├── system/
├── vendor/
└── [other files]
```

**Extracted images must include:**
- `boot.img` (8-16 MB)
- `dtbo.img` (1-8 MB)
- `init_boot.img` (4-8 MB)
- `recovery.img` (10-20 MB)
- `vendor_boot.img` (20-50 MB)

## Troubleshooting

### Device Not Detected

**Problem**: "Device not found in fastboot mode"

**Solution**:
1. Try different USB cable
2. Try different USB port
3. Restart device: `adb reboot bootloader`
4. Check Device Manager for "fastboot" entry
5. Update ADB/Fastboot drivers

### ROM Validation Failed

**Problem**: "ROM package validation failed"

**Solution**:
- Check ZIP file is not corrupted: `7z t ROM.zip`
- Verify ROM contains `payload.bin`
- Re-download ROM from official source
- Check ROM is for onyx device

### Extraction Failed

**Problem**: "Failed to extract payload.bin"

**Solution**:
- Ensure `payload-dumper-go.exe` exists in `tools/`
- Check disk space (need 5-10 GB free)
- Try running as Administrator
- Check Windows Defender isn't blocking

### Sideload Fails

**Problem**: "ROM sideload failed" or connection lost

**Solution**:
1. Don't interrupt USB connection
2. On device: Go back and retry "Apply from ADB"
3. Check `adb devices` shows "sideload" status
4. Try smaller ROM or different USB port
5. Disable USB power management in Device Manager

### Device Stuck in Recovery

**Problem**: Device won't boot normally

**Solution**:
1. From recovery: Select "Reboot System"
2. If stuck: Flash recovery from computer
3. Fastboot from computer to restore

## Log Files

Detailed logs saved in `logs/`:
```
logs/
├── 2024-01-15_10-30-45.log
├── 2024-01-15_14-22-18.log
└── ...
```

Each log contains:
- Timestamp
- Command outputs
- Error details
- Device information

## Safety Features

### Hardcoded Protections
- ✅ Wrong codename blocks flashing
- ✅ Missing images blocks flashing  
- ✅ Device verification mandatory
- ✅ No blind fastboot commands
- ✅ No automatic format/erase
- ✅ No bootloader unlocking
- ✅ Window close blocked during flashing

### Manual Format Data
User manually performs in recovery:
1. "Wipe Data"
2. "Format Data"
3. Recovery handles the operation

## Command Reference

### Manual Fastboot (if needed)
```bash
# Enter fastboot mode
adb reboot bootloader

# Check device
fastboot devices
fastboot getvar product

# Flash individual partition
fastboot flash boot boot.img
fastboot flash recovery recovery.img

# Reboot to recovery
fastboot reboot recovery
```

### Manual ADB Sideload
```bash
# In recovery, select "Apply from ADB"

# Sideload ROM
adb sideload ROM.zip

# Check device status
adb devices
```

## Project Structure

```
onyx-rom-flasher/
├── app.py                 # Entry point
├── requirements.txt       # Dependencies
├── README.md             # This file
├── tools/
│   ├── adb.exe          # Android Debug Bridge
│   ├── fastboot.exe     # Fastboot tool
│   └── payload-dumper-go.exe
├── core/
│   ├── models.py        # Data models
│   ├── logger.py        # Logging
│   ├── device.py        # Device manager
│   ├── package_validator.py  # ROM validation
│   ├── payload.py       # Payload extraction
│   └── workflow.py      # Flash workflow
├── ui/
│   ├── main_window.py   # Main UI
│   ├── rom_tab.py       # ROM/Flash tab
│   └── log_tab.py       # Logs tab
└── logs/                # Generated log files
```

## Advanced Usage

### Extract Images Only

```python
from core.payload import PayloadExtractor

extractor = PayloadExtractor(
    Path("tools/payload-dumper-go.exe"),
    logger
)

ok, images = extractor.extract_images(
    Path("ROM.zip"),
    Path("output"),
    ["boot", "recovery"]
)
```

### Programmatic Flashing

```python
from core.workflow import FlashWorkflow

workflow = FlashWorkflow(device, validator, extractor, logger)

workflow.select_rom(Path("ROM.zip"))
workflow.validate_package()
workflow.extract_images()
workflow.wait_fastboot()
workflow.verify_device()
workflow.flash_images()
workflow.reboot_recovery()
```

## Contributing

- Report issues with device logs attached
- Test on actual hardware before PRs
- Follow PEP 8 style guide
- Add tests for new features

## Disclaimer

This tool is provided AS-IS without warranty. Use at your own risk. The author is not responsible for:
- Bricked devices
- Data loss
- Corrupted ROMs
- Bootloader issues

**Always backup before flashing.**

## License

MIT License - See LICENSE file

## Credits

- Payload extractor: [payload-dumper-go](https://github.com/ssut/payload-dumper-go)
- Android tools: [Android SDK Platform Tools](https://developer.android.com/)
- Community ROM developers

## Support

- Report bugs: GitHub Issues
- Logs: Attach from `logs/` folder
- Device info: `adb getprop ro.product.model`
- Bootloader: `fastboot getvar all`

## FAQ

**Q: Will this work on other Xiaomi devices?**
A: No, V1 only supports onyx (POCO F7). V2+ will add more devices.

**Q: Can I use this on macOS/Linux?**
A: Not yet. Windows only for V1.

**Q: Is my data safe?**
A: Flashing doesn't erase userdata. Only recovery and boot partitions. But always backup.

**Q: How long does flashing take?**
A: 5-10 minutes total. First boot with new ROM takes 5-10 minutes.

**Q: Can I stop mid-flashing?**
A: Only before actual fastboot commands. Once started, let it complete.

---

Made with ❤️ for POCO F7 users
