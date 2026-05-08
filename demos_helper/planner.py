import json

from openai import OpenAI

from scene_helper.config import OPENAI_API_KEY

SYSTEM_PROMPT = """\
You are a VS Code demo planner. Given a written description of a topic, \
create a step-by-step coding demo plan that will be auto-typed in VS Code \
and screen recorded for educational purposes.

Output a JSON object with this exact structure:
{
  "title": "Short descriptive title",
  "steps": [
    {"action": "create_file", "filename": "01_topic.py", "content": "..."},
    {"action": "run_command", "command": "python 01_topic.py"},
    {"action": "pause", "seconds": 3}
  ]
}

Available actions:
- "create_file": Opens a new file in VS Code, auto-types the content \
character by character, and saves it.  Fields: filename, content.
- "run_command": Types and executes a command in the VS Code integrated \
terminal.  Fields: command.
- "pause": Waits for a number of seconds so viewers can read output.  \
Fields: seconds (integer).

Guidelines:
- Break the topic into logical segments, one concept per file.
- Number filenames sequentially: 01_name.py, 02_name.py, etc.
- Keep each file short (10-25 lines) with clear inline comments.
- Use descriptive print() statements so terminal output is self-explanatory.
- After each file, add a run_command to execute it and a pause (3-5 s) for \
viewers to read output.
- If external packages are needed, add a run_command with pip install as \
the very first step followed by a pause.
- Code must be correct, runnable, and educational.
- Add a 2-3 second pause between major segments.
- Do not include markdown, explanation, or anything outside the JSON object.
"""


def plan_demo(description: str) -> dict:
    """Use OpenAI to break a written description into a demo plan."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    return json.loads(response.choices[0].message.content)
