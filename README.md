# demo-helper

Turn plain-language prompts into auto-typed VS Code demos.

This repo now supports:
- Python demo planning and playback
- SQL demo planning and playback
- Visual-only SQL mode (no database execution)
- C#/.NET demo planning and playback
- Azure DevOps YAML pipeline demo planning and playback
- GitHub Actions YAML pipeline demo planning and playback
- Clean-window playback recording (mp4/webm)

## Who This Is For

If you are not technical, follow this README top to bottom exactly and copy/paste commands as-is.

## What You Need (Windows)

1. Python 3.10+
2. VS Code
3. PowerShell
4. Azure OpenAI / Foundry access
5. Optional for real SQL execution:
   - SQL Server instance (local or remote)
   - `sqlcmd`
6. Optional for standalone desktop GUI mode:
   - `gradio` Python package
   - `ffmpeg` on PATH (for webm/mp4 recording)

## Important Folder Rule

Run commands from the repository root:

`C:\demo-helper`

If you run commands from another folder (for example inside `.venv\Scripts`), imports can fail.

## 1. First-Time Setup

### Step 1: Open PowerShell in the repo root

```powershell
Set-Location C:\demo-helper
```

### Step 2: Create virtual environment (if needed)

If the virtual environment already exists, you can skip this.

```powershell
python -m venv .\demos_helper\.venv
```

### Step 3: Activate virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& .\demos_helper\.venv\Scripts\Activate.ps1
```

### Step 4: Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install openai pyautogui python-dotenv runwayml httpx
```

If you also want the standalone desktop GUI mode later:

```powershell
python -m pip install gradio
```

### Step 5: Install bundled `scene-helper` package (required)

This step is required for `demos_helper` to import shared config.

```powershell
Set-Location .\demos_helper\scene-helper
python -m pip install -e .
Set-Location ..\..
```

## 2. Configure Azure OpenAI / Foundry

Create or edit the root `.env` file at `C:\demo-helper\.env`.

Use this template:

```env
OPENAI_API_KEY=your-azure-openai-key
OPENAI_BASE_URL=https://pdtopenai.openai.azure.com/openai/v1/
OPENAI_CHAT_MODEL=gpt-4.1-mini
RUNWAYML_API_SECRET=your-runway-key-if-needed
```

### Field meanings

1. `OPENAI_API_KEY`
   - Your Azure OpenAI key.
2. `OPENAI_BASE_URL`
   - Azure endpoint in v1 format.
   - Use: `https://pdtopenai.openai.azure.com/openai/v1/`
3. `OPENAI_CHAT_MODEL`
   - Must be your Azure deployment name.
   - In your environment, this is `gpt-4.1-mini`.

If deployment name and model variable do not match, you can get 404 errors.

## 3. Quick Validation

```powershell
python -m demos_helper.cli --help
python -c "from scene_helper.config import OPENAI_BASE_URL, OPENAI_CHAT_MODEL; print(OPENAI_BASE_URL); print(OPENAI_CHAT_MODEL)"
```

Expected output should show your Azure URL and deployment name.

## 4. Python Demo Flow

### Create a plan file

```powershell
python -m demos_helper.cli plan "Intro to Python list comprehensions"
```

This creates `plan.json`.

### Play the plan

```powershell
python -m demos_helper.cli play plan.json
```

### One command: plan + play

```powershell
python -m demos_helper.cli run "Intro to Python list comprehensions"
```

### Optional playback tuning

```powershell
python -m demos_helper.cli play plan.json --countdown 8 --speed 0.02
```

## 5. SQL Demo Flow

### Create a SQL plan

```powershell
python -m demos_helper.cli sql-plan "Create a demo that builds a Sales table and inserts sample rows"
```

This creates `sqlplan.json`.

### Play SQL plan

```powershell
python -m demos_helper.cli play sqlplan.json
```

### One command: SQL plan + play

```powershell
python -m demos_helper.cli sql-run "Create a demo that builds a Sales table and inserts sample rows"
```

## 6. SQL Visual-Only Mode (No Database Needed)

If you do not have SQL Server ready yet, use visual-only mode.

### Create visual-only SQL plan

```powershell
python -m demos_helper.cli sql-plan --visual-only "Create a demo that builds a Sales table and inserts sample rows" -o sqlplan.visual.json
```

### Play visual-only SQL plan

```powershell
python -m demos_helper.cli play sqlplan.visual.json
```

This mode creates and types SQL files but avoids execution commands.

## 7. C#/.NET Demo Flow

### Create a C# plan

```powershell
python -m demos_helper.cli csharp-plan "Create a beginner C# demo that explains classes, properties, and methods" -o csharpplan.json
```

### Play C# plan

```powershell
python -m demos_helper.cli play csharpplan.json
```

### One command: C# plan + play

```powershell
python -m demos_helper.cli csharp-run "Create a beginner C# demo that explains classes, properties, and methods" --save-plan csharpplan.json
```

## 8. Azure DevOps YAML Pipeline Demo Flow

### Create an Azure DevOps plan

```powershell
python -m demos_helper.cli azdo-plan "Create an Azure DevOps pipeline for a .NET project with restore, build, test, and publish steps" -o azdoplan.json
```

### Play Azure DevOps plan

```powershell
python -m demos_helper.cli play azdoplan.json
```

### One command: Azure DevOps plan + play

```powershell
python -m demos_helper.cli azdo-run "Create an Azure DevOps pipeline for a .NET project with restore, build, test, and publish steps" --save-plan azdoplan.json
```

## 9. GitHub Actions YAML Pipeline Demo Flow

### Create a GitHub Actions plan

```powershell
python -m demos_helper.cli gha-plan "Create a GitHub Actions workflow for a .NET project with restore, build, test, and artifact upload" -o ghaplan.json
```

### Play GitHub Actions plan

```powershell
python -m demos_helper.cli play ghaplan.json
```

### One command: GitHub Actions plan + play

```powershell
python -m demos_helper.cli gha-run "Create a GitHub Actions workflow for a .NET project with restore, build, test, and artifact upload" --save-plan ghaplan.json
```

Each workflow creates its own separate plan file and can be played independently.

## 10. When You Want Real SQL Execution

For actual `CREATE TABLE` execution, you need:

1. A running SQL Server instance (or LocalDB)
2. `sqlcmd` installed

Typical command inside a plan step:

```powershell
sqlcmd -S localhost -E -d master -i output\01_create_table.sql
```

If your instance is named, use that in `-S`, for example:
- `localhost\SQLEXPRESS`
- `(localdb)\MSSQLLocalDB`

## 11. Playback Tips

1. Open VS Code first.
2. Keep VS Code focused during countdown.
3. Move mouse to any screen corner to emergency-stop playback.
4. Generated files are created in an `output` folder.

## 12. Presentation Recording (Clean VS Code Window)

If you want presentation-quality output with minimal clutter:
1. Use `record-play` to record an existing plan
2. Or use `record-run` to generate + play + record in one command

What these commands do:
1. Open a fresh VS Code window on a separate demo-only workspace
2. Use your current VS Code user environment (no separate profile)
3. Start recording right before playback
4. Stop recording immediately after playback
5. Export video at a fixed output size (default `1920x1280`)
6. Keep refocusing VS Code during playback to reduce interruptions

### Record an existing plan

```powershell
python -m demos_helper.cli record-play azdoplan.json --format mp4 --countdown 8
```

### Generate + record in one command

```powershell
python -m demos_helper.cli record-run azdo "Create a multi-stage Azure DevOps pipeline for a .NET app" --format mp4 --countdown 8
```

Scenario values for `record-run`:
1. `python`
2. `sql`
3. `sql-visual`
4. `csharp`
5. `azdo`
6. `gha`

Optional parameters:
1. `--plan-file <path>`
2. `--video-file <path>`
3. `--speed 0.02`
4. `--format webm`
5. `--resolution 1920x1280`

Stop controls during playback:
1. Press `Esc` to abort immediately
2. Mouse-corner failsafe is also enabled via pyautogui
3. On cancel, the command exits cleanly with no automatic restart

## 13. Troubleshooting (Most Common)

### Error: `ModuleNotFoundError: No module named 'demos_helper'`

Cause: command was run from the wrong folder.

Fix:

```powershell
Set-Location C:\demo-helper
python -m demos_helper.cli --help
```

### Error: 404 from Azure OpenAI

Usually one of these:

1. `OPENAI_BASE_URL` missing `/openai/v1/`
2. `OPENAI_CHAT_MODEL` does not match Azure deployment name

Fix `.env` values and retry.

### Error: 401 Authentication

Your `OPENAI_API_KEY` is invalid for that Azure resource, or expired.

### SQL plan plays but commands fail

You can still play typing steps without SQL Server.
For execution, install/start SQL Server and verify `sqlcmd` target instance.

### Agent UI says ffmpeg is missing

Install ffmpeg and make sure `ffmpeg` is available in PATH.

### Record commands fail with "code is required"

Install VS Code CLI and ensure `code` is on PATH.

## 14. Copilot Chat Guided Mode (Recommended)

Use Copilot Chat as the interactive interface.

Suggested flow in chat:
1. Pick scenario: Python, SQL, SQL Visual Only, C# .NET, Azure DevOps YAML, or GitHub Actions YAML
2. Enter your prompt
3. Confirm plan generation
4. Confirm playback
5. Optionally request recording guidance

Scenario to command mapping:
1. Python -> python -m demos_helper.cli plan "<prompt>" -o plan.json
2. SQL -> python -m demos_helper.cli sql-plan "<prompt>" -o sqlplan.json
3. SQL Visual Only -> python -m demos_helper.cli sql-plan --visual-only "<prompt>" -o sqlplan.visual.json
4. C# .NET -> python -m demos_helper.cli csharp-plan "<prompt>" -o csharpplan.json
5. Azure DevOps YAML -> python -m demos_helper.cli azdo-plan "<prompt>" -o azdoplan.json
6. GitHub Actions YAML -> python -m demos_helper.cli gha-plan "<prompt>" -o ghaplan.json
7. Play any plan -> python -m demos_helper.cli play "<plan file>"

## 15. Optional Standalone Desktop GUI Mode

If you still want a separate app interface, this project also includes one.

Launch:

```powershell
python -m demos_helper.cli agent-ui
```

Desktop GUI outputs:
1. Plan JSON files in plans/
2. Recordings in recordings/
