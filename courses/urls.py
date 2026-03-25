from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index),

    path('courses/', views.courses, name='courses'),

    path("course/<int:course_id>/", views.course_detail, name="course_detail"),

    path('lesson/<int:lesson_id>/', views.lesson_view),

    path("enroll/<int:id>/", views.enroll_course, name="enroll_course"),

    path('login/', views.login_view, name='login'),

    path('register/', views.register_view, name='register'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # ================= TEACHER =================
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),

    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),

    path('teacher/create/', views.teacher_create_course, name='create_courses'),

    path('teacher/edit/<int:id>/', views.teacher_edit_course, name='teacher_edit'),

    path('teacher/delete/<int:id>/', views.teacher_delete_course, name='teacher_delete'),

    path('teacher/course/<int:id>/', views.teacher_course_detail, name='teacher_course_detail'),
    
    path('teacher/course/<int:id>/quiz/create/', views.create_quiz, name='create_quiz'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
