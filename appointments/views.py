from typing import Any, cast

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from appointments.models import Appointment, Doctor, Patient
from appointments.selectors import (
    get_doctor_availability,
    get_patient_upcoming_appointments,
)

from appointments.serializers import (
    AppointmentBookingSerializer,
    AppointmentCancellationSerializer,
    AppointmentRescheduleSerializer,
    AppointmentSerializer,
    AvailabilityQuerySerializer,
    AvailabilitySlotSerializer,
)
from appointments.services import (
    AppointmentAlreadyCancelledError,
    CancelledAppointmentError,
    SlotUnavailableError,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
)
from appointments.validators import SLOT_DURATION_MINUTES


@api_view(["GET"])
def health_check(request: Request) -> Response:
    """
    Confirm that the API service is running.
    """
    return Response(
        {
            "status": "ok",
            "service": "clinic-booking-api",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def doctor_availability(
    request: Request,
    doctor_id: int,
) -> Response:
    """
    Return all available appointment slots for a doctor
    on a requested date.
    """

    doctor = cast(
        Doctor,
        get_object_or_404(
            Doctor,
            pk=doctor_id,
            is_active=True,
        ),
    )

    query_serializer = AvailabilityQuerySerializer(
        data=request.query_params,
    )

    query_serializer.is_valid(raise_exception=True)

    validated_data = cast(
        dict[str, Any],
        query_serializer.validated_data,
    )

    selected_date = validated_data["date"]

    available_slots = get_doctor_availability(
        doctor=doctor,
        selected_date=selected_date,
    )

    slot_serializer = AvailabilitySlotSerializer(
        available_slots,
        many=True,
    )

    return Response(
        {
            "doctor": {
                "id": doctor.pk,
                "full_name": doctor.full_name,
                "specialization": doctor.specialization,
            },
            "date": selected_date,
            "slot_duration_minutes": SLOT_DURATION_MINUTES,
            "available_slots": slot_serializer.data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def appointment_create(request: Request) -> Response:
    """
    Book a new appointment.
    """

    input_serializer = AppointmentBookingSerializer(
        data=request.data,
    )

    input_serializer.is_valid(raise_exception=True)

    validated_data = cast(
        dict[str, Any],
        input_serializer.validated_data,
    )

    try:
        appointment = book_appointment(
            doctor=validated_data["doctor"],
            patient=validated_data["patient"],
            start_time=validated_data["start_time"],
        )

    except ValidationError as exc:
        message = (
            exc.messages[0]
            if exc.messages
            else "The appointment could not be booked."
        )

        return Response(
            {
                "code": "invalid_appointment",
                "detail": message,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except SlotUnavailableError as exc:
        return Response(
            {
                "code": "slot_unavailable",
                "detail": str(exc),
            },
            status=status.HTTP_409_CONFLICT,
        )

    output_serializer = AppointmentSerializer(
        appointment,
    )

    return Response(
        output_serializer.data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
def appointment_cancel(
    request: Request,
    appointment_id: int,
) -> Response:
    """
    Cancel an existing appointment with a reason.
    """

    appointment = cast(
        Appointment,
        get_object_or_404(
            Appointment,
            pk=appointment_id,
        ),
    )

    input_serializer = AppointmentCancellationSerializer(
        data=request.data,
    )

    input_serializer.is_valid(raise_exception=True)

    validated_data = cast(
        dict[str, Any],
        input_serializer.validated_data,
    )

    try:
        cancelled_appointment = cancel_appointment(
            appointment=appointment,
            reason=validated_data["reason"],
        )

    except AppointmentAlreadyCancelledError as exc:
        return Response(
            {
                "code": "appointment_already_cancelled",
                "detail": str(exc),
            },
            status=status.HTTP_409_CONFLICT,
        )

    output_serializer = AppointmentSerializer(
        cancelled_appointment,
    )

    return Response(
        output_serializer.data,
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
def appointment_reschedule(
    request: Request,
    appointment_id: int,
) -> Response:
    """
    Move an active appointment to a new valid slot.
    """

    appointment = cast(
        Appointment,
        get_object_or_404(
            Appointment,
            pk=appointment_id,
        ),
    )

    input_serializer = AppointmentRescheduleSerializer(
        data=request.data,
    )

    input_serializer.is_valid(raise_exception=True)

    validated_data = cast(
        dict[str, Any],
        input_serializer.validated_data,
    )

    try:
        rescheduled_appointment = reschedule_appointment(
            appointment=appointment,
            new_start_time=validated_data["start_time"],
        )

    except CancelledAppointmentError as exc:
        return Response(
            {
                "code": "cancelled_appointment",
                "detail": str(exc),
            },
            status=status.HTTP_409_CONFLICT,
        )

    except ValidationError as exc:
        message = (
            exc.messages[0]
            if exc.messages
            else "The appointment could not be rescheduled."
        )

        return Response(
            {
                "code": "invalid_appointment",
                "detail": message,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    except SlotUnavailableError as exc:
        return Response(
            {
                "code": "slot_unavailable",
                "detail": str(exc),
            },
            status=status.HTTP_409_CONFLICT,
        )

    output_serializer = AppointmentSerializer(
        rescheduled_appointment,
    )

    return Response(
        output_serializer.data,
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
def patient_upcoming_appointments(
    _request: Request,
    patient_id: int,
) -> Response:
    """
    Return a patient's upcoming booked appointments,
    sorted by appointment date.
    """

    patient = cast(
        Patient,
        get_object_or_404(
            Patient,
            pk=patient_id,
        ),
    )

    appointments = get_patient_upcoming_appointments(
        patient=patient,
    )

    serializer = AppointmentSerializer(
        appointments,
        many=True,
    )

    return Response(
        {
            "patient": {
                "id": patient.pk,
                "full_name": patient.full_name,
            },
            "appointments": serializer.data,
        },
        status=status.HTTP_200_OK,
    )