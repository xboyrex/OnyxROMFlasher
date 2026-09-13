# How to Create Distribution ZIP

## Method 1: Automatic (Recommended)

### Run build.bat
```bash
double-click build.bat
```

This will:
1. Clean previous builds
2. Copy all files to `build/onyx-rom-flasher-v1.0.0/`
3. Create empty `tools/` directory
4. Create `logs/` directory
5. Create ZIP file (if 7-Zip is installed)

### Result
```
build/
└── onyx-rom-flasher-v1.0.0/
    └── [Ready to zip]

build/onyx-rom-flasher-v1.0.0.zip (if 7-Zip installed)
```

## Method 2: Manual

### Step 1: Prepare Directory
```bash
Create folder: onyx-rom-flasher-v1.0.0
Copy all files from current directory
```

### Step 2: Exclude These
```
❌ Don't include:
- .git/ (if exists)
- __pycache__/
- logs/*.log
- .*.payload/ (temp dirs)
- .*.extract/ (temp dirs)
- *.zip (old packages)

✅ Do include:
- Everything else
- Empty tools/ dir
- Empty logs/ dir
- All documentation
```

### Step 3: Create ZIP
```bash
Windows Explorer:
1. Right-click folder
2. Send to → Compressed (zipped) folder

7-Zip:
1. Right-click folder
2. 7-Zip → Add to archive
3. Format: .zip
4. Click OK

PowerShell:
Compress-Archive -Path "onyx-rom-flasher-v1.0.0" -DestinationPath "onyx-rom-flasher-v1.0.0.zip"
```

## Method 3: GitHub Release

### 1. Create Release
```bash
git tag v1.0.0
git push origin v1.0.0
```

### 2. Upload to GitHub
- Go to GitHub Releases
- Create new release
- Attach ZIP file
- Add release notes from CHANGELOG.md

### 3. Share Link
- GitHub handles distribution
- Users download from Releases page

## File Structure in ZIP

```
onyx-rom-flasher-v1.0.0.zip (220 KB)
│
└── onyx-rom-flasher-v1.0.0/
    ├── ✓ app.py
    ├── ✓ requirements.txt
    ├── ✓ README.md
    ├── ✓ QUICKSTART.md
    ├── ✓ START_HERE.txt
    ├── ✓ LICENSE
    ├── ✓ run.bat
    ├── ✓ setup.bat
    ├── ✓ build.bat
    ├── ✓ .gitignore
    ├── ✓ core/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── logger.py
    │   ├── device.py
    │   ├── package_validator.py
    │   ├── payload.py
    │   └── workflow.py
    ├── ✓ ui/
    │   ├── __init__.py
    │   ├── main_window.py
    │   ├── rom_tab.py
    │   └── log_tab.py
    ├── ✓ tools/
    │   └── README.txt
    ├── ✓ logs/
    │   └── .gitkeep
    ├── ✓ CHANGELOG.md
    ├── ✓ PROJECT_STRUCTURE.md
    ├── ✓ DISTRIBUTION_CHECKLIST.md
    ├── ✓ MANIFEST.md
    └── ✓ PACKAGE_READY.md
```

## Pre-ZIP Checklist

- [ ] All Python files present
- [ ] All documentation files present
- [ ] tools/ directory exists (empty)
- [ ] logs/ directory exists (empty)
- [ ] .gitignore included
- [ ] LICENSE included
- [ ] All .bat scripts included
- [ ] requirements.txt correct
- [ ] No __pycache__ folders
- [ ] No .pyc files
- [ ] No log files
- [ ] No old .zip files

## ZIP Distribution

### Host Options
1. **GitHub Releases** (recommended)
   - Free
   - Automatic download
   - Version control
   
2. **Direct Download**
   - Your own server
   - Dropbox
   - Google Drive
   
3. **Forums**
   - XDA Forums
   - Reddit
   - China forums (coolapk, etc)

### User Download Flow
```
User Downloads ZIP
    ↓
Extracts ZIP
    ↓
Runs setup.bat
    ↓
Downloads tools
    ↓
Runs run.bat
    ↓
Flashes ROM!
```

## Verification

### ZIP Contents Check
```bash
7z l onyx-rom-flasher-v1.0.0.zip | find "app.py"
7z l onyx-rom-flasher-v1.0.0.zip | find "core"
7z l onyx-rom-flasher-v1.0.0.zip | find "README.md"
```

### Extract & Test
```bash
Extract ZIP
Run setup.bat
Verify no errors
Run run.bat
Verify app launches
```

## File Sizes

```
Python files:        ~125 KB
Documentation:       ~80 KB
Scripts:             ~12 KB
Configuration:       ~2 KB
─────────────────────────────
Total (no tools):    ~220 KB

ZIP compressed:      ~50-80 KB
```

## Upload Checklist

- [ ] ZIP file created
- [ ] ZIP size reasonable
- [ ] ZIP can be extracted
- [ ] Contents verified
- [ ] Tools README included
- [ ] Version number correct
- [ ] Release notes prepared
- [ ] License included

---

**Ready to distribute!** 🚀
