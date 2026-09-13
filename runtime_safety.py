"""Runtime safety hardening for Onyx ROM Flasher V1."""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List

EXPECTED_CODENAME = "onyx"


def _parse_fastboot_devices(stdout: str) -> List[str]:
    result: List[str] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].lower() == "fastboot":
            result.append(parts[0])
    return result


def _fastboot_var(module: Any, serial: str, name: str) -> str:
    proc = module._ORIGINAL_RUN(
        [module._fastboot(), "-s", serial, "getvar", name], timeout=20
    )
    output = module._merged_output(proc)
    patterns = [
        rf"{re.escape(name)}\s*:\s*(.+)",
        rf"{re.escape(name)}\s*=\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _safe_fastboot_device(module: Any) -> Dict[str, Any]:
    proc = module._ORIGINAL_RUN([module._fastboot(), "devices"], timeout=20)
    if proc.returncode != 0:
        raise RuntimeError(
            "fastboot devices failed.\n" + module._merged_output(proc)[-3000:]
        )

    devices = _parse_fastboot_devices(proc.stdout or "")
    if not devices:
        module._VERIFIED_SERIAL = None
        return {"connected": False, "mode": "disconnected"}

    if len(devices) != 1:
        module._VERIFIED_SERIAL = None
        raise RuntimeError(
            f"Multiple fastboot devices detected ({len(devices)}). "
            "Disconnect all other Android devices and leave only the POCO F7 connected."
        )

    serial = devices[0]
    product = _fastboot_var(module, serial, "product")
    slot = _fastboot_var(module, serial, "current-slot")
    unlocked_raw = _fastboot_var(module, serial, "unlocked")

    unlocked_text = unlocked_raw.strip().lower()
    if unlocked_text in {"yes", "true", "1", "unlocked"}:
        unlocked = True
    elif unlocked_text in {"no", "false", "0", "locked"}:
        unlocked = False
    else:
        unlocked = None

    module._VERIFIED_SERIAL = serial
    return {
        "connected": True,
        "mode": "fastboot",
        "serial": serial,
        "product": product or "unknown",
        "codename": product or "unknown",
        "model": "POCO F7" if product.lower() == EXPECTED_CODENAME else (product or "unknown"),
        "slot": slot or "unknown",
        "battery": None,
        "unlocked": unlocked,
    }


def _read_ota_metadata(rom: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    with zipfile.ZipFile(rom, "r") as z:
        name = "META-INF/com/android/metadata"
        if name not in z.namelist():
            return values
        text = z.read(name).decode("utf-8", "replace")
        for line in text.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key in {"pre-device", "post-device", "ota-type"}:
                values[key] = value.strip()
    return values


def _validate_rom_result(original_result: Dict[str, Any], path: str) -> Dict[str, Any]:
    if not original_result.get("ok"):
        return original_result

    rom = Path(path).expanduser().resolve()
    try:
        with zipfile.ZipFile(rom, "r") as z:
            names = {name.replace("\\", "/").strip("/") for name in z.namelist()}
            if "payload.bin" not in names:
                return {"ok": False, "error": "V1 requires payload.bin at the ZIP root."}
            if "payload_properties.txt" not in names:
                return {
                    "ok": False,
                    "error": "A/B OTA package is incomplete: payload_properties.txt is missing.",
                }

        metadata = _read_ota_metadata(rom)
        for key in ("pre-device", "post-device"):
            value = metadata.get(key, "")
            if not value:
                continue
            devices = [item.strip().lower() for item in value.split("|") if item.strip()]
            if EXPECTED_CODENAME not in devices:
                return {
                    "ok": False,
                    "error": f"ROM metadata {key}={value!r} does not contain {EXPECTED_CODENAME!r}.",
                }

        original_result["metadata"] = metadata
        original_result["device"] = EXPECTED_CODENAME
        return original_result
    except (zipfile.BadZipFile, OSError) as exc:
        return {"ok": False, "error": f"ROM safety validation failed: {exc}"}


def install(module: Any) -> None:
    if getattr(module, "_SAFETY_INSTALLED", False):
        return

    module._ORIGINAL_RUN = module._run
    module._VERIFIED_SERIAL = None

    def safe_run(args, *, timeout=120):
        command = list(args)
        if command and module._VERIFIED_SERIAL:
            executable = Path(str(command[0])).name.lower()
            if executable in {"fastboot.exe", "fastboot"}:
                if len(command) < 2 or command[1].lower() != "devices":
                    if "-s" not in command:
                        command.insert(1, "-s")
                        command.insert(2, module._VERIFIED_SERIAL)
        return module._ORIGINAL_RUN(command, timeout=timeout)

    module._run = safe_run
    module._get_fastboot_device = lambda: _safe_fastboot_device(module)

    original_inspect = module.FlashEngine.inspect_rom

    def safe_inspect(self, path):
        result = original_inspect(self, path)
        hardened = _validate_rom_result(result, path)
        if not hardened.get("ok"):
            self.selected_rom = None
        return hardened

    module.FlashEngine.inspect_rom = safe_inspect

    original_start = module.FlashEngine.start

    def safe_start(self):
        dev = _safe_fastboot_device(module)
        if not dev.get("connected"):
            return {"ok": False, "error": "No POCO F7 in fastboot mode."}
        if str(dev.get("product", "")).lower() != EXPECTED_CODENAME:
            return {
                "ok": False,
                "error": f"Wrong device detected: {dev.get('product', 'unknown')}; expected {EXPECTED_CODENAME}.",
            }
        if dev.get("unlocked") is False:
            return {
                "ok": False,
                "error": "Bootloader is locked. Unlock the POCO F7 before flashing.",
            }
        return original_start(self)

    module.FlashEngine.start = safe_start
    module._SAFETY_INSTALLED = True
