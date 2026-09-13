# Onyx ROM Flasher

V1 desktop AOSP clean-flash architecture for POCO F7 (`onyx`).

## V1 flow
ROM ZIP → payload.bin → five required images → fastboot verification/flash →
recovery → user enters Apply from ADB → automatic `adb -d sideload`.

The application does **not** automatically format userdata.

## Required bundled tools
Place these Windows executables in `bin/`:

- `adb.exe`
- `fastboot.exe`
- `payload-dumper-go.exe`

Do not commit generated `work/`, `build/`, or `dist/` output.
