# courses/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Trang chủ
    path('', views.index, name='index'),

    # Danh sách khóa học
    path('courses/', views.courses, name='courses'),

    # Chi tiết khóa học
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),

    # Xem bài học chi tiết
    path('lesson/<int:lesson_id>/', views.lesson_view, name='lesson_view'),

    # Đăng ký khóa học
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Quiz - Ôn luyện theo khóa học
    path('course/<int:course_id>/quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),

    # Ôn luyện tổng hợp (tất cả bài tập của user)
    path('on-luyen/', views.quiz_list_all, name='quiz_list_all'),

    # ====================== API REST ======================
    # (Tách biệt hoàn toàn với web, không ảnh hưởng code cũ)
    path('api/', include('courses.api.urls')),
]