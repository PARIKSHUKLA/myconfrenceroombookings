from app import db
from datetime import datetime

class ConferenceRoom(db.Model):
    __tablename__ = 'conference_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def to_dict(self):
        """Serialize this room to a JSON-ready dict.

        Args:
            None.

        Returns:
            dict: ``{"id": int, "name": str, "capacity": int,
            "location": str}``.

        Examples:
            Example 1 - serialize a queried room::

                room = ConferenceRoom.query.get(1)
                room.to_dict()
                # {"id": 1, "name": "Azure Hall", "capacity": 30,
                #  "location": "Building A, Floor 3"}

            Example 2 - serialize a list of rooms for a JSON response::

                rooms = ConferenceRoom.query.all()
                [r.to_dict() for r in rooms]

            Browser / cURL:
                Not applicable — this is a plain Python model method, not
                an HTTP route. It's invoked internally by routes such as
                ``GET /rooms`` and ``GET /rooms/<room_id>``.
        """
        return {'id': self.id, 'name': self.name, 'capacity': self.capacity, 'location': self.location}

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='organizer', lazy=True)

    def to_dict(self):
        """Serialize this employee to a JSON-ready dict.

        Args:
            None.

        Returns:
            dict: ``{"id": int, "name": str, "email": str,
            "department": str}``.

        Examples:
            Example 1 - serialize a queried employee::

                employee = Employee.query.get(1)
                employee.to_dict()
                # {"id": 1, "name": "Alice Thompson",
                #  "email": "alice.thompson@corp.com",
                #  "department": "Engineering"}

            Example 2 - serialize every employee::

                [e.to_dict() for e in Employee.query.all()]

            Browser / cURL:
                Not applicable — this is a plain Python model method, not
                an HTTP route. No route currently exposes employees
                directly; ``organizer_id`` on a booking references this
                model's ``id``.
        """
        return {'id': self.id, 'name': self.name, 'email': self.email, 'department': self.department}

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    meeting_title = db.Column(db.String(200))
    attendees = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize this booking to a JSON-ready dict.

        Args:
            None.

        Returns:
            dict: ``{"id": int, "room_id": int, "organizer_id": int,
            "start_time": str, "end_time": str, "meeting_title": str,
            "attendees": int, "status": str}``. ``start_time`` and
            ``end_time`` are ISO 8601 strings; ``status`` is either
            ``"scheduled"`` or ``"cancelled"``.

        Examples:
            Example 1 - serialize a queried booking::

                booking = Booking.query.get(1)
                booking.to_dict()
                # {"id": 1, "room_id": 1, "organizer_id": 1,
                #  "start_time": "2025-07-01T18:00:00",
                #  "end_time": "2025-07-01T18:30:00",
                #  "meeting_title": "Team Sync 1", "attendees": 5,
                #  "status": "scheduled"}

            Example 2 - serialize a room's bookings for a JSON response::

                bookings = Booking.query.filter_by(room_id=1).all()
                [b.to_dict() for b in bookings]

            Browser / cURL:
                Not applicable — this is a plain Python model method, not
                an HTTP route. It's invoked internally by routes such as
                ``GET /bookings`` and ``POST /bookings``.
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'organizer_id': self.organizer_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'meeting_title': self.meeting_title,
            'attendees': self.attendees,
            'status': self.status
        }
