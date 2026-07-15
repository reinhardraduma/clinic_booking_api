from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from appointments.models import (
    Doctor,
    DoctorWorkingHour,
    Patient,
)

DOCTORS = [
    {
        "full_name": "Dr. Maleek Hassan",
        "email": "maleek.hassan@ponauende.com",
        "specialization": "General Medicine",
    },
    {
        "full_name": "Dr. Sheila Wanjiku",
        "email": "sheila.wanjiku@ponauende.com",
        "specialization": "Pediatrics",
    },
    {
        "full_name": "Dr. Vera Shipalapala",
        "email": "vera.shipalapala@ponauende.com",
        "specialization": "Dermatology",
    },
    {
        "full_name": "Dr. Otieno Omondi",
        "email": "otieno.omondi@ponauende.com",
        "specialization": "Cardiology",
    },
    {
        "full_name": "Dr. Papa Waroma",
        "email": "papa.waroma@ponauende.com",
        "specialization": "Family Medicine",
    },
]


PATIENTS = [
    {
        "full_name": "John Dorimee",
        "email": "john.dorime@gmail.com",
        "phone_number": "+254700000001",
    },
    {
        "full_name": "Mary Wanjiku",
        "email": "mary.wanjiku001@gmail.com",
        "phone_number": "+254729000001",
    },
    {
        "full_name": "Judas Mtakahela",
        "email": "judas.mtakahela@gmail.com",
        "phone_number": "+254750649080",
    },
]


class Command(BaseCommand):
    help = "Create sample doctors, patients, and working hours."

    @transaction.atomic  # This means the entire seed operation is treated as one transaction.If the command fails halfway through:
    # ...Django rolls back the operation instead of leaving partially-created sample data.
    def handle(self, *args, **options):
        doctors = self.create_doctors()
        self.create_patients()
        self.create_working_hours(doctors)

        self.stdout.write(self.style.SUCCESS("Sample clinic data created successfully."))

    def create_doctors(self):
        doctors = []

        for doctor_data in DOCTORS:
            doctor, created = Doctor.objects.update_or_create(
                email=doctor_data["email"],
                defaults={
                    "full_name": doctor_data["full_name"],
                    "specialization": doctor_data["specialization"],
                    "is_active": True,
                },
            )

            doctors.append(doctor)

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} doctor: {doctor.full_name}")

        return doctors

    def create_patients(self):
        for patient_data in PATIENTS:
            patient, created = Patient.objects.update_or_create(
                email=patient_data["email"],
                defaults={
                    "full_name": patient_data["full_name"],
                    "phone_number": patient_data["phone_number"],
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} patient: {patient.full_name}")

    def create_working_hours(self, doctors):
        weekdays = [
            DoctorWorkingHour.Weekday.MONDAY,
            DoctorWorkingHour.Weekday.TUESDAY,
            DoctorWorkingHour.Weekday.WEDNESDAY,
            DoctorWorkingHour.Weekday.THURSDAY,
            DoctorWorkingHour.Weekday.FRIDAY,
        ]

        for doctor in doctors:
            for weekday in weekdays:
                working_hour, created = DoctorWorkingHour.objects.update_or_create(
                    doctor=doctor,
                    weekday=weekday,
                    defaults={
                        "start_time": time(8, 0),
                        "end_time": time(16, 0),
                        "is_active": True,
                    },
                )

                action = "Created" if created else "Updated"

                self.stdout.write(f"{action} working hours: {working_hour}")
