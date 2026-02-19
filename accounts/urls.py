from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("signup/", views.signup, name="accounts.signup"),
    path("login/", views.login, name="accounts.login"),
    path("forgot-username/", views.forgot_username, name="accounts.forgot_username"),
    path(
        "password-reset/",
        views.SafePasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts.password_reset_done"),
        ),
        name="accounts.password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="accounts.password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.SafePasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts.password_reset_complete"),
        ),
        name="accounts.password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="accounts.password_reset_complete",
    ),
    path("logout/", views.logout, name="accounts.logout"),
    path("profile/", views.profile, name="accounts.profile"),
    path("profile/<int:user_id>/", views.profile, name="accounts.profile_with_id"),
    path("profile/edit/", views.edit_profile, name="accounts.profile_edit"),
    path("profile/<str:username>/edit/", views.edit_profile, name="accounts.profile_edit_user"),
    path("profile/<str:username>/", views.public_profile, name="accounts.public_profile"),
    path("manage_users/", views.manage_users, name="accounts.manage_users"),
    path("edit_user/<int:user_id>/", views.edit_user, name="accounts.edit_user"),
    path("remove_user/<int:user_id>/", views.remove_user, name="accounts.remove_user"),
    path("candidates/", views.candidate_search, name="accounts.candidate_search"),
    path("export-usage/", views.export_usage_report, name="accounts.export_usage_report"),
    path("send-test-email/", views.send_test_email, name="accounts.send_test_email"),
    path("applicant-clusters-map/", views.applicant_clusters_map, name="accounts.applicant_clusters_map"),
    path("save-search/", views.save_candidate_search, name="accounts.save_search"),
    path("delete-search/<int:search_id>/", views.delete_candidate_search, name="accounts.delete_search"),

    # --- NEW ENDPOINT FOR AI CHATBOT ---
    path("update-bio/", views.update_bio_ajax, name="accounts.update_bio_ajax"),
]