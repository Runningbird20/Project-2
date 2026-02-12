from django.urls import path
from . import views

urlpatterns = [
    path('job_board/', views.job_board, name='apply.job_board'),
    path("apply/<int:job_id>/", views.apply_to_job, name="apply.apply_to_job"),
    path('status/', views.application_status, name='application_status'),
    path('update-status/<int:application_id>/', views.update_status, name='update_status'),
]
