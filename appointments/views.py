from typing import Any, cast

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from appointments.models import Doctor
from appointments.selectors import get_doctor_availability
from appointments.serializers import (
    AvailabilityQuerySerializer,
    AvailabilitySlotSerializer,
)

from django.core.exceptions import ValidationError

from appointments.serializers import (
    AppointmentBookingSerializer,
    AppointmentSerializer,
    AvailabilityQuerySerializer,
    AvailabilitySlotSerializer,
)
from appointments.services import (
    SlotUnavailableError,
    book_appointment,
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
    Return all available 30-minute slots for a doctor
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
            "slot_duration_minutes": 30,
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