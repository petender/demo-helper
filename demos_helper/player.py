import time
from pathlib import Path
from typing import Callable
import shutil
import subprocess

import pyautogui

try:
    import ctypes
except ImportError:  # pragma: no cover
    ctypes = None

# Move mouse to any screen corner to abort at any time.
pyautogui.FAILSAFE = True
# Minimal built-in pause; we handle timing ourselves.
pyautogui.PAUSE = 0.01

DEFAULT_CHAR_DELAY = 0.03   # seconds between characters
DEFAULT_LINE_DELAY = 0.30   # extra pause after each newline
DEFAULT_COUNTDOWN = 5        # seconds before playback starts


def _is_escape_pressed() -> bool:
    if ctypes is None:
        return False
    # High-order bit indicates key is currently down.
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000)


def _check_abort() -> None:
    if _is_escape_pressed():
        raise KeyboardInterrupt("Playback aborted by ESC key")


def play_demo(
    plan: dict,
    char_delay: float = DEFAULT_CHAR_DELAY,
    line_delay: float = DEFAULT_LINE_DELAY,
    countdown: int = DEFAULT_COUNTDOWN,
    pre_step_hook: Callable[[], None] | None = None,
) -> None:
    """Execute a demo plan by simulating typing in VS Code."""
    title = plan.get("title", "Untitled")
    steps = plan["steps"]

    print(f"\nDemo: {title}")
    print(f"Steps: {len(steps)}")
    print(f"\nSwitch to VS Code now!  Starting in {countdown} seconds...")
    print("(Press ESC or move mouse to any screen corner to abort)\n")

    for i in range(countdown, 0, -1):
        _check_abort()
        print(f"  {i}...")
        time.sleep(1)
    print("  Go!\n")

    for idx, step in enumerate(steps, 1):
        _check_abort()
        if pre_step_hook:
            pre_step_hook()
        action = step["action"]
        if action == "create_file":
            print(f"[{idx}/{len(steps)}] create_file  {step['filename']}")
            _create_file(step["filename"], step["content"],
                         char_delay, line_delay)
        elif action == "run_command":
            print(f"[{idx}/{len(steps)}] run_command   {step['command']}")
            _run_command(step["command"], char_delay)
        elif action == "pause":
            secs = step.get("seconds", 2)
            print(f"[{idx}/{len(steps)}] pause         {secs}s")
            time.sleep(secs)
        else:
            print(f"[{idx}/{len(steps)}] unknown action '{action}', skipping")

    print("\nDemo playback complete!")


# ── helpers ──────────────────────────────────────────────────────────


def _type_text(text: str, char_delay: float, line_delay: float) -> None:
    """Type *text* character-by-character into the focused VS Code editor."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        _check_abort()
        for ch in line:
            _check_abort()
            if ch == "\t":
                pyautogui.press("tab")
            else:
                pyautogui.write(ch, interval=0)
            time.sleep(char_delay)

        if i < len(lines) - 1:
            # Dismiss autocomplete before pressing Enter
            pyautogui.press("escape")
            time.sleep(0.05)
            pyautogui.press("enter")
            time.sleep(line_delay)
            # Remove any auto-indentation so we control whitespace
            pyautogui.press("home")
            time.sleep(0.02)
            pyautogui.hotkey("shift", "end")
            time.sleep(0.02)
            pyautogui.press("delete")
            time.sleep(0.02)


def _create_file(
    filename: str,
    content: str,
    char_delay: float,
    line_delay: float,
) -> None:
    """Create *filename* in VS Code: new file → auto-type content → save."""
    path = Path("output") / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    # Open file without Ctrl-based shortcuts when possible.
    code_path = shutil.which("code")
    if code_path:
        subprocess.run(
            [code_path, "-r", "-g", f"{path}:1"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.8)
    else:
        # Fallback to Quick Open if VS Code CLI is not available.
        quick_open_path = str(path).replace("\\", "/")
        pyautogui.hotkey("ctrl", "p")
        time.sleep(0.6)
        pyautogui.write(quick_open_path, interval=0.03)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.8)

    _type_text(content, char_delay, line_delay)

    # Autosave may not flush immediately; poll briefly before fallback write.
    for _ in range(6):
        time.sleep(0.35)
        try:
            if path.read_text(encoding="utf-8") == content:
                return
        except OSError:
            pass

    # Final safety net so demos are never left with empty files.
    path.write_text(content, encoding="utf-8")


def _run_command(command: str, char_delay: float) -> None:
    """Focus the integrated terminal and execute *command*."""
    # Prefer command palette route to avoid Ctrl-based global shortcut conflicts.
    pyautogui.press("f1")
    time.sleep(0.25)
    pyautogui.write("Terminal: Focus Terminal", interval=0.01)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.5)

    _type_text(command, char_delay, line_delay=0)
    pyautogui.press("enter")
    time.sleep(1.0)
