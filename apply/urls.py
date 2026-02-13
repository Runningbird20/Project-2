from django.urls import path
from . import views

app_name = 'apply'  

urlpatterns = [
    #path('job_board/', views.job_board, name='apply.job_board'),
    path('apply/<int:job_id>/', views.submit_application, name='submit_application'),    
    path('status/', views.application_status, name='application_status'),
    path('update-status/<int:application_id>/', views.update_status, name='update_status'),
    path('submit/<int:job_id>/', views.submit_application, name='submit_application'),
]
