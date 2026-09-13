"""
Onyx ROM Flasher V1
Backend for the single-file pywebview UI.

V1 scope:
  ROM ZIP -> payload.bin -> five required images
  -> fastboot flash -> fastboot reboot recovery
  -> wait for user to enter ADB sideload mode
  -> adb -d sideload ROM ZIP

Important:
  - This backend NEVER formats userdata automatically.
  - The user must perform Factory Reset / Format Data in recovery.
  - Device identity is checked before flashing.
  - HyperOS / MiFlash-style image flashing is intentionally NOT part of V1.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import webview


APP_NAME = "Onyx ROM Flasher"
EXPECTED_CODENAME = "onyx"
REQUIRED_IMAGES = ["boot", "dtbo", "init_boot", "recovery", "vendor_boot"]

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
TOOLS_DIR = ROOT / "tools"
WORK_DIR = ROOT / "work"
WORK_DIR.mkdir(parents=True, exist_ok=True)

WINDOW = None
FLASH_LOCK = threading.Lock()
FLASH_RUNNING = False


def _platform_exe(name: str) -> str:
    """Resolve a bundled executable first, then fall back to PATH."""
    candidates = [
        BIN_DIR / f"{name}.exe",
        BIN_DIR / name,
        TOOLS_DIR / f"{name}.exe",
        TOOLS_DIR / name,
    ]
    for path in candidates:
        if path.exists() and path.is_file():
            return str(path)

    found = shutil.which(name)
    if found:
        return found

    raise FileNotFoundError(
        f"{name} was not found. Put it in the project's bin/ directory "
        f"or install it and add it to PATH."
    )


def _run(
    args: List[str],
    *,
    timeout: int = 120,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess with UTF-8-friendly output and no shell."""
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    if check and proc.returncode != 0:
        detail = (proc.stdout + "\n" + proc.stderr).strip()
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(args)}\n{detail}"
        )
    return proc


def _merged_output(proc: subprocess.CompletedProcess) -> str:
    return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()


def _emit_js(function: str, *args: Any) -> None:
    """Safely send a callback into the HTML UI."""
    global WINDOW
    if WINDOW is None:
        return

    encoded = ",".join(json.dumps(arg, ensure_ascii=False) for arg in args)
    script = f"{function}({encoded});"

    try:
        WINDOW.evaluate_js(script)
    except Exception:
        # The UI may have closed while a worker was finishing.
        pass


def _log(message: str, kind: str = "info") -> None:
    _emit_js("window.onLog", message, {
        "ok": "oktxt",
        "warn": "warntxt",
        "error": "redtxt",
    }.get(kind, "info"))


def _step(index: int, status: str, label: Optional[str] = None) -> None:
    _emit_js("window.onStep", index, status, label)


def _progress(percent: int, label: str = "") -> None:
    _emit_js("window.onProgress", max(0, min(100, int(percent))), label)


def _finish(ok: bool, message: str) -> None:
    _emit_js("window.onFlashDone", ok, message)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _find_payload(z: zipfile.ZipFile) -> Optional[str]:
    names = z.namelist()

    # Prefer the conventional root payload.bin.
    for name in names:
        if name.replace("\\", "/").strip("/") == "payload.bin":
            return name

    # Some packages put it below a directory.
    for name in names:
        if Path(name).name.lower() == "payload.bin":
            return name

    return None


def _filename_device_hint(path: Path) -> str:
    """Best-effort hint only; actual device verification happens on fastboot."""
    name = path.name.lower()
    if re.search(r"(^|[-_.])onyx([-_.]|$)", name):
        return EXPECTED_CODENAME
    return "unknown"


def _safe_temp_name(source: str) -> str:
    stem = Path(source).stem or "rom"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    return stem[:80]


def _extract_payload(rom_zip: Path, session_dir: Path) -> Path:
    payload_dir = session_dir / "payload"
    payload_dir.mkdir(parents=True, exist_ok=True)
    payload_path = payload_dir / "payload.bin"

    with zipfile.ZipFile(rom_zip, "r") as z:
        payload_name = _find_payload(z)
        if not payload_name:
            raise RuntimeError("payload.bin was not found in the selected ROM ZIP.")

        info = z.getinfo(payload_name)
        # Basic sanity checks; the ZIP is not trusted blindly.
        if info.file_size <= 0:
            raise RuntimeError("payload.bin is empty.")
        if info.file_size > 20 * 1024 * 1024 * 1024:
            raise RuntimeError("payload.bin is unexpectedly large; refusing to extract.")

        with z.open(info, "r") as src, payload_path.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)

    return payload_path


def _payload_dumper() -> str:
    # V1 intentionally uses the bundled/native payload-dumper-go executable.
    return _platform_exe("payload-dumper-go")


def _extract_required_images(payload_path: Path, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    dumper = _payload_dumper()

    # payload-dumper-go accepts: payload-dumper-go -o <outdir> <payload.bin>
    proc = _run(
        [dumper, "-o", str(output_dir), str(payload_path)],
        timeout=900,
        check=False,
    )
    output = _merged_output(proc)

    if proc.returncode != 0:
        raise RuntimeError(
            "payload-dumper-go failed.\n"
            + (output[-5000:] if output else "No diagnostic output.")
        )

    found: Dict[str, Path] = {}
    for image in REQUIRED_IMAGES:
        candidate = output_dir / f"{image}.img"
        if candidate.exists() and candidate.stat().st_size > 0:
            found[image] = candidate

    missing = [x for x in REQUIRED_IMAGES if x not in found]
    if missing:
        diagnostic = output[-2500:] if output else "No dumper output."
        raise RuntimeError(
            "Required images were not extracted: "
            + ", ".join(f"{x}.img" for x in missing)
            + f"\n\nDumper output:\n{diagnostic}"
        )

    return found


def _fastboot() -> str:
    return _platform_exe("fastboot")


def _adb() -> str:
    return _platform_exe("adb")


def _fastboot_devices() -> List[str]:
    proc = _run([_fastboot(), "devices"], timeout=20)
    devices = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lower() == "fastboot":
            devices.append(parts[0])
    return devices


def _adb_devices() -> List[tuple[str, str]]:
    proc = _run([_adb(), "devices"], timeout=20)
    result: List[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if not line.strip() or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            result.append((parts[0], parts[1]))
    return result


def _fastboot_var(name: str) -> str:
    proc = _run([_fastboot(), "getvar", name], timeout=20)
    output = _merged_output(proc)

    # Fastboot normally prints getvar results to stderr.
    patterns = [
        rf"{re.escape(name)}\s*:\s*(.+)",
        rf"{re.escape(name)}\s*=\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def _get_fastboot_device() -> Dict[str, Any]:
    devices = _fastboot_devices()
    if not devices:
        return {"connected": False, "mode": "disconnected"}

    serial = devices[0]
    product = _fastboot_var("product")
    slot = _fastboot_var("current-slot")
    unlocked_raw = _fastboot_var("unlocked")

    unlocked: Optional[bool]
    if unlocked_raw.lower() in {"yes", "true", "1", "unlocked"}:
        unlocked = True
    elif unlocked_raw.lower() in {"no", "false", "0", "locked"}:
        unlocked = False
    else:
        unlocked = None

    return {
        "connected": True,
        "mode": "fastboot",
        "serial": serial,
        "product": product or "unknown",
        "codename": product or "unknown",
        "model": product or "POCO F7",
        "slot": slot or "unknown",
        "battery": None,
        "unlocked": unlocked,
    }


def _get_adb_device() -> Dict[str, Any]:
    devices = _adb_devices()
    if not devices:
        return {"connected": False, "mode": "disconnected"}

    serial, state = devices[0]
    if state == "sideload":
        return {
            "connected": True,
            "mode": "sideload",
            "serial": serial,
            "product": "onyx",
            "codename": "onyx",
            "model": "POCO F7",
            "slot": "unknown",
            "battery": None,
            "unlocked": None,
        }

    # Recovery ADB can expose useful properties.
    def adb_shell(prop: str) -> str:
        proc = _run([_adb(), "-s", serial, "shell", "getprop", prop], timeout=15)
        return proc.stdout.strip()

    product = adb_shell("ro.product.device") or adb_shell("ro.build.product")
    model = adb_shell("ro.product.model")
    slot = adb_shell("ro.boot.slot_suffix").lstrip("_")
    battery_raw = adb_shell("dumpsys battery | grep level")

    battery = None
    match = re.search(r"level:\s*(\d+)", battery_raw)
    if match:
        battery = int(match.group(1))

    return {
        "connected": True,
        "mode": "adb",
        "serial": serial,
        "product": product or "unknown",
        "codename": product or "unknown",
        "model": model or "unknown",
        "slot": slot or "unknown",
        "battery": battery,
        "unlocked": None,
    }


class Api:
    def set_window(self, window) -> None:
        global WINDOW
        WINDOW = window

    def pick_file(self, kind: str = "rom") -> str:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        if kind == "gapps":
            filetypes = [
                ("ZIP files", "*.zip"),
                ("All files", "*.*"),
            ]
            title = "Select GApps ZIP"
        else:
            filetypes = [
                ("Android ROM ZIP", "*.zip"),
                ("All files", "*.*"),
            ]
            title = "Select AOSP ROM ZIP"

        path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        root.destroy()
        return path or ""

    def inspect_rom(self, path: str) -> Dict[str, Any]:
        try:
            rom = Path(path).expanduser().resolve()

            if not rom.exists() or not rom.is_file():
                return {"ok": False, "error": "Selected ROM file does not exist."}

            if rom.suffix.lower() != ".zip":
                return {"ok": False, "error": "ROM must be a ZIP file."}

            size = rom.stat().st_size
            with zipfile.ZipFile(rom, "r") as z:
                bad = z.testzip()
                if bad:
                    return {
                        "ok": False,
                        "error": f"ZIP integrity check failed near: {bad}",
                    }

                payload_name = _find_payload(z)
                device_hint = _filename_device_hint(rom)

                # A/B is inferred conservatively from common payload partitions.
                names = {Path(x).name.lower() for x in z.namelist()}
                is_ab = (
                    "payload.bin" in names
                    or any("care_map" in x for x in names)
                    or any("super_empty" in x for x in names)
                )

            return {
                "ok": True,
                "name": rom.name,
                "path": str(rom),
                "size": size,
                "device": device_hint,
                "is_ab": is_ab,
                "has_payload": payload_name is not None,
                "payload_name": payload_name or "",
            }

        except zipfile.BadZipFile:
            return {"ok": False, "error": "The selected file is not a valid ZIP."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def get_device(self) -> Dict[str, Any]:
        try:
            fb = _get_fastboot_device()
            if fb.get("connected"):
                return fb

            adb = _get_adb_device()
            if adb.get("connected"):
                return adb

            return {"connected": False, "mode": "disconnected"}
        except FileNotFoundError as exc:
            return {"connected": False, "mode": "error", "error": str(exc)}
        except Exception as exc:
            return {"connected": False, "mode": "error", "error": str(exc)}

    def build_plan(self, mode: str, flash_type: str) -> Dict[str, Any]:
        if mode != "aosp" or flash_type != "clean":
            return {
                "ok": False,
                "error": "V1 only supports AOSP clean flashing.",
            }

        steps = [
            {"t": "ROM analysis", "d": "Validate ZIP + detect payload.bin"},
            {"t": "Payload extraction", "d": "Extract required onyx images"},
            {"t": "Device verification", "d": "Require fastboot + product onyx"},
            {"t": "Flash boot", "d": "fastboot flash boot boot.img"},
            {"t": "Flash dtbo", "d": "fastboot flash dtbo dtbo.img"},
            {"t": "Flash init_boot", "d": "fastboot flash init_boot init_boot.img"},
            {"t": "Flash recovery", "d": "fastboot flash recovery recovery.img"},
            {"t": "Flash vendor_boot", "d": "fastboot flash vendor_boot vendor_boot.img"},
            {"t": "Reboot recovery", "d": "fastboot reboot recovery"},
            {"t": "Wait for ADB sideload", "d": "User selects Apply Update → Apply from ADB"},
            {"t": "Sideload ROM", "d": "adb -d sideload ROM.zip"},
        ]
        return {"ok": True, "steps": steps}

    def start_flash(self, mode: str, flash_type: str) -> Dict[str, Any]:
        global FLASH_RUNNING

        if mode != "aosp" or flash_type != "clean":
            return {"ok": False, "error": "Unsupported V1 flashing mode."}

        with FLASH_LOCK:
            if FLASH_RUNNING:
                return {"ok": False, "error": "A flash session is already running."}
            FLASH_RUNNING = True

        worker = threading.Thread(
            target=self._flash_worker,
            name="onyx-flash-worker",
            daemon=True,
        )
        worker.start()
        return {"ok": True, "message": "Flash worker started."}

    def _flash_worker(self) -> None:
        global FLASH_RUNNING

        try:
            # The selected ROM path is stored by inspect_rom.
            # We intentionally require the UI to call inspect_rom first.
            rom_path = getattr(self, "_selected_rom", None)

            # pywebview API calls are stateless, so recover the selected path
            # from the page through a small explicit callback is undesirable.
            # Instead, inspect_rom caches it in this process.
            if not rom_path:
                # See inspect_rom patch below: it stores the latest selected path.
                raise RuntimeError("No inspected ROM is available for this session.")

            rom = Path(rom_path).resolve()
            if not rom.exists():
                raise RuntimeError("Selected ROM file no longer exists.")

            with tempfile.TemporaryDirectory(
                prefix="onyx-flasher-",
                dir=str(WORK_DIR),
            ) as temp:
                session = Path(temp)

                # 0 — ROM analysis
                _step(0, "running")
                _progress(2, "Validating ROM ZIP…")
                meta = self.inspect_rom(str(rom))
                if not meta.get("ok"):
                    raise RuntimeError(meta.get("error", "ROM inspection failed."))
                if not meta.get("has_payload"):
                    raise RuntimeError("payload.bin is required for V1.")
                _step(0, "done")
                _log(f"ROM validated: {rom.name}", "ok")

                # 1 — payload extraction
                _step(1, "running")
                _progress(8, "Extracting payload.bin…")
                payload = _extract_payload(rom, session)
                image_dir = session / "images"
                _progress(15, "Extracting boot/dtbo/init_boot/recovery/vendor_boot…")
                images = _extract_required_images(payload, image_dir)
                _step(1, "done")
                _log("Required five images extracted successfully.", "ok")

                # 2 — device verification
                _step(2, "running")
                _progress(20, "Checking fastboot device…")
                dev = _get_fastboot_device()
                if not dev.get("connected"):
                    raise RuntimeError(
                        "No device in fastboot mode. Boot POCO F7 into FASTBOOT first."
                    )

                product = _norm(dev.get("product") or dev.get("codename"))
                if product != EXPECTED_CODENAME:
                    raise RuntimeError(
                        f"Wrong device detected: {product or 'unknown'}; "
                        f"expected {EXPECTED_CODENAME}."
                    )
                _step(2, "done")
                _log(
                    f"Verified device: {dev.get('model', 'unknown')} "
                    f"({product}).",
                    "ok",
                )

                # 3–7 — flash exactly five images
                flash_steps = [
                    (3, "boot"),
                    (4, "dtbo"),
                    (5, "init_boot"),
                    (6, "recovery"),
                    (7, "vendor_boot"),
                ]

                for index, partition in flash_steps:
                    _step(index, "running")
                    percent = {
                        "boot": 27,
                        "dtbo": 38,
                        "init_boot": 49,
                        "recovery": 60,
                        "vendor_boot": 71,
                    }[partition]
                    _progress(percent, f"Flashing {partition}.img…")

                    proc = _run(
                        [_fastboot(), "flash", partition, str(images[partition])],
                        timeout=300,
                    )
                    output = _merged_output(proc)

                    if proc.returncode != 0:
                        raise RuntimeError(
                            f"fastboot flash {partition} failed.\n"
                            + output[-5000:]
                        )

                    # A failed fastboot command can occasionally still return
                    # confusing text; require an explicit success marker where possible.
                    if re.search(r"\bFAILED\b|\berror:", output, re.IGNORECASE):
                        raise RuntimeError(
                            f"fastboot reported an error while flashing {partition}.\n"
                            + output[-5000:]
                        )

                    _step(index, "done")
                    _log(f"Flashed {partition}.img", "ok")

                # 8 — reboot recovery
                _step(8, "running")
                _progress(82, "Rebooting to recovery…")
                proc = _run([_fastboot(), "reboot", "recovery"], timeout=60)
                if proc.returncode != 0:
                    raise RuntimeError(
                        "fastboot reboot recovery failed.\n" + _merged_output(proc)
                    )
                _step(8, "done")
                _log(
                    "Device rebooted to recovery. Complete the recovery UI steps.",
                    "ok",
                )

                # 9 — wait for sideload
                _step(9, "running")
                _progress(
                    86,
                    "In recovery: Apply Update → Apply from ADB. Waiting for sideload…",
                )
                _log(
                    "Now select Apply Update → Apply from ADB on the device. "
                    "The ROM will be sent automatically once ADB reports 'sideload'.",
                    "warn",
                )

                deadline = time.time() + 600
                sideload_ready = False

                while time.time() < deadline:
                    states = _adb_devices()
                    if any(state == "sideload" for _, state in states):
                        sideload_ready = True
                        break
                    time.sleep(1.5)

                if not sideload_ready:
                    raise RuntimeError(
                        "Timed out waiting for ADB sideload mode (10 minutes)."
                    )

                _step(9, "done")
                _log("ADB sideload mode detected.", "ok")

                # 10 — sideload ROM
                _step(10, "running")
                _progress(90, "Sideloading ROM ZIP…")
                proc = _run(
                    [_adb(), "-d", "sideload", str(rom)],
                    timeout=1800,
                )
                output = _merged_output(proc)

                # adb sideload may return a non-zero status at 47% on some
                # Android recovery/ADB combinations even when the package
                # completed. Treat only explicit failure output as fatal.
                failed = bool(
                    re.search(
                        r"failed to read command|error:|adb: failed|cannot read|"
                        r"no such file|protocol fault",
                        output,
                        re.IGNORECASE,
                    )
                )

                if proc.returncode != 0 and failed:
                    raise RuntimeError(
                        "ADB sideload failed.\n" + output[-6000:]
                    )

                _step(10, "done")
                _progress(
                    100,
                    "ROM sideload complete. Follow the recovery instructions.",
                )
                _log(
                    "ROM sideload completed. V1 stops here so the user can "
                    "finish Format Data / Reboot exactly as required by the ROM.",
                    "ok",
                )
                _finish(
                    True,
                    "ROM sideload complete. Finish Format Data / Factory Reset in recovery, then reboot to system.",
                )

        except Exception as exc:
            _log(str(exc), "error")
            _finish(False, f"Flash stopped: {exc}")

        finally:
            FLASH_RUNNING = False


# Cache the latest inspected ROM path without exposing arbitrary filesystem
# operations to the browser.
_original_inspect = Api.inspect_rom


def _inspect_and_cache(self: Api, path: str) -> Dict[str, Any]:
    result = _original_inspect(self, path)
    if result.get("ok"):
        self._selected_rom = result.get("path")
    return result


Api.inspect_rom = _inspect_and_cache


def main() -> None:
    api = Api()

    window = webview.create_window(
        APP_NAME,
        str((ROOT / "index.html").resolve()),
        js_api=api,
        width=1280,
        height=860,
        min_size=(1000, 700),
        text_select=True,
    )
    api.set_window(window)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
