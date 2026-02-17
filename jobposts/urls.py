from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create, name='jobposts.create'),
    path('<int:post_id>/edit/', views.edit, name='jobposts.edit'),
    path('search/', views.search, name='jobposts.search'),
    path('dashboard/', views.employer_dashboard, name='jobposts.dashboard'),
    path('edit_post/<int:post_id>/', views.edit_post, name='jobposts.edit_post'),
    path('remove_post/<int:post_id>/', views.remove_post, name='jobposts.remove_post'),
]
