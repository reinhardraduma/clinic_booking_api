from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from appointments.models import (
    Appointment,
    Doctor,
    DoctorWorkingHour,
    Patient,
)
from appointments.validators import (
    MINIMUM_BOOKING_NOTICE,
    validate_appointment_slot,
    validate_doctor_working_hours,
    validate_slot_availability,
    validate_slot_start_time,
)


def make_aware_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
) -> datetime:
    """
    Create a timezone-aware datetime using the project's timezone.
    """
    return timezone.make_aware(
        datetime(
            year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
        )
    )


@pytest.mark.django_db
class TestAppointmentValidators:
    def setup_method(self) -> None:
        """
        Create reusable doctor, patient, and working-hour records.
        """
        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.validators@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="Test Patient",
            email="patient.validators@example.com",
            phone_number="555-0100",
        )

        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=datetime.strptime("08:00", "%H:%M").time(),
            end_time=datetime.strptime("10:00", "%H:%M").time(),
            is_active=True,
        )

        self.now = make_aware_datetime(
            2026,
            7,
            20,
            6,
            0,
        )

        self.valid_start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            0,
        )

    def test_rejects_naive_start_time(self) -> None:
        """
        Reject a datetime that does not include timezone information.
        """
        naive_start_time = datetime(
            2026,
            7,
            20,
            8,
            0,
        )

        with pytest.raises(
            ValidationError,
            match="Appointment start time must include timezone information.",
        ):
            validate_slot_start_time(naive_start_time)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_in_the_past(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject an appointment time earlier than the current time.
        """
        mocked_now.return_value = self.now

        past_time = self.now - timedelta(minutes=30)

        with pytest.raises(
            ValidationError,
            match="Appointments cannot be booked in the past.",
        ):
            validate_slot_start_time(past_time)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_equal_to_current_time(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject an appointment starting exactly at the current time.
        """
        mocked_now.return_value = self.now

        with pytest.raises(
            ValidationError,
            match="Appointments cannot be booked in the past.",
        ):
            validate_slot_start_time(self.now)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_with_insufficient_notice(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject a booking made less than one hour in advance.
        """
        mocked_now.return_value = self.now

        start_time = self.now + timedelta(minutes=30)

        with pytest.raises(
            ValidationError,
            match="Appointments must be booked at least one hour in advance.",
        ):
            validate_slot_start_time(start_time)

    @patch("appointments.validators.timezone.now")
    def test_accepts_exactly_minimum_booking_notice(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Accept an appointment exactly one hour in advance.
        """
        mocked_now.return_value = self.now

        start_time = self.now + MINIMUM_BOOKING_NOTICE

        validate_slot_start_time(start_time)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_with_seconds(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject an appointment time containing non-zero seconds.
        """
        mocked_now.return_value = self.now

        start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            0,
            second=15,
        )

        with pytest.raises(
            ValidationError,
            match="Appointment time must not include seconds.",
        ):
            validate_slot_start_time(start_time)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_with_microseconds(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject an appointment time containing microseconds.

        This separately covers the second half of the validator's
        seconds-or-microseconds condition.
        """
        mocked_now.return_value = self.now

        start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            0,
            second=0,
            microsecond=500000,
        )

        with pytest.raises(
            ValidationError,
            match="Appointment time must not include seconds.",
        ):
            validate_slot_start_time(start_time)

    @patch("appointments.validators.timezone.now")
    def test_rejects_start_time_not_on_thirty_minute_boundary(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject a slot that does not start at minute 00 or 30.
        """
        mocked_now.return_value = self.now

        start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            15,
        )

        with pytest.raises(
            ValidationError,
            match="Appointments must begin on a 30-minute slot.",
        ):
            validate_slot_start_time(start_time)

    @patch("appointments.validators.timezone.now")
    def test_accepts_valid_slot_start_time(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Accept a future, timezone-aware, correctly aligned slot.
        """
        mocked_now.return_value = self.now

        validate_slot_start_time(self.valid_start_time)

    def test_rejects_day_without_working_hours(self) -> None:
        """
        Reject a date on which the doctor does not work.
        """
        tuesday_start_time = make_aware_datetime(
            2026,
            7,
            21,
            8,
            0,
        )

        with pytest.raises(
            ValidationError,
            match="The doctor does not work on the selected day.",
        ):
            validate_doctor_working_hours(
                doctor=self.doctor,
                start_time=tuesday_start_time,
            )

    def test_rejects_inactive_working_hour(self) -> None:
        """
        Ignore inactive working-hour records.
        """
        monday_working_hour = DoctorWorkingHour.objects.get(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
        )

        monday_working_hour.is_active = False
        monday_working_hour.save(update_fields=["is_active"])

        with pytest.raises(
            ValidationError,
            match="The doctor does not work on the selected day.",
        ):
            validate_doctor_working_hours(
                doctor=self.doctor,
                start_time=self.valid_start_time,
            )

    def test_rejects_slot_before_working_hours(self) -> None:
        """
        Reject a slot beginning before the doctor's shift.
        """
        start_time = make_aware_datetime(
            2026,
            7,
            20,
            7,
            30,
        )

        with pytest.raises(
            ValidationError,
            match=("The selected slot begins before the doctor's working hours."),
        ):
            validate_doctor_working_hours(
                doctor=self.doctor,
                start_time=start_time,
            )

    def test_rejects_slot_ending_after_working_hours(self) -> None:
        """
        Reject a slot whose end time extends beyond the doctor's shift.
        """
        start_time = make_aware_datetime(
            2026,
            7,
            20,
            10,
            0,
        )

        with pytest.raises(
            ValidationError,
            match=("The selected slot ends after the doctor's working hours."),
        ):
            validate_doctor_working_hours(
                doctor=self.doctor,
                start_time=start_time,
            )

    def test_accepts_slot_inside_working_hours(self) -> None:
        """
        Accept a slot completely inside the doctor's working hours.
        """
        validate_doctor_working_hours(
            doctor=self.doctor,
            start_time=self.valid_start_time,
        )

    def test_rejects_already_booked_slot(self) -> None:
        """
        Reject a slot occupied by another booked appointment.
        """
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.valid_start_time,
            status=Appointment.Status.BOOKED,
        )

        with pytest.raises(
            ValidationError,
            match="The selected appointment slot is already booked.",
        ):
            validate_slot_availability(
                doctor=self.doctor,
                start_time=self.valid_start_time,
            )

    def test_cancelled_appointment_does_not_block_slot(self) -> None:
        """
        Confirm that a cancelled appointment releases its slot.
        """
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.valid_start_time,
            status=Appointment.Status.CANCELLED,
        )

        validate_slot_availability(
            doctor=self.doctor,
            start_time=self.valid_start_time,
        )

    def test_excluded_appointment_does_not_block_its_own_slot(
        self,
    ) -> None:
        """
        Allow rescheduling validation to exclude the current appointment.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.valid_start_time,
            status=Appointment.Status.BOOKED,
        )

        validate_slot_availability(
            doctor=self.doctor,
            start_time=self.valid_start_time,
            exclude_appointment_id=appointment.pk,
        )

    def test_other_appointment_still_blocks_slot_when_one_is_excluded(
        self,
    ) -> None:
        """
        Confirm exclusion only removes the specified appointment.
        """
        excluded_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.valid_start_time,
            status=Appointment.Status.BOOKED,
        )

        other_patient = Patient.objects.create(
            full_name="Other Patient",
            email="other.validator@example.com",
            phone_number="555-0101",
        )

        other_start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            30,
        )

        Appointment.objects.create(
            doctor=self.doctor,
            patient=other_patient,
            start_time=other_start_time,
            status=Appointment.Status.BOOKED,
        )

        with pytest.raises(
            ValidationError,
            match="The selected appointment slot is already booked.",
        ):
            validate_slot_availability(
                doctor=self.doctor,
                start_time=other_start_time,
                exclude_appointment_id=excluded_appointment.pk,
            )

    @patch("appointments.validators.timezone.now")
    def test_rejects_inactive_doctor(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Reject bookings for an inactive doctor.
        """
        mocked_now.return_value = self.now

        self.doctor.is_active = False
        self.doctor.save(update_fields=["is_active"])

        with pytest.raises(
            ValidationError,
            match=("Appointments cannot be booked with an inactive doctor."),
        ):
            validate_appointment_slot(
                doctor=self.doctor,
                start_time=self.valid_start_time,
            )

    @patch("appointments.validators.timezone.now")
    def test_validate_appointment_slot_runs_all_validations(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Accept a fully valid appointment through the main validator.
        """
        mocked_now.return_value = self.now

        validate_appointment_slot(
            doctor=self.doctor,
            start_time=self.valid_start_time,
        )

    @patch("appointments.validators.timezone.now")
    def test_validate_appointment_slot_allows_current_appointment(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Allow the current appointment to retain its slot during
        rescheduling validation.
        """
        mocked_now.return_value = self.now

        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.valid_start_time,
            status=Appointment.Status.BOOKED,
        )

        validate_appointment_slot(
            doctor=self.doctor,
            start_time=self.valid_start_time,
            exclude_appointment_id=appointment.pk,
        )
