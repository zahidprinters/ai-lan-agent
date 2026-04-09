"""AI Lan minimal runtime entrypoint for the new layered structure."""

import json

from agents.react.agent import ReactAgent


def main() -> None:
    agent = ReactAgent()
    payload: dict[str, object] = {
        "thought": "List project docs for context.",
        "action": "pc.list_workspace_files",
        "args": {"relative_path": "docs", "limit": 5},
        "safety_level": "low",
    }
    step = agent.run_step(payload, confirmed=False)
    print(json.dumps(step.result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
