# MoniTe Web Backend

This package implements the server side of the MoniTe Web system. It is
built with FastAPI and provides REST endpoints for managing routers,
running actions, configuring automation rules and retrieving
execution history. The backend communicates with routers through
pluggable drivers – currently only MikroTik RouterOS via its REST
API is implemented. Actions and automation rules are decoupled from
router types so that additional drivers can be added easily without
touching the rest of the code.

## Quick start

1. Install dependencies (preferably in a virtual environment):

   ```sh
   pip install -r requirements.txt
   ```

2. Set any required environment variables (optional). You can create a
   `.env` file to persist them. The following settings are supported:

   - `MONITE_DATABASE_URL` – SQLAlchemy connection string (default
     `sqlite+aiosqlite:///./monite.db`).
   - `MONITE_TELEGRAM_TOKEN` – Telegram bot token for alerting.
   - `MONITE_TELEGRAM_CHAT_ID` – Chat ID where alerts should be sent.

3. Run the application using Uvicorn:

   ```sh
   uvicorn monite_web.backend.app.main:app --reload
   ```

The API will be available at http://localhost:8000. The OpenAPI
documentation is served at `/docs`.

## Structure

- `app/main.py` – FastAPI application entrypoint; sets up the
  scheduler and registers routers.
- `app/models.py` – SQLAlchemy models for hosts, action runs and
  automation rules.
- `app/drivers/` – Drivers encapsulating router-specific logic.
- `app/services/` – Services for scheduling, alerting and parsing.
- `app/routers/` – API endpoints for hosts, actions, automation and history.

## Adding new router types

To support a new router, create a driver class in `app/drivers` that
subclasses `RouterDriver`. Implement `execute_action()`,
`list_supported_actions()` and `validate()`. Register the driver
by adding an entry to the `_DRIVER_REGISTRY` dictionary in
`app/drivers/__init__.py`. The rest of the application will pick up
the new driver automatically.
