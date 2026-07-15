from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from appointments.models import Appointment, Doctor, Patient
from appointments.validators import validate_appointment_slot


class SlotUnavailableError(Exception):
    """
    Raised when a requested appointment slot is no longer available.
    """


@transaction.atomic
def book_appointment(
    *,
    doctor: Doctor,
    patient: Patient,
    start_time: datetime,
) -> Appointment:
    """
    Validate and create a new appointment atomically.
    """

    validate_appointment_slot(
        doctor=doctor,
        start_time=start_time,
    )

    try:
        appointment = Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            start_time=start_time,
            status=Appointment.Status.BOOKED,
        )
    except IntegrityError as exc:
        raise SlotUnavailableError(
            "The selected appointment slot is no longer available."
        ) from exc

    return appointment