import argparse
import json
import sys

from .planner import plan_demo
from .player import play_demo


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

    args = parser.parse_args()

    if args.command == "plan":
        print(f'Planning demo for: "{args.description}"')
        plan = plan_demo(args.description)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        print(f"Plan saved to {args.output}")
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


if __name__ == "__main__":
    main()
