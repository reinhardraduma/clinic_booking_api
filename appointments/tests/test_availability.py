from datetime import date, time
from unittest.mock import patch

import pytest
from django.utils import timezone

from appointments.models import Appointment, Doctor, DoctorWorkingHour, Patient
from appointments.selectors import (
    generate_slots,
    get_doctor_availability,
)


@pytest.mark.django_db
class TestGenerateSlots:
    def test_generates_30_minute_slots(self):
        selected_date = date(2026, 7, 20)

        slots = generate_slots(
            selected_date=selected_date,
            start_time=time(8, 0),
            end_time=time(10, 0),
        )

        assert len(slots) == 4
        assert slots[0].hour == 8
        assert slots[0].minute == 0
        assert slots[1].hour == 8
        assert slots[1].minute == 30
        assert slots[-1].hour == 9
        assert slots[-1].minute == 30


@pytest.mark.django_db
class TestDoctorAvailability:
    def setup_method(self):
        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.test@example.com",
            specialization="General Medicine",
        )

        self.patient = Patient.objects.create(
            full_name="John Doe",
            email="john.test@example.com",
            phone_number="+254700000001",
        )

        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(10, 0),
        )

    @patch("appointments.selectors.timezone.now")
    def test_returns_all_free_slots(self, mocked_now):
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        availability = get_doctor_availability(
            doctor=self.doctor,
            selected_date=date(2026, 7, 20),
        )

        assert len(availability) == 4

    @patch("appointments.selectors.timezone.now")
    def test_excludes_booked_slot(self, mocked_now):
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        booked_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                8,
                30,
            )
        )

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=booked_time,
        )

        availability = get_doctor_availability(
            doctor=self.doctor,
            selected_date=date(2026, 7, 20),
        )

        returned_start_times = {
            slot["start_time"]
            for slot in availability
        }

        assert booked_time not in returned_start_times
        assert len(availability) == 3

    @patch("appointments.selectors.timezone.now")
    def test_returns_empty_list_on_non_working_day(
        self,
        mocked_now,
    ):
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        availability = get_doctor_availability(
            doctor=self.doctor,
            selected_date=date(2026, 7, 21),
        )

        assert availability == []