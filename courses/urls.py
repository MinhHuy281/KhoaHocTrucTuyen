# courses/urls.py
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Trang chủ
    path('', views.index, name='index'),

    # Danh sách khóa học
    path('courses/', views.courses, name='courses'),

    # Danh sách giảng viên + thống kê
    path('teachers/', views.teachers_statistics, name='teachers_statistics'),

    # Chi tiết khóa học
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),

    # Xem bài học chi tiết
    path('lesson/<int:lesson_id>/', views.lesson_view, name='lesson_view'),

    # Đăng ký khóa học
    path('enroll/<int:course_id>/', views.enroll_course, name='enroll_course'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('teacher/login/', views.teacher_login_view, name='teacher_login'),
    path('teacher/register/', views.register_teacher_view, name='teacher_register'),

    path('register/', views.register_view, name='register'),

    path('logout/', views.logout_view, name='logout'),

    path('profile/', views.user_profile, name='user_profile'),

    # Quiz - Ôn luyện theo khóa học
    path('course/<int:course_id>/quizzes/', views.quiz_list, name='quiz_list'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),

    # Ôn luyện tổng hợp (tất cả bài tập của user)
    path('on-luyen/', views.quiz_list_all, name='quiz_list_all'),


    # ================= TEACHER =================
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),

    path('teacher/profile/', views.teacher_profile, name='teacher_profile'),

    path('teacher/students/', views.teacher_students, name='teacher_students'),

    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),

    path('teacher/create/', views.teacher_create_course, name='create_courses'),

    path('teacher/edit/<int:id>/', views.teacher_edit_course, name='teacher_edit'),

    path('teacher/delete/<int:id>/', views.teacher_delete_course, name='teacher_delete'),

    path('teacher/course/<int:id>/', views.teacher_course_detail, name='teacher_course_detail'),
    
    path('teacher/course/<int:id>/quiz/create/', views.create_quiz, name='create_quiz'),

    path('teacher/quizzes/', views.teacher_quiz_results, name='teacher_quiz_results'),
    
    path('teacher/attempt/<int:attempt_id>/', views.teacher_attempt_detail, name='teacher_attempt_detail'),
    
    # ===== QUIZ MANAGEMENT (Quản lý ôn luyện) =====
    path('teacher/quiz-management/', views.teacher_quiz_management, name='teacher_quiz_management'),
    
    path('teacher/quiz/create/', views.teacher_create_quiz_standalone, name='teacher_create_quiz_standalone'),
    
    path('teacher/quiz/<int:quiz_id>/edit/', views.teacher_edit_quiz, name='teacher_edit_quiz'),
    
    path('teacher/quiz/<int:quiz_id>/delete/', views.teacher_delete_quiz, name='teacher_delete_quiz'),


        # ====================== API REST ======================
    # (Tách biệt hoàn toàn với web, không ảnh hưởng code cũ)
    path('api/', include('courses.api.urls')),



    path('payment/<int:enrollment_id>/', views.payment, name='payment'),

    path('mark-notifications-read/', views.mark_notifications_read),
    



]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

