from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from appointments.models import Appointment, Doctor, Patient
from appointments.services import (
    AppointmentAlreadyCancelledError,
    CancelledAppointmentError,
    SlotUnavailableError,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)


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
class TestAppointmentServices:
    def setup_method(self) -> None:
        """
        Create reusable doctor, patient, and appointment times.
        """
        self.doctor = Doctor.objects.create(
            full_name="Dr. Amina Hassan",
            email="amina.services@example.com",
            specialization="General Medicine",
            is_active=True,
        )

        self.patient = Patient.objects.create(
            full_name="Test Patient",
            email="patient.services@example.com",
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

    @patch("appointments.services.validate_appointment_slot")
    def test_book_appointment_creates_appointment(
        self,
        mocked_validate: MagicMock,
    ) -> None:
        """
        Create a booked appointment after validation succeeds.
        """
        appointment = book_appointment(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
        )

        assert appointment.pk is not None
        assert appointment.doctor == self.doctor
        assert appointment.patient == self.patient
        assert appointment.start_time == self.start_time
        assert appointment.status == Appointment.Status.BOOKED

        mocked_validate.assert_called_once_with(
            doctor=self.doctor,
            start_time=self.start_time,
        )

    @patch("appointments.services.Appointment.objects.create")
    @patch("appointments.services.validate_appointment_slot")
    def test_book_appointment_converts_integrity_error(
        self,
        mocked_validate: MagicMock,
        mocked_create: MagicMock,
    ) -> None:
        """
        Convert a database booking conflict into SlotUnavailableError.
        """
        mocked_create.side_effect = IntegrityError(
            "Duplicate appointment slot"
        )

        with pytest.raises(
            SlotUnavailableError,
            match=(
                "The selected appointment slot "
                "is no longer available."
            ),
        ):
            book_appointment(
                doctor=self.doctor,
                patient=self.patient,
                start_time=self.start_time,
            )

        mocked_validate.assert_called_once_with(
            doctor=self.doctor,
            start_time=self.start_time,
        )

    def test_cancel_appointment_updates_fields(self) -> None:
        """
        Cancel an active appointment and save its cancellation details.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        cancelled_appointment = cancel_appointment(
            appointment=appointment,
            reason="Patient changed plans.",
        )

        cancelled_appointment.refresh_from_db()

        assert (
            cancelled_appointment.status
            == Appointment.Status.CANCELLED
        )
        assert (
            cancelled_appointment.cancellation_reason
            == "Patient changed plans."
        )
        assert cancelled_appointment.cancelled_at is not None

    def test_cancel_appointment_rejects_already_cancelled(
        self,
    ) -> None:
        """
        Reject an appointment that has already been cancelled.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.CANCELLED,
        )

        with pytest.raises(
            AppointmentAlreadyCancelledError,
            match="This appointment has already been cancelled.",
        ):
            cancel_appointment(
                appointment=appointment,
                reason="Trying to cancel again.",
            )

    @patch("appointments.services.validate_appointment_slot")
    def test_reschedule_appointment_updates_start_time(
        self,
        mocked_validate: MagicMock,
    ) -> None:
        """
        Move an active appointment to a new valid time.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        rescheduled_appointment = reschedule_appointment(
            appointment=appointment,
            new_start_time=self.new_start_time,
        )

        rescheduled_appointment.refresh_from_db()

        assert (
            rescheduled_appointment.start_time
            == self.new_start_time
        )

        mocked_validate.assert_called_once_with(
            doctor=self.doctor,
            start_time=self.new_start_time,
            exclude_appointment_id=appointment.pk,
        )

    def test_reschedule_rejects_cancelled_appointment(
        self,
    ) -> None:
        """
        Reject rescheduling when the appointment is cancelled.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.CANCELLED,
        )

        with pytest.raises(
            CancelledAppointmentError,
            match=(
                "A cancelled appointment cannot be rescheduled."
            ),
        ):
            reschedule_appointment(
                appointment=appointment,
                new_start_time=self.new_start_time,
            )

    @patch("appointments.services.validate_appointment_slot")
    def test_reschedule_converts_integrity_error(
        self,
        mocked_validate: MagicMock,
    ) -> None:
        """
        Convert a database conflict during rescheduling into
        SlotUnavailableError.
        """
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            start_time=self.start_time,
            status=Appointment.Status.BOOKED,
        )

        with patch(
            "appointments.services."
            "Appointment.objects.select_for_update"
        ) as mocked_select_for_update:
            mocked_select_for_update.return_value.get.return_value = (
                appointment
            )

            with patch.object(
                appointment,
                "save",
                side_effect=IntegrityError(
                    "Duplicate appointment slot"
                ),
            ):
                with pytest.raises(
                    SlotUnavailableError,
                    match=(
                        "The selected appointment slot "
                        "is no longer available."
                    ),
                ):
                    reschedule_appointment(
                        appointment=appointment,
                        new_start_time=self.new_start_time,
                    )

        mocked_validate.assert_called_once_with(
            doctor=self.doctor,
            start_time=self.new_start_time,
            exclude_appointment_id=appointment.pk,
        )