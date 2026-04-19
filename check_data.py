import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KhoaHocTrucTuyen.settings')
django.setup()

from courses.models import Grade, Level, Subject

print("Levels:", Level.objects.count())
print("Grades:", Grade.objects.count()) 
print("Subjects:", Subject.objects.count())

if Level.objects.count() == 0:
    print("Creating test data...")
    l1 = Level.objects.create(name="Cấp 1")
    l2 = Level.objects.create(name="Cấp 2")
    g1 = Grade.objects.create(name="Lớp 1", level=l1)
    g2 = Grade.objects.create(name="Lớp 2", level=l1)
    g3 = Grade.objects.create(name="Lớp 3", level=l2)
    s1 = Subject.objects.create(name="Toán")
    s2 = Subject.objects.create(name="Tiếng Anh")
    s3 = Subject.objects.create(name="Lịch Sử")
    print("Test data created!")
    print("Levels:", Level.objects.count())
    print("Grades:", Grade.objects.count()) 
    print("Subjects:", Subject.objects.count())
