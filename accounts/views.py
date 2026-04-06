from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone


User = get_user_model()

RESET_SESSION_EMAIL_KEY = 'password_reset_email'
RESET_SESSION_CODE_KEY = 'password_reset_code'
RESET_SESSION_EXPIRES_KEY = 'password_reset_expires_at'
RESET_SESSION_VERIFIED_KEY = 'password_reset_verified'
RESET_SESSION_FAILED_ATTEMPTS_KEY = 'password_reset_failed_attempts'
RESET_MAX_FAILED_ATTEMPTS = 5


def _generate_reset_code() -> str:
	return f"{secrets.randbelow(1000000):06d}"


def _clear_reset_session(request) -> None:
	for key in (
		RESET_SESSION_EMAIL_KEY,
		RESET_SESSION_CODE_KEY,
		RESET_SESSION_EXPIRES_KEY,
		RESET_SESSION_VERIFIED_KEY,
		RESET_SESSION_FAILED_ATTEMPTS_KEY,
	):
		request.session.pop(key, None)
	request.session.modified = True


def forgot_password_request(request):
	if request.method == 'POST':
		email = request.POST.get('email', '').strip().lower()
		user = User.objects.filter(email__iexact=email).first()

		if not user:
			messages.error(request, 'Email chưa được đăng ký trong hệ thống. Vui lòng kiểm tra lại.')
			return render(request, 'password_reset_form.html')

		code = _generate_reset_code()
		expires_at = timezone.now() + timedelta(minutes=10)

		request.session[RESET_SESSION_EMAIL_KEY] = email
		request.session[RESET_SESSION_CODE_KEY] = code
		request.session[RESET_SESSION_EXPIRES_KEY] = expires_at.isoformat()
		request.session[RESET_SESSION_VERIFIED_KEY] = False
		request.session[RESET_SESSION_FAILED_ATTEMPTS_KEY] = 0
		request.session.modified = True

		send_mail(
			subject='Mã xác nhận đặt lại mật khẩu',
			message=(
				f'Xin chào {user.username},\n\n'
				f'Mã xác nhận đặt lại mật khẩu của bạn là: {code}\n'
				f'Mã này sẽ hết hạn sau 10 phút.\n\n'
				'Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.'
			),
			from_email=None,
			recipient_list=[user.email],
			fail_silently=False,
		)

		return redirect('password_reset_verify')

	return render(request, 'password_reset_form.html')


def forgot_password_verify(request):
	if not request.session.get(RESET_SESSION_EMAIL_KEY):
		return redirect('password_reset')

	if request.method == 'POST':
		code = request.POST.get('code', '').strip()
		stored_code = request.session.get(RESET_SESSION_CODE_KEY)
		expires_at_raw = request.session.get(RESET_SESSION_EXPIRES_KEY)
		failed_attempts = int(request.session.get(RESET_SESSION_FAILED_ATTEMPTS_KEY, 0) or 0)

		if failed_attempts >= RESET_MAX_FAILED_ATTEMPTS:
			_clear_reset_session(request)
			messages.error(request, 'Bạn đã nhập sai mã quá nhiều lần. Vui lòng yêu cầu mã mới.')
			return redirect('password_reset')

		if expires_at_raw:
			try:
				expires_at = datetime.fromisoformat(expires_at_raw)
				if timezone.is_naive(expires_at):
					expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
				if timezone.now() > expires_at:
					_clear_reset_session(request)
					messages.error(request, 'Mã xác nhận đã hết hạn. Vui lòng yêu cầu mã mới.')
					return redirect('password_reset')
			except ValueError:
				_clear_reset_session(request)
				messages.error(request, 'Phiên xác nhận không hợp lệ. Vui lòng thử lại.')
				return redirect('password_reset')

		if code and stored_code and code == stored_code:
			request.session[RESET_SESSION_VERIFIED_KEY] = True
			request.session[RESET_SESSION_FAILED_ATTEMPTS_KEY] = 0
			request.session.modified = True
			return redirect('password_reset_new')

		failed_attempts += 1
		request.session[RESET_SESSION_FAILED_ATTEMPTS_KEY] = failed_attempts
		request.session.modified = True

		remaining_attempts = RESET_MAX_FAILED_ATTEMPTS - failed_attempts
		if remaining_attempts <= 0:
			_clear_reset_session(request)
			messages.error(request, 'Bạn đã nhập sai mã quá nhiều lần. Vui lòng yêu cầu mã mới.')
			return redirect('password_reset')

		messages.error(request, 'Mã xác nhận không đúng. Vui lòng thử lại.')

	return render(request, 'password_reset_verify.html', {
		'email': request.session.get(RESET_SESSION_EMAIL_KEY),
	})


def forgot_password_new(request):
	if not request.session.get(RESET_SESSION_VERIFIED_KEY):
		return redirect('password_reset')

	email = request.session.get(RESET_SESSION_EMAIL_KEY)
	user = User.objects.filter(email__iexact=email).first() if email else None
	if not user:
		_clear_reset_session(request)
		return redirect('password_reset')

	if request.method == 'POST':
		password = request.POST.get('password', '')
		password2 = request.POST.get('password2', '')

		if password != password2:
			messages.error(request, 'Mật khẩu nhập lại không khớp.')
			return render(request, 'password_reset_new_password.html', {'email': email})

		try:
			validate_password(password, user=user)
		except ValidationError as exc:
			messages.error(request, ' '.join(exc.messages))
			return render(request, 'password_reset_new_password.html', {'email': email})

		user.set_password(password)
		user.save(update_fields=['password'])
		_clear_reset_session(request)
		messages.success(request, 'Đặt lại mật khẩu thành công. Bạn có thể đăng nhập lại.')
		return redirect('login')

	return render(request, 'password_reset_new_password.html', {
		'email': email,
	})


def register_view(request):
	from courses.views import register_view as course_register_view
	return course_register_view(request)


def register_teacher_view(request):
	from courses.views import register_teacher_view as course_register_teacher_view
	return course_register_teacher_view(request)
