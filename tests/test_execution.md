# Test Execution

## Integration Tests

Location: [tests/integration_tests/](integration_tests/). These run the full compiled LangGraph end-to-end against real infra — Postgres (SQL), Qdrant+BM25 (RAG), customer-api/operations-api (API), and the real Gemini LLM (planning + synthesis). No mocks.

### One-shot: `scripts/test-execution.ps1`

Fill in `.env` (see below), then run everything with one command:

```powershell
.\scripts\test-execution.ps1
```

This does every step below for you — starts Postgres/Redis, recreates and seeds the databases, rebuilds and brings up the full stack, installs Python deps, ingests the RAG docs, and runs `pytest tests/integration_tests -v`. Flags for faster iteration once the stack is already up: `-SkipDbReset`, `-SkipIngest`, `-SkipBuild`; pass extra pytest args with e.g. `-TestArgs "-k customer"`.

The manual steps below are what that script automates, for when you want to run (or debug) one piece by hand.

### Prerequisites

1. Fill in `.env` at the repo root (copy from `.env.example` if starting fresh) — every key in `.env.example` needs a real value, especially `GOOGLE_API_KEY`.
2. Start Postgres and Redis, then seed the databases (order matters — see [project-notes/DbSetup.md](../project-notes/DbSetup.md)):
   ```bash
   docker compose up -d postgres redis
   ```
   Once postgres is healthy, run `scripts/recreate-databases.ps1` (or the manual steps in `DbSetup.md`) against it. This seeds `membershipdb`'s three demo accounts used by the tests: `alice`/`customer123` (customer), `bob`/`worker123` (worker), `carol`/`manager123` (manager).
3. Bring up the rest of the stack:
   ```bash
   docker compose up -d
   ```
4. Install test dependencies (added to `requirements.txt`):
   ```bash
   pip install -r requirements.txt
   ```

5. Ingest the RAG documents into Qdrant (only needed once, or after `documents/*.md` changes):
   ```bash
   python scripts/ingest_documents.py
   ```


### Running

From the repo root:

```bash
python -m pytest tests/integration_tests -v
```

Run a single scenario file or case the normal pytest way, e.g.:

```bash
python -m pytest tests/integration_tests/test_smart_search.py -k customer -v
```

### Reading the results

Each scenario writes its input (username/role/debug mode/prompt) and the full JSON output of the graph run to `tests/integration_tests/results/<role>_<debug|nodebug>_<prompt-slug>.txt`. The in-test assertions are intentionally light (RBAC/structural invariants) since the plan and synthesized answer come from a live LLM and will vary run to run — review the result files for the actual quality of the plan/retrieval/answer.
