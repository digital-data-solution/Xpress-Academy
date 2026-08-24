from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<str:token>/", views.reset_password, name="reset_password"),
]
