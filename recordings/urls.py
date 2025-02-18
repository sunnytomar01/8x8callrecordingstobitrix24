from django.urls import path
from . import views  # Import views

urlpatterns = [
    path("list/", views.list_recordings, name="list_recordings"),
    path("recording/<str:object_id>/", views.get_recording, name="get_recording"),
]