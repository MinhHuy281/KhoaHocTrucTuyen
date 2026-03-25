from rest_framework import generics, permissions
from ..models import Course, Quiz
from .serializers import CourseSerializer, QuizSerializer

class CourseListAPI(generics.ListAPIView):
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CourseDetailAPI(generics.RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class QuizListByCourseAPI(generics.ListAPIView):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return Quiz.objects.filter(course_id=course_id)