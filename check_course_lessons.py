import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhoaHocTrucTuyen.settings')
django.setup()

from courses.models import Course, Lesson, Enrollment

# Check course 70 for lessons
try:
    course = Course.objects.get(id=70)
    lesson_count = course.lessons.count()
    first_lesson = course.lessons.order_by('order', 'id').first()
    print(f"Course 70: {course.title}")
    print(f"Lessons count: {lesson_count}")
    print(f"First lesson: {first_lesson}")
except Exception as e:
    print(f"Error: {e}")

# Check all courses and their lesson counts
print("\n--- All courses ---")
for course in Course.objects.all()[:5]:
    lesson_count = course.lessons.count()
    print(f"{course.id}: {course.title} - {lesson_count} lessons")
