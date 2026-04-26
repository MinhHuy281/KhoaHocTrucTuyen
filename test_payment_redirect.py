import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhoaHocTrucTuyen.settings')
django.setup()

from courses.models import Enrollment
from courses.views import get_payment_success_url

# Test with an actual enrollment
enrollments = Enrollment.objects.all()[:5]
print("--- Testing get_payment_success_url ---")
for enrollment in enrollments:
    success_url = get_payment_success_url(enrollment)
    course = enrollment.course
    lesson_count = course.lessons.count()
    first_lesson = course.lessons.order_by('order', 'id').first()
    print(f"\nEnrollment {enrollment.id}:")
    print(f"  Course: {course.title} (Lessons: {lesson_count})")
    print(f"  First Lesson: {first_lesson}")
    print(f"  Redirect URL: {success_url}")
    
    # Verify if it's a lesson or course URL
    if '/lesson/' in success_url:
        print(f"  ✅ Redirects to LESSON")
    else:
        print(f"  ❌ Redirects to COURSE")
