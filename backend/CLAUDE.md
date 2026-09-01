# CLAUDE.md — backend/ (thin API server)

A small FastAPI server. It runs the engine and streams what happens to the frontend.
That is ALL it does.

Read `PLAN.md` for what to build, `PROGRESS.md` for where we are. Root rules in
`../CLAUDE.md` apply. Depends on `package/` (Phase 1) — never on `frontend/`.

## Stack

Python 3.11+ · fastapi 0.141 · uvicorn · sse-starlette (SSE streaming) · the cairn package
installed editable (`pip install -e ../package`).

## The one architecture rule

**No business logic here.** The engine (`package/`) owns exploring, replaying, repairing,
and every memory call. The backend only: starts runs, forwards events, serves snapshots.
If you are about to write agent logic or a Sibyl call in this folder — stop, it belongs in
`package/src/cairn/`. (Same rule Rohit locked for Vouchley: logic lives in one place.)

## API surface (complete — do not grow it without a reason in PROGRESS.md)

```
POST /runs                  {task, site, variant?}  -> {run_id}     start a run (async)
GET  /runs/{id}/events      SSE stream of typed events from cairn.events
GET  /runs/{id}             final RunMetrics
GET  /memory/sites          list of learned sites + playbook health
GET  /memory/sites/{domain} full playbook JSON (the memory panel reads this)
DELETE /memory/sites/{domain}   forget (archive) — the demo "wipe memory" button
```

## Clean code rules

- One file per concern: `main.py` (app + routes), `runner.py` (run lifecycle, one active run
  at a time is fine), `schemas.py` (pydantic request/response models). Three files. Resist more.
- Type hints, ruff clean, no bare except, no prints — use logging.
- Every event forwarded AS-IS from `cairn.events` — never invent event shapes here; the
  frontend and the package must agree through one schema, owned by the package.
- CORS open for localhost only.
- No database. State lives in Sibyl (via the package) and in process memory for live runs.

## Definition of done

Route works via curl + ruff clean + PROGRESS.md updated.
