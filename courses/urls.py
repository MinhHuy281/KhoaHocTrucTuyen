# courses/urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

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
    path('login/', views.login_view, name='login'),

    path('register/', views.register_view, name='register'),

    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Quiz - Ôn luyện theo khóa học
    path('course/<int:course_id>/quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),

    # Ôn luyện tổng hợp (tất cả bài tập của user)
    path('on-luyen/', views.quiz_list_all, name='quiz_list_all'),


    # ================= TEACHER =================
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),

    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),

    path('teacher/create/', views.teacher_create_course, name='create_courses'),

    path('teacher/edit/<int:id>/', views.teacher_edit_course, name='teacher_edit'),

    path('teacher/delete/<int:id>/', views.teacher_delete_course, name='teacher_delete'),

    path('teacher/course/<int:id>/', views.teacher_course_detail, name='teacher_course_detail'),
    
    path('teacher/course/<int:id>/quiz/create/', views.create_quiz, name='create_quiz'),

    path('teacher/quizzes/', views.teacher_quiz_results, name='teacher_quiz_results'),
    
    path('teacher/attempt/<int:attempt_id>/', views.teacher_attempt_detail, name='teacher_attempt_detail'),


        # ====================== API REST ======================
    # (Tách biệt hoàn toàn với web, không ảnh hưởng code cũ)
    path('api/', include('courses.api.urls')),



    path('payment/<int:enrollment_id>/', views.payment, name='payment'),

    path('mark-notifications-read/', views.mark_notifications_read),
    



]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

