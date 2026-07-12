from django.urls import path
from appointments.views import health_check


app_name = "appointments"

urlpatterns = [
    path("health/", health_check, name="health-check"),
] #the list Django searches when matching URLs.