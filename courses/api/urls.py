from django.urls import path
from . import views as api_views

urlpatterns = [
    # ==================== AUTH ====================
    path('auth/register/', api_views.RegisterAPI.as_view(), name='api-register'),
    path('auth/login/', api_views.LoginAPI.as_view(), name='api-login'),
    path('auth/logout/', api_views.LogoutAPI.as_view(), name='api-logout'),
    path('auth/user/', api_views.UserDetailAPI.as_view(), name='api-user-detail'),
    
    # ==================== LEVEL, GRADE, SUBJECT ====================
    path('levels/', api_views.LevelListAPI.as_view(), name='api-level-list'),
    path('levels/<int:pk>/', api_views.LevelDetailAPI.as_view(), name='api-level-detail'),
    
    path('grades/', api_views.GradeListAPI.as_view(), name='api-grade-list'),
    path('grades/<int:pk>/', api_views.GradeDetailAPI.as_view(), name='api-grade-detail'),
    
    path('subjects/', api_views.SubjectListAPI.as_view(), name='api-subject-list'),
    path('subjects/<int:pk>/', api_views.SubjectDetailAPI.as_view(), name='api-subject-detail'),
    
    # ==================== COURSE ====================
    path('courses/', api_views.CourseListAPI.as_view(), name='api-course-list'),
    path('courses/<int:pk>/', api_views.CourseDetailAPI.as_view(), name='api-course-detail'),
    path('my-courses/', api_views.TeacherCoursesAPI.as_view(), name='api-teacher-courses'),
    
    # ==================== LESSON ====================
    path('courses/<int:course_id>/lessons/', api_views.LessonListAPI.as_view(), name='api-lesson-list'),
    path('lessons/<int:pk>/', api_views.LessonDetailAPI.as_view(), name='api-lesson-detail'),
    
    # ==================== QUIZ ====================
    path('courses/<int:course_id>/quizzes/', api_views.QuizListByCourseAPI.as_view(), name='api-quiz-list-by-course'),
    path('quizzes/<int:pk>/', api_views.QuizDetailAPI.as_view(), name='api-quiz-detail'),
    
    # ==================== QUESTION ====================
    path('quizzes/<int:quiz_id>/questions/', api_views.QuestionListByQuizAPI.as_view(), name='api-question-list'),
    path('questions/<int:pk>/', api_views.QuestionDetailAPI.as_view(), name='api-question-detail'),
    
    # ==================== CHOICE ====================
    path('questions/<int:question_id>/choices/', api_views.ChoiceListByQuestionAPI.as_view(), name='api-choice-list'),
    path('choices/<int:pk>/', api_views.ChoiceDetailAPI.as_view(), name='api-choice-detail'),
    
    # ==================== ENROLLMENT ====================
    path('enrollments/', api_views.EnrollmentListAPI.as_view(), name='api-enrollment-list'),
    path('enrollments/<int:pk>/', api_views.EnrollmentDetailAPI.as_view(), name='api-enrollment-detail'),
    path('courses/<int:course_id>/enroll/', api_views.EnrollCourseAPI.as_view(), name='api-enroll-course'),
    path('teacher/enrollments/', api_views.EnrollmentsByTeacherAPI.as_view(), name='api-enrollments-by-teacher'),
    
    # ==================== QUIZ ATTEMPT ====================
    path('quizzes/<int:quiz_id>/start/', api_views.StartQuizAPI.as_view(), name='api-start-quiz'),
    path('attempts/<int:pk>/', api_views.UserQuizAttemptAPI.as_view(), name='api-attempt-detail'),
    path('my-attempts/', api_views.UserAttemptListAPI.as_view(), name='api-my-attempts'),
    path('teacher/quiz-results/', api_views.QuizResultsByTeacherAPI.as_view(), name='api-quiz-results-by-teacher'),
    
    # ==================== NOTIFICATION ====================
    path('notifications/', api_views.NotificationListAPI.as_view(), name='api-notification-list'),
    path('notifications/<int:pk>/read/', api_views.NotificationMarkAsReadAPI.as_view(), name='api-notification-mark-read'),
]
