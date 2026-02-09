from django.urls import path
from . import views

urlpatterns = [
    path('job_board/', views.job_board, name='apply.job_board'),
    path("apply/<int:job_id>/", views.apply_to_job, name="apply.apply_to_job"),
]
