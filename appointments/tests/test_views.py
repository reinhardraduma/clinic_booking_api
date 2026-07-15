from datetime import datetime, timedelta
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from appointments.models import Appointment, Doctor, Patient
from appointments.services import (
    AppointmentAlreadyCancelledError,
    CancelledAppointmentError,
    SlotUnavailableError,
)


def get_response_data(response: Response) -> dict[str, Any]:
    """
    Return DRF response data as a dictionary.

    The cast helps Pylance understand that Response.data
    is not None in these tests.
    """
    return cast(dict[str, Any], response.data)


def make_aware_datetime(
    *,
    days_from_now: int,
    hour: int,
    minute: int = 0,
) -> datetime:
    """
    Create a future timezone-aware datetime.
    """
    future_date = timezone.localdate() + timedelta(
        days=days_from_now,
    )

    return timezone.make_aware(
        datetime.combine(
            future_date,
            datetime.min.time(),
        ).replace(
            hour=hour,
            minute=minute,
        )
    )


@pytest.mark.django_db
class TestAppointmentViews:
    def setup_method(self) -> None:
        """
        Create reusable test objects before every test.
        """
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.views@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="Test Patient",
            email="patient.views@example.com",
            phone_number="555-0100",
        )

        self.start_time = make_aware_datetime(
            days_from_now=7,
            hour=8,
            minute=0,
        )

        self.new_start_time = make_aware_datetime(
            days_from_now=7,
            hour=8,
            minute=30,
        )

        self.appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        self.health_url = reverse(
            "appointments:health-check",
        )

        self.availability_url = reverse(
            "appointments:doctor-availability",
            kwargs={
                "doctor_id": self.doctor.pk,
            },
        )

        self.create_url = reverse(
            "appointments:appointment-create",
        )

        self.cancel_url = reverse(
            "appointments:appointment-cancel",
            kwargs={
                "appointment_id": self.appointment.pk,
            },
        )

        self.reschedule_url = reverse(
            "appointments:appointment-reschedule",
            kwargs={
                "appointment_id": self.appointment.pk,
            },
        )

        self.patient_appointments_url = reverse(
            "appointments:patient-upcoming-appointments",
            kwargs={
                "patient_id": self.patient.pk,
            },
        )

    def test_health_check_returns_ok(self) -> None:
        """
        Confirm that the health-check endpoint returns 200.
        """
        response = cast(
            Response,
            self.client.get(self.health_url),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data == {
            "status": "ok",
            "service": "clinic-booking-api",
        }

    @patch("appointments.views.get_doctor_availability")
    def test_doctor_availability_returns_slots(
        self,
        mocked_get_availability: MagicMock,
    ) -> None:
        """
        Return serialized doctor availability information.
        """
        slot_start = make_aware_datetime(
            days_from_now=7,
            hour=9,
            minute=0,
        )

        slot_end = slot_start + timedelta(minutes=30)

        mocked_get_availability.return_value = [
            {
                "start_time": slot_start,
                "end_time": slot_end,
            }
        ]

        response = cast(
            Response,
            self.client.get(
                self.availability_url,
                {
                    "date": slot_start.date().isoformat(),
                },
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["doctor"] == {
            "id": self.doctor.pk,
            "full_name": self.doctor.full_name,
            "specialization": self.doctor.specialization,
        }
        assert data["slot_duration_minutes"] == 30
        assert len(data["available_slots"]) == 1

    def test_doctor_availability_returns_404_for_unknown_doctor(
        self,
    ) -> None:
        """
        Return 404 when the requested doctor does not exist.
        """
        unknown_url = reverse(
            "appointments:doctor-availability",
            kwargs={
                "doctor_id": 99999,
            },
        )

        response = cast(
            Response,
            self.client.get(
                unknown_url,
                {
                    "date": self.start_time.date().isoformat(),
                },
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("appointments.views.book_appointment")
    def test_appointment_create_returns_201(
        self,
        mocked_book_appointment: MagicMock,
    ) -> None:
        """
        Return the created appointment when booking succeeds.
        """
        mocked_book_appointment.return_value = self.appointment

        response = cast(
            Response,
            self.client.post(
                self.create_url,
                {
                    "doctor_id": self.doctor.pk,
                    "patient_id": self.patient.pk,
                    "start_time": self.start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] == self.appointment.pk
        assert data["status"] == Appointment.Status.BOOKED

        mocked_book_appointment.assert_called_once()

    @patch("appointments.views.book_appointment")
    def test_appointment_create_handles_validation_error(
        self,
        mocked_book_appointment: MagicMock,
    ) -> None:
        """
        Return 400 when appointment validation fails.
        """
        mocked_book_appointment.side_effect = ValidationError(
            "The requested appointment is invalid."
        )

        response = cast(
            Response,
            self.client.post(
                self.create_url,
                {
                    "doctor_id": self.doctor.pk,
                    "patient_id": self.patient.pk,
                    "start_time": self.start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data["code"] == "invalid_appointment"
        assert data["detail"] == (
            "The requested appointment is invalid."
        )

    @patch("appointments.views.book_appointment")
    def test_appointment_create_handles_slot_unavailable(
        self,
        mocked_book_appointment: MagicMock,
    ) -> None:
        """
        Return 409 when the selected slot becomes unavailable.
        """
        mocked_book_appointment.side_effect = SlotUnavailableError(
            "The selected appointment slot is no longer available."
        )

        response = cast(
            Response,
            self.client.post(
                self.create_url,
                {
                    "doctor_id": self.doctor.pk,
                    "patient_id": self.patient.pk,
                    "start_time": self.start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data == {
            "code": "slot_unavailable",
            "detail": (
                "The selected appointment slot "
                "is no longer available."
            ),
        }

    def test_appointment_create_rejects_missing_fields(self) -> None:
        """
        Return 400 when required booking fields are missing.
        """
        response = cast(
            Response,
            self.client.post(
                self.create_url,
                {},
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "doctor_id" in data
        assert "patient_id" in data
        assert "start_time" in data

    @patch("appointments.views.cancel_appointment")
    def test_appointment_cancel_returns_200(
        self,
        mocked_cancel_appointment: MagicMock,
    ) -> None:
        """
        Return the cancelled appointment when cancellation succeeds.
        """
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.cancellation_reason = "Patient changed plans."
        self.appointment.cancelled_at = timezone.now()

        mocked_cancel_appointment.return_value = self.appointment

        response = cast(
            Response,
            self.client.patch(
                self.cancel_url,
                {
                    "reason": "Patient changed plans.",
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == self.appointment.pk
        assert data["status"] == Appointment.Status.CANCELLED
        assert data["cancellation_reason"] == (
            "Patient changed plans."
        )

    @patch("appointments.views.cancel_appointment")
    def test_appointment_cancel_handles_already_cancelled(
        self,
        mocked_cancel_appointment: MagicMock,
    ) -> None:
        """
        Return 409 when the appointment was already cancelled.
        """
        mocked_cancel_appointment.side_effect = (
            AppointmentAlreadyCancelledError(
                "This appointment has already been cancelled."
            )
        )

        response = cast(
            Response,
            self.client.patch(
                self.cancel_url,
                {
                    "reason": "Trying again.",
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data == {
            "code": "appointment_already_cancelled",
            "detail": (
                "This appointment has already been cancelled."
            ),
        }

    def test_appointment_cancel_returns_404_for_unknown_appointment(
        self,
    ) -> None:
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
                    "reason": "Patient changed plans.",
                },
                format="json",
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("appointments.views.reschedule_appointment")
    def test_appointment_reschedule_returns_200(
        self,
        mocked_reschedule_appointment: MagicMock,
    ) -> None:
        """
        Return the updated appointment after successful rescheduling.
        """
        self.appointment.start_time = self.new_start_time

        mocked_reschedule_appointment.return_value = self.appointment

        response = cast(
            Response,
            self.client.patch(
                self.reschedule_url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == self.appointment.pk

        mocked_reschedule_appointment.assert_called_once()

    @patch("appointments.views.reschedule_appointment")
    def test_reschedule_handles_cancelled_appointment(
        self,
        mocked_reschedule_appointment: MagicMock,
    ) -> None:
        """
        Return 409 when attempting to reschedule a cancelled appointment.
        """
        mocked_reschedule_appointment.side_effect = (
            CancelledAppointmentError(
                "A cancelled appointment cannot be rescheduled."
            )
        )

        response = cast(
            Response,
            self.client.patch(
                self.reschedule_url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data == {
            "code": "cancelled_appointment",
            "detail": (
                "A cancelled appointment cannot be rescheduled."
            ),
        }

    @patch("appointments.views.reschedule_appointment")
    def test_reschedule_handles_validation_error(
        self,
        mocked_reschedule_appointment: MagicMock,
    ) -> None:
        """
        Return 400 when the requested new time is invalid.
        """
        mocked_reschedule_appointment.side_effect = ValidationError(
            "The selected new time is invalid."
        )

        response = cast(
            Response,
            self.client.patch(
                self.reschedule_url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert data == {
            "code": "invalid_appointment",
            "detail": "The selected new time is invalid.",
        }

    @patch("appointments.views.reschedule_appointment")
    def test_reschedule_handles_slot_unavailable(
        self,
        mocked_reschedule_appointment: MagicMock,
    ) -> None:
        """
        Return 409 when the new slot becomes unavailable.
        """
        mocked_reschedule_appointment.side_effect = (
            SlotUnavailableError(
                "The selected appointment slot is no longer available."
            )
        )

        response = cast(
            Response,
            self.client.patch(
                self.reschedule_url,
                {
                    "start_time": self.new_start_time.isoformat(),
                },
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert data == {
            "code": "slot_unavailable",
            "detail": (
                "The selected appointment slot "
                "is no longer available."
            ),
        }

    def test_reschedule_rejects_missing_start_time(self) -> None:
        """
        Return 400 when the new start time is missing.
        """
        response = cast(
            Response,
            self.client.patch(
                self.reschedule_url,
                {},
                format="json",
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "start_time" in data

    @patch("appointments.views.get_patient_upcoming_appointments")
    def test_patient_upcoming_appointments_returns_200(
        self,
        mocked_get_appointments: MagicMock,
    ) -> None:
        """
        Return the patient and their upcoming appointments.
        """
        mocked_get_appointments.return_value = [
            self.appointment,
        ]

        response = cast(
            Response,
            self.client.get(
                self.patient_appointments_url,
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["patient"] == {
            "id": self.patient.pk,
            "full_name": self.patient.full_name,
        }
        assert len(data["appointments"]) == 1
        assert data["appointments"][0]["id"] == (
            self.appointment.pk
        )

    def test_patient_upcoming_appointments_returns_404(
        self,
    ) -> None:
        """
        Return 404 when the requested patient does not exist.
        """
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