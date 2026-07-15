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