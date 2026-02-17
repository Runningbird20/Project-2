from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create, name='jobposts.create'),
    path('<int:post_id>/edit/', views.edit, name='jobposts.edit'),
    path('search/', views.search, name='jobposts.search'),
    path('dashboard/', views.dashboard, name='jobposts.dashboard'),
    path('delete/<int:job_id>/', views.delete_job, name='jobposts.delete'),
    path('job/<int:post_id>/', views.job_detail, name='jobposts.detail'),
]
