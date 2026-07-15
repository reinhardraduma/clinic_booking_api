from django.urls import path

from appointments.views import (
    appointment_create,
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
    "appointments/",
    appointment_create,
    name="appointment-create",
    ),
    path(
        "doctors/<int:doctor_id>/availability/",
        doctor_availability,
        name="doctor-availability",
    ),
]