from datetime import datetime, time, timedelta
from typing import cast

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from appointments.models import (
    Appointment,
    Doctor,
    DoctorWorkingHour,
    Patient,
)


def make_aware_datetime(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    """
    Create a timezone-aware datetime using the project timezone.
    """
    return timezone.make_aware(
        datetime(
            year,
            month,
            day,
            hour,
            minute,
        )
    )


@pytest.mark.django_db
class TestDoctorModel:
    def test_doctor_string_representation(self) -> None:
        """
        Return the doctor's full name when converted to text.
        """
        doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.model@example.com",
            specialization="General Medicine",
        )

        assert str(doctor) == "Dr. Amina Hassan"

    def test_doctors_are_ordered_by_full_name(self) -> None:
        """
        Return doctors alphabetically by full name.
        """
        Doctor.objects.create(
            full_name="Dr. Zoe Adams",
            email="zoe.model@example.com",
            specialization="Cardiology",
        )

        Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.order@example.com",
            specialization="General Medicine",
        )

        names = list(
            Doctor.objects.values_list(
                "full_name",
                flat=True,
            )
        )

        assert names == [
            "Dr. Amina Hassan",
            "Dr. Zoe Adams",
        ]

    def test_doctor_is_active_by_default(self) -> None:
        """
        Confirm that newly created doctors are active by default.
        """
        doctor = Doctor.objects.create(
            full_name="Dr. Brian Otieno",
            email="brian.model@example.com",
            specialization="Dermatology",
        )

        assert doctor.is_active is True


@pytest.mark.django_db
class TestPatientModel:
    def test_patient_string_representation(self) -> None:
        """
        Return the patient's full name when converted to text.
        """
        patient = Patient.objects.create(
            full_name="Jane Doe",
            email="jane.model@example.com",
            phone_number="555-0100",
        )

        assert str(patient) == "Jane Doe"

    def test_patients_are_ordered_by_full_name(self) -> None:
        """
        Return patients alphabetically by full name.
        """
        Patient.objects.create(
            full_name="Zachary Smith",
            email="zachary.model@example.com",
            phone_number="555-0101",
        )

        Patient.objects.create(
            full_name="Alice Brown",
            email="alice.model@example.com",
            phone_number="555-0102",
        )

        names = list(
            Patient.objects.values_list(
                "full_name",
                flat=True,
            )
        )

        assert names == [
            "Alice Brown",
            "Zachary Smith",
        ]


@pytest.mark.django_db
class TestDoctorWorkingHourModel:
    def setup_method(self) -> None:
        """
        Create a doctor before every working-hour test.
        """
        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.hours@example.com",
            specialization="General Medicine",
        )

    def test_working_hour_string_representation(self) -> None:
        """
        Return a readable description of the doctor's working hours.
        """
        working_hour = DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        assert str(working_hour) == ("Dr. Amina Hassan - Monday 08:00:00 to 17:00:00")

    def test_working_hour_is_active_by_default(self) -> None:
        """
        Confirm working hours are active by default.
        """
        working_hour = DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        assert working_hour.is_active is True

    def test_clean_accepts_valid_working_hours(self) -> None:
        """
        Accept working hours when end time is after start time.
        """
        working_hour = DoctorWorkingHour(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        working_hour.full_clean()

    def test_clean_rejects_equal_start_and_end_times(self) -> None:
        """
        Reject working hours with equal start and end times.
        """
        working_hour = DoctorWorkingHour(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(8, 0),
        )

        with pytest.raises(ValidationError) as exc_info:
            working_hour.full_clean()

        error = cast(
            dict[str, list[ValidationError]],
            exc_info.value.error_dict,
        )

        assert "end_time" in error
        assert error["end_time"][0].message == "End time must be later than start time."

    def test_clean_rejects_end_time_before_start_time(self) -> None:
        """
        Reject working hours ending before they begin.
        """
        working_hour = DoctorWorkingHour(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(17, 0),
            end_time=time(8, 0),
        )

        with pytest.raises(
            ValidationError,
            match="End time must be later than start time.",
        ):
            working_hour.full_clean()

    def test_clean_skips_comparison_when_start_time_is_missing(
        self,
    ) -> None:
        """
        Confirm clean does not compare times when start time is absent.
        """
        working_hour = DoctorWorkingHour(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=None,
            end_time=time(17, 0),
        )

        working_hour.clean()

    def test_clean_skips_comparison_when_end_time_is_missing(
        self,
    ) -> None:
        """
        Confirm clean does not compare times when end time is absent.
        """
        working_hour = DoctorWorkingHour(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=None,
        )

        working_hour.clean()

    def test_database_rejects_duplicate_doctor_weekday(self) -> None:
        """
        Enforce one working-hours record per doctor and weekday.
        """
        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DoctorWorkingHour.objects.create(
                    doctor=self.doctor,
                    weekday=DoctorWorkingHour.Weekday.MONDAY,
                    start_time=time(13, 0),
                    end_time=time(17, 0),
                )

    def test_database_rejects_invalid_working_hour_range(
        self,
    ) -> None:
        """
        Enforce end_time greater than start_time at database level.
        """
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DoctorWorkingHour.objects.create(
                    doctor=self.doctor,
                    weekday=DoctorWorkingHour.Weekday.TUESDAY,
                    start_time=time(17, 0),
                    end_time=time(8, 0),
                )

    def test_working_hours_are_ordered_by_doctor_weekday_and_time(
        self,
    ) -> None:
        """
        Confirm the model's default ordering.
        """
        second_doctor = Doctor.objects.create(
            full_name="Dr. Zoe Adams",
            email="zoe.hours@example.com",
            specialization="Cardiology",
        )

        tuesday = DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )

        monday = DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        other_doctor = DoctorWorkingHour.objects.create(
            doctor=second_doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        working_hours = list(DoctorWorkingHour.objects.all())

        assert working_hours == [
            monday,
            tuesday,
            other_doctor,
        ]


@pytest.mark.django_db
class TestAppointmentModel:
    def setup_method(self) -> None:
        """
        Create reusable doctor and patient records.
        """
        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.appointment-model@example.com",
            specialization="General Medicine",
        )

        self.patient = Patient.objects.create(
            full_name="Jane Doe",
            email="jane.appointment-model@example.com",
            phone_number="555-0110",
        )

        self.start_time = make_aware_datetime(
            2026,
            7,
            20,
            8,
            0,
        )

    def test_appointment_status_defaults_to_booked(self) -> None:
        """
        Confirm new appointments default to BOOKED.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        assert appointment.status == Appointment.Status.BOOKED

    def test_appointment_cancellation_fields_have_defaults(
        self,
    ) -> None:
        """
        Confirm cancellation fields are empty for new appointments.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        assert appointment.cancellation_reason == ""
        assert appointment.cancelled_at is None

    def test_appointment_end_time_is_thirty_minutes_later(
        self,
    ) -> None:
        """
        Calculate an appointment end time from its start time.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        assert appointment.end_time == (self.start_time + timedelta(minutes=30))

    def test_appointment_string_representation(self) -> None:
        """
        Return a readable appointment description.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        assert str(appointment) == (f"Jane Doe with Dr. Amina Hassan at {self.start_time}")

    def test_appointments_are_ordered_by_start_time(self) -> None:
        """
        Return appointments in chronological order.
        """
        later_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time + timedelta(hours=1),
        )

        earlier_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        appointments = list(Appointment.objects.all())

        assert appointments == [
            earlier_appointment,
            later_appointment,
        ]

    def test_database_rejects_duplicate_booked_slot(self) -> None:
        """
        Prevent two booked appointments for the same doctor and time.
        """
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        second_patient = Patient.objects.create(
            full_name="John Doe",
            email="john.duplicate@example.com",
            phone_number="555-0111",
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    doctor=self.doctor,
                    patient=second_patient,
                    start_time=self.start_time,
                    status=Appointment.Status.BOOKED,
                )

    def test_cancelled_appointment_does_not_block_slot(self) -> None:
        """
        Allow a new booking when the existing appointment is cancelled.
        """
        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.CANCELLED,
        )

        second_patient = Patient.objects.create(
            full_name="John Doe",
            email="john.cancelled-slot@example.com",
            phone_number="555-0112",
        )

        new_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=second_patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        assert new_appointment.pk is not None

    def test_multiple_cancelled_appointments_can_share_slot(
        self,
    ) -> None:
        """
        Confirm the conditional uniqueness constraint applies only
        to booked appointments.
        """
        first = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.CANCELLED,
        )

        second_patient = Patient.objects.create(
            full_name="Second Patient",
            email="second.cancelled@example.com",
            phone_number="555-0113",
        )

        second = Appointment.objects.create(
            doctor=self.doctor,
            patient=second_patient,
            start_time=self.start_time,
            status=Appointment.Status.CANCELLED,
        )

        assert first.pk is not None
        assert second.pk is not None
