# Project Structure

Complete file and directory organization for POCO F7 ROM Flasher.

## Directory Tree

```
onyx-rom-flasher/
│
├── 📄 app.py                          [ENTRY POINT]
│   └── Main application launcher with resource verification
│
├── 📄 requirements.txt
│   └── Python dependencies (PyQt5)
│
├── 📁 core/                           [BUSINESS LOGIC]
│   ├── __init__.py
│   ├── models.py                      [Data classes & enums]
│   │   ├── DeviceMode (enum)
│   │   ├── FlashState (enum)
│   │   ├── DeviceInfo (dataclass)
│   │   ├── ROMPackage (dataclass)
│   │   ├── CommandResult (dataclass)
│   │   └── Constants
│   │
│   ├── logger.py                      [Logging setup]
│   │   ├── setup_logger()
│   │   └── LogCapture (class)
│   │
│   ├── device.py                      [Device communication]
│   │   └── DeviceManager
│   │       ├── run_command()
│   │       ├── fastboot_devices()
│   │       ├── adb_devices()
│   │       ├── get_device_mode()
│   │       ├── fastboot_getvar()
│   │       ├── get_device_info()
│   │       ├── flash_partition()
│   │       ├── reboot_recovery()
│   │       ├── adb_sideload()
│   │       └── wait_for_device()
│   │
│   ├── package_validator.py           [ROM validation]
│   │   └── PackageValidator
│   │       ├── calculate_file_hash()
│   │       ├── validate_zip_structure()
│   │       ├── extract_payload_info()
│   │       ├── validate_rom_package()
│   │       ├── verify_extracted_images()
│   │       ├── extract_build_info()
│   │       └── cleanup_extraction()
│   │
│   ├── payload.py                     [Image extraction]
│   │   └── PayloadExtractor
│   │       ├── _verify_dumper()
│   │       ├── extract_images()
│   │       └── verify_extraction()
│   │
│   └── workflow.py                    [State machine]
│       └── FlashWorkflow
│           ├── set_state()
│           ├── request_stop()
│           ├── select_rom()
│           ├── validate_package()
│           ├── extract_images()
│           ├── wait_fastboot()
│           ├── verify_device()
│           ├── flash_images()
│           ├── reboot_recovery()
│           ├── wait_sideload_mode()
│           ├── sideload_rom()
│           └── cleanup()
│
├── 📁 ui/                             [USER INTERFACE]
│   ├── __init__.py
│   │
│   ├── main_window.py                 [Main window]
│   │   ├── SignalEmitter (QObject)
│   │   └── MainWindow (QMainWindow)
│   │       ├── init_ui()
│   │       ├── create_header()
│   │       ├── create_footer()
│   │       ├── setup_connections()
│   │       ├── on_log()
│   │       ├── on_error()
│   │       └── on_success()
│   │
│   ├── rom_tab.py                     [ROM & Flash tab]
│   │   ├── FlashSignals (QObject)
│   │   ├── FlashWorker (QThread)
│   │   └── ROMTab (QWidget)
│   │       ├── init_ui()
│   │       ├── create_rom_group()
│   │       ├── create_status_group()
│   │       ├── create_progress_group()
│   │       ├── create_device_group()
│   │       ├── create_control_group()
│   │       ├── select_rom()
│   │       ├── check_device()
│   │       ├── start_flashing()
│   │       └── stop_flashing()
│   │
│   └── log_tab.py                     [Log display tab]
│       └── LogTab (QWidget)
│           ├── init_ui()
│           ├── append_log()
│           ├── clear_log()
│           └── copy_log()
│
├── 📁 tools/                          [EXTERNAL BINARIES]
│   ├── README.txt                     [Download instructions]
│   ├── adb.exe                        [To be downloaded]
│   ├── fastboot.exe                   [To be downloaded]
│   └── payload-dumper-go.exe          [To be downloaded]
│
├── 📁 logs/                           [LOG FILES]
│   ├── 2024-01-15_10-30-45.log
│   ├── 2024-01-15_14-22-18.log
│   └── ...
│
├── 📄 README.md                       [Main documentation]
│   ├── Installation
│   ├── Device preparation
│   ├── Usage workflow
│   ├── ROM requirements
│   ├── Troubleshooting
│   ├── Log files
│   ├── Safety features
│   ├── Project structure
│   ├── Advanced usage
│   ├── Contributing
│   ├── License
│   └── FAQ
│
├── 📄 QUICKSTART.md                   [Quick start guide]
│   ├── 5-minute setup
│   ├── File structure
│   ├── Flashing steps
│   └── Troubleshooting
│
├── 📄 LICENSE                         [MIT License]
│
├── 📄 CHANGELOG.md                    [Version history]
│   ├── v1.0.0 features
│   ├── Planned features
│   ├── Known issues
│   └── Credits
│
├── 📄 DISTRIBUTION_CHECKLIST.md       [Release checklist]
│   ├── Pre-release verification
│   ├── Release preparation
│   ├── Package contents
│   ├── Post-release
│   └── Safety verification
│
├── 📄 PROJECT_STRUCTURE.md            [This file]
│   └── Directory organization
│
├── 📄 .gitignore                      [Git exclusions]
│   ├── Python cache
│   ├── IDE files
│   ├── Logs
│   └── Temporary files
│
├── 📄 run.bat                         [Windows launcher]
│   ├── Python check
│   ├── Dependencies check
│   └── App launch
│
├── 📄 setup.bat                       [Setup script]
│   ├── Python verification
│   ├── Directory creation
│   ├── Dependency installation
│   ├── Tool verification
│   └── Environment check
│
└── 📄 build.bat                       [Build script]
    ├── Clean build
    ├── Copy files
    ├── Create directories
    ├── Verify structure
    ├── Create ZIP
    └── Package summary
```

## File Relationships

### Startup Flow
```
run.bat
  └─> app.py
      ├─> core/logger.py
      ├─> core/models.py
      ├─> ui/main_window.py
      │   ├─> ui/rom_tab.py
      │   │   ├─> core/device.py
      │   │   ├─> core/package_validator.py
      │   │   ├─> core/payload.py
      │   │   └─> core/workflow.py
      │   └─> ui/log_tab.py
```

### Flashing Workflow
```
ROMTab.start_flashing()
  └─> FlashWorker.run()
      └─> FlashWorkflow
          ├─> validate_package()
          │   └─> PackageValidator
          ├─> extract_images()
          │   ├─> PackageValidator.extract_payload_info()
          │   └─> PayloadExtractor.extract_images()
          ├─> wait_fastboot()
          │   └─> DeviceManager.wait_for_device()
          ├─> verify_device()
          │   └─> DeviceManager.get_device_info()
          ├─> flash_images()
          │   └─> DeviceManager.flash_partition()
          ├─> reboot_recovery()
          │   └─> DeviceManager.reboot_recovery()
          ├─> wait_sideload_mode()
          │   └─> DeviceManager.get_device_mode()
          └─> sideload_rom()
              └─> DeviceManager.adb_sideload()
```

## Module Responsibilities

### core/models.py
- Data structures (DeviceInfo, ROMPackage, CommandResult)
- Enumerations (DeviceMode, FlashState)
- Configuration constants

### core/logger.py
- Logging setup and configuration
- File and console handlers
- Log message capture for UI

### core/device.py
- Device detection and communication
- Fastboot operations
- ADB operations
- Device information retrieval

### core/package_validator.py
- ROM ZIP validation
- Payload extraction
- Image verification
- Build info extraction
- File hashing

### core/payload.py
- Payload.bin extraction via payload-dumper-go
- Image verification
- Partition extraction

### core/workflow.py
- State machine implementation
- Workflow orchestration
- Error handling
- Cleanup operations

### ui/main_window.py
- Application window setup
- Tab management
- Signal connections
- User feedback (dialogs)

### ui/rom_tab.py
- ROM selection UI
- Device monitoring
- Flash operation initiation
- Status display
- Worker thread management

### ui/log_tab.py
- Log display
- Log management (clear, copy)
- Real-time updates

## Data Flow

### User Selection → Validation
```
User selects ROM
  └─> ROM path stored
      └─> ZIP structure validated
          └─> payload.bin located
              └─> Package marked valid
```

### Device Detection → Verification
```
User clicks Check Device
  └─> Device commands executed
      └─> Device mode detected
          └─> Device info retrieved
              └─> Product codename checked
                  └─> Status updated in UI
```

### Flashing Sequence
```
User clicks Start Flashing
  └─> ROM validation starts
      └─> Images extracted
          └─> Device wait starts
              └─> Device verified
                  └─> Images flashed (5 partitions)
                      └─> Recovery reboot
                          └─> Sideload wait
                              └─> ROM transferred
                                  └─> Completion
```

## Configuration

### Hardcoded Values
Located in `core/models.py`:
```python
REQUIRED_PARTITIONS = [
    "boot",
    "dtbo",
    "init_boot",
    "recovery",
    "vendor_boot",
]

EXPECTED_DEVICE_CODENAME = "onyx"
```

### Paths
- Tools: `tools/` subdirectory
- Logs: `logs/` subdirectory
- Temp extraction: `.{rom_name}_extract`
- Temp payload: `.{rom_name}_payload`

### Timeouts
- Device wait: 30-120s (configurable)
- Command execution: 30s default
- Sideload: 300s (5 minutes)

## Dependencies

### External Tools
- `adb.exe` - Android Debug Bridge
- `fastboot.exe` - Fastboot protocol
- `payload-dumper-go.exe` - Payload extraction

### Python Libraries
- PyQt5==5.15.9 - GUI framework

## Environment Variables
None required (all paths relative)

## System Requirements
- Windows 10/11 x64
- Python 3.8+
- USB 2.0+ cable
- ~5-10 GB free disk space

## Build Artifacts
```
build/
└── onyx-rom-flasher-vX.Y.Z/
    ├── [All source files]
    ├── tools/ (empty)
    └── logs/ (empty)
```

## Version Information

### Current Version
- **Version**: 1.0.0
- **Release Date**: 2024-01-XX
- **Status**: Stable

### Version Format
```
v[MAJOR].[MINOR].[PATCH]
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes
```

---

**Last Updated**: 2024-01-XX  
**Maintainer**: [Your Name]  
**Status**: Complete & Production Ready
