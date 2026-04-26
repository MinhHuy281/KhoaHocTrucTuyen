import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhoaHocTrucTuyen.settings')
django.setup()

from courses.models import Course, Lesson
from django.urls import reverse

course = Course.objects.get(id=70)
lesson = course.lessons.order_by('order', 'id').first()
if lesson:
    print(f"Lesson: {lesson}")
    print(f"Lesson ID: {lesson.id}")
    try:
        url = reverse('lesson_view', args=[lesson.id])
        print(f"Reversed URL: {url}")
    except Exception as e:
        print(f"Error reversing URL: {e}")
