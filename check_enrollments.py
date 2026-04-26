import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhoaHocTrucTuyen.settings')
django.setup()

from courses.models import Course, Enrollment

# Check all enrollments
print("--- All Enrollments ---")
for enrollment in Enrollment.objects.all():
    course = enrollment.course
    lesson_count = course.lessons.count()
    first_lesson = course.lessons.order_by('order', 'id').first()
    print(f"Enrollment {enrollment.id}: {enrollment.user.username} -> {course.title} (Lessons: {lesson_count}, First: {first_lesson})")

# Check courses with no lessons
print("\n--- Courses with NO lessons ---")
for course in Course.objects.all():
    if course.lessons.count() == 0:
        print(f"Course {course.id}: {course.title}")
