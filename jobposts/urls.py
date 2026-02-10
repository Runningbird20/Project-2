from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create, name='jobposts.create'),
    path('search/', views.search, name='jobposts.search'),
]
