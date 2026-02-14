from django.urls import path
from . import views

app_name = 'apply'  

urlpatterns = [
    path('submit/<int:job_id>/', views.submit_application, name='submit_application'),
    path('status/', views.application_status, name='application_status'),
    path('update-status/<int:application_id>/', views.update_status, name='update_status'),
    path('pipeline/<int:job_id>/', views.employer_pipeline, name='employer_pipeline'),
    path('pipeline/<int:job_id>/export/', views.export_applicants_csv, name='export_applicants_csv'),
]