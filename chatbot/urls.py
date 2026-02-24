from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    path("ask/", views.ask_panda, name="ask_panda"),
    path("greet/", views.panda_greet, name="panda_greet"),
    path("clear/", views.clear_history, name="clear_history"),
    path("feedback/", views.save_feedback, name="save_feedback"),
]
