from models import Booking

def check_overlap(room_id, start_time, end_time, exclude_id=None):
    """Check whether a proposed booking slot conflicts with existing ones.

    Two bookings overlap when one starts before the other ends AND ends
    after the other starts. This uses strict less-than comparisons so
    that back-to-back bookings (e.g. 09:00-09:30 followed by
    09:30-10:00) are correctly allowed. Only bookings with
    ``status == "scheduled"`` are considered; cancelled bookings are
    ignored.

    Args:
        room_id (int): ID of the conference room whose schedule to
            check.
        start_time (datetime.datetime): Proposed booking start.
        end_time (datetime.datetime): Proposed booking end.
        exclude_id (int, optional): Booking ID to exclude from the
            check. Used when rescheduling a booking so it doesn't
            conflict with its own prior slot. Defaults to ``None``.

    Returns:
        bool: ``True`` if the proposed slot overlaps an existing
        scheduled booking for the room, ``False`` if the slot is free.

    Examples:
        Example 1 - check a new booking for conflicts::

            from datetime import datetime
            check_overlap(
                room_id=1,
                start_time=datetime(2026, 7, 20, 10, 0),
                end_time=datetime(2026, 7, 20, 10, 30),
            )
            # False -> slot is free

        Example 2 - check a reschedule, excluding the booking's own row::

            check_overlap(
                room_id=1,
                start_time=datetime(2026, 7, 20, 14, 0),
                end_time=datetime(2026, 7, 20, 14, 30),
                exclude_id=3,
            )
            # True -> conflicts with another scheduled booking

        Browser / cURL:
            Not applicable — this is an internal helper function, not an
            HTTP route. It's used inside ``POST /bookings`` and
            ``PUT /bookings/<booking_id>`` to reject conflicting time
            slots with HTTP 409.
    """
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None
