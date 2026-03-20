from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Level(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Grade(models.Model):
    name = models.CharField(max_length=50)
    level = models.ForeignKey(Level,on_delete=models.CASCADE)

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

    image = models.ImageField(
        upload_to='courses/',          
        blank=True,                  
        null=True,
        verbose_name="Ảnh khóa học",
        help_text="Kích thước khuyến nghị: 800x450px hoặc lớn hơn"
    )
    is_published = models.BooleanField(default=False, verbose_name="Đã xuất bản")
    
    
    def __str__(self):
        return self.title

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)

    video_url = models.URLField(max_length=500, blank=True, null=True,help_text="Dán link YouTube (watch, youtu.be, embed đều được)")
    video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)
    is_free_preview = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def get_youtube_id(self):
        if not self.video_url:  # Giả sử field là video_url (URLField)
            return None
        
        url = self.video_url.strip()  # loại bỏ khoảng trắng thừa
        
        # Xử lý các dạng phổ biến
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'v' in params:
            return params['v'][0]  # lấy ID từ ?v=...
        
        # Dạng youtu.be/...
        if 'youtu.be' in url:
            path = parsed.path.lstrip('/')
            return path.split('?')[0].split('&')[0]
        
        # Dạng embed/...
        if '/embed/' in url:
            return parsed.path.split('/embed/')[1].split('?')[0]
        
        return None


class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'  
    )
    created = models.DateTimeField(auto_now_add=True, null=True)

class Quiz(models.Model):
    """Bài tập ôn luyện gắn với một Lesson hoặc Course"""
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_limit = models.PositiveIntegerField(default=600)  # Tổng thời gian (giây), ví dụ 10 phút = 600s
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

        self.correct_answers = 0
        self.wrong_answers = 0
        self.score = 0
        self.total_points = sum(q.points for q in self.quiz.questions.all())


        if self.total_points > 0:
            self.percentage = (self.score / self.total_points) * 100
        self.completed = True
        self.finished_at = timezone.now()
        self.save()