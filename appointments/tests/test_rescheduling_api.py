from datetime import time
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from appointments.models import (
    Appointment,
    Doctor,
    DoctorWorkingHour,
    Patient,
)


def get_response_data(response: Response) -> dict[str, Any]:
    """
    Tell Pylance that the DRF response data is a dictionary.
    """
    return cast(dict[str, Any], response.data)


@pytest.mark.django_db
class TestAppointmentReschedulingAPI:
    def setup_method(self) -> None:
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.reschedule@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="John Doe",
            email="john.reschedule@example.com",
            phone_number="+254700000001",
        )

        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        self.original_start_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                10,
                0,
            )
        )

        self.new_start_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                11,
                0,
            )
        )

        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.original_start_time,
            status=Appointment.Status.BOOKED,
        )

        self.url = reverse(
            "appointments:appointment-reschedule",
            kwargs={
                "appointment_id": self.appointment.pk,
            },
        )

    @patch("appointments.validators.timezone.now")
    def test_reschedules_appointment(
        self,
        mocked_now: MagicMock,
    ) -> None:
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["start_time"] == (
            self.new_start_time.isoformat().replace("+00:00", "Z")
        )

        self.appointment.refresh_from_db()

        assert self.appointment.start_time == self.new_start_time

    @patch("appointments.validators.timezone.now")
    def test_original_slot_becomes_available(
        self,
        mocked_now: MagicMock,
    ) -> None:
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_200_OK

        replacement = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.original_start_time,
            status=Appointment.Status.BOOKED,
        )

        assert replacement.pk is not None

    @patch("appointments.validators.timezone.now")
    def test_rejects_taken_new_slot_and_preserves_original(
        self,
        mocked_now: MagicMock,
    ) -> None:
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        other_patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.reschedule@example.com",
            phone_number="+254700000002",
        )

        Appointment.objects.create(
            doctor=self.doctor,
            patient=other_patient,
            start_time=self.new_start_time,
            status=Appointment.Status.BOOKED,
        )

        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        self.appointment.refresh_from_db()

        assert (
            self.appointment.start_time
            == self.original_start_time
        )

    @patch("appointments.validators.timezone.now")
    def test_rejects_rescheduling_cancelled_appointment(
        self,
        mocked_now: MagicMock,
    ) -> None:
        mocked_now.return_value = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.cancellation_reason = "Patient cancelled"
        self.appointment.cancelled_at = timezone.now()

        self.appointment.save(
            update_fields=[
                "status",
                "cancellation_reason",
                "cancelled_at",
                "updated_at",
            ]
        )

        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data["code"] == "cancelled_appointment"

    def test_requires_new_start_time(self) -> None:
        response = cast(
            Response,
            self.client.patch(
                self.url,
                {},
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_time" in data

    def test_returns_404_for_unknown_appointment(self) -> None:
        unknown_url = reverse(
            "appointments:appointment-reschedule",
            kwargs={
                "appointment_id": 99999,
            },
        )

        response = cast(
            Response,
            self.client.patch(
                unknown_url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND