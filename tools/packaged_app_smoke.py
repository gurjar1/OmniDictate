from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from PIL import Image, ImageGrab


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "OmniDictateSmoke"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the per-user package, screenshot the installed app, and uninstall it.")
    parser.add_argument(
        "--installer",
        default=str(ROOT / "smoke_test_assets" / "packaging" / "installer-whisper-user-smoke" / "OmniDictate_Setup_v3.0.0-whisper-user-smoke.exe"),
    )
    parser.add_argument("--install-dir", default=str(DEFAULT_INSTALL_DIR))
    parser.add_argument("--screenshot", default=str(ROOT / "smoke_test_assets" / "ui" / "packaged-whisper-main.png"))
    parser.add_argument("--launch-timeout", type=float, default=30.0)
    parser.add_argument(
        "--package-profile",
        default="",
        help="Optional profile override. Final public smokes leave this blank so the frozen executable must provide its own profile.",
    )
    parser.add_argument("--package-smoke-model", default="tiny")
    parser.add_argument(
        "--package-smoke-load-whisper",
        action="store_true",
        help="Ask the installed app to load the named Whisper model during the frozen runtime self-test.",
    )
    parser.add_argument(
        "--use-isolated-settings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Launch the installed app with a temporary QSettings app id so screenshots show first-run defaults.",
    )
    return parser.parse_args()


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with {completed.returncode}: {command}")


def _find_window_for_pid(pid: int) -> int:
    import win32gui
    import win32process

    matches: list[int] = []

    def _enum(hwnd, _extra):
        if not win32gui.IsWindowVisible(hwnd):
            return
        _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
        title = win32gui.GetWindowText(hwnd)
        if window_pid == pid and "OmniDictate" in title:
            matches.append(hwnd)

    win32gui.EnumWindows(_enum, None)
    return matches[0] if matches else 0


def _capture_window(hwnd: int, output_path: Path) -> None:
    import ctypes
    import win32ui
    import win32gui
    import win32con

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.5)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    if right <= left or bottom <= top:
        raise RuntimeError(f"Invalid window bounds: {(left, top, right, bottom)}")
    width = right - left
    height = bottom - top
    image = None
    window_dc = win32gui.GetWindowDC(hwnd)
    source_dc = win32ui.CreateDCFromHandle(window_dc)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source_dc, width, height)
    memory_dc.SelectObject(bitmap)
    try:
        rendered = ctypes.windll.user32.PrintWindow(hwnd, memory_dc.GetSafeHdc(), 2)
        if rendered:
            bits = bitmap.GetBitmapBits(True)
            image = Image.frombuffer("RGB", (width, height), bits, "raw", "BGRX", 0, 1)
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        memory_dc.DeleteDC()
        source_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, window_dc)
    if image is None:
        image = ImageGrab.grab(bbox=(left, top, right, bottom))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _delete_registry_tree(root, subkey: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    child_name = winreg.EnumKey(key, 0)
                except OSError:
                    break
                _delete_registry_tree(root, f"{subkey}\\{child_name}")
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        return


def _cleanup_isolated_settings(org: str, app: str) -> None:
    import winreg

    _delete_registry_tree(winreg.HKEY_CURRENT_USER, f"Software\\{org}\\{app}")


def main() -> int:
    args = parse_args()
    installer = Path(args.installer).resolve()
    install_dir = Path(args.install_dir)
    screenshot = Path(args.screenshot)
    artifact_dir = installer.parent
    install_log = artifact_dir / "packaged-ui-install.log"
    uninstall_log = artifact_dir / "packaged-ui-uninstall.log"
    settings_org = "OmniCorp"
    settings_app = f"OmniDictatePackagedSmoke{uuid.uuid4().hex}"

    if not installer.exists():
        raise SystemExit(f"Installer not found: {installer}")
    if install_dir.exists():
        shutil.rmtree(install_dir)

    _run(
        [
            str(installer),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CURRENTUSER",
            f"/DIR={install_dir}",
            "/MERGETASKS=!desktopicon",
            f"/LOG={install_log}",
        ]
    )

    installed_exe = install_dir / "OmniDictate.exe"
    if not installed_exe.exists():
        raise RuntimeError(f"Installed executable not found: {installed_exe}")
    python_dll = install_dir / "_internal" / "python311.dll"
    if not python_dll.exists():
        raise RuntimeError(f"Installed Python DLL not found: {python_dll}")
    if "build-whisper-final" in str(installed_exe).lower() or "build-whisper-final" in str(python_dll).lower():
        raise RuntimeError(f"Installed payload points at a build work directory: {install_dir}")

    launch_env = os.environ.copy()
    launch_env["OMNIDICTATE_DISABLE_AUTO_UPDATE_CHECK"] = "1"
    if args.package_profile:
        launch_env["OMNIDICTATE_PACKAGE_PROFILE"] = args.package_profile
    if args.use_isolated_settings:
        launch_env["OMNIDICTATE_SETTINGS_ORG"] = settings_org
        launch_env["OMNIDICTATE_SETTINGS_APP"] = settings_app

    runtime_report = artifact_dir / "packaged-runtime-smoke.json"
    runtime_command = [
        str(installed_exe),
        "--package-smoke-report",
        str(runtime_report),
        "--package-smoke-model",
        args.package_smoke_model,
    ]
    if args.package_smoke_load_whisper:
        runtime_command.append("--package-smoke-load-whisper")
    runtime_result = subprocess.run(runtime_command, env=launch_env, cwd=install_dir, timeout=max(args.launch_timeout, 30.0), check=False)
    if runtime_result.returncode != 0:
        report_text = runtime_report.read_text(encoding="utf-8") if runtime_report.exists() else "<missing report>"
        raise RuntimeError(f"Packaged runtime self-test failed with {runtime_result.returncode}: {report_text}")
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    if runtime_payload.get("status") != "passed":
        raise RuntimeError(f"Packaged runtime self-test did not pass: {runtime_payload}")

    process = subprocess.Popen([str(installed_exe)], env=launch_env)
    try:
        deadline = time.time() + args.launch_timeout
        hwnd = 0
        while time.time() < deadline:
            hwnd = _find_window_for_pid(process.pid)
            if hwnd:
                break
            if process.poll() is not None:
                raise RuntimeError(f"Installed app exited early with {process.returncode}")
            time.sleep(0.25)
        if not hwnd:
            raise RuntimeError("Timed out waiting for installed app window.")
        time.sleep(2.0)
        _capture_window(hwnd, screenshot)
        print(f"Packaged app screenshot saved: {screenshot.resolve()}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if args.use_isolated_settings:
            _cleanup_isolated_settings(settings_org, settings_app)

    uninstaller = install_dir / "unins000.exe"
    if not uninstaller.exists():
        raise RuntimeError(f"Uninstaller not found: {uninstaller}")
    _run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/LOG={uninstall_log}"])
    time.sleep(2.0)
    if installed_exe.exists() or (install_dir / "_internal").exists():
        raise RuntimeError(f"Installed payload still exists after uninstall: {install_dir}")
    settings_note = "isolated first-run settings" if args.use_isolated_settings else "current user settings"
    print(f"Packaged app smoke passed with {settings_note}. Install dir exists after uninstall: {install_dir.exists()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
