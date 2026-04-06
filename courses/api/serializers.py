from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import (
    Course, Quiz, Question, Choice, Lesson, Level, Grade, Subject,
    Enrollment, UserQuizAttempt, UserAnswer, Notification
)
from accounts.models import UserProfile


# ==================== LEVEL, GRADE, SUBJECT ====================
class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id', 'name']


class GradeSerializer(serializers.ModelSerializer):
    level = LevelSerializer(read_only=True)
    
    class Meta:
        model = Grade
        fields = ['id', 'name', 'level']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']


# ==================== LESSON ====================
class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'video_url', 'video_file', 'content', 'order', 'is_free_preview']


class LessonDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = '__all__'


# ==================== CHOICE & QUESTION ====================
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'quiz', 'text', 'order', 'points', 'choices']


class QuestionDetailSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = '__all__'
        read_only_fields = ['quiz']


# ==================== QUIZ ====================
class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = ['id', 'course', 'lesson', 'title', 'description', 'time_limit', 'minutes', 'created_at', 'updated_at', 'question_count', 'questions']
    
    def get_question_count(self, obj):
        return obj.questions.count()


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = '__all__'


# ==================== USER & USER PROFILE ====================
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'role', 'phone', 'avatar', 'bio']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


class UserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']


# ==================== COURSE ====================
class CourseSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    level = LevelSerializer(read_only=True)
    grade = GradeSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    lesson_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'price', 'is_free', 'subject', 'grade', 'level', 'teacher', 'image', 'is_published', 'lesson_count']
    
    def get_lesson_count(self, obj):
        return obj.lessons.count()


class CourseDetailSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    level = LevelSerializer(read_only=True)
    grade = GradeSerializer(read_only=True)
    subject = SubjectSerializer(read_only=True)
    lessons = LessonSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
    
    def get_enrollment_count(self, obj):
        return obj.enrollments.count()


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['title', 'description', 'price', 'is_free', 'subject', 'grade', 'level', 'image', 'is_published']


# ==================== ENROLLMENT ====================
class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course', 'created', 'is_paid', 'status']


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    course = CourseDetailSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = '__all__'


# ==================== USER ANSWER ====================
class UserAnswerSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_choice = ChoiceSerializer(read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_choice', 'is_correct']


# ==================== USER QUIZ ATTEMPT ====================
class UserQuizAttemptSerializer(serializers.ModelSerializer):
    quiz = QuizSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    answers = UserAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserQuizAttempt
        fields = ['id', 'user', 'quiz', 'started_at', 'finished_at', 'score', 'total_points', 'correct_answers', 'wrong_answers', 'percentage', 'completed', 'answers']


class UserQuizAttemptDetailSerializer(serializers.ModelSerializer):
    quiz = QuizDetailSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    answers = UserAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserQuizAttempt
        fields = '__all__'


# ==================== NOTIFICATION ====================
class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read', 'created_at']
