import argparse
import json
import sys

try:
    from .agent_experience import launch_agent_gui
except ModuleNotFoundError:  # pragma: no cover
    launch_agent_gui = None
from .csharp_planner import plan_csharp_demo
from .planner import plan_demo
from .pipeline_planner import plan_pipeline_demo
from .player import play_demo
from .recording_runner import generate_and_record, run_recorded_play
from .sql_planner import plan_sql_demo


def main():
    parser = argparse.ArgumentParser(
        prog="demo-helper",
        description=(
            "Turn written descriptions into auto-typed VS Code demos "
            "for screen recording."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── plan ─────────────────────────────────────────────────────────
    plan_p = sub.add_parser(
        "plan", help="Generate a demo plan from a description",
    )
    plan_p.add_argument(
        "description", help="Written description of what to demo",
    )
    plan_p.add_argument(
        "-o", "--output", default="plan.json",
        help="Output file for the plan (default: plan.json)",
    )

    # ── sql-plan ─────────────────────────────────────────────────────
    sql_plan_p = sub.add_parser(
        "sql-plan", help="Generate a SQL demo plan from a description",
    )
    sql_plan_p.add_argument(
        "description", help="Written description of what SQL demo to create",
    )
    sql_plan_p.add_argument(
        "-o", "--output", default="sqlplan.json",
        help="Output file for the SQL plan (default: sqlplan.json)",
    )
    sql_plan_p.add_argument(
        "--visual-only",
        action="store_true",
        help="Generate a visual-only SQL plan (no run_command steps)",
    )

    # ── csharp-plan ──────────────────────────────────────────────────
    csharp_plan_p = sub.add_parser(
        "csharp-plan", help="Generate a C#/.NET demo plan from a description",
    )
    csharp_plan_p.add_argument(
        "description", help="Written description of what C# demo to create",
    )
    csharp_plan_p.add_argument(
        "-o", "--output", default="csharpplan.json",
        help="Output file for the C# plan (default: csharpplan.json)",
    )

    # ── azdo-plan ────────────────────────────────────────────────────
    azdo_plan_p = sub.add_parser(
        "azdo-plan", help="Generate an Azure DevOps YAML pipeline demo plan",
    )
    azdo_plan_p.add_argument(
        "description", help="Written description of what Azure DevOps pipeline demo to create",
    )
    azdo_plan_p.add_argument(
        "-o", "--output", default="azdoplan.json",
        help="Output file for the Azure DevOps plan (default: azdoplan.json)",
    )

    # ── gha-plan ─────────────────────────────────────────────────────
    gha_plan_p = sub.add_parser(
        "gha-plan", help="Generate a GitHub Actions YAML pipeline demo plan",
    )
    gha_plan_p.add_argument(
        "description", help="Written description of what GitHub Actions demo to create",
    )
    gha_plan_p.add_argument(
        "-o", "--output", default="ghaplan.json",
        help="Output file for the GitHub Actions plan (default: ghaplan.json)",
    )

    # ── play ─────────────────────────────────────────────────────────
    play_p = sub.add_parser(
        "play", help="Play a previously saved demo plan in VS Code",
    )
    play_p.add_argument(
        "plan_file", help="Path to a plan JSON file",
    )
    play_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    play_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )

    # ── run ──────────────────────────────────────────────────────────
    run_p = sub.add_parser(
        "run", help="Plan and immediately play a demo",
    )
    run_p.add_argument(
        "description", help="Written description of what to demo",
    )
    run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    run_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )
    run_p.add_argument(
        "--save-plan",
        help="Also save the generated plan to this file",
    )

    # ── sql-run ──────────────────────────────────────────────────────
    sql_run_p = sub.add_parser(
        "sql-run", help="Create and immediately play a SQL demo",
    )
    sql_run_p.add_argument(
        "description", help="Written description of what SQL demo to create",
    )
    sql_run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    sql_run_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )
    sql_run_p.add_argument(
        "--save-plan", default="sqlplan.json",
        help="Save generated SQL plan to this file (default: sqlplan.json)",
    )
    sql_run_p.add_argument(
        "--visual-only",
        action="store_true",
        help="Generate a visual-only SQL plan (no run_command steps)",
    )

    # ── csharp-run ───────────────────────────────────────────────────
    csharp_run_p = sub.add_parser(
        "csharp-run", help="Create and immediately play a C#/.NET demo",
    )
    csharp_run_p.add_argument(
        "description", help="Written description of what C# demo to create",
    )
    csharp_run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    csharp_run_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )
    csharp_run_p.add_argument(
        "--save-plan", default="csharpplan.json",
        help="Save generated C# plan to this file (default: csharpplan.json)",
    )

    # ── azdo-run ─────────────────────────────────────────────────────
    azdo_run_p = sub.add_parser(
        "azdo-run", help="Create and immediately play an Azure DevOps YAML demo",
    )
    azdo_run_p.add_argument(
        "description", help="Written description of what Azure DevOps pipeline demo to create",
    )
    azdo_run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    azdo_run_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )
    azdo_run_p.add_argument(
        "--save-plan", default="azdoplan.json",
        help="Save generated Azure DevOps plan to this file (default: azdoplan.json)",
    )

    # ── gha-run ──────────────────────────────────────────────────────
    gha_run_p = sub.add_parser(
        "gha-run", help="Create and immediately play a GitHub Actions YAML demo",
    )
    gha_run_p.add_argument(
        "description", help="Written description of what GitHub Actions demo to create",
    )
    gha_run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    gha_run_p.add_argument(
        "--countdown", type=int, default=5,
        help="Seconds before playback starts (default: 5)",
    )
    gha_run_p.add_argument(
        "--save-plan", default="ghaplan.json",
        help="Save generated GitHub Actions plan to this file (default: ghaplan.json)",
    )

    # ── agent-ui ─────────────────────────────────────────────────────
    sub.add_parser(
        "agent-ui",
        help="Launch interactive agent GUI for scenario selection, planning, playback, and recording",
    )

    # ── record-play ──────────────────────────────────────────────────
    record_play_p = sub.add_parser(
        "record-play",
        help="Open clean VS Code window, play a plan, and record playback to webm/mp4",
    )
    record_play_p.add_argument("plan_file", help="Path to an existing plan JSON file")
    record_play_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    record_play_p.add_argument(
        "--countdown", type=int, default=8,
        help="Seconds before playback starts (default: 8)",
    )
    record_play_p.add_argument(
        "--format", choices=["webm", "mp4"], default="mp4",
        help="Recording format (default: mp4)",
    )
    record_play_p.add_argument(
        "--resolution", default="1920x1280",
        help="Output recording resolution WIDTHxHEIGHT (default: 1920x1280)",
    )
    record_play_p.add_argument(
        "--mode", choices=["stable", "typing"], default="typing",
        help="Playback mode for recording (default: typing)",
    )
    record_play_p.add_argument(
        "--clean-view",
        action="store_true",
        help="Use VS Code keyboard shortcuts to hide panes before recording (off by default)",
    )
    record_play_p.add_argument(
        "--no-focus-lock",
        action="store_true",
        help="Do not force VS Code to stay focused during recording",
    )
    record_play_p.add_argument(
        "--video-file",
        help="Optional custom output video file path",
    )

    # ── record-run ───────────────────────────────────────────────────
    record_run_p = sub.add_parser(
        "record-run",
        help="Generate plan, open clean VS Code window, play, and record in one command",
    )
    record_run_p.add_argument(
        "scenario",
        choices=["python", "sql", "sql-visual", "csharp", "azdo", "gha"],
        help="Scenario to generate and record",
    )
    record_run_p.add_argument("prompt", help="Prompt to generate the plan")
    record_run_p.add_argument(
        "--plan-file",
        help="Optional custom output plan path",
    )
    record_run_p.add_argument(
        "--speed", type=float, default=0.03,
        help="Seconds between characters (default: 0.03)",
    )
    record_run_p.add_argument(
        "--countdown", type=int, default=8,
        help="Seconds before playback starts (default: 8)",
    )
    record_run_p.add_argument(
        "--format", choices=["webm", "mp4"], default="mp4",
        help="Recording format (default: mp4)",
    )
    record_run_p.add_argument(
        "--resolution", default="1920x1280",
        help="Output recording resolution WIDTHxHEIGHT (default: 1920x1280)",
    )
    record_run_p.add_argument(
        "--mode", choices=["stable", "typing"], default="typing",
        help="Playback mode for recording (default: typing)",
    )
    record_run_p.add_argument(
        "--clean-view",
        action="store_true",
        help="Use VS Code keyboard shortcuts to hide panes before recording (off by default)",
    )
    record_run_p.add_argument(
        "--no-focus-lock",
        action="store_true",
        help="Do not force VS Code to stay focused during recording",
    )
    record_run_p.add_argument(
        "--video-file",
        help="Optional custom output video file path",
    )

    args = parser.parse_args()

    if args.command == "plan":
        print(f'Planning demo for: "{args.description}"')
        plan = plan_demo(args.description)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"Plan saved to {args.output}")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

    elif args.command == "sql-plan":
        print(f'Planning SQL demo for: "{args.description}"')
        plan = plan_sql_demo(args.description, visual_only=args.visual_only)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"SQL plan saved to {args.output}")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

    elif args.command == "csharp-plan":
        print(f'Planning C# demo for: "{args.description}"')
        plan = plan_csharp_demo(args.description)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"C# plan saved to {args.output}")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

    elif args.command == "azdo-plan":
        print(f'Planning Azure DevOps pipeline demo for: "{args.description}"')
        plan = plan_pipeline_demo(args.description, pipeline_type="azure-devops")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"Azure DevOps plan saved to {args.output}")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

    elif args.command == "gha-plan":
        print(f'Planning GitHub Actions demo for: "{args.description}"')
        plan = plan_pipeline_demo(args.description, pipeline_type="github-actions")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"GitHub Actions plan saved to {args.output}")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

    elif args.command == "play":
        with open(args.plan_file, encoding="utf-8") as f:
            plan = json.load(f)
        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "run":
        print(f'Planning demo for: "{args.description}"')
        plan = plan_demo(args.description)
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

        if args.save_plan:
            with open(args.save_plan, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print(f"Plan saved to {args.save_plan}")

        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "sql-run":
        print(f'Planning SQL demo for: "{args.description}"')
        plan = plan_sql_demo(args.description, visual_only=args.visual_only)
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

        if args.save_plan:
            with open(args.save_plan, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print(f"SQL plan saved to {args.save_plan}")

        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "csharp-run":
        print(f'Planning C# demo for: "{args.description}"')
        plan = plan_csharp_demo(args.description)
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

        if args.save_plan:
            with open(args.save_plan, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print(f"C# plan saved to {args.save_plan}")

        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "azdo-run":
        print(f'Planning Azure DevOps pipeline demo for: "{args.description}"')
        plan = plan_pipeline_demo(args.description, pipeline_type="azure-devops")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

        if args.save_plan:
            with open(args.save_plan, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print(f"Azure DevOps plan saved to {args.save_plan}")

        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "gha-run":
        print(f'Planning GitHub Actions demo for: "{args.description}"')
        plan = plan_pipeline_demo(args.description, pipeline_type="github-actions")
        print(f"  Title: {plan.get('title', 'Untitled')}")
        print(f"  Steps: {len(plan['steps'])}")

        if args.save_plan:
            with open(args.save_plan, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print(f"GitHub Actions plan saved to {args.save_plan}")

        play_demo(plan, char_delay=args.speed, countdown=args.countdown)

    elif args.command == "agent-ui":
        if launch_agent_gui is None:
            raise RuntimeError(
                "agent-ui is unavailable because demos_helper.agent_experience is missing."
            )
        launch_agent_gui()

    elif args.command == "record-play":
        with open(args.plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        workspace_dir, recording_file = run_recorded_play(
            plan=plan,
            speed=args.speed,
            countdown=args.countdown,
            video_format=args.format,
            resolution=args.resolution,
            mode=args.mode,
            clean_view=args.clean_view,
            focus_lock=not args.no_focus_lock,
            video_file=args.video_file,
        )
        print(f"Playback workspace: {workspace_dir}")
        print(f"Recording saved to: {recording_file}")

    elif args.command == "record-run":
        plan_file, workspace_dir, recording_file = generate_and_record(
            scenario=args.scenario,
            prompt=args.prompt,
            speed=args.speed,
            countdown=args.countdown,
            video_format=args.format,
            resolution=args.resolution,
            mode=args.mode,
            clean_view=args.clean_view,
            focus_lock=not args.no_focus_lock,
            plan_path=args.plan_file,
            video_file=args.video_file,
        )
        print(f"Plan saved to: {plan_file}")
        print(f"Playback workspace: {workspace_dir}")
        print(f"Recording saved to: {recording_file}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Playback cancelled by user.")
        sys.exit(130)
