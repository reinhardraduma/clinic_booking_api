from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from appointments.models import Appointment, Doctor, Patient
from appointments.validators import validate_appointment_slot


class SlotUnavailableError(Exception):
    """
    Raised when a requested appointment slot is no longer available.
    """


class AppointmentAlreadyCancelledError(Exception):
    """
    Raised when attempting to cancel an appointment
    that is already cancelled.
    """


class CancelledAppointmentError(Exception):
    """
    Raised when attempting to reschedule a cancelled appointment.
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
        raise SlotUnavailableError("The selected appointment slot is no longer available.") from exc

    return appointment


@transaction.atomic
def cancel_appointment(
    *,
    appointment: Appointment,
    reason: str,
) -> Appointment:
    """
    Cancel an active appointment and release its slot.

    The appointment row is locked so two cancellation
    requests cannot update it at the same time.
    """

    locked_appointment = Appointment.objects.select_for_update().get(
        pk=appointment.pk,
    )

    if locked_appointment.status == Appointment.Status.CANCELLED:
        raise AppointmentAlreadyCancelledError("This appointment has already been cancelled.")

    locked_appointment.status = Appointment.Status.CANCELLED
    locked_appointment.cancellation_reason = reason
    locked_appointment.cancelled_at = timezone.now()

    locked_appointment.save(
        update_fields=[
            "status",
            "cancellation_reason",
            "cancelled_at",
            "updated_at",
        ]
    )

    return locked_appointment


def reschedule_appointment(
    *,
    appointment: Appointment,
    new_start_time: datetime,
) -> Appointment:
    """
    Move an active appointment to a new slot atomically.

    If validation or saving fails, the original appointment time
    remains unchanged.
    """

    try:
        with transaction.atomic():
            locked_appointment = Appointment.objects.select_for_update().get(
                pk=appointment.pk,
            )

            if locked_appointment.status == Appointment.Status.CANCELLED:
                raise CancelledAppointmentError("A cancelled appointment cannot be rescheduled.")

            validate_appointment_slot(
                doctor=locked_appointment.doctor,
                start_time=new_start_time,
                exclude_appointment_id=locked_appointment.pk,
            )

            locked_appointment.start_time = new_start_time
            locked_appointment.save(
                update_fields=[
                    "start_time",
                    "updated_at",
                ]
            )

            return locked_appointment

    except IntegrityError as exc:
        raise SlotUnavailableError("The selected appointment slot is no longer available.") from exc
