from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from appointments.models import Appointment, DoctorWorkingHour


SLOT_DURATION_MINUTES = 30
MINIMUM_BOOKING_NOTICE = timedelta(hours=1)


def validate_slot_start_time(start_time):
    """
    Validate general rules that apply to every appointment slot.
    """

    if timezone.is_naive(start_time):
        raise ValidationError(
            "Appointment start time must include timezone information."
        )

    now = timezone.now()

    if start_time <= now:
        raise ValidationError(
            "Appointments cannot be booked in the past."
        )

    if start_time < now + MINIMUM_BOOKING_NOTICE:
        raise ValidationError(
            "Appointments must be booked at least one hour in advance."
        )

    if start_time.second != 0 or start_time.microsecond != 0:
        raise ValidationError(
            "Appointment time must not include seconds."
        )

    if start_time.minute not in (0, 30):
        raise ValidationError(
            "Appointments must begin on a 30-minute slot."
        )


def validate_doctor_working_hours(doctor, start_time):
    """
    Confirm that the selected slot falls inside the doctor's schedule.
    """

    local_start_time = timezone.localtime(start_time)

    weekday = local_start_time.weekday()

    try:
        working_hour = DoctorWorkingHour.objects.get(
            doctor=doctor,
            weekday=weekday,
            is_active=True,
        )
    except DoctorWorkingHour.DoesNotExist as exc:
        raise ValidationError(
            "The doctor does not work on the selected day."
        ) from exc

    appointment_end_time = (
        local_start_time + timedelta(minutes=SLOT_DURATION_MINUTES)
    )

    selected_start = local_start_time.time()
    selected_end = appointment_end_time.time()

    if selected_start < working_hour.start_time:
        raise ValidationError(
            "The selected slot begins before the doctor's working hours."
        )

    if selected_end > working_hour.end_time:
        raise ValidationError(
            "The selected slot ends after the doctor's working hours."
        )


def validate_slot_availability(
    doctor,
    start_time,
    exclude_appointment_id=None,
):
    """
    Confirm that another active appointment does not occupy the slot.
    """

    appointments = Appointment.objects.filter(
        doctor=doctor,
        start_time=start_time,
        status=Appointment.Status.BOOKED,
    )

    if exclude_appointment_id is not None:
        appointments = appointments.exclude(
            id=exclude_appointment_id,
        )

    if appointments.exists():
        raise ValidationError(
            "The selected appointment slot is already booked."
        )


def validate_appointment_slot(
    doctor,
    start_time,
    exclude_appointment_id=None,
):
    """
    Run every validation rule required for booking or rescheduling.
    """

    if not doctor.is_active:
        raise ValidationError(
            "Appointments cannot be booked with an inactive doctor."
        )

    validate_slot_start_time(start_time)

    validate_doctor_working_hours(
        doctor=doctor,
        start_time=start_time,
    )

    validate_slot_availability(
        doctor=doctor,
        start_time=start_time,
        exclude_appointment_id=exclude_appointment_id,
    )