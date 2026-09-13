# Onyx ROM Flasher

**V1.3 hardened native Windows GUI / POCO F7 (`onyx`)**

## V1 clean-flash flow

1. Select an A/B OTA ROM ZIP.
2. Validate ZIP integrity.
3. Require root-level `payload.bin` and `payload_properties.txt`.
4. Check OTA metadata for `onyx` when metadata is present.
5. Extract exactly:
   - `boot.img`
   - `dtbo.img`
   - `init_boot.img`
   - `recovery.img`
   - `vendor_boot.img`
6. Detect exactly one fastboot device.
7. Query `product`, `current-slot`, and `unlocked` using that device's serial.
8. Require product `onyx` and reject a known locked bootloader.
9. Flash only the five whitelisted partitions.
10. Reboot to recovery.
11. Wait for ADB sideload mode.
12. Run `adb -d sideload ROM.zip`.

The application never formats `userdata` automatically.

## Safety hardening

- Multiple fastboot devices are rejected; the tool will not silently choose the first device.
- Every fastboot `getvar`, `flash`, and `reboot` operation is pinned to the verified serial.
- A known locked bootloader is rejected before flashing.
- OTA metadata is checked for `pre-device` / `post-device` when available.
- A/B packages without `payload_properties.txt` are rejected before flashing.
- Only the five V1 partitions are allowed.
- No `fastboot -w`, `erase userdata`, or automatic factory reset is used.
- HyperOS/MiFlash-style factory flashing is outside V1.
- This software is not claimed to be 100% safe. Test on a controlled device first.

## Native GUI

Tkinter/ttk is used. There is no HTML frontend, pywebview, WebView2, or browser runtime.

## Bundled tools

`bin/` must contain:

- `adb.exe`
- `fastboot.exe`
- `payload-dumper-go.exe`
- `AdbWinApi.dll`
- `AdbWinUsbApi.dll`

## Windows build

GitHub Actions produces `OnyxROMFlasher-Windows.zip`.

The portable bundle intentionally uses:

```text
OnyxROMFlasher/
  OnyxROMFlasher.exe
  bin/
    adb.exe
    fastboot.exe
    payload-dumper-go.exe
    AdbWinApi.dll
    AdbWinUsbApi.dll
```

There is no `_internal/` directory.

For a local Windows build:

```text
python -m pip install pyinstaller==6.22.1
python build_windows.py
```

`build_windows.py` is the single authoritative build path.
