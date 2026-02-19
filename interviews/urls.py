from django.urls import path

from . import views

app_name = "interviews"

urlpatterns = [
    path("propose/", views.propose_slot, name="propose"),
    path("book/<int:slot_id>/", views.book_slot, name="book"),
    path("ics/<int:slot_id>/", views.download_ics, name="download_ics"),
]

