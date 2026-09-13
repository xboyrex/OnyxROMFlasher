# Onyx ROM Flasher

**V1.2 — Native Windows GUI / POCO F7 (`onyx`)**

## V1 flow

ROM ZIP → validate `payload.bin` → extract exactly five images → verify fastboot product `onyx` → flash:

```text
fastboot flash boot boot.img
fastboot flash dtbo dtbo.img
fastboot flash init_boot init_boot.img
fastboot flash recovery recovery.img
fastboot flash vendor_boot vendor_boot.img
```

Then:

```text
fastboot reboot recovery
```

The user manually completes recovery actions:

1. Format Data / Factory Reset if required by the ROM.
2. Apply Update → Apply from ADB.
3. Once recovery exposes ADB sideload mode, the tool automatically runs:

```text
adb -d sideload ROM.zip
```

## Safety boundaries

- The application does **not** automatically format `userdata`.
- Only the five V1 partitions are whitelisted.
- Device product must be exactly `onyx` before flashing.
- HyperOS/MiFlash-style factory flashing is not part of V1.
- Do not disconnect the phone or interrupt flashing once it starts.
- This software is not claimed to be 100% safe. Test on a controlled device/setup first.

## Native GUI

V1.2 replaces the previous pywebview/HTML interface with a native Tkinter/ttk Windows GUI.

There is no `index.html`, no pywebview dependency, and no WebView2 requirement.

## Bundled tools

Place these in `bin/`:

- `adb.exe`
- `fastboot.exe`
- `payload-dumper-go.exe`

For Windows packaging, GitHub Actions builds an onedir portable folder and uploads `OnyxROMFlasher-Windows.zip`.

## Local build

```text
python -m pip install pyinstaller
python build_windows.py
```

Output:

```text
dist/OnyxROMFlasher/OnyxROMFlasher.exe
```
