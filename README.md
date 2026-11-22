# Campus Tycoon — Team project

Independent starting point for the Nova SBE Introduction to Programming team project.
The team extension is still to be defined.

## Baseline

Copied from the completed Campus Tycoon solo project, commit
`a10728f4edfacce67ff5523d1749ea92a9a360ee`.
The original project is stored separately in `../campus-tycoon`.

The baseline includes the five-day kiosk simulation and its tests.
The documents in `docs/product-brief.html` and `specs/first-feature.md`
describe the original solo project.

## Local setup

Install uv, then run these commands from this directory:

```sh
uv sync --locked
uv run pytest
uv run streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Open http://127.0.0.1:8503 in your browser.
Stop the server with Ctrl+C.

The app creates its own `campus_week.sqlite3` file in this directory.
Set `CAMPUS_TYCOON_DB` to use another file. A database in the old solo
format is left unchanged and reported with an error.
Local databases, virtual environments and secrets are excluded from Git.

## Team and deployment

Team members and student numbers: to be added by the team.

Public deployed URL: to be added after deployment.
