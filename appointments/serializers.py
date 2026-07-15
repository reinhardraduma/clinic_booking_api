from rest_framework import serializers


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