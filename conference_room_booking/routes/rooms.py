from flask import Blueprint, request, jsonify
from app import db
from models import ConferenceRoom, Booking
from datetime import datetime, timedelta

rooms_bp = Blueprint('rooms', __name__)

@rooms_bp.route('/rooms', methods=['GET'])
def get_rooms():
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """
    Returns a room's booked time slots, optionally filtered by date.
    Optional query param: ?date=YYYY-MM-DD
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
    """
    Returns the open (unbooked) time gaps for a room on a given day,
    computed against a business-hours window.
    Required query param: ?date=YYYY-MM-DD
    Optional query params:
      business_start=HH:MM (default 09:00)
      business_end=HH:MM   (default 18:00)
      min_duration=<minutes> (drop gaps shorter than this)
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
