from rest_framework import serializers
from appointments.models import Appointment, Doctor, Patient


class AvailabilityQuerySerializer(serializers.Serializer):
    """
    Validate query parameters for the doctor availability endpoint.
    """

    date = serializers.DateField(required=True)


class AvailabilitySlotSerializer(serializers.Serializer):
    """
    Format one available appointment slot.
    """

    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()

class AppointmentBookingSerializer(serializers.Serializer):
    """
    Validate data required to book an appointment.
    """

    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True),
        source="doctor",
    )

    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(),
        source="patient",
    )

    start_time = serializers.DateTimeField()


class DoctorSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = (
            "id",
            "full_name",
            "specialization",
        )


class PatientSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = (
            "id",
            "full_name",
        )


class AppointmentSerializer(serializers.ModelSerializer):
    doctor = DoctorSummarySerializer(read_only=True)
    patient = PatientSummarySerializer(read_only=True)
    end_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "doctor",
            "patient",
            "start_time",
            "end_time",
            "status",
            "cancellation_reason",
            "cancelled_at",
            "created_at",
            "updated_at",
        )


class AppointmentCancellationSerializer(serializers.Serializer):
    """
    Validate appointment cancellation input.
    """

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=500,
    )