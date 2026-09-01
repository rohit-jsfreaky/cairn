# PLAN — backend/ (Phase 3, Sep 6)

Finish line in `../MASTER-PLAN.md`. Do not start until Phases 1 and 2 pass their finish lines.
The MCP server (Phase 2) is the product; this backend exists to feed the demo dashboard.

### 2a. Skeleton
- FastAPI app, `schemas.py`, health route, CORS for localhost.
- `pip install -e ../package` wired; app imports `cairn` cleanly.
- ✅ `GET /health` returns the cairn package version.

### 2b. Run lifecycle + SSE
- `runner.py`: start a run in a background task; subscribe to the engine's event stream
  (`cairn.events`); buffer + fan out over SSE.
- `POST /runs`, `GET /runs/{id}/events`, `GET /runs/{id}`.
- Events must include every MemoryWrite / MemoryRead — the frontend's memory panel is built
  from exactly these.
- ✅ `curl -N` on the SSE route shows live step + memory events during a real run.

### 2c. Memory snapshot routes
- `GET /memory/sites`, `GET /memory/sites/{domain}`, `DELETE /memory/sites/{domain}` —
  all through `cairn.store`, zero direct Sibyl imports here.
- ✅ full curl flow: start run → watch stream → list sites → fetch playbook → forget →
  rerun is slow. (= the Phase 2 finish line)

### Deliberately NOT building
Auth, multi-user, persistence of run history beyond the journal, deployment config. Demo
runs on localhost. Anything here that is not needed for the judge screen is waste.
