# Quick Start Guide - POCO F7 ROM Flasher

## 5-Minute Setup

### Step 1: Install Python
1. Download from https://www.python.org/
2. Run installer
3. **IMPORTANT**: Check "Add Python to PATH"
4. Click Install

### Step 2: Download Flasher
1. Click "Code" → "Download ZIP"
2. Extract to folder (e.g., `C:\onyx-rom-flasher`)

### Step 3: Run Setup
1. Open folder in File Explorer
2. Double-click `setup.bat`
3. Wait for setup to complete

### Step 4: Get Tools
Download and extract to `tools/` folder:

**ADB & Fastboot:**
- Download: https://developer.android.com/studio/releases/platform-tools
- Extract files:
  - `adb.exe` → `tools/adb.exe`
  - `fastboot.exe` → `tools/fastboot.exe`

**Payload Dumper:**
- Download: https://github.com/ssut/payload-dumper-go/releases
- Download: `payload-dumper-go-windows.exe`
- Rename and move:
  - Rename to `payload-dumper-go.exe`
  - Move to `tools/payload-dumper-go.exe`

### Step 5: Verify Setup
1. Double-click `setup.bat` again
2. All tools should show [✓]

## Flashing

### Before You Start
- ✅ Backup all data
- ✅ Bootloader MUST be unlocked
- ✅ Use good quality USB cable
- ✅ Close other USB apps (iTunes, etc.)

### Unlock Bootloader (First Time Only)
```
1. Phone → Settings → About → Tap Build Number 7 times
2. Settings → Developer → Enable OEM Unlocking
3. adb reboot bootloader
4. fastboot flashing unlock
5. Confirm on phone (Volume Up)
```

### Flash ROM
```
1. Double-click run.bat
2. Select ROM ZIP file
3. Boot phone into Fastboot:
   - Power off completely
   - Hold Volume Down + Power for 3 seconds
   - Fastboot screen appears
4. Click "Start Flashing"
5. Wait for completion
```

### In Recovery (Auto)
```
Phone will reboot to recovery automatically
- Select "Apply Update"
- Select "Apply from ADB"
- Keep USB connected
- Tool transfers ROM automatically
```

### After Flashing
```
1. Phone: Select "Reboot System Now"
2. First boot takes 5-10 minutes
3. Setup wizard appears
4. Done!
```

## File Structure

After setup, you should have:

```
onyx-rom-flasher/
├── run.bat              ← Double-click to start
├── setup.bat            ← Run once for setup
├── README.md            ← Full documentation
├── requirements.txt     ← Dependencies list
├── tools/
│   ├── adb.exe         ← Required
│   ├── fastboot.exe    ← Required
│   └── payload-dumper-go.exe ← Required
└── logs/               ← Auto-created
```

## Troubleshooting

### "Device not found"
1. Try different USB port
2. Try different USB cable
3. Run: `fastboot devices`
4. Check Device Manager for "fastboot"

### "ROM validation failed"
1. Re-download ROM
2. Verify ZIP is not corrupted
3. Check ROM is for onyx device

### "Extraction failed"
1. Check disk space (need 5-10 GB)
2. Verify payload-dumper-go.exe exists
3. Run as Administrator

### "Sideload fails"
1. Don't interrupt USB connection
2. Keep phone in recovery mode
3. In recovery: Try again from "Apply Update"

## Commands (If Needed)

```bash
# Enter fastboot
adb reboot bootloader

# Check device
fastboot devices

# Verify device is onyx
fastboot getvar product

# Check device serial
fastboot getvar serialno

# Sideload manually
adb sideload ROM.zip
```

## Important Notes

⚠️ **DO NOT:**
- Disconnect USB during flashing
- Turn off phone during flashing
- Flash wrong device type
- Update system during flashing
- Close application during flashing

✅ **DO:**
- Backup all data first
- Ensure bootloader is unlocked
- Use quality USB cable
- Keep USB connected
- Read all prompts carefully

## First Boot Takes Time

After clicking "Reboot System Now":
- **5-10 minutes** before home screen
- **Do not interrupt**
- Phone may reboot itself
- This is normal

## Get Help

1. Check `logs/` folder for detailed errors
2. Read full README.md
3. Share logs when asking for help
4. Check GitHub Issues

## Video Tutorial

See setup video at: [GitHub Releases](https://github.com/yourrepo/releases)

---

**Ready? Double-click `run.bat` to start!**
