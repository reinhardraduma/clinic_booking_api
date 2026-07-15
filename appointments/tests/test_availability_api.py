from datetime import date, time
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient

from appointments.models import Doctor, DoctorWorkingHour


def get_response_data(response: Response) -> dict[str, Any]:
    """
    Return the DRF response body as a dictionary.

    DRF types Response.data as optional, so this cast helps
    Pylance understand the response data used in these tests.
    """
    return cast(dict[str, Any], response.data)


@pytest.mark.django_db
class TestDoctorAvailabilityAPI:
    def setup_method(self) -> None:
        """
        Create a fresh API client, doctor, working hours,
        and endpoint URL before every test.
        """
        self.client = APIClient()

        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.api@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        DoctorWorkingHour.objects.create(
            doctor=self.doctor,
            weekday=DoctorWorkingHour.Weekday.MONDAY,
            start_time=time(8, 0),
            end_time=time(10, 0),
        )

        self.url = reverse(
            "appointments:doctor-availability",
            kwargs={"doctor_id": self.doctor.pk},
        )

    @patch("appointments.selectors.timezone.now")
    def test_returns_available_slots(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Return four 30-minute slots between 8:00 AM
        and 10:00 AM.
        """
        mocked_now.return_value = timezone.make_aware(timezone.datetime(2026, 7, 20, 6, 0))

        response = cast(
            Response,
            self.client.get(
                self.url,
                {"date": "2026-07-20"},
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK

        assert data["doctor"] == {
            "id": self.doctor.pk,
            "full_name": self.doctor.full_name,
            "specialization": self.doctor.specialization,
        }

        assert data["date"] == date(2026, 7, 20)
        assert data["slot_duration_minutes"] == 30
        assert len(data["available_slots"]) == 4

    def test_requires_date_parameter(self) -> None:
        """
        Return 400 when the date query parameter is missing.
        """
        response = cast(
            Response,
            self.client.get(self.url),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in data

    def test_rejects_invalid_date(self) -> None:
        """
        Return 400 when the date query parameter is invalid.
        """
        response = cast(
            Response,
            self.client.get(
                self.url,
                {"date": "not-a-date"},
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "date" in data

    def test_returns_404_for_unknown_doctor(self) -> None:
        """
        Return 404 when the requested doctor does not exist.
        """
        unknown_url = reverse(
            "appointments:doctor-availability",
            kwargs={"doctor_id": 99999},
        )

        response = cast(
            Response,
            self.client.get(
                unknown_url,
                {"date": "2026-07-20"},
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_inactive_doctor(self) -> None:
        """
        Return 404 when the requested doctor is inactive.
        """
        self.doctor.is_active = False
        self.doctor.save()

        response = cast(
            Response,
            self.client.get(
                self.url,
                {"date": "2026-07-20"},
            ),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("appointments.selectors.timezone.now")
    def test_returns_empty_slots_on_non_working_day(
        self,
        mocked_now: MagicMock,
    ) -> None:
        """
        Return an empty list when the doctor does not work
        on the requested weekday.
        """
        mocked_now.return_value = timezone.make_aware(timezone.datetime(2026, 7, 20, 6, 0))

        response = cast(
            Response,
            self.client.get(
                self.url,
                {"date": "2026-07-21"},
            ),
        )

        data = get_response_data(response)

        assert response.status_code == status.HTTP_200_OK
        assert data["date"] == date(2026, 7, 21)
        assert data["available_slots"] == []
