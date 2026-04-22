from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from django.utils import timezone

class Level(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Grade(models.Model):
    name = models.CharField(max_length=50)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    is_free = models.BooleanField(default=True)

    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    grade = models.ForeignKey('Grade', on_delete=models.CASCADE)
    level = models.ForeignKey('Level', on_delete=models.CASCADE)

    # ✅ FIX NHẸ: thêm related_name (rất quan trọng cho notification & query)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='courses_teaching'
    )

    image = models.ImageField(
        upload_to='courses/',
        blank=True,
        null=True,
        verbose_name="Ảnh khóa học",
        help_text="Kích thước khuyến nghị: 800x450px hoặc lớn hơn"
    )

    is_published = models.BooleanField(default=False, verbose_name="Đã xuất bản")

    def __str__(self):
        # ✅ FIX: tránh None
        teacher_name = self.teacher.username if self.teacher else "No Teacher"
        return f"{self.title} - {teacher_name}"


class Lesson(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)

    video_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Dán link YouTube (watch, youtu.be, embed đều được)"
    )

    video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    slide_file = models.FileField(
        upload_to='lessons/slides/',
        blank=True,
        null=True,
        help_text="Tải file slide .ppt hoặc .pptx từ máy lên"
    )
    slide_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Dùng cho link slide cũ nếu chưa upload file"
    )

    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_free_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def get_youtube_id(self):
        if not self.video_url:
            return None

        import urllib.parse
        parsed = urllib.parse.urlparse(self.video_url)
        params = urllib.parse.parse_qs(parsed.query)

        if 'v' in params:
            return params['v'][0]

        if 'youtu.be' in self.video_url:
            return parsed.path.lstrip('/').split('?')[0]

        if '/embed/' in self.video_url:
            return parsed.path.split('/embed/')[1].split('?')[0]

        return None

class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Chờ thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('approved', 'Đã duyệt'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')

    created = models.DateTimeField(auto_now_add=True)

    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.user} - {self.course} - {self.status}"

    # ✅ THÊM HÀM NÀY (AUTO DUYỆT)
    def approve(self):
        self.is_paid = True
        self.status = 'approved'
        self.save()

    # ✅ CHECK QUYỀN HỌC
    def can_learn(self):
        return self.status == 'approved'

class Quiz(models.Model):
    """Bài tập ôn luyện gắn với một Lesson hoặc Course"""
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit = models.PositiveIntegerField(default=600)  # Tổng thời gian (giây), ví dụ 10 phút = 600s
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def minutes(self):
        """Trả về thời lượng bài ôn luyện theo phút (làm tròn lên)."""
        if self.time_limit <= 0:
            return 0
        return (self.time_limit + 59) // 60

    def __str__(self):
        return f"{self.title} - {self.course.title}"

    class Meta:
        ordering = ['-created_at']

class Question(models.Model):
    """Câu hỏi trắc nghiệm"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()  # Nội dung câu hỏi
    order = models.PositiveIntegerField(default=1)  # Thứ tự câu hỏi
    points = models.PositiveIntegerField(default=1)  # Điểm cho câu đúng

    def __str__(self):
        return self.text[:50]

    class Meta:
        ordering = ['order']

class Choice(models.Model):
    """Lựa chọn (option) cho câu hỏi"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:50]

class UserQuizAttempt(models.Model):
    """Kết quả làm bài của user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)  # Tổng điểm đạt được
    total_points = models.PositiveIntegerField(default=0)  # Tổng điểm có thể đạt
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)  # % đúng
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"

    def calculate_score(self):
        answers = self.answers.select_related('question', 'selected_choice').all()
        questions = list(self.quiz.questions.all())

        self.correct_answers = 0
        self.wrong_answers = 0
        self.score = 0
        self.total_points = sum(question.points for question in questions)

        for answer in answers:
            if answer.is_correct:
                self.correct_answers += 1
                self.score += answer.question.points

        self.wrong_answers = max(len(questions) - self.correct_answers, 0)

        if self.total_points > 0:
            self.percentage = (self.score / self.total_points) * 100
        else:
            self.percentage = 0

        self.completed = True
        self.finished_at = timezone.now()
        self.save()


class UserAnswer(models.Model):
    """Câu trả lời của user cho từng câu hỏi"""
    attempt = models.ForeignKey(UserQuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.text[:30]}"


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message


class LessonComment(models.Model):
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_comments')
    content = models.TextField(max_length=1000)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True  # Nested comments không cần rating
    )
    
    # 🆕 Hỗ trợ nested comments: comment trả lời comment
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.parent_comment:
            return f"{self.user.username} phản hồi {self.parent_comment.user.username} - {self.lesson.title}"
        return f"{self.user.username} - {self.lesson.title} ({self.rating} sao)"
    
    # 🆕 Lấy tất cả replies
    def get_all_replies(self):
        return self.replies.all().prefetch_related('user')
    
    # 🆕 Kiểm tra có phải comment gốc không
    def is_root_comment(self):
        return self.parent_comment is None


class CourseComment(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_comments')
    content = models.TextField(max_length=1000)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True  # Nested comments không cần rating
    )
    
    # 🆕 Hỗ trợ nested comments: comment trả lời comment
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.parent_comment:
            return f"{self.user.username} phản hồi {self.parent_comment.user.username} - {self.course.title}"
        return f"{self.user.username} - {self.course.title} ({self.rating} sao)"
    
    # 🆕 Lấy tất cả replies
    def get_all_replies(self):
        return self.replies.all().prefetch_related('user')
    
    # 🆕 Kiểm tra có phải comment gốc không
    def is_root_comment(self):
        return self.parent_comment is None