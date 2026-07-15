from datetime import timedelta
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from appointments.models import Appointment, Doctor, Patient


def get_response_data(response: Response) -> dict[str, Any]:
    """
    Tell Pylance that the DRF response data is a dictionary.
    """
    return cast(dict[str, Any], response.data)


@pytest.mark.django_db
class TestPatientUpcomingAppointmentsAPI:
    def setup_method(self) -> None:
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.patient-list@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="John Doe",
            email="john.patient-list@example.com",
            phone_number="+254700000001",
        )

        self.other_patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.patient-list@example.com",
            phone_number="+254700000002",
        )

        self.url = reverse(
            "appointments:patient-upcoming-appointments",
            kwargs={
                "patient_id": self.patient.pk,
            },
        )

    @patch("appointments.selectors.timezone.now")
    def test_returns_upcoming_appointments_in_date_order(
        self,
        mocked_now: MagicMock,
    ) -> None:
        current_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                6,
                0,
            )
        )

        mocked_now.return_value = current_time

        later_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=current_time + timedelta(days=2),
            status=Appointment.Status.BOOKED,
        )

        earlier_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=current_time + timedelta(days=1),
            status=Appointment.Status.BOOKED,
        )

        response = cast(
            Response,
            self.client.get(self.url),
        )

        data = get_response_data(response)
        appointments = cast(
            list[dict[str, Any]],
            data["appointments"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(appointments) == 2

        assert appointments[0]["id"] == earlier_appointment.pk
        assert appointments[1]["id"] == later_appointment.pk

    @patch("appointments.selectors.timezone.now")
    def test_excludes_past_appointments(
        self,
        mocked_now: MagicMock,
    ) -> None:
        current_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                12,
                0,
            )
        )

        mocked_now.return_value = current_time

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=current_time - timedelta(days=1),
            status=Appointment.Status.BOOKED,
        )

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=current_time + timedelta(days=1),
            status=Appointment.Status.BOOKED,
        )

        response = cast(
            Response,
            self.client.get(self.url),
        )

        data = get_response_data(response)
        appointments = cast(
            list[dict[str, Any]],
            data["appointments"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(appointments) == 1

    @patch("appointments.selectors.timezone.now")
    def test_excludes_cancelled_appointments(
        self,
        mocked_now: MagicMock,
    ) -> None:
        current_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                12,
                0,
            )
        )

        mocked_now.return_value = current_time

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=current_time + timedelta(days=1),
            status=Appointment.Status.CANCELLED,
            cancellation_reason="Patient cancelled.",
            cancelled_at=current_time,
        )

        response = cast(
            Response,
            self.client.get(self.url),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["appointments"] == []

    @patch("appointments.selectors.timezone.now")
    def test_excludes_other_patients_appointments(
        self,
        mocked_now: MagicMock,
    ) -> None:
        current_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                12,
                0,
            )
        )

        mocked_now.return_value = current_time

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.other_patient,
            start_time=current_time + timedelta(days=1),
            status=Appointment.Status.BOOKED,
        )

        response = cast(
            Response,
            self.client.get(self.url),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["appointments"] == []

    def test_returns_404_for_unknown_patient(self) -> None:
        unknown_url = reverse(
            "appointments:patient-upcoming-appointments",
            kwargs={
                "patient_id": 99999,
            },
        )

        response = cast(
            Response,
            self.client.get(unknown_url),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
