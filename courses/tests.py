# courses/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Course, Level, Grade, Subject, Quiz, Question, Choice, Enrollment, UserQuizAttempt

class QuizTestCase(TestCase):

    def setUp(self):
        self.level = Level.objects.create(name="Cấp 1")
        self.grade = Grade.objects.create(name="Lớp 1", level=self.level)
        self.subject = Subject.objects.create(name="Toán")

        self.user = User.objects.create_user(username='testuser', password='123456')
        self.course = Course.objects.create(
            title="Toán lớp 1",
            price=0,
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
        self.client.login(username='testuser', password='123456')

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
        self.client.login(username='newuser', password='123')

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