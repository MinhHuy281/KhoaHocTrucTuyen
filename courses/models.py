from django.db import models
from django.contrib.auth.models import User


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

    # ✅ THÊM TEACHER
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    image = models.ImageField(
        upload_to='courses/',
        blank=True,
        null=True,
        verbose_name="Ảnh khóa học",
        help_text="Kích thước khuyến nghị: 800x450px hoặc lớn hơn"
    )

    is_published = models.BooleanField(default=False, verbose_name="Đã xuất bản")

    def __str__(self):
        return f"{self.title} - {self.teacher}"


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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"