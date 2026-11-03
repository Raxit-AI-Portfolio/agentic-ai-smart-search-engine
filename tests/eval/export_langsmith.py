"""Exports root runs of the LangSmith project to tests/eval/results/langsmith_runs.json.

    python -m tests.eval.export_langsmith --limit 200
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from langsmith import Client

from agentic_core.configs import config  # noqa: F401  (loads .env into os.environ)

OUT = Path(__file__).parent / "results" / "langsmith_runs.json"


def main(limit: int, since_minutes: int | None) -> None:
    project = os.environ.get("LANGCHAIN_PROJECT", "efsse")
    start_time = datetime.now(timezone.utc) - timedelta(minutes=since_minutes) if since_minutes else None
    rows = []
    for run in Client().list_runs(project_name=project, is_root=True, limit=limit, start_time=start_time):
        rows.append(
            {
                "id": str(run.id),
                "name": run.name,
                "start_time": run.start_time.isoformat() if run.start_time else None,
                "latency_s": (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else None,
                "prompt_tokens": run.prompt_tokens,
                "completion_tokens": run.completion_tokens,
                "total_tokens": run.total_tokens,
                "total_cost": float(run.total_cost) if run.total_cost is not None else None,
                "status": run.status,
                "error": run.error,
            }
        )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} runs from project '{project}' to {OUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--since-minutes", type=int, default=None)
    args = parser.parse_args()
    main(args.limit, args.since_minutes)
