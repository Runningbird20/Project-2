from django.urls import path
from . import views

app_name = 'apply'  

urlpatterns = [
    path('submit/<int:job_id>/', views.submit_application, name='submit_application'),
    path('submitted/<int:job_id>/', views.application_submitted, name='application_submitted'),
    path('status/', views.application_status, name='application_status'),
    path('update-status/<int:application_id>/', views.update_status, name='update_status'),
    path('pipeline/<int:job_id>/', views.employer_pipeline, name='employer_pipeline'),
    path('archive/<int:application_id>/', views.archive_application, name='archive_application'),
    path('pipeline/archive/<int:application_id>/', views.archive_rejected_applicant, name='archive_rejected_applicant'),
    path('pipeline/<int:job_id>/export/', views.export_applicants_csv, name='export_applicants_csv'),
    path('offer-letter/<int:application_id>/', views.offer_letter, name='offer_letter'),

]
