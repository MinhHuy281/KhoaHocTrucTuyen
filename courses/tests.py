from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from accounts.models import UserProfile
from accounts.auth import SeparateSessionAuth

from .models import (
    Course, Level, Grade, Subject, Quiz, Question, Choice,
    Enrollment, UserQuizAttempt, Lesson, Notification
)


class TeacherDailyReportTestCase(TestCase):

    def setUp(self):
        self.level = Level.objects.create(name='Cấp 1')
        self.grade = Grade.objects.create(name='Lớp 1', level=self.level)
        self.subject = Subject.objects.create(name='Toán')
        self.teacher = User.objects.create_user(username='teacher1', password='123456', is_staff=True)
        self.student = User.objects.create_user(username='student1', password='123456')
        self.course = Course.objects.create(
            title='Khóa học toán',
            price=100000,
            is_free=False,
            level=self.level,
            grade=self.grade,
            subject=self.subject,
            teacher=self.teacher,
            is_published=True,
        )
        self.other_course = Course.objects.create(
            title='Khóa học văn',
            price=80000,
            is_free=False,
            level=self.level,
            grade=self.grade,
            subject=self.subject,
            teacher=self.teacher,
            is_published=True,
        )

        today_enrollment = Enrollment.objects.create(user=self.student, course=self.course)
        today_enrollment.approve()

        yesterday_enrollment = Enrollment.objects.create(user=self.student, course=self.other_course)
        yesterday = timezone.now() - timedelta(days=1)
        Enrollment.objects.filter(id=yesterday_enrollment.id).update(
            created=yesterday,
            paid_at=yesterday,
            status='approved',
            is_paid=True,
        )

        self.client = Client()
        session = self.client.session
        session['_teacher_auth_id'] = self.teacher.id
        session.save()

    def test_teacher_report_page_shows_report_data(self):
        response = self.client.get(reverse('teacher_report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Báo cáo ngày')
        self.assertContains(response, 'Khóa học toán')
        self.assertContains(response, 'Đăng ký trong ngày')
        self.assertContains(response, '100.000 VNĐ')

    def test_teacher_dashboard_no_longer_shows_report_block(self):
        response = self.client.get(reverse('teacher_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Báo cáo ngày')

class QuizTestCase(TestCase):

    def setUp(self):
        self.level = Level.objects.create(name="Cấp 1")
        self.grade = Grade.objects.create(name="Lớp 1", level=self.level)
        self.subject = Subject.objects.create(name="Toán")

        self.user = User.objects.create_user(username='testuser', password='123456')
        self.course = Course.objects.create(
            title="Toán lớp 1",
            price=1000,
            is_free=False,
            level=self.level,
            grade=self.grade,
            subject=self.subject,
            is_published=True
        )
        self.quiz = Quiz.objects.create(
            title="Bài kiểm tra số 1",
            course=self.course,
            time_limit=600
        )
        self.question = Question.objects.create(
            quiz=self.quiz,
            text="2 + 2 = ?",
            points=10
        )
        self.choice_correct = Choice.objects.create(
            question=self.question, text="4", is_correct=True
        )
        self.choice_wrong = Choice.objects.create(
            question=self.question, text="5", is_correct=False
        )

        Enrollment.objects.create(user=self.user, course=self.course)

        self.client = Client()
        session = self.client.session
        session[SeparateSessionAuth.USER_SESSION_KEY] = self.user.id
        session.save()

    # ==================== TEST CHO QUIZ LIST ====================

    def test_quiz_list_returns_200_for_enrolled_user(self):
        """User đã enroll phải truy cập được trang danh sách bài ôn luyện"""
        response = self.client.get(reverse('quiz_list', args=[self.course.id]))
        self.assertEqual(response.status_code, 200)

    def test_quiz_list_contains_quiz_title(self):
        """Trang quiz_list phải hiển thị tiêu đề quiz"""
        response = self.client.get(reverse('quiz_list', args=[self.course.id]))
        self.assertContains(response, "Bài kiểm tra số 1")

    def test_quiz_list_redirects_if_user_not_enrolled(self):
        """User chưa enroll phải bị redirect về trang chi tiết khóa học"""
        new_user = User.objects.create_user(username='newuser', password='123')
        new_session = self.client.session
        new_session[SeparateSessionAuth.USER_SESSION_KEY] = new_user.id
        new_session.save()

        response = self.client.get(reverse('quiz_list', args=[self.course.id]))
        self.assertRedirects(response, reverse('course_detail', args=[self.course.id]))

    # ==================== TEST CHO START QUIZ ====================

    def test_start_quiz_creates_new_attempt(self):
        """Gọi start_quiz phải tạo mới một UserQuizAttempt"""
        response = self.client.get(reverse('start_quiz', args=[self.quiz.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserQuizAttempt.objects.filter(user=self.user, quiz=self.quiz).exists())

    # ==================== TEST CHO TAKE QUIZ ====================

    def test_take_quiz_calculates_correct_score(self):
        """Chọn đáp án đúng phải tính điểm chính xác"""
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz)

        response = self.client.post(
            reverse('take_quiz', args=[attempt.id]),
            {f'question_{self.question.id}': self.choice_correct.id}
        )

        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 10)
        self.assertEqual(attempt.correct_answers, 1)
        self.assertEqual(attempt.percentage, 100.0)

    def test_take_quiz_calculates_wrong_score(self):
        """Chọn đáp án sai phải tính điểm = 0"""
        attempt = UserQuizAttempt.objects.create(user=self.user, quiz=self.quiz)

        response = self.client.post(
            reverse('take_quiz', args=[attempt.id]),
            {f'question_{self.question.id}': self.choice_wrong.id}
        )

        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 0)
        self.assertEqual(attempt.correct_answers, 0)
        self.assertEqual(attempt.percentage, 0.0)


class PaymentNotificationTestCase(TestCase):

    def setUp(self):
        self.level = Level.objects.create(name='Cấp 2')
        self.grade = Grade.objects.create(name='Lớp 6', level=self.level)
        self.subject = Subject.objects.create(name='Vật lý')

        self.teacher = User.objects.create_user(username='teacher_pay', password='123456', is_staff=True)
        self.student = User.objects.create_user(username='student_pay', password='123456')
        self.admin = User.objects.create_superuser(username='admin_pay', email='admin@example.com', password='123456')

        self.course = Course.objects.create(
            title='Khóa học vật lý',
            price=100000,
            is_free=False,
            level=self.level,
            grade=self.grade,
            subject=self.subject,
            teacher=self.teacher,
            is_published=True,
        )

        self.enrollment = Enrollment.objects.create(user=self.student, course=self.course)

        self.client = Client()
        session = self.client.session
        session[SeparateSessionAuth.USER_SESSION_KEY] = self.student.id
        session.save()

    def test_payment_confirm_notifies_teacher_and_admin_share(self):
        response = self.client.post(reverse('payment_confirm', args=[self.enrollment.id]))

        self.assertEqual(response.status_code, 200)

        teacher_notifications = Notification.objects.filter(
            user=self.teacher,
            message__icontains='Admin nhận 10000 VNĐ',
        )
        admin_notifications = Notification.objects.filter(
            user=self.admin,
            message__icontains='Đã nhận 10000 VNĐ (10%)',
        )

        self.assertEqual(teacher_notifications.count(), 1)
        self.assertEqual(admin_notifications.count(), 1)


class APITestCaseBase(APITestCase):
    def setUp(self):
        self.level = Level.objects.create(name="Cơ bản")
        self.grade = Grade.objects.create(name="Lớp 1", level=self.level)
        self.subject = Subject.objects.create(name="Tin học")

        self.teacher = User.objects.create_user(
            username="api_teacher",
            password="Test@123456",
            email="teacher@example.com",
            first_name="API",
            last_name="Teacher",
        )
        UserProfile.objects.create(user=self.teacher, role="teacher")

        self.student = User.objects.create_user(
            username="api_student",
            password="Test@123456",
            email="student@example.com",
            first_name="API",
            last_name="Student",
        )
        UserProfile.objects.create(user=self.student, role="student")

        self.course = Course.objects.create(
            title="Khóa học Python API",
            description="Khóa học dùng để test API",
            price=0,
            is_free=True,
            subject=self.subject,
            grade=self.grade,
            level=self.level,
            teacher=self.teacher,
            is_published=True,
        )

        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Bài học 1",
            content="Nội dung bài học 1",
            order=1,
            is_free_preview=True,
        )

        self.quiz = Quiz.objects.create(
            course=self.course,
            lesson=self.lesson,
            title="Quiz API",
            description="Quiz test",
            time_limit=600,
        )

        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Python là gì?",
            order=1,
            points=5,
        )
        self.correct_choice = Choice.objects.create(
            question=self.question,
            text="Ngôn ngữ lập trình",
            is_correct=True,
        )
        self.wrong_choice = Choice.objects.create(
            question=self.question,
            text="Trình duyệt",
            is_correct=False,
        )


class AuthAPITests(APITestCase):
    def test_register_api_creates_user_and_token(self):
        response = self.client.post(
            reverse('api-register'),
            {
                'username': 'new_student',
                'email': 'new_student@example.com',
                'password': 'Test@123456',
                'first_name': 'New',
                'last_name': 'Student',
                'role': 'student',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'new_student')
        self.assertTrue(User.objects.filter(username='new_student').exists())
        self.assertTrue(Token.objects.filter(user__username='new_student').exists())

    def test_login_api_returns_token(self):
        user = User.objects.create_user(username='login_user', password='Test@123456')
        UserProfile.objects.create(user=user, role='student')

        response = self.client.post(
            reverse('api-login'),
            {'username': 'login_user', 'password': 'Test@123456'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.data)

    def test_user_detail_does_not_expose_password(self):
        user = User.objects.create_user(username='detail_user', password='Test@123456')
        UserProfile.objects.create(user=user, role='student')
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = self.client.get(reverse('api-user-detail'))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['username'], 'detail_user')


class CourseAndQuizAPITests(APITestCaseBase):
    def setUp(self):
        super().setUp()
        self.student_token = Token.objects.create(user=self.student)
        self.teacher_token = Token.objects.create(user=self.teacher)

    def auth_as_student(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.student_token.key}')

    def test_course_list_returns_published_courses(self):
        response = self.client.get(reverse('api-course-list'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Khóa học Python API')

    def test_course_detail_returns_lessons_and_quizzes(self):
        response = self.client.get(reverse('api-course-detail', args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.course.id)
        self.assertEqual(len(response.data['lessons']), 1)
        self.assertEqual(len(response.data['quizzes']), 1)

    def test_student_can_enroll_in_free_course(self):
        self.auth_as_student()
        response = self.client.post(reverse('api-enroll-course', args=[self.course.id]), format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'approved')
        self.assertTrue(Enrollment.objects.filter(user=self.student, course=self.course).exists())

    def test_student_cannot_start_quiz_without_enrollment(self):
        self.auth_as_student()
        response = self.client.post(reverse('api-start-quiz', args=[self.quiz.id]), format='json')

        self.assertEqual(response.status_code, 403)

    def test_student_can_start_quiz_after_enrollment(self):
        Enrollment.objects.create(user=self.student, course=self.course, status='approved', is_paid=True)
        self.auth_as_student()

        response = self.client.post(reverse('api-start-quiz', args=[self.quiz.id]), format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['quiz']['id'], self.quiz.id)
        self.assertEqual(response.data['user']['id'], self.student.id)

    def test_student_can_submit_answers_and_get_score(self):
        Enrollment.objects.create(user=self.student, course=self.course, status='approved', is_paid=True)
        attempt = UserQuizAttempt.objects.create(user=self.student, quiz=self.quiz)
        self.auth_as_student()

        response = self.client.put(
            reverse('api-attempt-detail', args=[attempt.id]),
            {
                'answers': [
                    {
                        'question_id': self.question.id,
                        'choice_id': self.correct_choice.id,
                    }
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.completed, True)
        self.assertEqual(attempt.correct_answers, 1)
        self.assertEqual(attempt.score, 5)
        self.assertEqual(attempt.percentage, 100.0)