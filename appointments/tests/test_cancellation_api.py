from datetime import time
from typing import Any, cast

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
class TestAppointmentCancellationAPI:
    def setup_method(self) -> None:
        """
        Create fresh test data before every test.
        """
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.cancel@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="John Doe",
            email="john.cancel@example.com",
            phone_number="+254700000001",
        )

        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(16, 0),
        )

        self.start_time = timezone.make_aware(
            timezone.datetime(
                2026,
                7,
                20,
                10,
                0,
            )
        )

        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        self.url = reverse(
            "appointments:appointment-cancel",
            kwargs={
                "appointment_id": self.appointment.pk,
            },
        )

    def test_cancels_booked_appointment(self) -> None:
        """
        Cancel a booked appointment and store the reason.
        """
        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "reason": "Patient is unavailable.",
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["status"] == Appointment.Status.CANCELLED
        assert data["cancellation_reason"] == ("Patient is unavailable.")
        assert data["cancelled_at"] is not None

        self.appointment.refresh_from_db()

        assert self.appointment.status == Appointment.Status.CANCELLED
        assert self.appointment.cancellation_reason == ("Patient is unavailable.")
        assert self.appointment.cancelled_at is not None

    def test_requires_cancellation_reason(self) -> None:
        """
        Return 400 when the cancellation reason is missing.
        """
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
        assert "reason" in data

    def test_rejects_blank_cancellation_reason(self) -> None:
        """
        Return 400 when the cancellation reason is blank.
        """
        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "reason": "   ",
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "reason" in data

    def test_rejects_second_cancellation(self) -> None:
        """
        Return 409 when an appointment is already cancelled.
        """
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.cancellation_reason = "Already cancelled"
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
                    "reason": "Cancel again",
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data["code"] == "appointment_already_cancelled"
        assert data["detail"] == ("This appointment has already been cancelled.")

    def test_returns_404_for_unknown_appointment(self) -> None:
        """
        Return 404 when the appointment does not exist.
        """
        unknown_url = reverse(
            "appointments:appointment-cancel",
            kwargs={
                "appointment_id": 99999,
            },
        )

        response = cast(
            Response,
            self.client.patch(
                unknown_url,
                {
                    "reason": "Patient unavailable",
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancelled_slot_can_be_booked_again(self) -> None:
        """
        Confirm that cancelling an appointment releases its slot.

        The cancelled row remains for history, while a new booked
        appointment may use the same doctor and start time.
        """
        response = cast(
            Response,
            self.client.patch(
                self.url,
                {
                    "reason": "Patient changed plans.",
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_200_OK

        self.appointment.refresh_from_db()

        assert self.appointment.status == Appointment.Status.CANCELLED

        replacement_patient = Patient.objects.create(
            full_name="Mary Wanjiku",
            email="mary.cancel@example.com",
            phone_number="+254700000002",
        )

        replacement_appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=replacement_patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        assert replacement_appointment.pk is not None

        appointments_for_slot = Appointment.objects.filter(
            doctor=self.doctor,
            start_time=self.start_time,
        )

        assert appointments_for_slot.count() == 2

        assert (
            appointments_for_slot.filter(
                status=Appointment.Status.CANCELLED,
            ).count()
            == 1
        )

        assert (
            appointments_for_slot.filter(
                status=Appointment.Status.BOOKED,
            ).count()
            == 1
        )
