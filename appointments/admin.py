from django.contrib import admin

from appointments.models import (
    Appointment,
    Doctor,
    DoctorWorkingHour,
    Patient,
)


@admin.register(Doctor) #is equivalent to admin.site.register(Doctor, DoctorAdmin)
class DoctorAdmin(admin.ModelAdmin):
    #This controls the columns shown on the admin list page.
    list_display = (
        "id",
        "full_name",
        "email",
        "specialization",
        "is_active",
    )#This adds filters on the right side of the admin.
    list_filter = (
        "is_active",
        "specialization",
    )#This adds a search box.
    search_fields = (
        "full_name",
        "email",
        "specialization",
    )
    ordering = ("full_name",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email",
        "phone_number",
    )
    search_fields = (
        "full_name",
        "email",
        "phone_number",
    )
    ordering = ("full_name",)


@admin.register(DoctorWorkingHour)
class DoctorWorkingHourAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor",
        "weekday",
        "start_time",
        "end_time",
        "is_active",
    )
    list_filter = (
        "weekday",
        "is_active",
    )
    search_fields = (
        "doctor__full_name", #The double underscore here: means Follow the foreign key relationship to Doctor, then search the full_name field.
        "doctor__email",
    )
    ordering = (
        "doctor",
        "weekday",
        "start_time",
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "doctor",
        "patient",
        "start_time",
        "status",
        "cancelled_at",
    )
    list_filter = (
        "status",
        "doctor",
    )
    search_fields = (
        "doctor__full_name",
        "patient__full_name",
        "patient__email",
    )
    ordering = ("start_time",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "cancelled_at",
    )