from django.urls import path

from appointments.views import (
    doctor_availability,
    health_check,
)


app_name = "appointments"

urlpatterns = [
    path(
        "health/",
        health_check,
        name="health-check",
    ),
    path(
        "doctors/<int:doctor_id>/availability/",
        doctor_availability,
        name="doctor-availability",
    ),
]