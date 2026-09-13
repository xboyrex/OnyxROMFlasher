"""
Onyx ROM Flasher V1.2
Native Windows GUI using Tkinter/ttk.

V1 scope:
  ROM ZIP -> payload.bin -> five required images
  -> fastboot flash -> fastboot reboot recovery
  -> wait for user to enter ADB sideload mode
  -> adb -d sideload ROM ZIP

Safety:
  - Never formats userdata automatically.
  - Requires fastboot product == onyx before flashing.
  - Only the five whitelisted images are flashed.
  - HyperOS/MiFlash-style flashing is not part of V1.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


APP_NAME = "Onyx ROM Flasher"
APP_VERSION = "V1.2 Native GUI"
EXPECTED_CODENAME = "onyx"
REQUIRED_IMAGES = ["boot", "dtbo", "init_boot", "recovery", "vendor_boot"]

ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
TOOLS_DIR = ROOT / "tools"
WORK_DIR = ROOT / "work"
WORK_DIR.mkdir(parents=True, exist_ok=True)

FLASH_LOCK = threading.Lock()
FLASH_RUNNING = False


def _platform_exe(name: str) -> str:
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


def _run(args: List[str], *, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )


def _merged_output(proc: subprocess.CompletedProcess) -> str:
    return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _find_payload(z: zipfile.ZipFile) -> Optional[str]:
    names = z.namelist()
    for name in names:
        if name.replace("\\", "/").strip("/") == "payload.bin":
            return name
    for name in names:
        if Path(name).name.lower() == "payload.bin":
            return name
    return None


def _filename_device_hint(path: Path) -> str:
    if re.search(r"(^|[-_.])onyx([-_.]|$)", path.name.lower()):
        return EXPECTED_CODENAME
    return "unknown"


def _extract_payload(rom_zip: Path, session_dir: Path) -> Path:
    payload_dir = session_dir / "payload"
    payload_dir.mkdir(parents=True, exist_ok=True)
    payload_path = payload_dir / "payload.bin"

    with zipfile.ZipFile(rom_zip, "r") as z:
        payload_name = _find_payload(z)
        if not payload_name:
            raise RuntimeError("payload.bin was not found in the selected ROM ZIP.")
        info = z.getinfo(payload_name)
        if info.file_size <= 0:
            raise RuntimeError("payload.bin is empty.")
        if info.file_size > 20 * 1024 * 1024 * 1024:
            raise RuntimeError("payload.bin is unexpectedly large; refusing to extract.")
        with z.open(info, "r") as src, payload_path.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    return payload_path


def _extract_required_images(payload_path: Path, output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dumper = _platform_exe("payload-dumper-go")
    proc = _run([dumper, "-o", str(output_dir), str(payload_path)], timeout=900)
    output = _merged_output(proc)

    if proc.returncode != 0:
        raise RuntimeError(
            "payload-dumper-go failed.\n" + (output[-5000:] if output else "No diagnostic output.")
        )

    found: Dict[str, Path] = {}
    for image in REQUIRED_IMAGES:
        candidate = output_dir / f"{image}.img"
        if candidate.exists() and candidate.stat().st_size > 0:
            found[image] = candidate

    missing = [x for x in REQUIRED_IMAGES if x not in found]
    if missing:
        raise RuntimeError(
            "Required images were not extracted: "
            + ", ".join(f"{x}.img" for x in missing)
            + "\n\nDumper output:\n"
            + (output[-2500:] if output else "No dumper output.")
        )
    return found


def _fastboot() -> str:
    return _platform_exe("fastboot")


def _adb() -> str:
    return _platform_exe("adb")


def _fastboot_devices() -> List[str]:
    proc = _run([_fastboot(), "devices"], timeout=20)
    return [
        parts[0]
        for line in proc.stdout.splitlines()
        if len(parts := line.split()) >= 2 and parts[1].lower() == "fastboot"
    ]


def _adb_devices() -> List[tuple[str, str]]:
    proc = _run([_adb(), "devices"], timeout=20)
    result = []
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
            "connected": True, "mode": "sideload", "serial": serial,
            "product": "onyx", "codename": "onyx", "model": "POCO F7",
            "slot": "unknown", "battery": None, "unlocked": None,
        }

    def adb_shell(prop: str) -> str:
        proc = _run([_adb(), "-s", serial, "shell", "getprop", prop], timeout=15)
        return proc.stdout.strip()

    product = adb_shell("ro.product.device") or adb_shell("ro.build.product")
    model = adb_shell("ro.product.model")
    slot = adb_shell("ro.boot.slot_suffix").lstrip("_")

    return {
        "connected": True, "mode": "adb", "serial": serial,
        "product": product or "unknown", "codename": product or "unknown",
        "model": model or "unknown", "slot": slot or "unknown",
        "battery": None, "unlocked": None,
    }


class FlashEngine:
    """Flashing engine with UI callbacks; no GUI dependency."""

    def __init__(self, on_log: Callable[[str, str], None],
                 on_step: Callable[[int, str], None],
                 on_progress: Callable[[int, str], None],
                 on_done: Callable[[bool, str], None]):
        self.on_log = on_log
        self.on_step = on_step
        self.on_progress = on_progress
        self.on_done = on_done
        self.selected_rom: Optional[str] = None

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
                    return {"ok": False, "error": f"ZIP integrity check failed near: {bad}"}
                payload_name = _find_payload(z)

            result = {
                "ok": True,
                "name": rom.name,
                "path": str(rom),
                "size": size,
                "device": _filename_device_hint(rom),
                "has_payload": payload_name is not None,
                "payload_name": payload_name or "",
            }
            if result["ok"]:
                self.selected_rom = result["path"]
            return result
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

    def start(self) -> Dict[str, Any]:
        global FLASH_RUNNING
        with FLASH_LOCK:
            if FLASH_RUNNING:
                return {"ok": False, "error": "A flash session is already running."}
            if not self.selected_rom:
                return {"ok": False, "error": "Select and validate a ROM ZIP first."}
            FLASH_RUNNING = True

        threading.Thread(target=self._flash_worker, name="onyx-flash-worker", daemon=True).start()
        return {"ok": True, "message": "Flash worker started."}

    def _flash_worker(self) -> None:
        global FLASH_RUNNING
        try:
            rom_path = self.selected_rom
            if not rom_path:
                raise RuntimeError("No inspected ROM is available for this session.")
            rom = Path(rom_path).resolve()
            if not rom.exists():
                raise RuntimeError("Selected ROM file no longer exists.")

            with tempfile.TemporaryDirectory(prefix="onyx-flasher-", dir=str(WORK_DIR)) as temp:
                session = Path(temp)

                self.on_step(0, "running")
                self.on_progress(2, "Validating ROM ZIP...")
                meta = self.inspect_rom(str(rom))
                if not meta.get("ok"):
                    raise RuntimeError(meta.get("error", "ROM inspection failed."))
                if not meta.get("has_payload"):
                    raise RuntimeError("payload.bin is required for V1.")
                self.on_step(0, "done")
                self.on_log(f"ROM validated: {rom.name}", "ok")

                self.on_step(1, "running")
                self.on_progress(8, "Extracting payload.bin...")
                payload = _extract_payload(rom, session)
                image_dir = session / "images"
                self.on_progress(15, "Extracting five required images...")
                images = _extract_required_images(payload, image_dir)
                self.on_step(1, "done")
                self.on_log("boot, dtbo, init_boot, recovery and vendor_boot extracted.", "ok")

                self.on_step(2, "running")
                self.on_progress(20, "Checking fastboot device...")
                dev = _get_fastboot_device()
                if not dev.get("connected"):
                    raise RuntimeError("No device in fastboot mode. Boot POCO F7 into FASTBOOT first.")
                product = _norm(dev.get("product") or dev.get("codename"))
                if product != EXPECTED_CODENAME:
                    raise RuntimeError(
                        f"Wrong device detected: {product or 'unknown'}; expected {EXPECTED_CODENAME}."
                    )
                self.on_step(2, "done")
                self.on_log(
                    f"Verified device: {dev.get('model', 'unknown')} ({product})",
                    "ok",
                )

                flash_steps = [
                    (3, "boot", 27),
                    (4, "dtbo", 38),
                    (5, "init_boot", 49),
                    (6, "recovery", 60),
                    (7, "vendor_boot", 71),
                ]
                for index, partition, percent in flash_steps:
                    self.on_step(index, "running")
                    self.on_progress(percent, f"Flashing {partition}.img...")
                    proc = _run(
                        [_fastboot(), "flash", partition, str(images[partition])],
                        timeout=300,
                    )
                    output = _merged_output(proc)
                    if proc.returncode != 0 or re.search(r"\bFAILED\b|\berror:", output, re.I):
                        raise RuntimeError(
                            f"fastboot flash {partition} failed.\n{output[-5000:]}"
                        )
                    self.on_step(index, "done")
                    self.on_log(f"Flashed {partition}.img", "ok")

                self.on_step(8, "running")
                self.on_progress(82, "Rebooting to recovery...")
                proc = _run([_fastboot(), "reboot", "recovery"], timeout=60)
                if proc.returncode != 0:
                    raise RuntimeError(
                        "fastboot reboot recovery failed.\n" + _merged_output(proc)
                    )
                self.on_step(8, "done")
                self.on_log("Device rebooted to recovery.", "ok")

                self.on_step(9, "running")
                self.on_progress(86, "Waiting for ADB sideload mode...")
                self.on_log(
                    "On the phone: Apply Update -> Apply from ADB. Waiting for sideload mode.",
                    "warn",
                )
                deadline = time.time() + 600
                while time.time() < deadline:
                    if any(state == "sideload" for _, state in _adb_devices()):
                        break
                    time.sleep(1.5)
                else:
                    raise RuntimeError("Timed out waiting for ADB sideload mode (10 minutes).")
                self.on_step(9, "done")
                self.on_log("ADB sideload mode detected.", "ok")

                self.on_step(10, "running")
                self.on_progress(90, "Sideloading ROM ZIP...")
                proc = _run([_adb(), "-d", "sideload", str(rom)], timeout=1800)
                output = _merged_output(proc)
                failed = bool(re.search(
                    r"failed to read command|error:|adb: failed|cannot read|no such file|protocol fault",
                    output, re.I
                ))
                if proc.returncode != 0 and failed:
                    raise RuntimeError("ADB sideload failed.\n" + output[-6000:])
                self.on_step(10, "done")
                self.on_progress(100, "ROM sideload complete.")
                self.on_log(
                    "ROM sideload completed. V1 stops here; no automatic userdata format.",
                    "ok",
                )
                self.on_done(
                    True,
                    "ROM sideload complete.\n\n"
                    "On the phone, finish Format Data / Factory Reset in recovery, "
                    "then reboot to system.",
                )
        except Exception as exc:
            self.on_log(str(exc), "error")
            self.on_done(False, f"Flash stopped:\n{exc}")
        finally:
            FLASH_RUNNING = False


# ---------------------------- Native Windows GUI ----------------------------

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


BG = "#0b0d12"
PANEL = "#121620"
PANEL2 = "#171c27"
BORDER = "#283041"
TEXT = "#f2f5fa"
MUTED = "#9aa5b5"
ACCENT = "#7c5cff"
ACCENT2 = "#4f8cff"
SUCCESS = "#39d98a"
WARNING = "#ffbf69"
DANGER = "#ff5c6c"


class OnyxApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(bg=BG)

        self.rom_path = ""
        self.rom_meta: Optional[Dict[str, Any]] = None
        self.busy = False
        self.last_device: Dict[str, Any] = {}

        self.engine = FlashEngine(
            self.ui_log,
            self.ui_step,
            self.ui_progress,
            self.ui_done,
        )

        self._setup_style()
        self._build_ui()
        self.after(300, self.refresh_device)
        self.after(2000, self._device_loop)

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 23))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("PanelTitle.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 11))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=PANEL2, foreground=TEXT, font=("Segoe UI Semibold", 10))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10), padding=(16, 10))
        style.map("Accent.TButton",
                  background=[("active", ACCENT2), ("disabled", "#252b38")],
                  foreground=[("disabled", "#697386"), ("!disabled", "#ffffff")])
        style.configure("Secondary.TButton", font=("Segoe UI Semibold", 9), padding=(12, 8))
        style.map("Secondary.TButton",
                  background=[("active", BORDER)], foreground=[("!disabled", TEXT)])
        style.configure("TProgressbar", troughcolor="#202633", background=ACCENT,
                        bordercolor="#202633", lightcolor=ACCENT, darkcolor=ACCENT)

    def _card(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=BORDER)

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 18))

        tk.Label(header, text="ONYX ROM FLASHER", bg=BG, fg=TEXT,
                 font=("Segoe UI Semibold", 24)).pack(side="left")
        tk.Label(header, text="  AOSP CLEAN FLASH  •  V1.2", bg=BG, fg=ACCENT,
                 font=("Segoe UI Semibold", 10)).pack(side="left", pady=(10, 0))
        tk.Label(header, text="POCO F7 / onyx", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="right", pady=(10, 0))

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(2, weight=1)

        # Device card
        device = self._card(body)
        device.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        tk.Label(device, text="DEVICE", bg=PANEL, fg=MUTED,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=16, pady=(14, 2))
        row = tk.Frame(device, bg=PANEL)
        row.pack(fill="x", padx=16, pady=(0, 14))
        self.device_dot = tk.Label(row, text="●", bg=PANEL, fg=DANGER, font=("Segoe UI", 15))
        self.device_dot.pack(side="left")
        self.device_status = tk.Label(row, text="Not connected", bg=PANEL, fg=TEXT,
                                      font=("Segoe UI Semibold", 12))
        self.device_status.pack(side="left", padx=8)
        self.product_status = tk.Label(row, text="Product: —", bg=PANEL, fg=MUTED,
                                       font=("Segoe UI", 9))
        self.product_status.pack(side="left", padx=12)
        ttk.Button(row, text="Refresh", style="Secondary.TButton",
                   command=self.refresh_device).pack(side="right")

        # ROM card
        rom = self._card(body)
        rom.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        tk.Label(rom, text="ROM PACKAGE", bg=PANEL, fg=MUTED,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=16, pady=(14, 4))
        romrow = tk.Frame(rom, bg=PANEL)
        romrow.pack(fill="x", padx=16, pady=(0, 8))
        self.rom_name = tk.Label(romrow, text="No ROM selected", bg=PANEL, fg=TEXT,
                                 font=("Segoe UI Semibold", 11), anchor="w")
        self.rom_name.pack(side="left", fill="x", expand=True)
        ttk.Button(romrow, text="Select ROM ZIP", style="Secondary.TButton",
                   command=self.select_rom).pack(side="right")
        self.rom_detail = tk.Label(rom, text="Select an AOSP ROM containing payload.bin.",
                                   bg=PANEL, fg=MUTED, font=("Segoe UI", 9), anchor="w")
        self.rom_detail.pack(fill="x", padx=16, pady=(0, 14))

        # Right: safety + actions
        info = self._card(body)
        info.grid(row=0, column=1, rowspan=2, sticky="nsew", pady=(0, 10))
        tk.Label(info, text="V1 FLASH PLAN", bg=PANEL, fg=MUTED,
                 font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=16, pady=(14, 6))

        self.step_labels = []
        step_names = [
            "Validate ROM",
            "Extract payload + images",
            "Verify onyx device",
            "Flash boot",
            "Flash dtbo",
            "Flash init_boot",
            "Flash recovery",
            "Flash vendor_boot",
            "Reboot recovery",
            "Wait for ADB sideload",
            "Sideload ROM ZIP",
        ]
        steps_frame = tk.Frame(info, bg=PANEL)
        steps_frame.pack(fill="both", expand=True, padx=12)
        for i, name in enumerate(step_names):
            r = tk.Frame(steps_frame, bg=PANEL)
            r.pack(fill="x", pady=2)
            icon = tk.Label(r, text="○", width=2, bg=PANEL, fg=MUTED,
                            font=("Segoe UI Semibold", 10))
            icon.pack(side="left")
            label = tk.Label(r, text=name, bg=PANEL, fg=MUTED,
                             font=("Segoe UI", 9), anchor="w")
            label.pack(side="left", fill="x")
            self.step_labels.append((icon, label))

        warning = tk.Frame(info, bg="#1e1a12", highlightthickness=1,
                           highlightbackground="#4a3a20")
        warning.pack(fill="x", padx=16, pady=12)
        tk.Label(warning, text="⚠  USER ACTION REQUIRED", bg="#1e1a12",
                 fg=WARNING, font=("Segoe UI Semibold", 9)).pack(anchor="w", padx=12, pady=(10, 3))
        tk.Label(
            warning,
            text="After reboot to recovery:\n"
                 "1. Format Data / Factory Reset manually\n"
                 "2. Apply Update → Apply from ADB\n"
                 "3. Tool will sideload the selected ROM automatically",
            bg="#1e1a12", fg="#e5d9c6", justify="left",
            font=("Segoe UI", 9)
        ).pack(anchor="w", padx=12, pady=(0, 10))

        action = tk.Frame(info, bg=PANEL)
        action.pack(fill="x", padx=16, pady=(0, 16))
        self.flash_btn = ttk.Button(action, text="START CLEAN FLASH",
                                    style="Accent.TButton", command=self.start_flash)
        self.flash_btn.pack(fill="x")
        self.flash_btn.state(["disabled"])

        # Progress / logs
        progress = self._card(body)
        progress.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 0))
        progress.grid_rowconfigure(2, weight=1)
        progress.grid_columnconfigure(0, weight=1)

        top = tk.Frame(progress, bg=PANEL)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.progress_label = tk.Label(top, text="Ready", bg=PANEL, fg=TEXT,
                                       font=("Segoe UI Semibold", 10))
        self.progress_label.pack(side="left")
        self.percent_label = tk.Label(top, text="0%", bg=PANEL, fg=ACCENT,
                                      font=("Segoe UI Semibold", 10))
        self.percent_label.pack(side="right")

        self.progressbar = ttk.Progressbar(progress, maximum=100, mode="determinate")
        self.progressbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        log_frame = tk.Frame(progress, bg="#090b10")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(
            log_frame, bg="#090b10", fg="#cbd3df", insertbackground=TEXT,
            relief="flat", borderwidth=0, wrap="word", font=("Consolas", 9),
            padx=12, pady=10
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)
        for tag, color in [("ok", SUCCESS), ("warn", WARNING), ("error", DANGER), ("info", "#aab4c3")]:
            self.log_text.tag_configure(tag, foreground=color)

        self.ui_log("Application initialized. Connect POCO F7 in FASTBOOT mode.", "info")

    def _device_loop(self):
        if not self.busy:
            self.refresh_device(silent=True)
        self.after(2500, self._device_loop)

    def _set_device(self, dev):
        self.last_device = dev
        if not dev.get("connected"):
            self.device_dot.config(fg=DANGER)
            self.device_status.config(text="Not connected")
            self.product_status.config(text="Product: —", fg=MUTED)
            return

        mode = str(dev.get("mode", "")).upper()
        product = str(dev.get("product", "unknown"))
        ok = product.lower() == EXPECTED_CODENAME
        self.device_dot.config(fg=SUCCESS if ok else DANGER)
        self.device_status.config(text=f"{dev.get('model', 'Device')}  •  {mode}")
        self.product_status.config(
            text=f"Product: {product}",
            fg=SUCCESS if ok else DANGER
        )
        self._update_start_state()

    def refresh_device(self, silent=False):
        def worker():
            dev = self.engine.get_device()
            self.after(0, lambda: self._set_device(dev))
            if not silent and dev.get("mode") == "error":
                self.after(0, lambda: self.ui_log(dev.get("error", "Device check failed."), "error"))
        threading.Thread(target=worker, daemon=True).start()

    def select_rom(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(
            title="Select AOSP ROM ZIP",
            filetypes=[("Android ROM ZIP", "*.zip"), ("All files", "*.*")]
        )
        if not path:
            return
        self.rom_name.config(text="Checking ROM...", fg=MUTED)
        self.rom_detail.config(text=path, fg=MUTED)

        def worker():
            result = self.engine.inspect_rom(path)
            self.after(0, lambda: self._rom_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _rom_result(self, result):
        if not result.get("ok"):
            self.rom_meta = None
            self.rom_path = ""
            self.rom_name.config(text="ROM validation failed", fg=DANGER)
            self.rom_detail.config(text=result.get("error", "Unknown error"), fg=DANGER)
            self.ui_log(result.get("error", "ROM validation failed."), "error")
            self._update_start_state()
            return

        self.rom_meta = result
        self.rom_path = result["path"]
        size_mb = result["size"] / (1024 * 1024)
        self.rom_name.config(text=result["name"], fg=TEXT)
        self.rom_detail.config(
            text=f"{size_mb:.1f} MB  •  payload.bin: {'FOUND' if result['has_payload'] else 'MISSING'}",
            fg=SUCCESS if result["has_payload"] else DANGER
        )
        if result["has_payload"]:
            self.ui_log(f"ROM selected and validated: {result['name']}", "ok")
        else:
            self.ui_log("payload.bin is required for V1.", "error")
        self._update_start_state()

    def _update_start_state(self):
        product = str(self.last_device.get("product", "")).lower()
        ready = bool(
            self.rom_meta
            and self.rom_meta.get("has_payload")
            and self.last_device.get("mode") == "fastboot"
            and product == EXPECTED_CODENAME
            and not self.busy
        )
        if ready:
            self.flash_btn.state(["!disabled"])
        else:
            self.flash_btn.state(["disabled"])

    def start_flash(self):
        if self.busy:
            return
        product = str(self.last_device.get("product", "")).lower()
        if product != EXPECTED_CODENAME or self.last_device.get("mode") != "fastboot":
            messagebox.showerror("Device not ready", "Connect POCO F7 (onyx) in FASTBOOT mode first.")
            return
        if not self.rom_meta or not self.rom_meta.get("has_payload"):
            messagebox.showerror("ROM not ready", "Select a valid ROM ZIP containing payload.bin.")
            return

        confirm = messagebox.askyesno(
            "Confirm clean flash",
            "This will flash ONLY:\n\n"
            "boot • dtbo • init_boot • recovery • vendor_boot\n\n"
            "Then the device will reboot to recovery.\n\n"
            "The tool will NOT format userdata automatically.\n\n"
            "Continue?"
        )
        if not confirm:
            return

        self.busy = True
        self._update_start_state()
        self._reset_steps()
        self.progressbar["value"] = 0
        self.percent_label.config(text="0%")
        self.progress_label.config(text="Starting...")
        self.ui_log("=== CLEAN FLASH STARTED ===", "info")
        result = self.engine.start()
        if not result.get("ok"):
            self.busy = False
            self._update_start_state()
            self.ui_done(False, result.get("error", "Could not start flash."))

    def _reset_steps(self):
        for icon, label in self.step_labels:
            icon.config(text="○", fg=MUTED)
            label.config(fg=MUTED)

    def ui_log(self, message: str, kind: str = "info"):
        def apply():
            self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n", kind)
            self.log_text.see("end")
        self.after(0, apply)

    def ui_step(self, index: int, status: str):
        def apply():
            if 0 <= index < len(self.step_labels):
                icon, label = self.step_labels[index]
                if status == "running":
                    icon.config(text="●", fg=ACCENT)
                    label.config(fg=TEXT)
                elif status == "done":
                    icon.config(text="✓", fg=SUCCESS)
                    label.config(fg=SUCCESS)
                elif status == "error":
                    icon.config(text="✕", fg=DANGER)
                    label.config(fg=DANGER)
        self.after(0, apply)

    def ui_progress(self, percent: int, label: str = ""):
        def apply():
            self.progressbar["value"] = percent
            self.percent_label.config(text=f"{percent}%")
            self.progress_label.config(text=label or "Working...")
        self.after(0, apply)

    def ui_done(self, ok: bool, message: str):
        def apply():
            self.busy = False
            self._update_start_state()
            if ok:
                self.progressbar["value"] = 100
                self.percent_label.config(text="100%")
                self.progress_label.config(text="Completed — finish recovery steps")
                self.ui_log("=== FLASH SEQUENCE COMPLETE ===", "ok")
                messagebox.showinfo("Onyx ROM Flasher", message)
            else:
                self.progress_label.config(text="Stopped — check log")
                self.ui_log("=== FLASH SEQUENCE STOPPED ===", "error")
                messagebox.showerror("Onyx ROM Flasher", message)
        self.after(0, apply)


# Install safety hardening before the GUI/flash engine is used.
import runtime_safety as _runtime_safety
_runtime_safety.install(sys.modules[__name__])


def main() -> None:
    app = OnyxApp()
    app.mainloop()


if __name__ == "__main__":
    main()
