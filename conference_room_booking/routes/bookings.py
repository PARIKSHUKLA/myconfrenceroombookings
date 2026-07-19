from flask import Blueprint, request, jsonify
from app import db
from models import Booking, ConferenceRoom, Employee
from utils.conflict import check_overlap
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)

@bookings_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """List bookings, optionally filtered by room or organizer.

    Route:
        GET /bookings

    Args:
        room_id (int, optional): Query parameter. Conference room ID to
            filter results by. When omitted, bookings for all rooms are
            returned.
        organizer_id (int, optional): Query parameter. Employee ID to
            filter results by. When omitted, bookings for all organizers
            are returned.

    Returns:
        flask.Response: JSON body shaped as
        ``{"data": list[dict], "error": str | None, "status": int}``,
        HTTP 200. Each dict in ``data`` is a booking, see
        :meth:`models.Booking.to_dict`.

    Examples:
        Example 1 - list every booking in the system::

            GET /bookings

        Example 2 - list only room 1's bookings organized by employee 2::

            GET /bookings?room_id=1&organizer_id=2

        Browser:
            http://127.0.0.1:5000/bookings?room_id=1

        cURL:
            curl.exe "http://127.0.0.1:5000/bookings?room_id=1"
    """
    room_id = request.args.get('room_id', type=int)
    organizer_id = request.args.get('organizer_id', type=int)
    query = Booking.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    if organizer_id:
        query = query.filter_by(organizer_id=organizer_id)
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Fetch a single booking by ID.

    Route:
        GET /bookings/<booking_id>

    Args:
        booking_id (int): Path parameter. Primary key of the booking to
            retrieve.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": dict, "error": None, "status": 200}`` where ``data`` is
        a booking (see :meth:`models.Booking.to_dict`). If no booking
        exists with that ID, JSON body
        ``{"data": None, "error": "Booking not found", "status": 404}``,
        HTTP 404.

    Examples:
        Example 1 - fetch booking 1::

            GET /bookings/1

        Example 2 - fetch a booking that does not exist (404)::

            GET /bookings/9999

        Browser:
            http://127.0.0.1:5000/bookings/1

        cURL:
            curl.exe http://127.0.0.1:5000/bookings/1
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking for a conference room.

    Rejects the request if required fields are missing, the datetimes are
    malformed, ``end_time`` is not after ``start_time``, or the requested
    slot overlaps an existing ``scheduled`` booking for the same room (see
    :func:`utils.conflict.check_overlap`).

    Route:
        POST /bookings

    Args:
        room_id (int): JSON body field, required. ID of the conference
            room to book.
        organizer_id (int): JSON body field, required. ID of the employee
            organizing the meeting.
        start_time (str): JSON body field, required. ISO 8601 datetime,
            e.g. ``"2026-07-20T10:00:00"``.
        end_time (str): JSON body field, required. ISO 8601 datetime,
            must be after ``start_time``.
        meeting_title (str, optional): JSON body field. Defaults to
            ``""``.
        attendees (int, optional): JSON body field. Defaults to ``1``.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": dict, "error": None, "status": 201}``, HTTP 201, where
        ``data`` is the created booking (see
        :meth:`models.Booking.to_dict`). On missing/invalid fields, JSON
        body with ``"error"`` set and HTTP 400. On a time-slot conflict,
        JSON body with ``"error"`` set and HTTP 409.

    Examples:
        Example 1 - book "Azure Hall" for a sprint planning meeting::

            POST /bookings
            Content-Type: application/json

            {
                "room_id": 1,
                "organizer_id": 2,
                "start_time": "2026-07-20T10:00:00",
                "end_time": "2026-07-20T10:30:00",
                "meeting_title": "Sprint Planning",
                "attendees": 6
            }

        Example 2 - minimal booking, omitting optional fields::

            POST /bookings
            Content-Type: application/json

            {
                "room_id": 2,
                "organizer_id": 1,
                "start_time": "2026-07-21T13:00:00",
                "end_time": "2026-07-21T13:15:00"
            }

        Browser:
            Not directly callable — browsers can only issue GET requests
            by navigating to a URL. Use a REST client or curl instead.

        cURL (PowerShell, use curl.exe not the curl alias):
            curl.exe -X POST http://127.0.0.1:5000/bookings -H "Content-Type: application/json" -d '{"room_id":1,"organizer_id":2,"start_time":"2026-07-20T10:00:00","end_time":"2026-07-20T10:30:00","meeting_title":"Sprint Planning","attendees":6}'
    """
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    required = ['room_id', 'organizer_id', 'start_time', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({'data': None, 'error': f'Missing field: {field}', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(data['room_id'], start, end):
        return jsonify({'data': None, 'error': 'Time slot conflicts with existing booking', 'status': 409}), 409
    booking = Booking(
        room_id=data['room_id'],
        organizer_id=data['organizer_id'],
        start_time=start,
        end_time=end,
        meeting_title=data.get('meeting_title', ''),
        attendees=data.get('attendees', 1),
        status='scheduled'
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 201}), 201

@bookings_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
def reschedule_booking(booking_id):
    """Reschedule an existing booking to a new start/end time.

    Only the time window can be changed; room, organizer, title, and
    attendee count are left untouched. The new slot is checked for
    conflicts against every other ``scheduled`` booking in the same room
    (see :func:`utils.conflict.check_overlap`).

    Route:
        PUT /bookings/<booking_id>

    Args:
        booking_id (int): Path parameter. ID of the booking to
            reschedule.
        start_time (str): JSON body field, required. New ISO 8601 start
            datetime, e.g. ``"2026-07-20T14:00:00"``.
        end_time (str): JSON body field, required. New ISO 8601 end
            datetime, must be after ``start_time``.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": dict, "error": None, "status": 200}`` where ``data``
        is the updated booking (see :meth:`models.Booking.to_dict`). If
        ``booking_id`` doesn't exist, HTTP 404. On missing/invalid
        fields, HTTP 400. On a time-slot conflict, HTTP 409.

    Examples:
        Example 1 - move booking 3 to a 2pm slot::

            PUT /bookings/3
            Content-Type: application/json

            {
                "start_time": "2026-07-20T14:00:00",
                "end_time": "2026-07-20T14:30:00"
            }

        Example 2 - extend booking 5 to a full hour::

            PUT /bookings/5
            Content-Type: application/json

            {
                "start_time": "2026-07-21T09:00:00",
                "end_time": "2026-07-21T10:00:00"
            }

        Browser:
            Not directly callable — browsers cannot issue PUT requests
            from the address bar. Use a REST client or curl instead.

        cURL (PowerShell, use curl.exe not the curl alias):
            curl.exe -X PUT http://127.0.0.1:5000/bookings/3 -H "Content-Type: application/json" -d '{"start_time":"2026-07-20T14:00:00","end_time":"2026-07-20T14:30:00"}'
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(booking.room_id, start, end, exclude_id=booking_id):
        return jsonify({'data': None, 'error': 'New time slot conflicts with existing booking', 'status': 409}), 409
    booking.start_time = start
    booking.end_time = end
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    """Cancel a booking.

    This is a soft delete: the row is kept and its ``status`` field is
    set to ``"cancelled"`` rather than removing the record. Cancelled
    bookings no longer count toward conflict checks (see
    :func:`utils.conflict.check_overlap`) or availability queries.

    Route:
        DELETE /bookings/<booking_id>

    Args:
        booking_id (int): Path parameter. ID of the booking to cancel.

    Returns:
        flask.Response: On success, JSON body
        ``{"data": dict, "error": None, "status": 200}`` where ``data``
        is the booking with ``status`` now ``"cancelled"`` (see
        :meth:`models.Booking.to_dict`). If ``booking_id`` doesn't exist,
        JSON body ``{"data": None, "error": "Booking not found",
        "status": 404}``, HTTP 404.

    Examples:
        Example 1 - cancel booking 3::

            DELETE /bookings/3

        Example 2 - cancel a booking that does not exist (404)::

            DELETE /bookings/9999

        Browser:
            Not directly callable — browsers cannot issue DELETE
            requests from the address bar. Use a REST client or curl
            instead.

        cURL:
            curl.exe -X DELETE http://127.0.0.1:5000/bookings/3
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})
