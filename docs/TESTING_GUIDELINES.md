# Testing & Development Guidelines

- Always use the .venv virtual environment for all test, run, and development commands.
- Activate the environment before running any Python scripts or pytest:
  - On Windows PowerShell: `& .venv\Scripts\Activate.ps1`
  - On Unix/macOS: `source .venv/bin/activate`
- Run tests using the environment's Python:
  - `python -m pytest --maxfail=50 --disable-warnings -v`
- Do not use system Python or global pytest.
- All automation/scripts should assume .venv is present and active.
- Document this guideline in README and developer docs.

## Replay Gate

- Router and policy changes should be replay-validated with the dry-run audit gate before merge or release.
- Local strict replay command:
  - `python scripts/replay_audit.py --input tests/fixtures/replay/strict_pass.jsonl --output temp/benchmarks/local_replay_report.json --strict`
- Strict mode exits nonzero when replay finds diverged or skipped rows.
- The CI workflow runs the strict replay gate when router, safety, replay-script, or replay-fixture files change.
