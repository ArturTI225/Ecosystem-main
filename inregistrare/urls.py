from django.urls import path

from .views import edit_profile, login_view, logout, profile, register

urlpatterns = [
    path("signup/", register, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout, name="logout"),
    path("profile/", profile, name="inregistrare_profile"),
    path("edit_profile/", edit_profile, name="edit_profile"),
]
