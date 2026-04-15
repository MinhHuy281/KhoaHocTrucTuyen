# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import re

# Import models
from .models import (
    Course, Lesson, Enrollment, Quiz, Question, Choice, UserQuizAttempt, UserAnswer,
    Level, Grade, Subject, Notification
)

# Import accounts
from accounts.models import UserProfile
from accounts.auth import SeparateSessionAuth
from accounts.decorators import teacher_required, student_required


def is_strong_password(password):
    """Yêu cầu mật khẩu mạnh: >=8 ký tự, có hoa/thường/số/ký tự đặc biệt."""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def paginate_request_queryset(request, queryset, per_page=12, page_param='page'):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param)
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop(page_param, None)
    query_string = query_params.urlencode()

    return page_obj, query_string


# Trang chủ
def index(request):
    courses = Course.objects.all().order_by('-id')
    page_obj, query_string = paginate_request_queryset(request, courses, per_page=6)
    return render(request, "index.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "query_string": query_string,
    })


# Danh sách khóa học
def courses(request):
    courses = Course.objects.all().order_by('-id')

    level = request.GET.get("level")
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    q = request.GET.get("q")

    if level:
        courses = courses.filter(level_id=level)
    if grade:
        courses = courses.filter(grade_id=grade)
    if subject:
        courses = courses.filter(subject_id=subject)
    if q:
        courses = courses.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q)
        )

    levels = Level.objects.all()
    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    page_obj, query_string = paginate_request_queryset(request, courses, per_page=6)

    return render(request, "courses.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "query_string": query_string,
        "levels": levels,
        "grades": grades,
        "subjects": subjects,
        "q": q
    })


# Chi tiết khóa học
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all().order_by('order')
    first_lesson = lessons.first()
    lesson_page_obj, lesson_query_string = paginate_request_queryset(
        request,
        lessons,
        per_page=6,
        page_param='lesson_page'
    )
    quiz_count = course.quizzes.count()

    enrollment = None
    enrolled = False
    approved = False
    pending = False

    if request.user.is_authenticated:
        # ✅ FIX: chỉ tự mở khóa khi giá thực tế bằng 0
        if course.price == 0:
            enrollment, _ = course.enrollments.get_or_create(
                user=request.user,
                defaults={'status': 'approved'}
            )
        else:
            enrollment = course.enrollments.filter(user=request.user).first()

        if enrollment:
            enrolled = True

            if enrollment and enrollment.status == 'approved':
                approved = True
            elif enrollment.status == 'paid':
                pending = True

    return render(request, "course_detail.html", {
        "course": course,
        "lessons": lesson_page_obj,
        "lessons_total": lessons.count(),
        "first_lesson": first_lesson,
        "lesson_query_string": lesson_query_string,
        "quiz_count": quiz_count,
        "enrollment": enrollment,
        "enrolled": enrolled,
        "approved": approved,
        "pending": pending
    })

# Xem bài học (lesson)
def lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.course

    # ===== CHECK QUYỀN =====
    enrollment = None
    if request.user.is_authenticated:
        enrollment = course.enrollments.filter(
            user=request.user,
            status='approved'   # 🔒 chỉ cho người đã duyệt
        ).first()

    # 👉 khóa có phí chỉ mở khi đã được duyệt thanh toán
    if not (course.price == 0 or enrollment):
        messages.warning(request, 'Vui lòng đăng ký khóa học để xem bài này.')
        return redirect('course_detail', course_id=course.id)

    # ===== XỬ LÝ VIDEO YOUTUBE =====
    video_id = ""

    if lesson.video_url:
        url = lesson.video_url.strip()

        # bắt mọi dạng link youtube
        match = re.search(r"(?:v=|youtu\.be/|embed/)([^&?/]+)", url)

        if match:
            video_id = match.group(1)
        else:
            video_id = url  # fallback nếu nhập sẵn ID

    return render(request, "lesson.html", {
        "lesson": lesson,
        "video_id": video_id
    })

# ĐĂNG NHẬP HỌC VIÊN
def login_view(request):
    """Đăng nhập USER/STUDENT tại /login/."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not is_strong_password(password or ""):
            messages.error(
                request,
                '❌ Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.'
            )
            return render(request, 'login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                messages.error(request, '❌ Tài khoản quản trị vui lòng đăng nhập tại trang admin.')
                return render(request, 'login.html')

            # Tài khoản staff (giảng viên/nhân sự) không đăng nhập ở trang học viên.
            if user.is_staff:
                messages.error(request, '❌ Tài khoản này vui lòng đăng nhập ở trang giảng viên hoặc admin.')
                return render(request, 'login.html')

            # Chỉ cho student/user vào login này.
            if hasattr(user, 'profile') and user.profile.is_teacher():
                messages.error(request, '❌ Đây là tài khoản giảng viên. Vui lòng đăng nhập ở trang giảng viên.')
                return render(request, 'login.html')

            SeparateSessionAuth.login_user(request, user)
            messages.success(request, f'👋 Chào mừng {user.username}!')
            return redirect('/')
        else:
            messages.error(request, '❌ Tên đăng nhập hoặc mật khẩu sai!')
            return render(request, 'login.html')

    return render(request, 'login.html')


def teacher_login_view(request):
    """Đăng nhập TEACHER tại /teacher/login/."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not is_strong_password(password or ""):
            messages.error(
                request,
                '❌ Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.'
            )
            return render(request, 'teacher_login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                messages.error(request, '❌ Tài khoản quản trị vui lòng đăng nhập tại trang admin.')
                return render(request, 'teacher_login.html')

            try:
                if hasattr(user, 'profile') and user.profile.is_teacher():
                    SeparateSessionAuth.login_teacher(request, user)
                    messages.success(request, f'👋 Chào mừng giảng viên {user.username}!')
                    return redirect('/teacher/')

                messages.error(request, '❌ Tài khoản này không phải giảng viên!')
                return render(request, 'teacher_login.html')
            except Exception:
                messages.error(request, '❌ Tài khoản này không phải giảng viên!')
                return render(request, 'teacher_login.html')
        else:
            messages.error(request, '❌ Tên đăng nhập hoặc mật khẩu sai!')
            return render(request, 'teacher_login.html')

    return render(request, 'teacher_login.html')


# ĐĂNG KÝ
def _register_by_role(request, role='student'):
    """Đăng ký tách biệt theo role để tránh lẫn luồng student/teacher."""
    template_name = 'teacher_register.html' if role == 'teacher' else 'register.html'

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        form_data = {
            'username': username,
            'email': email,
            'phone': phone,
            'role': role,
        }

        if password != password2:
            messages.error(request, '❌ Mật khẩu không khớp!')
            return render(request, template_name, {'form_data': form_data})

        if not is_strong_password(password):
            messages.error(
                request,
                '❌ Mật khẩu phải có ít nhất 8 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.'
            )
            return render(request, template_name, {'form_data': form_data})

        try:
            validate_password(password)
        except ValidationError as exc:
            messages.error(request, '❌ ' + ' '.join(exc.messages))
            return render(request, template_name, {'form_data': form_data})

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Tên đăng nhập đã tồn tại!')
            return render(request, template_name, {'form_data': form_data})

        if User.objects.filter(email=email).exists():
            messages.error(request, '❌ Email đã được sử dụng!')
            return render(request, template_name, {'form_data': form_data})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        UserProfile.objects.create(
            user=user,
            role=role,
            phone=phone if phone else ''
        )

        if role == 'teacher':
            user.is_staff = True
            user.save()
            messages.success(request, '✅ Đăng ký giảng viên thành công!')
            # Tách hẳn session: clear user session trước khi login teacher
            SeparateSessionAuth.logout_user(request)
            SeparateSessionAuth.login_teacher(request, user)
            return redirect('/teacher/')
        else:
            messages.success(request, '✅ Đăng ký học viên thành công!')
            # Tách hẳn session: clear teacher session trước khi login user
            SeparateSessionAuth.logout_teacher(request)
            SeparateSessionAuth.login_user(request, user)
            return redirect('/')

    return render(request, template_name)


def register_view(request):
    """Đăng ký học viên (route mặc định /register/)."""
    return _register_by_role(request, role='student')


def register_teacher_view(request):
    """Đăng ký giảng viên riêng biệt (route /teacher/register/)."""
    return _register_by_role(request, role='teacher')


# ĐĂNG XUẤT
def logout_view(request):
    """Đăng xuất - xóa cả 2 session"""
    SeparateSessionAuth.logout_user(request)
    SeparateSessionAuth.logout_teacher(request)
    django_logout(request)
    messages.success(request, '👋 Đã đăng xuất!')
    return redirect('/')


@student_required
def user_profile(request):
    user = request.current_user
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={'role': 'student'}
    )

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        bio = request.POST.get('bio', '').strip()

        if email and User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, '❌ Email này đã được dùng bởi tài khoản khác.')
            return redirect('user_profile')

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        profile.phone = phone
        profile.bio = bio

        avatar = request.FILES.get('avatar')
        if avatar:
            profile.avatar = avatar

        profile.save()
        messages.success(request, '✅ Đã cập nhật thông tin cá nhân.')
        return redirect('user_profile')

    purchased_enrollments = Enrollment.objects.filter(
        user=user,
        status__in=['paid', 'approved']
    ).select_related(
        'course',
        'course__subject',
        'course__grade',
        'course__level'
    ).order_by('-created')

    quiz_history = UserQuizAttempt.objects.filter(
        user=user,
        completed=True
    ).select_related(
        'quiz',
        'quiz__course'
    ).order_by('-finished_at', '-started_at')

    enrollment_page_obj, enrollment_query_string = paginate_request_queryset(
        request,
        purchased_enrollments,
        per_page=6,
        page_param='enrollment_page'
    )
    quiz_page_obj, quiz_query_string = paginate_request_queryset(
        request,
        quiz_history,
        per_page=6,
        page_param='quiz_page'
    )

    return render(request, 'user_profile.html', {
        'profile': profile,
        'purchased_enrollments': enrollment_page_obj,
        'purchased_enrollments_page_obj': enrollment_page_obj,
        'purchased_enrollments_query_string': enrollment_query_string,
        'quiz_history': quiz_page_obj,
        'quiz_history_page_obj': quiz_page_obj,
        'quiz_history_query_string': quiz_query_string,
    })


# === PHẦN ÔN LUYỆN (QUIZ) ===
@student_required
def quiz_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # ✅ FIX: khóa free thì cho qua luôn
    if not (course.is_free or course.price == 0):
        if not course.enrollments.filter(user=request.current_user).exists():
            messages.warning(request, 'Bạn cần đăng ký khóa học để làm bài tập!')
            return redirect('course_detail', course_id=course.id)
    
    quizzes = course.quizzes.all()

    if not quizzes.exists():
        messages.info(request, 'Khóa học này chưa có bài ôn luyện nào.')
    
    return render(request, 'quiz_list.html', {
        'course': course,
        'quizzes': quizzes
    })


@student_required
def start_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    course = quiz.course

    # ✅ FIX: khóa free thì cho qua
    if not (course.is_free or course.price == 0):
        if not course.enrollments.filter(user=request.user).exists():
            messages.warning(request, 'Bạn cần mua khóa học để làm bài!')
            return redirect('course_detail', course_id=course.id)

    # ✅ Giới hạn số lần làm
    previous_attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        completed=True
    ).count()

    if previous_attempts >= 3:
        messages.warning(request, 'Bạn đã hết lượt làm lại bài này (tối đa 3 lần).')
        return redirect('quiz_list', course_id=course.id)

    # ✅ Tạo attempt
    attempt = UserQuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        started_at=timezone.now()
    )

    return redirect('take_quiz', attempt_id=attempt.id)

@student_required
def take_quiz(request, attempt_id):
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    quiz = attempt.quiz
    
    if attempt.completed:
        return redirect('quiz_result', attempt_id=attempt.id)
    
    questions = quiz.questions.all().order_by('order')
    
    if request.method == 'POST':
        score = 0
        correct = 0
        total_points = 0
        
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            selected_choice = None
            is_correct = False
            
            if selected_choice_id:
                try:
                    selected_choice = Choice.objects.get(id=selected_choice_id, question=question)
                    total_points += question.points
                    if selected_choice.is_correct:
                        score += question.points
                        correct += 1
                        is_correct = True
                except Choice.DoesNotExist:
                    pass
            
            # Lưu câu trả lời
            UserAnswer.objects.create(
                attempt=attempt,
                question=question,
                selected_choice=selected_choice,
                is_correct=is_correct
            )
        
        attempt.score = score
        attempt.correct_answers = correct
        attempt.wrong_answers = questions.count() - correct
        attempt.total_points = total_points
        attempt.percentage = (score / total_points * 100) if total_points > 0 else 0
        attempt.finished_at = timezone.now()
        attempt.completed = True
        attempt.save()
        
        messages.success(request, f'Bạn đã hoàn thành bài tập! Điểm: {attempt.percentage:.1f}%')
        return redirect('quiz_result', attempt_id=attempt.id)
    
    return render(request, 'take_quiz.html', {
        'attempt': attempt,
        'quiz': quiz,
        'questions': questions,
        'time_limit': quiz.time_limit,
    })
# ================= TEACHER =================

@teacher_required
def teacher_dashboard(request):
    if not request.user.is_staff:
        return redirect('/')

    courses = Course.objects.filter(teacher=request.user)
    course_page_obj, course_query_string = paginate_request_queryset(
        request,
        courses,
        per_page=6,
        page_param='course_page'
    )

    # 🔔 ALL NOTIFICATIONS
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    # 🔴 UNREAD ONLY
    unread_notifications = notifications.filter(is_read=False)
    unread_count = unread_notifications.count()

    return render(request, 'teacher/index_teacher.html', {
        'courses': course_page_obj,
        'course_page_obj': course_page_obj,
        'course_query_string': course_query_string,
        'notifications': notifications[:5],
        'unread_count': unread_count,
        'unread_notifications': unread_notifications
    })


@teacher_required
def teacher_profile(request):
    teacher = request.current_teacher
    profile, _ = UserProfile.objects.get_or_create(
        user=teacher,
        defaults={'role': 'teacher'}
    )

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        bio = request.POST.get('bio', '').strip()

        if email and User.objects.filter(email=email).exclude(id=teacher.id).exists():
            messages.error(request, '❌ Email này đã được dùng bởi tài khoản khác.')
            return redirect('teacher_profile')

        teacher.first_name = first_name
        teacher.last_name = last_name
        teacher.email = email
        teacher.save()

        profile.phone = phone
        profile.bio = bio
        profile.role = 'teacher'

        avatar = request.FILES.get('avatar')
        if avatar:
            profile.avatar = avatar

        profile.save()
        messages.success(request, '✅ Đã cập nhật thông tin giảng viên.')
        return redirect('teacher_profile')

    teaching_courses = Course.objects.filter(teacher=teacher).annotate(
        approved_students=Count('enrollments', filter=Q(enrollments__status='approved')),
        quizzes_count=Count('quizzes', distinct=True)
    ).select_related('subject', 'grade', 'level').order_by('-id')

    teaching_attempts = UserQuizAttempt.objects.filter(
        quiz__course__teacher=teacher,
        completed=True
    ).select_related('user', 'quiz', 'quiz__course').order_by('-finished_at', '-started_at')

    total_students = Enrollment.objects.filter(
        course__teacher=teacher,
        status='approved'
    ).count()

    total_attempts = UserQuizAttempt.objects.filter(
        quiz__course__teacher=teacher,
        completed=True
    ).count()

    return render(request, 'teacher/teacher_profile.html', {
        'profile': profile,
        'teaching_courses': teaching_courses,
        'teaching_attempts': teaching_attempts,
        'total_students': total_students,
        'total_attempts': total_attempts,
    })

@teacher_required
def teacher_courses(request):
    if not request.user.is_staff:
        return redirect('/')

    courses = Course.objects.filter(teacher=request.user)
    page_obj, query_string = paginate_request_queryset(request, courses, per_page=8)

    return render(request, 'teacher/teacher_courses.html', {
        'courses': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
    })


@teacher_required
def teacher_create_course(request):
    if not request.user.is_staff:
        return redirect('/')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        subject_id = request.POST.get('subject')
        new_subject_name = request.POST.get('new_subject', '').strip()
        grade_id = request.POST.get('grade')
        level_id = request.POST.get('level')

        # Nếu nhập môn mới, tạo Subject mới hoặc dùng lại nếu đã tồn tại
        if new_subject_name:
            subject_obj, _ = Subject.objects.get_or_create(
                name__iexact=new_subject_name,
                defaults={'name': new_subject_name}
            )
            subject_id = subject_obj.id

        # Yêu cầu phải có môn học
        if not subject_id:
            subjects = Subject.objects.all()
            grades = Grade.objects.all()
            levels = Level.objects.all()
            return render(request, 'teacher/create_course.html', {
                'subjects': subjects,
                'grades': grades,
                'levels': levels,
                'error': 'Vui lòng chọn môn học hoặc nhập tên môn mới.'
            })

        # ✅ THÊM
        is_free = request.POST.get('is_free') == 'on'
        image = request.FILES.get('image')

        course = Course.objects.create(
            title=title,
            description=description,
            price=price if price else 0,
            is_free=is_free,              # ✅ THÊM
            subject_id=subject_id,
            grade_id=grade_id,
            level_id=level_id,
            teacher=request.user,
            image=image                  # ✅ THÊM
        )

        # ✅ THÊM: tạo luôn lesson đầu nếu có video
        video_url = request.POST.get('video_url')
        content = request.POST.get('content')

        if video_url or content:
            Lesson.objects.create(
                course=course,
                title="Bài học 1",
                video_url=video_url,
                content=content,
                order=1,
                is_free_preview=True
            )

        return redirect('/teacher/courses/')

    subjects = Subject.objects.all()
    grades = Grade.objects.all()
    levels = Level.objects.all()

    return render(request, 'teacher/create_course.html', {
        'subjects': subjects,
        'grades': grades,
        'levels': levels
    })

@teacher_required
def teacher_edit_course(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)

    if request.method == 'POST':
        course.title = request.POST.get('title')
        course.description = request.POST.get('description')
        course.price = request.POST.get('price')
        course.subject_id = request.POST.get('subject')
        course.grade_id = request.POST.get('grade')
        course.level_id = request.POST.get('level')
        course.is_free = request.POST.get('is_free') == 'on'
        
        image = request.FILES.get('image')
        if image:
            course.image = image
        course.save()
        

        return redirect('/teacher/courses/')

    subjects = Subject.objects.all()
    grades = Grade.objects.all()
    levels = Level.objects.all()

    return render(request, 'teacher/edit_course.html', {
        'course': course,
        'subjects': subjects,
        'grades': grades,
        'levels': levels
    })


@student_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    answers = attempt.answers.all().select_related('question', 'selected_choice')
    return render(request, 'quiz_result.html', {
        'attempt': attempt,
        'answers': answers
    })

@student_required
def quiz_list_all(request):
    # Chỉ hiển thị bài ôn luyện của các khóa đã được duyệt học.
    enrolled_courses = Course.objects.filter(
        enrollments__user=request.current_user,
        enrollments__status='approved'
    ).distinct()

    quizzes = Quiz.objects.filter(course__in=enrolled_courses).order_by('-created_at').distinct()
    page_obj, query_string = paginate_request_queryset(request, quizzes, per_page=6)

    if not quizzes.exists():
        messages.info(request, 'Hiện chưa có bài ôn luyện khả dụng cho các khóa bạn đã mở.')

    return render(request, 'quiz_list_all.html', {
        'quizzes': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'title': 'Ôn Luyện Tất Cả'
    })
def teacher_delete_course(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)
    course.delete()

    return redirect('/teacher/courses/')

@teacher_required
def teacher_course_detail(request, id):
    teacher = request.current_teacher
    course = get_object_or_404(Course, id=id, teacher=teacher)
    lessons = course.lessons.all().order_by('order')

    return render(request, 'teacher/course_detail.html', {
        'course': course,
        'lessons': lessons
    })

@teacher_required
def teacher_quiz_results(request):
    if not request.user.is_staff:
        return redirect('/')

    # Lấy tất cả quiz của teacher
    quizzes = Quiz.objects.filter(course__teacher=request.user).select_related('course')
    quiz_page_obj, quiz_query_string = paginate_request_queryset(
        request,
        quizzes,
        per_page=4,
        page_param='quiz_page'
    )

    # Lấy attempts cho mỗi quiz
    quiz_data = []
    for quiz in quiz_page_obj:
        attempts = UserQuizAttempt.objects.filter(quiz=quiz).select_related('user').order_by('-finished_at')
        quiz_data.append({
            'quiz': quiz,
            'attempts': attempts
        })

    return render(request, 'teacher/quiz_results.html', {
        'quiz_data': quiz_data,
        'quiz_page_obj': quiz_page_obj,
        'quiz_query_string': quiz_query_string,
    })

@teacher_required
def teacher_attempt_detail(request, attempt_id):
    """Xem chi tiết câu trả lời của học viên"""
    if not request.user.is_staff:
        return redirect('/')

    # Lấy attempt và kiểm tra quyền (phải là teacher của quiz này)
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id)
    
    # Kiểm tra xem người dùng có phải là teacher của khóa học chứa quiz này không
    if attempt.quiz.course.teacher != request.user:
        return redirect('/')

    # Lấy tất cả câu trả lời của attempt
    answers = attempt.answers.all().select_related('question', 'selected_choice')

    return render(request, 'teacher/attempt_detail.html', {
        'attempt': attempt,
        'answers': answers
    })

@teacher_required
def teacher_edit_course(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)

    if request.method == 'POST':
        course.title = request.POST.get('title')
        course.description = request.POST.get('description')
        course.price = request.POST.get('price')
        course.subject_id = request.POST.get('subject')
        course.grade_id = request.POST.get('grade')
        course.level_id = request.POST.get('level')
        course.is_free = request.POST.get('is_free') == 'on'

        image = request.FILES.get('image')
        if image:
            course.image = image

        course.save()

        # ===== UPDATE LESSON =====
        video_url = request.POST.get('video_url')
        content = request.POST.get('content')

        lesson = course.lessons.first()

        if lesson:
            lesson.video_url = video_url
            lesson.content = content
            lesson.save()
        else:
            Lesson.objects.create(
                course=course,
                title="Bài học 1",
                video_url=video_url,
                content=content,
                order=1,
                is_free_preview=True
            )

        return redirect('/teacher/courses/')

    subjects = Subject.objects.all()
    grades = Grade.objects.all()
    levels = Level.objects.all()

    return render(request, 'teacher/edit_course.html', {
        'course': course,
        'subjects': subjects,
        'grades': grades,
        'levels': levels
    })

@teacher_required
def create_quiz(request, id):
    teacher = request.current_teacher
    course = get_object_or_404(Course, id=id, teacher=teacher)
    lessons = Lesson.objects.filter(course=course)

    if request.method == "POST":

        lesson_id = request.POST.get("lesson_id")
        title = request.POST.get("title")

        lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

        # tạo quiz
        quiz = Quiz.objects.create(
            course=course,
            lesson=lesson,
            title=title
        )

        questions = request.POST.getlist("question[]")
        option_a = request.POST.getlist("option_a[]")
        option_b = request.POST.getlist("option_b[]")
        option_c = request.POST.getlist("option_c[]")
        option_d = request.POST.getlist("option_d[]")
        correct = request.POST.getlist("correct_answer[]")

        for i in range(len(questions)):

            question = Question.objects.create(
                quiz=quiz,
                text=questions[i],
                order=i+1
            )

            Choice.objects.create(
                question=question,
                text=option_a[i],
                is_correct=(correct[i] == "A")
            )

            Choice.objects.create(
                question=question,
                text=option_b[i],
                is_correct=(correct[i] == "B")
            )

            Choice.objects.create(
                question=question,
                text=option_c[i],
                is_correct=(correct[i] == "C")
            )

            Choice.objects.create(
                question=question,
                text=option_d[i],
                is_correct=(correct[i] == "D")
            )

        return redirect("teacher_courses")

    return render(request,"teacher/create_quiz.html",{
        "course":course,
        "lessons":lessons
    })


@student_required
def payment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)

    if request.method == "POST":
        enrollment.is_paid = True
        enrollment.status = 'approved'
        enrollment.save()

        # ===== NOTIFICATION USER =====
        # Notification.objects.create(
        #     user=request.user,
        #     message=f"Bạn đã thanh toán thành công khóa học '{enrollment.course.title}'"
        # )

        # ===== NOTIFICATION TEACHER (FIX CHUẨN) =====
        teacher = enrollment.course.teacher

        if teacher and teacher != request.user:
            Notification.objects.create(
                user=teacher,
                message=f" Học viên {request.user.username} đã thanh toán {enrollment.course.price} VNĐ cho khóa học '{enrollment.course.title}'"
            )

        messages.success(request, "Thanh toán thành công!")
        return redirect('course_detail', course_id=enrollment.course.id)

    return render(request, 'payment.html', {
        'enrollment': enrollment
    })



@student_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course
    )

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        payment_method = request.POST.get("payment_method")

        # 👉 validate đơn giản
        if not full_name or not email or not phone or not payment_method:
            return render(request, 'enroll_confirm.html', {
                'enrollment': enrollment,
                'error': 'Vui lòng nhập đầy đủ thông tin!'
            })

        # 👉 redirect qua payment sau khi nhập xong
        return redirect('payment', enrollment_id=enrollment.id)

    return render(request, 'enroll_confirm.html', {
        'enrollment': enrollment
    })



@teacher_required
def mark_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({'status': 'ok'})
    
