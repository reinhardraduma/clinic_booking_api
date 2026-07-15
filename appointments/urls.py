from django.urls import path

from appointments.views import (
    appointment_create,
    appointment_cancel,
    appointment_reschedule,
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
    "appointments/<int:appointment_id>/cancel/",
    appointment_cancel,
    name="appointment-cancel",
    ),
    path(
    "appointments/<int:appointment_id>/reschedule/",
    appointment_reschedule,
    name="appointment-reschedule",
    ),
    path(
        "doctors/<int:doctor_id>/availability/",
        doctor_availability,
        name="doctor-availability",
    ),
]