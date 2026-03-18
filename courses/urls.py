from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index),

    path('courses/', views.courses, name='courses'),

    path("course/<int:course_id>/", views.course_detail, name="course_detail"),

    path('lesson/<int:lesson_id>/', views.lesson_view),
    
    path("enroll/<int:id>/",views.enroll_course,name="enroll_course"),

    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),

    path('register/', views.register_view, name='register'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

]