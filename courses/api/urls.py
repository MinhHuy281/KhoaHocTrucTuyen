from django.urls import path
from . import views as api_views

urlpatterns = [
    path('courses/', api_views.CourseListAPI.as_view(), name='api-course-list'),
    path('courses/<int:pk>/', api_views.CourseDetailAPI.as_view(), name='api-course-detail'),
    path('courses/<int:course_id>/quizzes/', api_views.QuizListByCourseAPI.as_view(), name='api-quiz-list-by-course'),
]