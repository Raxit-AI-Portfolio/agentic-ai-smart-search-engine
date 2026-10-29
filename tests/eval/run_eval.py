"""Gold-answer eval for the compiled graph. Requires the same live stack as
tests/integration_tests (see tests/test_execution.md). Run from repo root:

    python -m tests.eval.run_eval --runs 3
"""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx

from agentic_core.configs import config  # noqa: F401  (loads .env into os.environ)
from langchain_core.callbacks import get_usage_metadata_callback

from agentic_core.graph import graph
from agentic_core.services.auth_service import build_initial_state
from agentic_core.state.state import State

import os

HERE = Path(__file__).parent
DEMO_USERS = {
    "customer": ("alice", "customer123"),
    "worker": ("bob", "worker123"),
    "manager": ("carol", "manager123"),
}


def login_all() -> dict[str, str]:
    base = os.environ.get("AUTH_API_BASE_URL", "http://localhost:8003")
    tokens = {}
    with httpx.Client(base_url=base, timeout=10) as client:
        for role, (username, password) in DEMO_USERS.items():
            response = client.post("/auth/token", json={"username": username, "password": password})
            response.raise_for_status()
            tokens[role] = response.json()["access_token"]
    return tokens


def score(case: dict, output: dict) -> dict:
    steps = [s for s in output.get("step_results", {}).values()]
    used_sources = {s["source"] for s in steps if not s.get("error")}
    resources = [s["resource"] for s in steps if not s.get("error")]
    answer = (output.get("answer") or "").lower()

    checks = {}
    if "expect_sources" in case:
        checks["routing"] = set(case["expect_sources"]) <= used_sources
    if "expect_resource_any" in case:
        checks["citation"] = any(r in res for r in case["expect_resource_any"] for res in resources)
    if "answer_any" in case:
        checks["fact"] = any(t in answer for t in case["answer_any"])
    if "answer_all" in case:
        checks["fact"] = all(t in answer for t in case["answer_all"])
    if "answer_none" in case:
        checks["no_failure_phrase"] = not any(t in answer for t in case["answer_none"])
    if "forbid_sources" in case:
        checks["rbac"] = not (set(case["forbid_sources"]) & {s["source"] for s in steps})
    if "forbid_resource_any" in case:
        checks["rbac"] = not any(f in res for f in case["forbid_resource_any"] for res in resources)
    return checks


async def run_case(case: dict, token: str) -> dict:
    state = build_initial_state(query=case["query"], authorization_header=f"Bearer {token}", debug=False)
    start = time.perf_counter()
    with get_usage_metadata_callback() as usage_cb:
        result = await graph.ainvoke(state, config={"callbacks": [usage_cb]})
    latency = time.perf_counter() - start

    output = State(**result).model_dump(mode="json", exclude={"authorization_header"})
    total_tokens = sum(u.get("total_tokens", 0) for u in usage_cb.usage_metadata.values())
    return {"checks": score(case, output), "latency_s": round(latency, 2), "total_tokens": total_tokens, "answer": output.get("answer")}


async def main(runs: int) -> None:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    tokens = login_all()
    detail = []
    for case in cases:
        for i in range(runs):
            try:
                record = await run_case(case, tokens[case["role"]])
            except Exception as exc:
                record = {"checks": {"crashed": False}, "latency_s": None, "total_tokens": 0, "answer": f"ERROR: {exc}"}
            record.update(case_id=case["id"], run=i + 1)
            detail.append(record)
            print(case["id"], i + 1, record["checks"], record["latency_s"], record["total_tokens"])

    by_check: dict[str, list[bool]] = {}
    for record in detail:
        for name, ok in record["checks"].items():
            by_check.setdefault(name, []).append(ok)

    latencies = sorted(r["latency_s"] for r in detail if r["latency_s"] is not None)
    tokens_used = [r["total_tokens"] for r in detail if r["total_tokens"]]
    summary = {
        "runs_per_case": runs,
        "cases": len(cases),
        "pass_rate_by_check": {name: round(sum(v) / len(v), 3) for name, v in by_check.items()},
        "rbac_leaks": sum(1 for r in detail if r["checks"].get("rbac") is False),
        "latency_p50_s": statistics.median(latencies) if latencies else None,
        "latency_p95_s": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else None,
        "tokens_median": statistics.median(tokens_used) if tokens_used else None,
    }
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "eval_summary.json").write_text(json.dumps({"summary": summary, "detail": detail}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    asyncio.run(main(parser.parse_args().runs))
