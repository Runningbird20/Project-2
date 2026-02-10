from django.urls import path
from . import views

urlpatterns = [
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('logout/', views.logout, name='accounts.logout'),
    path('profile/', views.profile, name='accounts.profile'),
    path("profile/edit/", views.edit_profile, name="accounts.profile_edit"),
    path("manage_accounts/", views.manage_accounts, name="accounts.manage_accounts"),
    path('remove_user/<int:user_id>/', views.remove_user, name='accounts.remove_user'),
]