from django.urls import path
from . import views  # This imports the views from your PIApp folder

urlpatterns = [
    # This leaves the path empty so it loads right away at http://127.0.0
    path('', views.login, name='login'), 
]

