# accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views   # views trong app accounts

app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    # thêm password_reset nếu cần
]