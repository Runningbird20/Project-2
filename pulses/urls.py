from django.urls import path
from . import views

app_name = "pulses"

urlpatterns = [
    path("", views.pulses_feed, name="feed"),
    path("upload/", views.upload_pulse, name="upload"),
    path('delete/<int:pulse_id>/', views.delete_pulse, name='delete')
]
