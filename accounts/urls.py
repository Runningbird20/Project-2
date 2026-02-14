from django.urls import path
from . import views

urlpatterns = [
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('logout/', views.logout, name='accounts.logout'),
    path('profile/', views.profile, name='accounts.profile'),
    path('profile/edit/', views.edit_profile, name='accounts.profile_edit'),
    path('manage_users/', views.manage_users, name='accounts.manage_users'),
    path('edit_user/<int:user_id>/', views.edit_user, name='accounts.edit_user'),
    path('remove_user/<int:user_id>/', views.remove_user, name='accounts.remove_user'),
    path('profile/<str:username>/edit/', views.edit_profile, name='accounts.profile_edit_user'),
    path('profile/<str:username>/', views.public_profile, name='accounts.public_profile'),
]