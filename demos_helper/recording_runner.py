import json
import os
import re
import shutil
import subprocess
import threading
import time
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Tuple
from ctypes import wintypes

from .csharp_planner import plan_csharp_demo
from .pipeline_planner import plan_pipeline_demo
from .planner import plan_demo
from .player import play_demo
from .sql_planner import plan_sql_demo


def _enable_dpi_awareness() -> None:
    # Align Win32 coordinates with physical pixels used by ffmpeg capture.
    # Try the most modern API first, then progressively older fallbacks.
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _default_plan_name(scenario: str) -> str:
    mapping = {
        "python": "plan.json",
        "sql": "sqlplan.json",
        "sql-visual": "sqlplan.visual.json",
        "csharp": "csharpplan.json",
        "azdo": "azdoplan.json",
        "gha": "ghaplan.json",
    }
    return mapping[scenario]


def _sanitize_for_filename(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return sanitized or "file"


def build_plan_for_scenario(scenario: str, prompt: str) -> Dict:
    if scenario == "python":
        return plan_demo(prompt)
    if scenario == "sql":
        return plan_sql_demo(prompt, visual_only=False)
    if scenario == "sql-visual":
        return plan_sql_demo(prompt, visual_only=True)
    if scenario == "csharp":
        return plan_csharp_demo(prompt)
    if scenario == "azdo":
        return plan_pipeline_demo(prompt, pipeline_type="azure-devops")
    if scenario == "gha":
        return plan_pipeline_demo(prompt, pipeline_type="github-actions")

    raise ValueError(f"Unsupported scenario: {scenario}")


def save_plan(plan: Dict, plan_file: Path) -> None:
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} is required but was not found on PATH.")
    return path


def _prepare_demo_workspace(session_dir: Path) -> Path:
    workspace_dir = session_dir / "demo-workspace"
    settings_dir = workspace_dir / ".vscode"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    settings_dir.mkdir(parents=True, exist_ok=True)

    settings = {
        "workbench.startupEditor": "none",
        "workbench.tips.enabled": False,
        "workbench.welcome.enabled": False,
        "window.zoomLevel": 0,
        "editor.minimap.enabled": False,
        "breadcrumbs.enabled": False,
        "files.autoSave": "afterDelay",
        "files.autoSaveDelay": 200,
        "workbench.activityBar.visible": False,
        "workbench.statusBar.visible": False,
        "extensions.ignoreRecommendations": True,
    }
    with open(settings_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    return workspace_dir


def _create_session_dir(root: Path) -> Path:
    session_dir = root / "recordings" / f"session-{_timestamp()}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _launch_vscode_window(workspace_dir: Path) -> None:
    code_path = _ensure_tool("code")
    subprocess.Popen(
        [
            code_path,
            "-n",
            str(workspace_dir),
            "--maximized",
            "--skip-release-notes",
            "--skip-add-to-recently-opened",
        ],
        shell=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _build_ffmpeg_cmd(
    video_file: Path,
    resolution: str,
    input_target: str = "desktop",
    capture_region: Tuple[int, int, int, int] | None = None,
) -> list[str]:
    ffmpeg_path = _ensure_tool("ffmpeg")
    width, height = resolution.lower().split("x", 1)
    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )
    base: list[str] = [
        ffmpeg_path,
        "-y",
        "-f",
        "gdigrab",
        "-framerate",
        "30",
    ]

    if capture_region is not None and input_target == "desktop":
        x, y, w, h = capture_region
        base.extend([
            "-offset_x", str(x),
            "-offset_y", str(y),
            "-video_size", f"{w}x{h}",
        ])

    base.extend([
        "-i",
        input_target,
        "-vf",
        scale_filter,
    ])

    if video_file.suffix.lower() == ".mp4":
        return base + [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video_file),
        ]

    return base + [
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuv420p",
        str(video_file),
    ]


def _start_recording(
    video_file: Path,
    resolution: str,
    ffmpeg_log_file: Path,
) -> subprocess.Popen:
    _ensure_tool("ffmpeg")
    video_file.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Reliable default for multi-monitor setups: capture only primary monitor desktop.
    capture_region = _get_primary_desktop_region()

    log_handle = open(ffmpeg_log_file, "w", encoding="utf-8")
    try:
        cmd = _build_ffmpeg_cmd(
            video_file,
            resolution,
            input_target="desktop",
            capture_region=capture_region,
        )
        log_handle.write("\n=== ffmpeg capture: primary-desktop ===\n")
        log_handle.flush()

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            shell=False,
        )

        time.sleep(0.8)
        if proc.poll() is None:
            print("Recording capture method: primary-desktop")
            return proc

        raise RuntimeError(
            f"ffmpeg failed to start recording (exit code {proc.returncode}). "
            f"See log: {ffmpeg_log_file}"
        )
    finally:
        log_handle.close()


def _get_primary_desktop_region() -> Tuple[int, int, int, int]:
    user32 = ctypes.windll.user32
    width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    height = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    return (0, 0, width, height)


def _position_vscode_on_primary(title_hint: str) -> None:
    user32 = ctypes.windll.user32

    hwnd = None
    # Allow window creation/render latency and only target the demo workspace window.
    for _ in range(12):
        hwnd = _find_vscode_window_hwnd(title_hint, strict_workspace=True)
        if hwnd is not None:
            break
        time.sleep(0.2)

    if hwnd is None:
        return

    width = user32.GetSystemMetrics(0)   # SM_CXSCREEN
    height = user32.GetSystemMetrics(1)  # SM_CYSCREEN

    SW_RESTORE = 9
    SW_MAXIMIZE = 3
    SWP_NOZORDER = 0x0004
    SWP_SHOWWINDOW = 0x0040

    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(hwnd, 0, 0, 0, width, height, SWP_NOZORDER | SWP_SHOWWINDOW)
    user32.ShowWindow(hwnd, SW_MAXIMIZE)


def _find_vscode_window_hwnd(title_hint: str, strict_workspace: bool = False) -> int | None:
    user32 = ctypes.windll.user32
    title_hint_l = title_hint.lower()
    workspace_hint = title_hint_l.split(" - ", 1)[0]
    found: dict[str, int | None] = {"exact": None, "fallback": None}

    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    @enum_proc
    def _callback(hwnd: int, lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value.lower()
        if "visual studio code" not in title:
            return True

        if strict_workspace and workspace_hint not in title and title_hint_l not in title:
            return True

        if found["fallback"] is None:
            found["fallback"] = hwnd

        if workspace_hint in title or title_hint_l in title:
            found["exact"] = hwnd
            return False

        return True

    for _ in range(10):
        user32.EnumWindows(_callback, 0)
        if found["exact"] is not None:
            return int(found["exact"])
        if found["fallback"] is not None:
            return int(found["fallback"])
        time.sleep(0.15)

    return None


def _close_vscode_window(title_hint: str) -> None:
    hwnd = _find_vscode_window_hwnd(title_hint, strict_workspace=True)
    if hwnd is not None:
        # WM_CLOSE
        ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
        time.sleep(0.4)

    # Fallback close path when window title changed and HWND matching missed.
    workspace_hint = title_hint.split(" - ", 1)[0]
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"if ($ws.AppActivate('{workspace_hint}')) {{ $ws.SendKeys('%{{F4}}') }}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _activate_vscode_window(title_hint: str) -> None:
    activated = False

    hwnd = _find_vscode_window_hwnd(title_hint, strict_workspace=True)
    if hwnd is not None:
        user32 = ctypes.windll.user32
        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        activated = True

    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$ok = $ws.AppActivate('{title_hint}'); "
        "if (-not $ok) { Start-Sleep -Milliseconds 50; $null = $ws.AppActivate('Visual Studio Code') }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Let focus settle before sending keystrokes for the next step.
    if activated:
        time.sleep(0.08)


def _prepare_clean_view_shortcuts() -> None:
    # Use native VS Code shortcuts to reduce clutter in the recording window.
    # Ctrl+B toggles Side Bar, Ctrl+J toggles panel, Ctrl+Shift+P opens command palette.
    import pyautogui

    pyautogui.press("escape")
    time.sleep(0.1)

    pyautogui.hotkey("ctrl", "b")
    time.sleep(0.2)

    pyautogui.hotkey("ctrl", "j")
    time.sleep(0.2)

    # Hide activity/status bars via commands for a cleaner code-only look.
    pyautogui.hotkey("ctrl", "shift", "p")
    time.sleep(0.3)
    pyautogui.write("View: Toggle Activity Bar Visibility", interval=0.01)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.25)

    pyautogui.hotkey("ctrl", "shift", "p")
    time.sleep(0.3)
    pyautogui.write("View: Toggle Status Bar Visibility", interval=0.01)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.25)

    # Open Explorer view and focus editor area.
    pyautogui.hotkey("ctrl", "shift", "e")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "1")
    time.sleep(0.2)


def _focus_keeper(stop_event: threading.Event, title_hint: str, interval_seconds: float = 0.7) -> None:
    while not stop_event.is_set():
        _activate_vscode_window(title_hint)
        stop_event.wait(interval_seconds)


def _is_escape_pressed() -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000)


def _check_abort() -> None:
    if _is_escape_pressed():
        raise KeyboardInterrupt("Playback aborted by ESC key")


def _open_file_in_vscode(file_path: Path) -> None:
    code_path = _ensure_tool("code")
    subprocess.run(
        [code_path, "-r", "-g", f"{file_path}:1"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_plan_stable(plan: Dict, workspace_dir: Path, title_hint: str) -> None:
    steps = plan.get("steps", [])
    print(f"\nDemo: {plan.get('title', 'Untitled')}")
    print(f"Steps: {len(steps)}")
    print("\nStable mode: deterministic file writes + visual file opening in VS Code")

    output_dir = workspace_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, step in enumerate(steps, 1):
        _check_abort()
        _activate_vscode_window(title_hint)

        action = step.get("action")
        if action == "create_file":
            rel_name = step["filename"]
            target = output_dir / rel_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(step.get("content", ""), encoding="utf-8")
            print(f"[{idx}/{len(steps)}] create_file  {rel_name}")
            _open_file_in_vscode(target)
            time.sleep(1.0)
        elif action == "run_command":
            command = step.get("command", "")
            print(f"[{idx}/{len(steps)}] run_command   {command}")
            subprocess.run(
                command,
                shell=True,
                cwd=workspace_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.8)
        elif action == "pause":
            secs = int(step.get("seconds", 2))
            print(f"[{idx}/{len(steps)}] pause         {secs}s")
            for _ in range(secs):
                _check_abort()
                time.sleep(1)
        else:
            print(f"[{idx}/{len(steps)}] unknown action '{action}', skipping")

    print("\nDemo playback complete!")


def _run_plan_stable_with_hook(
    plan: Dict,
    workspace_dir: Path,
    title_hint: str,
    post_step_hook: Callable[[dict, int, int], None] | None = None,
) -> None:
    steps = plan.get("steps", [])
    print(f"\nDemo: {plan.get('title', 'Untitled')}")
    print(f"Steps: {len(steps)}")
    print("\nStable mode: deterministic file writes + visual file opening in VS Code")

    output_dir = workspace_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for idx, step in enumerate(steps, 1):
        _check_abort()
        _activate_vscode_window(title_hint)

        action = step.get("action")
        if action == "create_file":
            rel_name = step["filename"]
            target = output_dir / rel_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(step.get("content", ""), encoding="utf-8")
            print(f"[{idx}/{len(steps)}] create_file  {rel_name}")
            _open_file_in_vscode(target)
            time.sleep(1.0)
        elif action == "run_command":
            command = step.get("command", "")
            print(f"[{idx}/{len(steps)}] run_command   {command}")
            subprocess.run(
                command,
                shell=True,
                cwd=workspace_dir,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.8)
        elif action == "pause":
            secs = int(step.get("seconds", 2))
            print(f"[{idx}/{len(steps)}] pause         {secs}s")
            for _ in range(secs):
                _check_abort()
                time.sleep(1)
        else:
            print(f"[{idx}/{len(steps)}] unknown action '{action}', skipping")

        if post_step_hook:
            post_step_hook(step, idx, len(steps))

    print("\nDemo playback complete!")


def _save_primary_desktop_screenshot(target_file: Path) -> None:
    import pyautogui

    target_file.parent.mkdir(parents=True, exist_ok=True)
    image = pyautogui.screenshot()
    image.save(target_file)


def _count_create_file_steps(plan: Dict) -> int:
    return sum(1 for step in plan.get("steps", []) if step.get("action") == "create_file")


def _build_screenshot_post_step_hook(
    plan: Dict,
    captures_dir: Path,
    title_hint: str,
) -> Callable[[dict, int, int], None]:
    create_file_total = _count_create_file_steps(plan)
    create_file_index = 0

    def _post_step_hook(step: dict, idx: int, total: int) -> None:
        nonlocal create_file_index
        if step.get("action") != "create_file":
            return

        create_file_index += 1
        filename = _sanitize_for_filename(step.get("filename", f"step-{idx}"))
        screenshot_file = captures_dir / f"{create_file_index:02d}_{filename}.png"

        # Keep the active editor visible before taking the screenshot.
        _activate_vscode_window(title_hint)
        time.sleep(0.25)
        _save_primary_desktop_screenshot(screenshot_file)
        print(
            f"      screenshot {create_file_index}/{create_file_total}: "
            f"{screenshot_file.name}"
        )

    return _post_step_hook


def run_screenshot_play(
    plan: Dict,
    speed: float,
    countdown: int,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    session_dir: Path | None = None,
    artifact_dir: Path | None = None,
    screenshots_dir: str | None = None,
    plan_file_name: str | None = None,
    scenario_name: str | None = None,
) -> Tuple[Path, Path]:
    _enable_dpi_awareness()

    root = Path.cwd()
    if session_dir is None:
        session_dir = _create_session_dir(root)
    else:
        session_dir.mkdir(parents=True, exist_ok=True)

    if artifact_dir is None:
        artifact_dir = session_dir / (scenario_name or "play")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    save_plan(plan, artifact_dir / (plan_file_name or "plan.json"))

    workspace_dir = _prepare_demo_workspace(session_dir)
    captures_dir = Path(screenshots_dir) if screenshots_dir else artifact_dir / "screenshots"
    captures_dir.mkdir(parents=True, exist_ok=True)

    title_hint = f"{workspace_dir.name} - Visual Studio Code"
    post_step_hook = _build_screenshot_post_step_hook(
        plan=plan,
        captures_dir=captures_dir,
        title_hint=title_hint,
    )

    try:
        _launch_vscode_window(workspace_dir)
        time.sleep(2.5)
        _activate_vscode_window(title_hint)
        _position_vscode_on_primary(title_hint)
        time.sleep(0.5)
        if clean_view:
            _prepare_clean_view_shortcuts()

        previous_cwd = Path.cwd()
        focus_stop = threading.Event()
        focus_thread = None
        if focus_lock:
            focus_thread = threading.Thread(
                target=_focus_keeper,
                args=(focus_stop, title_hint),
                daemon=True,
            )
            focus_thread.start()

        try:
            os.chdir(workspace_dir)
            if mode == "typing":
                play_demo(
                    plan,
                    char_delay=speed,
                    countdown=countdown,
                    pre_step_hook=(lambda: _activate_vscode_window(title_hint)),
                    post_step_hook=post_step_hook,
                )
            else:
                _run_plan_stable_with_hook(
                    plan,
                    workspace_dir,
                    title_hint,
                    post_step_hook=post_step_hook,
                )
        finally:
            focus_stop.set()
            if focus_thread is not None:
                focus_thread.join(timeout=1)
            os.chdir(previous_cwd)
    finally:
        _close_vscode_window(title_hint)

    return workspace_dir, captures_dir


def _stop_recording(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return

    try:
        if proc.stdin:
            proc.stdin.write(b"q\n")
            proc.stdin.flush()
    except Exception:
        proc.terminate()
    finally:
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def run_recorded_play(
    plan: Dict,
    speed: float,
    countdown: int,
    video_format: str,
    resolution: str,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    session_dir: Path | None = None,
    artifact_dir: Path | None = None,
    video_file: str | None = None,
    capture_screenshots: bool = False,
    screenshots_dir: str | None = None,
    plan_file_name: str | None = None,
    scenario_name: str | None = None,
) -> Tuple[Path, Path, Path | None]:
    _enable_dpi_awareness()

    root = Path.cwd()
    if session_dir is None:
        session_dir = _create_session_dir(root)
    else:
        session_dir.mkdir(parents=True, exist_ok=True)

    if artifact_dir is None:
        artifact_dir = session_dir / (scenario_name or "play")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    save_plan(plan, artifact_dir / (plan_file_name or "plan.json"))

    workspace_dir = _prepare_demo_workspace(session_dir)

    suffix = ".mp4" if video_format == "mp4" else ".webm"
    recording_file = Path(video_file) if video_file else artifact_dir / f"playback-{_timestamp()}{suffix}"
    ffmpeg_log_file = artifact_dir / "ffmpeg.log"
    captures_dir: Path | None = None

    title_hint = f"{workspace_dir.name} - Visual Studio Code"
    post_step_hook: Callable[[dict, int, int], None] | None = None
    if capture_screenshots:
        captures_dir = Path(screenshots_dir) if screenshots_dir else artifact_dir / "screenshots"
        captures_dir.mkdir(parents=True, exist_ok=True)
        post_step_hook = _build_screenshot_post_step_hook(
            plan=plan,
            captures_dir=captures_dir,
            title_hint=title_hint,
        )

    try:
        _launch_vscode_window(workspace_dir)
        time.sleep(2.5)
        _activate_vscode_window(title_hint)
        _position_vscode_on_primary(title_hint)
        time.sleep(0.5)
        if clean_view:
            _prepare_clean_view_shortcuts()

        rec_proc = _start_recording(
            recording_file,
            resolution=resolution,
            ffmpeg_log_file=ffmpeg_log_file,
        )
        previous_cwd = Path.cwd()
        focus_stop = threading.Event()
        focus_thread = None
        if focus_lock:
            focus_thread = threading.Thread(
                target=_focus_keeper,
                args=(focus_stop, title_hint),
                daemon=True,
            )
            focus_thread.start()
        try:
            os.chdir(workspace_dir)
            if mode == "typing":
                play_demo(
                    plan,
                    char_delay=speed,
                    countdown=countdown,
                    pre_step_hook=(lambda: _activate_vscode_window(title_hint)),
                    post_step_hook=post_step_hook,
                )
            else:
                if post_step_hook:
                    _run_plan_stable_with_hook(
                        plan,
                        workspace_dir,
                        title_hint,
                        post_step_hook=post_step_hook,
                    )
                else:
                    _run_plan_stable(plan, workspace_dir, title_hint)
        finally:
            focus_stop.set()
            if focus_thread is not None:
                focus_thread.join(timeout=1)
            _stop_recording(rec_proc)
            os.chdir(previous_cwd)
    finally:
        _close_vscode_window(title_hint)

    if not recording_file.exists() or recording_file.stat().st_size == 0:
        raise RuntimeError(
            f"Recording file was not created correctly: {recording_file}. "
            f"Check ffmpeg log: {ffmpeg_log_file}"
        )

    return workspace_dir, recording_file, captures_dir


def generate_and_record(
    scenario: str,
    prompt: str,
    speed: float,
    countdown: int,
    video_format: str,
    resolution: str,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    plan_path: str | None = None,
    video_file: str | None = None,
) -> Tuple[Path, Path, Path]:
    plan = build_plan_for_scenario(scenario, prompt)

    root = Path.cwd()
    session_dir = _create_session_dir(root)
    scenario_dir = session_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    trace_plan_file = scenario_dir / _default_plan_name(scenario)
    plan_file = Path(plan_path) if plan_path else trace_plan_file
    save_plan(plan, plan_file)
    if plan_file != trace_plan_file:
        save_plan(plan, trace_plan_file)

    workspace_dir, recording_file, _captures_dir = run_recorded_play(
        plan=plan,
        speed=speed,
        countdown=countdown,
        video_format=video_format,
        resolution=resolution,
        mode=mode,
        clean_view=clean_view,
        focus_lock=focus_lock,
        session_dir=session_dir,
        artifact_dir=scenario_dir,
        video_file=video_file,
    )
    return plan_file, workspace_dir, recording_file


def run_capture_play(
    plan: Dict,
    capture_mode: str,
    speed: float,
    countdown: int,
    video_format: str,
    resolution: str,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    session_dir: Path | None = None,
    artifact_dir: Path | None = None,
    video_file: str | None = None,
    screenshots_dir: str | None = None,
    plan_file_name: str | None = None,
    scenario_name: str | None = None,
) -> Tuple[Path, Path | None, Path | None]:
    if capture_mode == "screenshots":
        workspace_dir, captures_dir = run_screenshot_play(
            plan=plan,
            speed=speed,
            countdown=countdown,
            mode=mode,
            clean_view=clean_view,
            focus_lock=focus_lock,
            session_dir=session_dir,
            artifact_dir=artifact_dir,
            screenshots_dir=screenshots_dir,
            plan_file_name=plan_file_name,
            scenario_name=scenario_name,
        )
        return workspace_dir, None, captures_dir

    workspace_dir, recording_file, captures_dir = run_recorded_play(
        plan=plan,
        speed=speed,
        countdown=countdown,
        video_format=video_format,
        resolution=resolution,
        mode=mode,
        clean_view=clean_view,
        focus_lock=focus_lock,
        session_dir=session_dir,
        artifact_dir=artifact_dir,
        video_file=video_file,
        capture_screenshots=(capture_mode == "both"),
        screenshots_dir=screenshots_dir,
        plan_file_name=plan_file_name,
        scenario_name=scenario_name,
    )
    return workspace_dir, recording_file, captures_dir


def generate_and_capture(
    scenario: str,
    prompt: str,
    capture_mode: str,
    speed: float,
    countdown: int,
    video_format: str,
    resolution: str,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    plan_path: str | None = None,
    video_file: str | None = None,
    screenshots_dir: str | None = None,
) -> Tuple[Path, Path, Path | None, Path | None]:
    plan = build_plan_for_scenario(scenario, prompt)

    root = Path.cwd()
    session_dir = _create_session_dir(root)
    scenario_dir = session_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    trace_plan_file = scenario_dir / _default_plan_name(scenario)
    plan_file = Path(plan_path) if plan_path else trace_plan_file
    save_plan(plan, plan_file)
    if plan_file != trace_plan_file:
        save_plan(plan, trace_plan_file)

    workspace_dir, recording_file, captures_dir = run_capture_play(
        plan=plan,
        capture_mode=capture_mode,
        speed=speed,
        countdown=countdown,
        video_format=video_format,
        resolution=resolution,
        mode=mode,
        clean_view=clean_view,
        focus_lock=focus_lock,
        session_dir=session_dir,
        artifact_dir=scenario_dir,
        video_file=video_file,
        screenshots_dir=screenshots_dir,
    )
    return plan_file, workspace_dir, recording_file, captures_dir


def generate_and_screenshot(
    scenario: str,
    prompt: str,
    speed: float,
    countdown: int,
    mode: str,
    clean_view: bool = False,
    focus_lock: bool = True,
    plan_path: str | None = None,
    screenshots_dir: str | None = None,
) -> Tuple[Path, Path, Path]:
    plan = build_plan_for_scenario(scenario, prompt)

    root = Path.cwd()
    session_dir = _create_session_dir(root)
    scenario_dir = session_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)

    trace_plan_file = scenario_dir / _default_plan_name(scenario)
    plan_file = Path(plan_path) if plan_path else trace_plan_file
    save_plan(plan, plan_file)
    if plan_file != trace_plan_file:
        save_plan(plan, trace_plan_file)

    workspace_dir, captures_dir = run_screenshot_play(
        plan=plan,
        speed=speed,
        countdown=countdown,
        mode=mode,
        clean_view=clean_view,
        focus_lock=focus_lock,
        session_dir=session_dir,
        artifact_dir=scenario_dir,
        screenshots_dir=screenshots_dir,
    )
    return plan_file, workspace_dir, captures_dir
