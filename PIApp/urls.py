from django.urls import path

from . import views

urlpatterns = [
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup, name="signup"),
    path("activity/", views.activity_setup, name="activity_setup"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("logout/", views.logout_view, name="logout"),
]
