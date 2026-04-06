# accounts/urls.py
from django.urls import path
from . import views   # views trong app accounts

urlpatterns = [
    path('password-reset/', views.forgot_password_request, name='password_reset'),
    path('password-reset/verify/', views.forgot_password_verify, name='password_reset_verify'),
    path('password-reset/new/', views.forgot_password_new, name='password_reset_new'),
]