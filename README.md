# Rescue Evidence Fusion & Coordination Platform — Prototype

This is a working Sprint 1 prototype covering the High-priority functional
requirements from the SRS: authentication, evidence submission, evidence
fusion & confidence scoring, task assignment (with duplicate prevention),
and automatic alert generation.

It's built to actually run end-to-end on your laptop, not just as boilerplate.

## What's real vs. simplified

| Area | Prototype | Full build (per SRS) |
|---|---|---|
| Database | SQLite, plain lat/lng floats | PostgreSQL + PostGIS |
| Spatial correlation | Haversine distance in Python | PostGIS ST_DWithin query |
| Auth | Password + JWT | + Two-factor OTP (FR-1.2) |
| Real-time updates | Dashboard polls every 5s | WebSocket/MQTT push |
| Offline sync | In-browser memory queue (demo only) | Persistent on-device storage |

Everything else — the fusion weighting logic, confidence scoring, alert
threshold, duplicate-task blocking — is real, working logic, not a mock.

## Requirements implemented (Sprint 1 / High priority)

FR-1.1, FR-1.2, FR-1.4, FR-2.1, FR-2.2, FR-2.4, FR-2.5, FR-2.6,
FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-4.1, FR-4.2, FR-4.3, FR-4.4,
FR-5.1, FR-5.2, FR-5.4

## How to run

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`. Interactive API docs (Swagger) at
`http://localhost:8000/docs` — you can test every endpoint from there
without touching the frontend at all.

### 2. Frontend

No build step — just open the HTML files directly in a browser:

- `frontend/dashboard.html` — Control Room dashboard (map, zones, alerts, task assignment)
- `frontend/field-app.html` — Field responder evidence submission (mobile-simulation)

Open both side by side. Submit evidence from `field-app.html`, watch it
appear as a zone with a live confidence score on `dashboard.html` within
5 seconds (auto-refresh).

**Note:** if you open the HTML files via `file://`, some browsers block
the fetch calls to `localhost:8000` due to CORS/mixed-content rules. If
that happens, serve the frontend folder too:

```bash
cd frontend
python -m http.server 5500
```
Then open `http://localhost:5500/dashboard.html` and
`http://localhost:5500/field-app.html` instead.

## Demo script (to actually see fusion + alerting work)

1. Open both frontend pages.
2. In the dashboard, create a team (e.g. "Alpha Squad").
3. In the field app, click "Simulate GPS reading", pick **Thermal**, submit.
4. Click "Simulate GPS reading" again (small jitter, same zone), pick
   **Audio**, submit.
5. Do it again with **Visual**, then **Sensor**.
6. Watch the dashboard: a zone appears, its confidence score climbs with
   each submission (weighted fusion, FR-3.3), and once it crosses 75 an
   alert appears in the sidebar automatically (FR-5.1) — no manual trigger.
7. Back in the dashboard, assign a task for that zone to your team.
8. Try assigning the same zone again — it'll be blocked (FR-4.4, 409 error).

## Project structure

```
rescue_prototype/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── core/security.py     # password hashing, JWT
│   │   ├── db/
│   │   │   ├── database.py      # SQLite connection
│   │   │   └── models.py        # User, Team, Evidence, SurvivorZone, Task, Alert
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── fusion_engine.py # FR-3.1–3.4: correlation + scoring
│   │   │   └── alert_service.py # FR-5.1: threshold check
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── evidence.py
│   │       ├── teams.py
│   │       ├── tasks.py
│   │       └── alerts.py
│   └── requirements.txt
└── frontend/
    ├── dashboard.html            # Control Room
    └── field-app.html            # Field responder submission
```

## What's next (Sprint 2+, per SRS priorities)

- Medium-priority: reports/export (FR-6.3–6.5), offline conflict resolution
  (FR-7.2), device health weighting (FR-3.5)
- Swap SQLite → PostGIS for real spatial queries
- Add the 2FA/OTP step to login
- Replace polling with WebSocket push
- Persistent (not in-memory) offline queue on the field app
