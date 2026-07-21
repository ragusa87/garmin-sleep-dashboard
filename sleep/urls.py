from django.urls import path

from . import views

app_name = "sleep"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("setup/", views.setup, name="setup"),
    path("api/payload.json", views.payload_json, name="payload"),
]
