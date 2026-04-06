from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone


from .views import (
	RESET_MAX_FAILED_ATTEMPTS,
	RESET_SESSION_CODE_KEY,
	RESET_SESSION_EMAIL_KEY,
	RESET_SESSION_EXPIRES_KEY,
)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ForgotPasswordFlowTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username='forgot_user',
			email='forgot@example.com',
			password='OldPass@123',
		)

	def test_reset_flow_with_email_code(self):
		response = self.client.post(reverse('password_reset'), {'email': 'forgot@example.com'})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('password_reset_verify'))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('Mã xác nhận đặt lại mật khẩu', mail.outbox[0].subject)

		session = self.client.session
		code = session['password_reset_code']

		response = self.client.post(reverse('password_reset_verify'), {'code': code})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('password_reset_new'))

		response = self.client.post(
			reverse('password_reset_new'),
			{
				'password': 'NewPass@123',
				'password2': 'NewPass@123',
			},
		)
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('login'))

		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('NewPass@123'))

	def test_reset_request_with_nonexistent_email(self):
		response = self.client.post(reverse('password_reset'), {'email': 'missing@example.com'})
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'password_reset_form.html')
		self.assertContains(response, 'Email chưa được đăng ký trong hệ thống. Vui lòng kiểm tra lại.')
		self.assertEqual(len(mail.outbox), 0)

	def test_verify_fails_when_code_expired(self):
		self.client.post(reverse('password_reset'), {'email': 'forgot@example.com'})
		session = self.client.session
		session[RESET_SESSION_EXPIRES_KEY] = (timezone.now() - timedelta(minutes=1)).isoformat()
		session.save()

		response = self.client.post(reverse('password_reset_verify'), {'code': '000000'})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('password_reset'))

		session = self.client.session
		self.assertNotIn(RESET_SESSION_EMAIL_KEY, session)
		self.assertNotIn(RESET_SESSION_CODE_KEY, session)

	def test_verify_locks_session_after_too_many_wrong_attempts(self):
		self.client.post(reverse('password_reset'), {'email': 'forgot@example.com'})

		for _ in range(RESET_MAX_FAILED_ATTEMPTS):
			response = self.client.post(reverse('password_reset_verify'), {'code': '999999'})

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('password_reset'))

		session = self.client.session
		self.assertNotIn(RESET_SESSION_EMAIL_KEY, session)
		self.assertNotIn(RESET_SESSION_CODE_KEY, session)

	def test_new_password_rejects_weak_password(self):
		self.client.post(reverse('password_reset'), {'email': 'forgot@example.com'})
		code = self.client.session['password_reset_code']
		self.client.post(reverse('password_reset_verify'), {'code': code})

		response = self.client.post(
			reverse('password_reset_new'),
			{
				'password': '12345678',
				'password2': '12345678',
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'password_reset_new_password.html')

		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('OldPass@123'))
