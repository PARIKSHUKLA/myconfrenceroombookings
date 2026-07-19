from flask import Blueprint, request, jsonify
from app import db
from models import ConferenceRoom, Booking
from datetime import datetime, timedelta

rooms_bp = Blueprint('rooms', __name__)

@rooms_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """List every conference room.

    Route:
        GET /rooms

    Args:
        None.

    Returns:
        flask.Response: JSON body
        ``{"data": list[dict], "error": None, "status": 200}`` where each
        dict in ``data`` is a room (see
        :meth:`models.ConferenceRoom.to_dict`).

    Examples:
        Example 1 - list all rooms::

            GET /rooms

        Example 2 - same call, explicit host/port::

            GET http://127.0.0.1:5000/rooms

        Browser:
            http://127.0.0.1:5000/rooms

        cURL:
            curl.exe http://127.0.0.1:5000/rooms
    """
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Fetch a single conference room by ID.

    Route:
        GET /rooms/<room_id>

    Args:
        room_id (int): Path parameter. Primary key of the room to
            retrieve.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": dict, "error": None, "status": 200}`` where ``data``
        is a room (see :meth:`models.ConferenceRoom.to_dict`). If no room
        exists with that ID, JSON body ``{"data": None, "error": "Room
        not found", "status": 404}``, HTTP 404.

    Examples:
        Example 1 - fetch room 1 ("Azure Hall")::

            GET /rooms/1

        Example 2 - fetch a room that does not exist (404)::

            GET /rooms/9999

        Browser:
            http://127.0.0.1:5000/rooms/1

        cURL:
            curl.exe http://127.0.0.1:5000/rooms/1
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """List a room's booked time slots, optionally filtered to one day.

    Note this returns what is *already booked*, not open time — for the
    inverse (open gaps), see :func:`get_free_slots`.

    Route:
        GET /rooms/<room_id>/availability

    Args:
        room_id (int): Path parameter. ID of the room to check.
        date (str, optional): Query parameter. ``YYYY-MM-DD``. When
            given, only bookings starting on that calendar date are
            returned. When omitted, every ``scheduled`` booking for the
            room is returned.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": list[dict], "error": None, "status": 200}`` where each
        dict in ``data`` is a booking (see
        :meth:`models.Booking.to_dict`). On a malformed ``date``, JSON
        body with ``"error"`` set and HTTP 400.

    Examples:
        Example 1 - all scheduled bookings for room 1::

            GET /rooms/1/availability

        Example 2 - room 1's bookings on a specific day::

            GET /rooms/1/availability?date=2025-07-01

        Browser:
            http://127.0.0.1:5000/rooms/1/availability?date=2025-07-01

        cURL:
            curl.exe "http://127.0.0.1:5000/rooms/1/availability?date=2025-07-01"
    """
    date_str = request.args.get('date', type=str)
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled'
    )
    if date_str:
        try:
            target_date = datetime.fromisoformat(date_str).date()
            query = query.filter(db.func.date(Booking.start_time) == target_date)
        except ValueError:
            return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/free-slots', methods=['GET'])
def get_free_slots(room_id):
    """List a room's open (unbooked) time gaps for a given day.

    Computed by walking the room's ``scheduled`` bookings for the day in
    start-time order and returning every gap between them, clipped to a
    business-hours window. This is the inverse of
    :func:`get_availability`, which returns booked slots instead.

    Route:
        GET /rooms/<room_id>/free-slots

    Args:
        room_id (int): Path parameter. ID of the room to check.
        date (str): Query parameter, required. ``YYYY-MM-DD`` — the
            calendar day to compute free slots for.
        business_start (str, optional): Query parameter. ``HH:MM``, 24hr
            clock. Start of the day's bookable window. Defaults to
            ``"09:00"``.
        business_end (str, optional): Query parameter. ``HH:MM``, 24hr
            clock. End of the day's bookable window. Defaults to
            ``"18:00"``. Must be later than ``business_start``.
        min_duration (int, optional): Query parameter. Minimum gap length
            in minutes. Gaps shorter than this are dropped from the
            result. Defaults to ``None`` (no filtering).

    Returns:
        flask.Response: On success, JSON body
        ``{"data": list[dict], "error": None, "status": 200}`` where each
        dict in ``data`` is ``{"start_time": str, "end_time": str}``
        (ISO 8601). On a missing/malformed ``date``, an invalid
        ``business_start``/``business_end``, or ``business_end`` not
        after ``business_start``, JSON body with ``"error"`` set and
        HTTP 400. If ``room_id`` doesn't exist, HTTP 404.

    Examples:
        Example 1 - free slots for room 1 during default 09:00-18:00::

            GET /rooms/1/free-slots?date=2025-07-01

        Example 2 - free slots of at least an hour, wider window::

            GET /rooms/1/free-slots?date=2025-07-01&business_start=09:00&business_end=22:00&min_duration=60

        Browser:
            http://127.0.0.1:5000/rooms/1/free-slots?date=2025-07-01&business_start=09:00&business_end=22:00

        cURL:
            curl.exe "http://127.0.0.1:5000/rooms/1/free-slots?date=2025-07-01&business_start=09:00&business_end=22:00&min_duration=60"
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404

    date_str = request.args.get('date', type=str)
    if not date_str:
        return jsonify({'data': None, 'error': 'Missing required query param: date (YYYY-MM-DD)', 'status': 400}), 400
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400

    business_start_str = request.args.get('business_start', '09:00')
    business_end_str = request.args.get('business_end', '18:00')
    try:
        day_start = datetime.combine(target_date, datetime.strptime(business_start_str, '%H:%M').time())
        day_end = datetime.combine(target_date, datetime.strptime(business_end_str, '%H:%M').time())
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid business_start/business_end format. Use HH:MM.', 'status': 400}), 400
    if day_end <= day_start:
        return jsonify({'data': None, 'error': 'business_end must be after business_start', 'status': 400}), 400

    min_duration = request.args.get('min_duration', type=int)

    bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < day_end,
        Booking.end_time > day_start,
    ).order_by(Booking.start_time).all()

    free_slots = []
    cursor = day_start
    for booking in bookings:
        slot_start = max(cursor, day_start)
        slot_end = min(booking.start_time, day_end)
        if slot_end > slot_start:
            free_slots.append((slot_start, slot_end))
        cursor = max(cursor, booking.end_time)
    if cursor < day_end:
        free_slots.append((cursor, day_end))

    if min_duration:
        free_slots = [
            (s, e) for s, e in free_slots
            if (e - s) >= timedelta(minutes=min_duration)
        ]

    return jsonify({
        'data': [
            {'start_time': s.isoformat(), 'end_time': e.isoformat()}
            for s, e in free_slots
        ],
        'error': None,
        'status': 200
    })
