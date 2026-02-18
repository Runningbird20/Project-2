from django.urls import path

from . import views

urlpatterns = [
    path('jobposts/<int:post_id>/', views.job_location, name='map.job_location'),
    path('jobs/', views.jobs_map, name='map.jobs_map'),
]
