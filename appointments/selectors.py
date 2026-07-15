from datetime import date, datetime, time, timedelta
from django.utils import timezone
from django.db.models import QuerySet
from appointments.models import Appointment, Doctor, DoctorWorkingHour, Patient
from appointments.validators import (
    MINIMUM_BOOKING_NOTICE,
    SLOT_DURATION_MINUTES,
)


def combine_local_date_and_time(
    selected_date: date,
    selected_time: time,
) -> datetime:
    """
    Combine a date and time into a timezone-aware datetime
    using Django's currently configured timezone.
    """

    naive_datetime = datetime.combine(
        selected_date,
        selected_time,
    )

    return timezone.make_aware(
        naive_datetime,
        timezone.get_current_timezone(),
    )


def generate_slots(
    selected_date: date,
    start_time: time,
    end_time: time,
) -> list[datetime]:
    """
    Generate all possible 30-minute appointment start times
    within a doctor's working period.
    """

    current_slot = combine_local_date_and_time(
        selected_date=selected_date,
        selected_time=start_time,
    )

    working_period_end = combine_local_date_and_time(
        selected_date=selected_date,
        selected_time=end_time,
    )

    slot_duration = timedelta(
        minutes=SLOT_DURATION_MINUTES,
    )

    slots = []

    while current_slot + slot_duration <= working_period_end:
        slots.append(current_slot)
        current_slot += slot_duration

    return slots


def get_booked_slot_times(
    doctor: Doctor,
    selected_date: date,
) -> set[datetime]:
    """
    Return the booked appointment start times for a doctor
    on the selected local date.
    """

    day_start = combine_local_date_and_time(
        selected_date=selected_date,
        selected_time=time.min,
    )

    next_day_start = day_start + timedelta(days=1)

    booked_start_times = Appointment.objects.filter(
        doctor=doctor,
        status=Appointment.Status.BOOKED,
        start_time__gte=day_start,
        start_time__lt=next_day_start,
    ).values_list(
        "start_time",
        flat=True,
    )

    return set(booked_start_times)


def get_doctor_availability(
    doctor: Doctor,
    selected_date: date,
) -> list[dict]:
    """
    Return all available 30-minute slots for a doctor
    on a selected date.
    """

    weekday = selected_date.weekday()

    try:
        working_hour = DoctorWorkingHour.objects.get(
            doctor=doctor,
            weekday=weekday,
            is_active=True,
        )
    except DoctorWorkingHour.DoesNotExist:
        return []

    possible_slots = generate_slots(
        selected_date=selected_date,
        start_time=working_hour.start_time,
        end_time=working_hour.end_time,
    )

    booked_slot_times = get_booked_slot_times(
        doctor=doctor,
        selected_date=selected_date,
    )

    earliest_allowed_time = (
        timezone.now() + MINIMUM_BOOKING_NOTICE
    )

    available_slots = []

    slot_duration = timedelta(
        minutes=SLOT_DURATION_MINUTES,
    )

    for slot_start in possible_slots:
        if slot_start < earliest_allowed_time:
            continue

        if slot_start in booked_slot_times:
            continue

        available_slots.append(
            {
                "start_time": slot_start,
                "end_time": slot_start + slot_duration,
            }
        )

    return available_slots


def get_patient_upcoming_appointments(
    *,
    patient: Patient,
) -> QuerySet[Appointment]:
    """
    Return a patient's upcoming booked appointments,
    ordered from earliest to latest.
    """

    return (
        Appointment.objects.filter(
            patient=patient,
            status=Appointment.Status.BOOKED,
            start_time__gte=timezone.now(),
        )
        .select_related(
            "doctor",
            "patient",
        )
        .order_by("start_time")
    )