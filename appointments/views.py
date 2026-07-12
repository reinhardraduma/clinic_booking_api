from rest_framework.decorators import api_view #from the package rest framework ,we open decorator module and take the object api_view. api_view converts a normal Python function into a Django REST Framework API view.
from rest_framework.response import Response
from rest_framework import status


@api_view(["GET"]) # This decorator means the endpoint accepts only HTTP GET requests.
def health_check(request): #The request object contains information such as: HTTP method; headers; authenticated user; body data; query parameters.
    """
    Return a simple response confirming that the API is running.
    """
    return Response(
        {
            "status": "ok",
            "service": "clinic-booking-api",
        },
        status=status.HTTP_200_OK,
    ) #DRF’s Response class converts Python dictionaries into JSON.