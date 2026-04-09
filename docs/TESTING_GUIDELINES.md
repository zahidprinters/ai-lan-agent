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
