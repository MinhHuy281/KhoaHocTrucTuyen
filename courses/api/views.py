from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from ..models import (
    Course, Quiz, Question, Choice, Lesson, Level, Grade, Subject,
    Enrollment, UserQuizAttempt, UserAnswer, Notification,
    LessonComment, CourseComment
)
from accounts.models import UserProfile
from .serializers import (
    CourseSerializer, CourseDetailSerializer, CourseCreateUpdateSerializer,
    QuizSerializer, QuizDetailSerializer,
    QuestionSerializer, QuestionDetailSerializer,
    ChoiceSerializer,
    LessonSerializer, LessonDetailSerializer,
    LevelSerializer, GradeSerializer, SubjectSerializer,
    EnrollmentSerializer, EnrollmentDetailSerializer,
    UserQuizAttemptSerializer, UserQuizAttemptDetailSerializer,
    UserAnswerSerializer,
    UserSerializer, UserDetailSerializer,
    NotificationSerializer,
    LessonCommentSerializer,
    LessonCommentCreateSerializer,
    CourseCommentSerializer,
    CourseCommentCreateSerializer
)
from .permissions import IsTeacher, IsTeacherOrReadOnly, IsTeacherOrOwner, IsEnrolledOrTeacher


# ==================== AUTHENTICATION ====================
class RegisterAPI(generics.CreateAPIView):
    """Đăng ký tài khoản mới"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        role = request.data.get('role', 'student')  # 'student' hoặc 'teacher'
        
        # Kiểm tra user đã tồn tại
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username đã tồn tại'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Tạo user mới
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Tạo profile
        UserProfile.objects.create(user=user, role=role)
        
        # Tạo token
        Token.objects.create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': Token.objects.get(user=user).key
        }, status=status.HTTP_201_CREATED)


class LoginAPI(generics.GenericAPIView):
    """Đăng nhập và lấy token"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = User.objects.filter(username=username).first()
        if not user:
            return Response({'error': 'Username hoặc password sai'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({'error': 'Username hoặc password sai'}, status=status.HTTP_401_UNAUTHORIZED)
        
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        })


class LogoutAPI(generics.GenericAPIView):
    """Đăng xuất (xóa token)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        return Response({'message': 'Đăng xuất thành công'})


# ==================== USER ====================
class UserDetailAPI(generics.RetrieveUpdateAPIView):
    """Lấy/cập nhật thông tin user"""
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserListAPI(generics.ListAPIView):
    """Danh sách users (chỉ admin)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================== LEVEL ====================
class LevelListAPI(generics.ListCreateAPIView):
    """Danh sách/tạo level"""
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class LevelDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa level"""
    queryset = Level.objects.all()
    serializer_class = LevelSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================== GRADE ====================
class GradeListAPI(generics.ListCreateAPIView):
    """Danh sách/tạo grade"""
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class GradeDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa grade"""
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================== SUBJECT ====================
class SubjectListAPI(generics.ListCreateAPIView):
    """Danh sách/tạo subject"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class SubjectDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa subject"""
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================== COURSE ====================
class CourseListAPI(generics.ListCreateAPIView):
    """Danh sách/tạo khóa học"""
    queryset = Course.objects.filter(is_published=True)
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    search_fields = ['title', 'description', 'subject__name']
    ordering_fields = ['created_at', 'title', 'price']
    ordering = ['-id']
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class CourseDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa khóa học"""
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsTeacherOrOwner]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CourseCreateUpdateSerializer
        return CourseDetailSerializer


class TeacherCoursesAPI(generics.ListAPIView):
    """Danh sách khóa học của giáo viên (bao gồm chưa xuất bản)"""
    serializer_class = CourseSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return Course.objects.filter(teacher=self.request.user)


# ==================== LESSON ====================
class LessonListAPI(generics.ListCreateAPIView):
    """Danh sách/tạo bài học"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        return Lesson.objects.filter(course_id=course_id)
    
    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        serializer.save(course=course)


class LessonDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa bài học"""
    serializer_class = LessonDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Lesson.objects.all()


# ==================== QUIZ ====================
class QuizListByCourseAPI(generics.ListCreateAPIView):
    """Danh sách/tạo quiz theo khóa học"""
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return Quiz.objects.filter(course_id=course_id)
    
    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        serializer.save(course=course)


class QuizDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa quiz"""
    queryset = Quiz.objects.all()
    serializer_class = QuizDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================== QUESTION ====================
class QuestionListByQuizAPI(generics.ListCreateAPIView):
    """Danh sách/tạo câu hỏi theo quiz"""
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        quiz_id = self.kwargs['quiz_id']
        return Question.objects.filter(quiz_id=quiz_id)
    
    def perform_create(self, serializer):
        quiz_id = self.kwargs.get('quiz_id')
        quiz = get_object_or_404(Quiz, id=quiz_id)
        serializer.save(quiz=quiz)


class QuestionDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa câu hỏi"""
    queryset = Question.objects.all()
    serializer_class = QuestionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================== CHOICE ====================
class ChoiceListByQuestionAPI(generics.ListCreateAPIView):
    """Danh sách/tạo lựa chọn theo câu hỏi"""
    serializer_class = ChoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        question_id = self.kwargs['question_id']
        return Choice.objects.filter(question_id=question_id)
    
    def perform_create(self, serializer):
        question_id = self.kwargs.get('question_id')
        question = get_object_or_404(Question, id=question_id)
        serializer.save(question=question)


class ChoiceDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Chi tiết/cập nhật/xóa lựa chọn"""
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================== ENROLLMENT ====================
class EnrollmentListAPI(generics.ListAPIView):
    """Danh sách đăng ký của user"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)


class EnrollmentDetailAPI(generics.RetrieveUpdateAPIView):
    """Chi tiết đăng ký"""
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentDetailSerializer
    permission_classes = [permissions.IsAuthenticated]


class EnrollCourseAPI(generics.CreateAPIView):
    """Đăng ký khóa học"""
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        course_id = kwargs.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        
        # Kiểm tra đã đăng ký
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {'error': 'Bạn đã đăng ký khóa học này'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Tạo enrollment
        enrollment = Enrollment.objects.create(
            user=request.user,
            course=course,
            status='pending',
            is_paid=course.is_free
        )
        
        # Nếu free, tự động approved
        if course.is_free:
            enrollment.approve()
        
        return Response(
            EnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED
        )


class EnrollmentsByTeacherAPI(generics.ListAPIView):
    """Danh sách học viên trong các khóa học của giáo viên"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return Enrollment.objects.filter(course__teacher=self.request.user)


# ==================== USER QUIZ ATTEMPT ====================
class StartQuizAPI(generics.CreateAPIView):
    """Bắt đầu bài quiz"""
    serializer_class = UserQuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        quiz_id = kwargs.get('quiz_id')
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Kiểm tra enrolled
        course = quiz.course
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if not enrollment or not enrollment.can_learn():
            return Response(
                {'error': 'Bạn chưa đăng ký khóa học này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Tạo attempt
        attempt = UserQuizAttempt.objects.create(user=request.user, quiz=quiz)
        return Response(
            UserQuizAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED
        )


class UserQuizAttemptAPI(generics.RetrieveUpdateAPIView):
    """Chi tiết attempt, submit đáp án"""
    queryset = UserQuizAttempt.objects.all()
    serializer_class = UserQuizAttemptDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        """Update đáp án"""
        attempt = self.get_object()
        
        # Chỉ user của attempt mới được update
        if attempt.user != request.user:
            return Response(
                {'error': 'Không có quyền cập nhật'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        answers = request.data.get('answers', [])
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            choice_id = answer_data.get('choice_id')
            
            question = get_object_or_404(Question, id=question_id)
            choice = get_object_or_404(Choice, id=choice_id) if choice_id else None
            
            UserAnswer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults={
                    'selected_choice': choice,
                    'is_correct': choice.is_correct if choice else False
                }
            )
        
        attempt.calculate_score()
        return Response(UserQuizAttemptDetailSerializer(attempt).data)


class UserAttemptListAPI(generics.ListAPIView):
    """Danh sách lần làm quiz của user"""
    serializer_class = UserQuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserQuizAttempt.objects.filter(user=self.request.user)


class QuizResultsByTeacherAPI(generics.ListAPIView):
    """Danh sách kết quả quiz của học viên cho các khóa học của giáo viên"""
    serializer_class = UserQuizAttemptSerializer
    permission_classes = [IsTeacher]
    
    def get_queryset(self):
        return UserQuizAttempt.objects.filter(quiz__course__teacher=self.request.user)


# ==================== NOTIFICATION ====================
class NotificationListAPI(generics.ListAPIView):
    """Danh sách thông báo của user"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationMarkAsReadAPI(generics.UpdateAPIView):
    """Đánh dấu thông báo đã đọc"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response(NotificationSerializer(notification).data)


# ==================== LESSON COMMENTS ====================
class LessonCommentViewSet(viewsets.ModelViewSet):
    """API ViewSet cho Lesson Comments"""
    permission_classes = [permissions.IsAuthenticated, IsEnrolledOrTeacher]
    
    def get_lesson(self):
        return get_object_or_404(Lesson, id=self.kwargs.get('lesson_id'))
    
    def get_queryset(self):
        lesson = self.get_lesson()
        return (
            lesson.comments
            .filter(parent_comment__isnull=True)
            .prefetch_related('user', 'replies__user')
            .order_by('-created_at')
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LessonCommentCreateSerializer
        return LessonCommentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['lesson_id'] = self.kwargs.get('lesson_id')
        return context
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'], url_path='reply')
    def reply_comment(self, request, pk=None, lesson_id=None):
        lesson = self.get_lesson()
        parent_comment = get_object_or_404(LessonComment, id=pk, lesson=lesson, parent_comment__isnull=True)
        
        serializer = LessonCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'lesson_id': lesson.id}
        )
        
        if serializer.is_valid():
            serializer.validated_data['parent_comment'] = parent_comment
            serializer.save()
            return Response(
                LessonCommentSerializer(serializer.instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None, lesson_id=None):
        lesson = self.get_lesson()
        comment = get_object_or_404(LessonComment, id=pk, lesson=lesson)
        
        if request.user != comment.user and request.user != lesson.course.teacher:
            return Response(
                {'error': 'Bạn không có quyền xóa comment này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ==================== COURSE COMMENTS ====================
class CourseCommentViewSet(viewsets.ModelViewSet):
    """API ViewSet cho Course Comments"""
    permission_classes = [permissions.IsAuthenticated, IsEnrolledOrTeacher]
    
    def get_course(self):
        return get_object_or_404(Course, id=self.kwargs.get('course_id'))
    
    def get_queryset(self):
        course = self.get_course()
        return (
            course.comments
            .filter(parent_comment__isnull=True)
            .prefetch_related('user', 'replies__user')
            .order_by('-created_at')
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CourseCommentCreateSerializer
        return CourseCommentSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['course_id'] = self.kwargs.get('course_id')
        return context
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['post'], url_path='reply')
    def reply_comment(self, request, pk=None, course_id=None):
        course = self.get_course()
        parent_comment = get_object_or_404(CourseComment, id=pk, course=course, parent_comment__isnull=True)
        
        serializer = CourseCommentCreateSerializer(
            data=request.data,
            context={'request': request, 'course_id': course.id}
        )
        
        if serializer.is_valid():
            serializer.validated_data['parent_comment'] = parent_comment
            serializer.save()
            return Response(
                CourseCommentSerializer(serializer.instance).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None, course_id=None):
        course = self.get_course()
        comment = get_object_or_404(CourseComment, id=pk, course=course)
        
        if request.user != comment.user and request.user != course.teacher:
            return Response(
                {'error': 'Bạn không có quyền xóa comment này'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
