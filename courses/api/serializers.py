from rest_framework import serializers
from django.contrib.auth.models import User
from ..models import (
    Course, Quiz, Question, Choice, Lesson, Level, Grade, Subject,
    Enrollment, UserQuizAttempt, UserAnswer, Notification,
    LessonComment, CourseComment
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


# ==================== USER (Simple) ====================
class UserSimpleSerializer(serializers.ModelSerializer):
    """Hiển thị thông tin user cơ bản"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


# ==================== LESSON COMMENT ====================
class LessonCommentReplySerializer(serializers.ModelSerializer):
    """Serializer cho comment trả lời (nested)"""
    user = UserSimpleSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonComment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at', 'replies_count', 'is_root_comment']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_replies_count(self, obj):
        return obj.replies.count()


class LessonCommentSerializer(serializers.ModelSerializer):
    """Serializer cho comment bài học (gốc)"""
    user = UserSimpleSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = LessonComment
        fields = ['id', 'user', 'content', 'rating', 'created_at', 'updated_at', 'replies', 'is_root_comment']
        read_only_fields = ['id', 'created_at', 'updated_at', 'parent_comment']
    
    def get_replies(self, obj):
        """Lấy tất cả replies của comment này"""
        replies = obj.replies.all()
        serializer = LessonCommentReplySerializer(replies, many=True)
        return serializer.data


class LessonCommentCreateSerializer(serializers.ModelSerializer):
    """Dùng để tạo comment/reply mới"""
    class Meta:
        model = LessonComment
        fields = ['content', 'rating', 'parent_comment']
    
    def create(self, validated_data):
        parent_comment = validated_data.get('parent_comment')

        
        if parent_comment and not validated_data.get('rating'):
            validated_data['rating'] = parent_comment.rating or 5

        validated_data['user'] = self.context['request'].user
        validated_data['lesson_id'] = self.context['lesson_id']
        return super().create(validated_data)


# ==================== COURSE COMMENT ====================
class CourseCommentReplySerializer(serializers.ModelSerializer):
    """Serializer cho comment trả lời (nested)"""
    user = UserSimpleSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseComment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at', 'replies_count', 'is_root_comment']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_replies_count(self, obj):
        return obj.replies.count()


class CourseCommentSerializer(serializers.ModelSerializer):
    """Serializer cho comment khóa học (gốc)"""
    user = UserSimpleSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseComment
        fields = ['id', 'user', 'content', 'rating', 'created_at', 'updated_at', 'replies', 'is_root_comment']
        read_only_fields = ['id', 'created_at', 'updated_at', 'parent_comment']
    
    def get_replies(self, obj):
        """Lấy tất cả replies của comment này"""
        replies = obj.replies.all()
        serializer = CourseCommentReplySerializer(replies, many=True)
        return serializer.data


class CourseCommentCreateSerializer(serializers.ModelSerializer):
    """Dùng để tạo comment/reply mới"""
    class Meta:
        model = CourseComment
        fields = ['content', 'rating', 'parent_comment']
    
    def create(self, validated_data):
        parent_comment = validated_data.get('parent_comment')
        if parent_comment and not validated_data.get('rating'):
            validated_data['rating'] = parent_comment.rating or 5

        validated_data['user'] = self.context['request'].user
        validated_data['course_id'] = self.context['course_id']
        return super().create(validated_data)
