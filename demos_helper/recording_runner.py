import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

from .csharp_planner import plan_csharp_demo
from .pipeline_planner import plan_pipeline_demo
from .planner import plan_demo
from .player import play_demo
from .sql_planner import plan_sql_demo


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
        "editor.minimap.enabled": False,
        "breadcrumbs.enabled": False,
        "workbench.activityBar.visible": False,
        "workbench.statusBar.visible": False,
        "extensions.ignoreRecommendations": True,
    }
    with open(settings_dir / "settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

    return workspace_dir


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


def _build_ffmpeg_cmd(video_file: Path, input_target: str, resolution: str) -> list[str]:
    ffmpeg_path = _ensure_tool("ffmpeg")
    width, height = resolution.lower().split("x", 1)
    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    )
    base = [
        ffmpeg_path,
        "-y",
        "-f",
        "gdigrab",
        "-framerate",
        "30",
        "-i",
        input_target,
        "-vf",
        scale_filter,
    ]

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
    window_titles: list[str],
    resolution: str,
) -> subprocess.Popen:
    _ensure_tool("ffmpeg")
    video_file.parent.mkdir(parents=True, exist_ok=True)

    # Desktop capture is more reliable on Windows than title-based capture,
    # which can produce black frames depending on window composition state.
    desktop_cmd = _build_ffmpeg_cmd(video_file, "desktop", resolution)
    return subprocess.Popen(
        desktop_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


def _activate_vscode_window(title_hint: str) -> None:
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"if (-not $ws.AppActivate('{title_hint}')) {{ $null = $ws.AppActivate('Visual Studio Code') }}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _focus_keeper(stop_event: threading.Event, title_hint: str, interval_seconds: float = 0.7) -> None:
    while not stop_event.is_set():
        _activate_vscode_window(title_hint)
        stop_event.wait(interval_seconds)


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
    video_file: str | None = None,
) -> Tuple[Path, Path]:
    root = Path.cwd()
    session_dir = root / "recordings" / f"session-{_timestamp()}"
    session_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = _prepare_demo_workspace(session_dir)

    suffix = ".mp4" if video_format == "mp4" else ".webm"
    recording_file = Path(video_file) if video_file else session_dir / f"playback-{_timestamp()}{suffix}"

    _launch_vscode_window(workspace_dir)
    time.sleep(2.5)
    title_hint = f"{workspace_dir.name} - Visual Studio Code"
    _activate_vscode_window(title_hint)
    time.sleep(0.5)

    window_titles = [
        title_hint,
        "Visual Studio Code",
    ]
    rec_proc = _start_recording(
        recording_file,
        window_titles=window_titles,
        resolution=resolution,
    )
    previous_cwd = Path.cwd()
    focus_stop = threading.Event()
    focus_thread = threading.Thread(
        target=_focus_keeper,
        args=(focus_stop, title_hint),
        daemon=True,
    )
    focus_thread.start()
    try:
        os.chdir(workspace_dir)
        play_demo(
            plan,
            char_delay=speed,
            countdown=countdown,
            pre_step_hook=lambda: _activate_vscode_window(title_hint),
        )
    finally:
        focus_stop.set()
        focus_thread.join(timeout=1)
        _stop_recording(rec_proc)
        os.chdir(previous_cwd)

    return workspace_dir, recording_file


def generate_and_record(
    scenario: str,
    prompt: str,
    speed: float,
    countdown: int,
    video_format: str,
    resolution: str,
    plan_path: str | None = None,
    video_file: str | None = None,
) -> Tuple[Path, Path, Path]:
    plan = build_plan_for_scenario(scenario, prompt)

    plan_file = Path(plan_path) if plan_path else Path(_default_plan_name(scenario))
    save_plan(plan, plan_file)

    workspace_dir, recording_file = run_recorded_play(
        plan=plan,
        speed=speed,
        countdown=countdown,
        video_format=video_format,
        resolution=resolution,
        video_file=video_file,
    )
    return plan_file, workspace_dir, recording_file
