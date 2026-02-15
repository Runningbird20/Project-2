from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create, name='jobposts.create'),
    path('<int:post_id>/edit/', views.edit, name='jobposts.edit'),
    path('search/', views.search, name='jobposts.search'),
    path('dashboard/', views.dashboard, name='jobposts.dashboard'),
]
