from django.core.exceptions import ValidationError #allows your model to reject invalid data with a meaningful message
from django.db import models #imports Django’s database modeling tools.
from django.db.models import Q #Q object represents a database condition.Q is used inside database constraints.


class Doctor(models.Model):
    """
    Represents a doctor in the clinic.
    """

    full_name = models.CharField(max_length=100)#stores the doctor’s name as short text.
    email = models.EmailField(unique=True)#EmailField provides email-format validation through Django forms, serializers, and model validation.
    specialization = models.CharField(max_length=100)#This stores the doctor’s medical specialization.
    is_active = models.BooleanField(default=True) #A doctor who leaves the clinic does not necessarily have to be deleted. You can mark them inactive:

    created_at = models.DateTimeField(auto_now_add=True)#auto_now implies This updates every time the doctor record is saved.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:#Meta contains extra instructions about the model. This tells Django: By default, sort doctors alphabetically by full_name.
        ordering = ["full_name"]#Doctor.objects.all().order_by("full_name")

    def __str__(self): #This controls how a doctor object is displayed as text.
        return self.full_name


class Patient(models.Model):
    """
    Represents a patient who can book appointments.
    """

    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class DoctorWorkingHour(models.Model):#This model stores a doctor’s working period for a particular weekday.
    """
    Defines a doctor's working period for a particular weekday.
    Python constant:Weekday.MONDAY
    Database value:0
Human-readable label:Monday
    """

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE, #This tells Django what to do with the working hours if the doctor is deleted.
        related_name="working_hours",
    )#This creates a relationship between DoctorWorkingHour and Doctor

    weekday = models.IntegerField(
        choices=Weekday.choices,
    )#This stores the selected weekday as an integer.Django automatically creates get_weekday_display() because the field has choices.

    start_time = models.TimeField()
    end_time = models.TimeField()

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["doctor", "weekday", "start_time"]
        """
        Constraints are rules enforced by the database.This is important because application validation alone is not always enough.
        Imagine two requests reach the server at almost the same moment. A database constraint provides a final safety layer that protects the data.
        You have two working-hour constraints.
        """
        #Unique doctor working day
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "weekday"],
                name="unique_doctor_working_day",  #Every database constraint needs a name. Django uses this name in migrations and database error reporting.
            ),#Check end time after start time
            models.CheckConstraint(
                condition=Q(end_time__gt=models.F("start_time")),#models.f... means Use the value in this row’s start_time column.
                name="working_hour_end_after_start",#__gt-> greter than
            ),#so Q(end_time__gt=models.F("start_time")) implies end_time > start_time
        ]

    def clean(self):
        """
        Perform model-level validation before saving through forms,
        admin, or when full_clean() is called.
        """
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError(
                    {
                        "end_time": (
                            "End time must be later than start time."
                        )
                    }
                )

    def __str__(self):
        return (
            f"{self.doctor} - "
            f"{self.get_weekday_display()} "
            f"{self.start_time} to {self.end_time}"
        )


class Appointment(models.Model):
    """
    Represents an appointment between a doctor and a patient.
    """

    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        CANCELLED = "CANCELLED", "Cancelled"

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT, #protects historical data when say a doctor profile is deleted
        related_name="appointments",
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT, #protects historical data when say a patient profile is deleted
        related_name="appointments",
    )

    start_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
    )

    cancellation_reason = models.TextField(
        blank=True,
        default="",
    )

    cancelled_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

        #A doctor cannot have more than one booked appointment at the same exact start time.
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_time"],
                condition=Q(status="BOOKED"), #The uniqueness applies only where:status is booked
                name="unique_active_doctor_appointment_slot",
            ),
        ]

    @property 
    def end_time(self):
        """
        Return the appointment end time.

        Every appointment lasts 30 minutes.
        """
        from datetime import timedelta
        #Storing both values creates the possibility of inconsistent data:
        return self.start_time + timedelta(minutes=30)

    def __str__(self):
        return (
            f"{self.patient} with {self.doctor} "
            f"at {self.start_time}"
        )