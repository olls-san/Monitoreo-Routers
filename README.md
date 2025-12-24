# MoniTe Web

MoniTe Web is a full‑stack monitoring and automation system for network devices.
It consists of a FastAPI backend built with async SQLAlchemy, APScheduler and
a React + Tailwind frontend. The application uses a strategy pattern to
support multiple router types (currently MikroTik via REST) and provides
actions such as recharging balance, querying balance and retrieving USSD logs.

## Backend

### Requirements

* Python 3.11+
* Virtual environment (recommended)

Install dependencies with `pip install -r requirements.txt`. Since this MVP
uses SQLite via `aiosqlite` and FastAPI, no additional services are needed.

### Running

```bash
# Activate your virtual environment first
export MONITE_DATABASE_URL="sqlite+aiosqlite:///./monite.db"
# Launch the API server.  It binds to 127.0.0.1:8000 by default.  If you need
# to allow external connections or avoid IPv6 resolution issues, you can
# specify the host explicitly:
uvicorn monite_web.backend.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://localhost:8000`. Tables are created on
startup (by default bound to 127.0.0.1:8000; if you encounter connection issues with IPv6, ensure you access `http://127.0.0.1:8000`). The scheduler will start automatically and schedule any existing
automation rules.

### Primary Endpoints

* `GET /hosts` – list all hosts (routers) without exposing passwords.
* `POST /hosts` – create a host. Requires name, ip, port, type, username,
  password.
* `PUT /hosts/{id}` – update host fields.
* `DELETE /hosts/{id}` – remove a host.
* `GET /hosts/{id}/actions` – retrieve supported actions for a given host.
* `POST /hosts/{id}/execute` – execute an action on a host.
* `GET /hosts/{id}/health` – perform a real health check on a single host.
* `GET /hosts/health` – return health for all hosts.
* `GET /action-runs` – list recorded action runs with optional filters.
* `GET /automation-rules` – list automation rules.
* `POST /automation-rules` – create a new automation rule.
* `PUT /automation-rules/{id}` – update an existing rule (schedules are
  rescheduled automatically).
* `DELETE /automation-rules/{id}` – delete a rule and cancel its schedule.
* `GET /config` – returns non‑secret configuration for the frontend.

## Frontend

### Requirements

* Node.js 18+

### Running

```bash
cd monite_web/frontend
npm install
npm run dev
```

The development server runs on `http://localhost:5173` and proxies API calls
to the backend. The UI features tabs for Routers, Historial, Checkeos,
Comandos and Configuración. Routers are displayed with an online/offline
indicator and latency fetched via the `/hosts/health` endpoint.

### Notes

* Password fields are never returned by the API or displayed in the UI.
* Response bodies for actions are stored as JSON strings in the database to
  avoid SQLite serialization errors. Parsed responses are stored separately.
* Telegram alerts can be enabled by setting the `MONITE_TELEGRAM_TOKEN` and
  `MONITE_TELEGRAM_CHAT_ID` environment variables. Alerts respect a cooldown
  per host and alert type.
* The scheduler is resilient: if it fails to start, the API will still be
  available.
