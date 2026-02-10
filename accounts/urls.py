from django.urls import path
from . import views

urlpatterns = [
    path('signup', views.signup, name='accounts.signup'),
    path('login/', views.login, name='accounts.login'),
    path('logout/', views.logout, name='accounts.logout'),
    path('profile/', views.profile, name='accounts.profile'),
    path("profile/edit/", views.edit_profile, name="accounts.profile_edit"),
    path("profile/<str:username>/", views.public_profile, name="accounts.public_profile"),
]
