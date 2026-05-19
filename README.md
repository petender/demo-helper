# demo-helper

Create demo-ready VS Code typing videos from natural language prompts.

This repo supports:
- Python demos
- SQL demos
- SQL visual-only demos (no DB connection required)
- C# demos
- Azure DevOps YAML demos
- GitHub Actions YAML demos
- Primary-monitor MP4/WebM recording
- Primary-monitor screenshot capture (one image per `create_file` step)

## Recommended Usage: Agentic (Chat-First)

Use Copilot Chat as the main interface.

How it works:
1. You describe the scenario in chat.
2. The agent asks follow-up questions (scenario, filename, record/play, countdown).
3. The agent generates the plan.
4. The agent runs playback/recording for you.
5. You review the generated video from `recordings/session-*/`.

You do not need to run Python commands manually for normal usage.

## Prerequisites (Windows)

Required:
1. Python 3.10+
2. VS Code with `code` CLI available on PATH
3. PowerShell
4. ffmpeg available on PATH
5. Azure OpenAI/Foundry credentials

Optional:
1. `sqlcmd` and SQL Server (only for real SQL execution, not needed for visual-only SQL demos)
2. `gradio` (only for optional standalone GUI mode)

## One-Time Setup

From repo root (`C:\demo-helper`):

```powershell
python -m venv .\demos_helper\.venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\demos_helper\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install openai pyautogui python-dotenv runwayml httpx
Set-Location .\demos_helper\scene-helper
python -m pip install -e .
Set-Location ..\..
```

Create `.env` at repo root:

```env
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://<youropenairesource>.openai.azure.com/openai/v1/
OPENAI_CHAT_MODEL=gpt-4.1-mini
```

## Agentic Scenarios

The chat agent can run these scenarios end-to-end:
1. `python`
2. `sql`
3. `sql-visual`
4. `csharp`
5. `azdo`
6. `gha`

Plan file defaults:
1. `plan.json`
2. `sqlplan.json`
3. `sqlplan.visual.json`
4. `csharpplan.json`
5. `azdoplan.json`
6. `ghaplan.json`

When using agentic `record-run`, the plan is stored inside the session trace folder by default.

## Recording Behavior (Current Final)

Recording is optimized for reliability:
1. Opens a fresh demo VS Code window.
2. Moves/maximizes it on the primary monitor.
3. Captures primary desktop (scaled to requested output resolution).
4. Supports typing mode (default) and stable mode fallback.
5. Closes demo VS Code window on completion.

Recommended recording defaults:
- `--format mp4`
- `--resolution 1920x1280`
- `--no-focus-lock` when you want to keep using another monitor

## Minimal CLI Reference (Fallback)

Use these only if you explicitly want manual execution.

Generate plan:
```powershell
python -m demos_helper.cli <scenario>-plan "<prompt>"
```

Play plan:
```powershell
python -m demos_helper.cli play <plan-file>
```

Record existing plan:
```powershell
python -m demos_helper.cli record-play <plan-file> --format mp4 --countdown 8 --resolution 1920x1280 --no-focus-lock
```

Capture screenshots for an existing plan:
```powershell
python -m demos_helper.cli screenshot-play <plan-file> --countdown 8 --no-focus-lock
```

Generate and record in one command:
```powershell
python -m demos_helper.cli record-run <scenario> "<prompt>" --format mp4 --countdown 8 --resolution 1920x1280 --no-focus-lock
```

Generate and capture screenshots in one command:
```powershell
python -m demos_helper.cli screenshot-run <scenario> "<prompt>" --countdown 8 --no-focus-lock
```

## Output Locations

1. `record-play` outputs:
	- Scenario folder: `recordings/session-*/<plan-stem>/`
	- Plan snapshot: `recordings/session-*/<plan-stem>/<plan-file-name>.json`
	- Video: `recordings/session-*/<plan-stem>/playback-*.mp4`
	- Log: `recordings/session-*/<plan-stem>/ffmpeg.log`
2. `record-run` outputs (recommended trace layout):
	- Scenario folder: `recordings/session-*/<scenario>/`
	- Plan: `recordings/session-*/<scenario>/<default-plan-name>.json`
	- Video: `recordings/session-*/<scenario>/playback-*.mp4`
	- Log: `recordings/session-*/<scenario>/ffmpeg.log`
3. `screenshot-play` outputs:
	- Scenario folder: `recordings/session-*/<plan-stem>/`
	- Plan snapshot: `recordings/session-*/<plan-stem>/<plan-file-name>.json`
	- Screenshot folder: `recordings/session-*/<plan-stem>/screenshots/`
	- Images: `recordings/session-*/<plan-stem>/screenshots/01_<filename>.png`, `02_<filename>.png`, ...
4. `screenshot-run` outputs:
	- Scenario folder: `recordings/session-*/<scenario>/`
	- Plan: `recordings/session-*/<scenario>/<default-plan-name>.json`
	- Screenshot folder: `recordings/session-*/<scenario>/screenshots/`
	- Images: one PNG per `create_file` step
5. Demo workspace files (typed/generated files):
	- `recordings/session-*/demo-workspace/output/`
6. If you pass a custom `--plan-file`, that file is saved too, and a session trace copy is still kept under the scenario folder.

## Troubleshooting

`ModuleNotFoundError: demos_helper`
- Run from repo root: `C:\demo-helper`

Azure 404 errors
- Ensure `.env` uses `/openai/v1/` base URL and deployment name in `OPENAI_CHAT_MODEL`

`ffmpeg` or `code` not found
- Add them to PATH and reopen terminal

Need SQL demo without DB
- Use `sql-visual` scenario

## Optional Standalone GUI

Only if you want a separate app (not chat-first mode):

```powershell
python -m pip install gradio
python -m demos_helper.cli agent-ui
```
