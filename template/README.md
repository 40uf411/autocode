# Clean Architecture FastAPI Template

This template delivers a FastAPI project organised using clean architecture with RBAC, caching, and database adapters for SQLite (default) and PostgreSQL.

## Features
- Full authentication stack: users, roles, privileges, and linking tables with SQLAlchemy indexes and auditing columns (`template/app/infrastructure/db/repositories.py:1`).
- JWT login that rejects blocked/soft-deleted accounts plus per-endpoint privilege enforcement via dependencies (`template/app/api/dependencies.py:1`, `template/app/api/routes/users.py:1`).
- DragonflyDB-backed caching for user fetches and JWT blocklists with a local TTL fallback for tests (`template/app/core/caching.py:1`, `template/app/services/user_service.py:1`, `template/app/services/token_service.py:1`).
- Database adapters for SQLite and Postgres, seeded admin role/user, and resettable session factory (`template/app/infrastructure/db/adapters`, `template/app/infrastructure/db/session.py:1`, `template/app/infrastructure/db/seeds.py:1`).
- Tests, Docker artefacts, and `.env` sample to reproduce the environment anywhere.
- Extended auth flows: logout via token blocklist, password resets (self + admin), block/unblock actions, and soft/hard delete across all aggregates (`template/app/api/routes/auth.py:1`, `template/app/api/routes/users.py:1`, `template/app/api/routes/roles.py:1`, `template/app/api/routes/privileges.py:1`).
- List endpoints are paginated (`page` + `per_page`, max 1000) and return light-weight summaries, while dedicated detail endpoints expose related data on demand (e.g. `/users/{id}`, `/roles/{id}`).
- Role model supports a single `is_superuser` role that bypasses privilege checks (seeded admin role) so you can bootstrap without manually attaching privileges (`template/app/api/schemas.py:38`, `template/app/services/role_service.py:14`, `template/app/services/auth_service.py:7`).
- System utilities: `/system/ping` returns server time, `/system/editable-resources` introspects editable tables, and both server lifecycle events and user activity are written to `logs/server.log` / `logs/activity.log`.
- Blueprint-driven entity scaffolding: describe new domains in `entities.json`, then run `python scripts/generate_entities.py` to regenerate `custom_*` models/schemas/services/routers from the templates in `blueprint/`.

## Getting Started
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/macOS
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and tweak secrets, database URL, cache URL (Dragonfly), and cache TTL.
3. Launch the API:
   ```bash
   uvicorn app.main:app --reload
   ```

> **Windows note:** the optional PostgreSQL driver (`asyncpg`) requires Microsoft C++ Build Tools. Install them or remove the line from `requirements.txt` when sticking to SQLite.
> The service automatically falls back to SQLite if the Postgres driver is missing or a connection cannot be established at startup, and it will only attempt the Postgres connection once per process.

The API exposes login/logout/password reset endpoints under `/auth`, plus CRUD/administrative operations for `/users`, `/roles`, and `/privileges` (including block/unblock, password resets, and soft/hard delete toggles). System endpoints under `/system` provide ping/status and editable-resource metadata. An initial `admin@example.com` user (`ChangeMe123!`) is seeded for bootstrapping, and logging output can be found under `logs/`.

## Testing
```bash
pytest
```

## Docker
Build and run (API + PostgreSQL + Dragonfly cache):
```bash
docker compose -f docker/docker-compose.yml up --build
```

The HTTP API listens on `http://localhost:8000`, PostgreSQL on `5432`, and Dragonfly on `6379`.

## Blueprint scaffolding
Describe one or more entities in `entities.json`, e.g.
```json
[
  {
    "name": "Rig",
    "table": "rigs",
    "attributes": [
      {"name": "id", "type": "int", "primary_key": true, "nullable": false},
      {"name": "name", "type": "string", "nullable": false}
    ]
  }
]
```
Then run:
```bash
python scripts/generate_entities.py --config entities.json
```
The script purges existing `custom_*.py` files and regenerates models/schemas/repositories/services/routes using the templates located in `blueprint/`. Wire the generated files into your project as needed.
