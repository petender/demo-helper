# demo-helper

Turn written descriptions into auto-typed VS Code demos for screen recording.

## Setup

1. Clone the repo and install dependencies:

   ```bash
   pip install openai pyautogui
   ```

2. Copy `.env.example` to `.env` and add your OpenAI API key:

   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```

## Usage

### Plan a demo

Generate a step-by-step plan from a description:

```bash
demo-helper plan "Intro to Python list comprehensions"
```

This saves a `plan.json` file. Use `-o` to specify a different output path.

### Play a demo

Replay a saved plan in VS Code:

```bash
demo-helper play plan.json
```

Options:
- `--speed` — seconds between characters (default: 0.03)
- `--countdown` — seconds before playback starts (default: 5)

### Plan and play in one step

```bash
demo-helper run "Intro to Python list comprehensions"
```

Options:
- `--speed` — seconds between characters (default: 0.03)
- `--countdown` — seconds before playback starts (default: 5)
- `--save-plan` — also save the generated plan to a file

## Output

All files created during playback are written to an `output/` folder in the current directory.

## Tips

- Switch focus to VS Code during the countdown.
- Move the mouse to any screen corner to abort playback at any time.
