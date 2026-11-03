"""Standalone CLI runner for the compiled LangGraph — no UI. Reads a bearer
token from AUTH_TOKEN (get one via POST /auth/token on auth-api) so it
exercises the same build_initial_state -> graph.ainvoke path the Streamlit UI
uses, for quick manual testing without the frontend.
"""

import argparse
import asyncio
import json
import os

from agentic_core.graph import graph
from agentic_core.services.auth_service import build_initial_state
from agentic_core.state.state import State


async def run(query: str, token: str, debug: bool) -> None:
    state = build_initial_state(query=query, authorization_header=f"Bearer {token}", debug=debug)
    result = await graph.ainvoke(state)
    final_state = State(**result)

    print(final_state.answer)
    if final_state.view_mode != "direct":
        print("\n--- trace ---")
        for line in final_state.trace:
            print(line)
    if final_state.debug:
        print("\n--- step results ---")
        print(json.dumps([sr.model_dump(mode="json") for sr in final_state.step_results.values()], indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one query through the EFSSE graph.")
    parser.add_argument("query", help="Natural-language question to ask.")
    parser.add_argument("--token", default=os.environ.get("AUTH_TOKEN"), help="Bearer token (or set AUTH_TOKEN env var).")
    parser.add_argument("--debug", action="store_true", help="Request manager debug detail (ignored for non-manager roles).")
    args = parser.parse_args()

    if not args.token:
        parser.error("a bearer token is required — pass --token or set AUTH_TOKEN")

    asyncio.run(run(args.query, args.token, args.debug))


if __name__ == "__main__":
    main()
