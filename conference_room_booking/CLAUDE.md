# Conference Room Booking System

## Project Overview
A lightweight Flask + SQLAlchemy REST API for booking conference rooms — built for a workshop/prototype setting, not production. It models three resources: `ConferenceRoom` (name, capacity, location), `Employee` (organizer of a booking), and `Booking` (a room + organizer + time window). The API lets a client list rooms, create/reschedule/cancel bookings, and inspect a room's schedule two ways: `GET /rooms/<id>/availability` (what's already booked) and `GET /rooms/<id>/free-slots` (the open gaps, computed against a business-hours window). Booking writes are guarded by `utils/conflict.py::check_overlap`, which rejects any new/rescheduled slot that overlaps an existing `scheduled` booking in the same room. There is no authentication layer and no `/employees` route — see Useful Context below. Data lives in a local SQLite file (`db/bookings.db`), seedable via `db/seed_data.py`.

**Example usage** (server on `http://127.0.0.1:5000`, no auth headers needed):
```
GET  /rooms                                  # list all rooms
GET  /rooms/1/free-slots?date=2025-07-01     # open gaps for room 1 on that day
POST /bookings                               # body: {"room_id":1,"organizer_id":2,"start_time":"2026-07-20T10:00:00","end_time":"2026-07-20T10:30:00"}
PUT  /bookings/3                             # reschedule: body: {"start_time":"2026-07-20T14:00:00","end_time":"2026-07-20T14:30:00"}
DELETE /bookings/3                           # cancel (soft-delete, sets status="cancelled")
```
Each route's docstring (in `app.py`, `routes/bookings.py`, `routes/rooms.py`) has two full examples plus browser/curl invocations — check those before writing new client code against this API.

## Tech Stack
- Language: Python 3.11
- Framework: Flask 3.0
- ORM: Flask-SQLAlchemy 3.1
- Database: SQLite (db/bookings.db)

## Coding Conventions
- snake_case for all functions/variables; Blueprint instances are suffixed `_bp` (`bookings_bp`, `rooms_bp`).
- Every route returns the same JSON envelope: `{"data": ..., "error": ..., "status": <int>}`, and the `status` field always mirrors the actual HTTP status code returned.
- Route handler names reflect domain semantics, not generic CRUD verbs — the `PUT /bookings/<id>` handler is `reschedule_booking` (not `update_booking`), and `DELETE /bookings/<id>` is `cancel_booking` (not `delete_booking`), matching the fact that it's a soft-delete.
- Model serialization goes through a `to_dict()` instance method on each model (`ConferenceRoom`, `Employee`, `Booking`) rather than a separate serializer/schema layer.
- Datetimes cross the API boundary as ISO 8601 strings — parsed on the way in with `datetime.fromisoformat()`, serialized on the way out with `.isoformat()`.
- Route/method docstrings follow Google style (Args/Returns/Examples, plus a Browser/cURL block) — see any function in `routes/bookings.py` or `routes/rooms.py` as the template for new routes.

## Do Not Touch
- The blueprint imports inside `create_app()` in `app.py` (`from routes.bookings import bookings_bp`, `from routes.rooms import rooms_bp`) must stay **inside the function body**, not moved to module-level imports at the top of the file. `routes/bookings.py` and `routes/rooms.py` both do `from app import db`, so importing them at module load time creates a circular import — confirmed firsthand: running `python app.py` directly throws `ImportError: cannot import name 'bookings_bp' from partially initialized module 'routes.bookings'`. Use `flask run` (with `FLASK_APP=app.py`, via the project's venv) to start the dev server instead.

## Useful Context
- **No authentication or authorization exists anywhere in this codebase.** No login route, no token/session issuance, no `@login_required`-style decorators. `SECRET_KEY` is set in `app.py` but nothing actually uses it. Every route is fully open — don't assume auth headers are needed when writing clients or tests against this API.
- `GET /rooms/<id>/availability` is misleadingly named — it returns a room's **booked** slots, not open ones. For actual computed open gaps (against a business-hours window, with an optional `min_duration` filter), use `GET /rooms/<id>/free-slots` instead (added in `routes/rooms.py`).
