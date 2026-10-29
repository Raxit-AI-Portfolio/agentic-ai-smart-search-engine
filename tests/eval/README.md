# Eval: reproducing the portfolio results

Gold-answer eval for the compiled graph. Runs against the same live stack as `tests/integration_tests` (real Postgres, Qdrant, APIs, Gemini). Cases are in `cases.json`; assertions are routing (sources used), citation (document cited), fact (answer text), and RBAC leak (forbidden source/document reached).

## Prerequisites

1. `.env` at repo root, copied from `.env.example`, with a real `GOOGLE_API_KEY`. Optional tracing: set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT=efsse` (a LangSmith account and key; the project is created on the first trace). `.env` is loaded by `agentic_core/configs/config.py`.
2. Docker Desktop running. Create the external volume once on a new machine:
   ```bash
   docker volume create docker-postgre-data
   ```
3. Start the stack in order (see `tests/test_execution.md` for detail):
   ```bash
   docker compose up -d postgres redis
   ```
   ```powershell
   .\scripts\recreate-databases.ps1
   ```
   ```bash
   docker compose up -d
   ```
   ```bash
   pip install -r requirements.txt
   ```
   ```bash
   python scripts/ingest_documents.py
   ```

## Run

Integration tests (pass/fail plus per-test timing):
```bash
python -m pytest tests/integration_tests -v --durations=0
```

Eval (10 cases x 3 runs; writes `results/eval_summary.json`):
```bash
python -m tests.eval.run_eval --runs 3
```

Export LangSmith root runs from the eval window (writes `results/langsmith_runs.json`; max 100 runs, use a minutes value just above the eval duration):
```bash
python -m tests.eval.export_langsmith --since-minutes 30
```

## Notes

- Run the export right after the eval. Integration-test runs in the same window blend into the export; the eval runs are the last 30 by `start_time`.
- Token counts in `eval_summary.json` come from a LangChain usage callback. Cost comes from LangSmith only.
- The LLM is set by `PLANNING_MODEL` in `.env` (default `gemini-2.5-flash`). Reported results used `gemini-2.5-flash-lite`.
- Results vary run to run (live LLM). Reported run: 10 cases x 3, routing 100%, citation 100%, 0 RBAC leaks, fact match 80%, p50 7.3s, p95 27.4s, median 7,869 tokens.
