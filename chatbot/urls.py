from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.ask_panda, name='ask_panda'),
    path('clear/', views.clear_history, name='clear_history'),
    path('feedback/', views.save_feedback, name='save_feedback'),
    path('chatbot/greet/', views.panda_greet, name='panda_greet'),
]