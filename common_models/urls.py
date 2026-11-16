from django.urls import path

from .views import fetch_cities

app_name = "utilities"

urlpatterns = [
    path("fetch-cities", fetch_cities, name="fetch-cities"),
]
