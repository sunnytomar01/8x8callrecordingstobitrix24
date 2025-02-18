from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("recordings/", include("recordings.urls")),  # ✅ Include the recordings app with "recordings/" prefix
]
