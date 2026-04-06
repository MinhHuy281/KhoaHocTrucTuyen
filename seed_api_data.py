from __future__ import annotations

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "KhoaHocTrucTuyen.settings")
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from accounts.models import UserProfile  # noqa: E402
from courses.models import (  # noqa: E402
    Choice,
    Course,
    Enrollment,
    Grade,
    Lesson,
    Level,
    Question,
    Quiz,
    Subject,
)


DEFAULT_TEACHER_USERNAME = "demo_teacher"
DEFAULT_STUDENT_USERNAME = "demo_student"
DEFAULT_PASSWORD = "Test@123456"


def get_or_create_user(username: str, email: str, role: str) -> User:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "first_name": "Demo",
            "last_name": role.title(),
        },
    )
    if created:
        user.set_password(DEFAULT_PASSWORD)
        user.save()
    else:
        changed = False
        if not user.email:
            user.email = email
            changed = True
        if changed:
            user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
    if profile.role != role:
        profile.role = role
        profile.save(update_fields=["role"])
    return user


def main() -> None:
    teacher = get_or_create_user(
        DEFAULT_TEACHER_USERNAME,
        "demo_teacher@example.com",
        "teacher",
    )
    student = get_or_create_user(
        DEFAULT_STUDENT_USERNAME,
        "demo_student@example.com",
        "student",
    )

    level, _ = Level.objects.get_or_create(name="Cơ bản")
    grade, _ = Grade.objects.get_or_create(name="Lớp 1", defaults={"level": level})
    if grade.level_id != level.id:
        grade.level = level
        grade.save(update_fields=["level"])

    subject, _ = Subject.objects.get_or_create(name="Tin học")

    course, created = Course.objects.get_or_create(
        title="Khóa học Python cơ bản",
        defaults={
            "description": "Khóa học mẫu để test API.",
            "price": 0,
            "is_free": True,
            "subject": subject,
            "grade": grade,
            "level": level,
            "teacher": teacher,
            "is_published": True,
        },
    )
    if not created:
        course.description = "Khóa học mẫu để test API."
        course.price = 0
        course.is_free = True
        course.subject = subject
        course.grade = grade
        course.level = level
        course.teacher = teacher
        course.is_published = True
        course.save()

    lesson1, _ = Lesson.objects.get_or_create(
        course=course,
        title="Giới thiệu Python",
        defaults={
            "content": "Nội dung bài học giới thiệu Python.",
            "order": 1,
            "is_free_preview": True,
        },
    )
    if lesson1.order != 1:
        lesson1.order = 1
        lesson1.save(update_fields=["order"])

    lesson2, _ = Lesson.objects.get_or_create(
        course=course,
        title="Biến và kiểu dữ liệu",
        defaults={
            "content": "Nội dung về biến và kiểu dữ liệu.",
            "order": 2,
            "is_free_preview": False,
        },
    )
    if lesson2.order != 2:
        lesson2.order = 2
        lesson2.save(update_fields=["order"])

    quiz, _ = Quiz.objects.get_or_create(
        course=course,
        lesson=lesson1,
        title="Quiz Python cơ bản",
        defaults={
            "description": "Quiz mẫu cho test API.",
            "time_limit": 600,
        },
    )

    question1, _ = Question.objects.get_or_create(
        quiz=quiz,
        text="Python là ngôn ngữ gì?",
        defaults={"order": 1, "points": 1},
    )
    if question1.order != 1:
        question1.order = 1
        question1.save(update_fields=["order"])

    question2, _ = Question.objects.get_or_create(
        quiz=quiz,
        text="Biến dùng để làm gì?",
        defaults={"order": 2, "points": 1},
    )
    if question2.order != 2:
        question2.order = 2
        question2.save(update_fields=["order"])

    choice_specs = [
        (question1, "Ngôn ngữ lập trình", True),
        (question1, "Hệ điều hành", False),
        (question1, "Trình duyệt web", False),
        (question2, "Lưu trữ dữ liệu", True),
        (question2, "Vẽ hình", False),
        (question2, "Kết nối Internet", False),
    ]
    for question, text, is_correct in choice_specs:
        choice, _ = Choice.objects.get_or_create(
            question=question,
            text=text,
            defaults={"is_correct": is_correct},
        )
        if choice.is_correct != is_correct:
            choice.is_correct = is_correct
            choice.save(update_fields=["is_correct"])

    enrollment, _ = Enrollment.objects.get_or_create(
        user=student,
        course=course,
        defaults={"status": "approved", "is_paid": True},
    )
    if enrollment.status != "approved" or not enrollment.is_paid:
        enrollment.status = "approved"
        enrollment.is_paid = True
        enrollment.save(update_fields=["status", "is_paid"])

    print("Seed dữ liệu đã sẵn sàng")
    print(f"Teacher: {teacher.username} / {DEFAULT_PASSWORD}")
    print(f"Student: {student.username} / {DEFAULT_PASSWORD}")
    print(f"Course: {course.id} - {course.title}")
    print(f"Lesson count: {course.lessons.count()}")
    print(f"Quiz count: {course.quizzes.count()}")
    print(f"Enrollment count: {course.enrollments.count()}")


if __name__ == "__main__":
    main()
