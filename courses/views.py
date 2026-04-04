# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import re

# Import models
from .models import (
    Course, Lesson, Enrollment, Quiz, Question, Choice, UserQuizAttempt,
    Level, Grade, Subject, Notification
)

# Import accounts
from accounts.models import UserProfile
from accounts.auth import SeparateSessionAuth
from accounts.decorators import teacher_required, student_required


# Trang chủ
def index(request):
    courses = Course.objects.all()
    return render(request, "index.html", {"courses": courses})


# Danh sách khóa học
def courses(request):
    courses = Course.objects.all()

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

    return render(request, "courses.html", {
        "courses": courses,
        "levels": levels,
        "grades": grades,
        "subjects": subjects,
        "q": q
    })


# Chi tiết khóa học
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all().order_by('order')

    enrollment = None
    enrolled = False
    approved = False
    pending = False

    if request.user.is_authenticated:
        # ✅ FIX: auto enroll nếu khóa FREE
        if course.is_free or course.price == 0:
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
        "lessons": lessons,
        "enrollment": enrollment,
        "enrolled": enrolled,
        "approved": approved,
        "pending": pending
    })

# Xem bài học (lesson)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
import re

@student_required
def lesson_view(request, id):
    lesson = get_object_or_404(Lesson, id=id)
    course = lesson.course

    # ===== CHECK QUYỀN =====
    enrollment = course.enrollments.filter(
        user=request.current_user,
        status='approved'   # 🔒 chỉ cho người đã thanh toán
    ).first()

    # 👉 nếu KHÔNG phải khóa free
    if course.price > 0 and not enrollment:
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

# ĐĂNG NHẬP
def login_view(request):
    """
    Đăng nhập với SESSION RIÊNG cho User và Teacher
    Admin đăng nhập tại /admin/login/
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if role == 'teacher':
                # Kiểm tra xem có phải teacher không
                try:
                    if hasattr(user, 'profile') and user.profile.is_teacher():
                        # ✅ Đăng nhập với SESSION RIÊNG cho teacher
                        SeparateSessionAuth.login_teacher(request, user)
                        messages.success(request, f'👋 Chào mừng giảng viên {user.username}!')
                        return redirect('/teacher/')
                    else:
                        messages.error(request, '❌ Tài khoản này không phải giảng viên!')
                        return render(request, 'login.html')
                except:
                    messages.error(request, '❌ Tài khoản này không phải giảng viên!')
                    return render(request, 'login.html')
            else:
                # ✅ Đăng nhập với SESSION RIÊNG cho user
                SeparateSessionAuth.login_user(request, user)
                messages.success(request, f'👋 Chào mừng {user.username}!')
                return redirect('/')
        else:
            messages.error(request, '❌ Tên đăng nhập hoặc mật khẩu sai!')
            return render(request, 'login.html')

    return render(request, 'login.html')


# ĐĂNG KÝ
def register_view(request):
    """Đăng ký tài khoản User hoặc Teacher"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role', 'student')

        if password != password2:
            messages.error(request, '❌ Mật khẩu không khớp!')
            return render(request, 'register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Tên đăng nhập đã tồn tại!')
            return render(request, 'register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, '❌ Email đã được sử dụng!')
            return render(request, 'register.html')

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
            # ✅ Auto login với SESSION RIÊNG
            SeparateSessionAuth.login_teacher(request, user)
            return redirect('/teacher/')
        else:
            messages.success(request, '✅ Đăng ký học viên thành công!')
            # ✅ Auto login với SESSION RIÊNG
            SeparateSessionAuth.login_user(request, user)
            return redirect('/')

    return render(request, 'register.html')


# ĐĂNG XUẤT
def logout_view(request):
    """Đăng xuất - xóa cả 2 session"""
    SeparateSessionAuth.logout_user(request)
    SeparateSessionAuth.logout_teacher(request)
    messages.success(request, '👋 Đã đăng xuất!')
    return redirect('/')
    messages.info(request, 'Bạn đã đăng xuất.')
    return redirect('login')


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


@login_required
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

@login_required
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
            if selected_choice_id:
                try:
                    choice = Choice.objects.get(id=selected_choice_id, question=question)
                    total_points += question.points
                    if choice.is_correct:
                        score += question.points
                        correct += 1
                except Choice.DoesNotExist:
                    pass
        
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

@login_required
def teacher_dashboard(request):
    if not request.user.is_staff:
        return redirect('/')

    courses = Course.objects.filter(teacher=request.user)

    # 🔔 ALL NOTIFICATIONS
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    # 🔴 UNREAD ONLY
    unread_notifications = notifications.filter(is_read=False)
    unread_count = unread_notifications.count()

    return render(request, 'teacher/index_teacher.html', {
        'courses': courses,
        'notifications': notifications[:5],
        'unread_count': unread_count,
        'unread_notifications': unread_notifications
    })

@login_required
def teacher_courses(request):
    if not request.user.is_staff:
        return redirect('/')

    courses = Course.objects.filter(teacher=request.user)

    return render(request, 'teacher/teacher_courses.html', {
        'courses': courses
    })


@login_required
def teacher_create_course(request):
    if not request.user.is_staff:
        return redirect('/')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        subject_id = request.POST.get('subject')
        grade_id = request.POST.get('grade')
        level_id = request.POST.get('level')

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

@login_required
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


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id, user=request.user)
    return render(request, 'quiz_result.html', {'attempt': attempt})

@login_required
def quiz_list_all(request):
    # Lấy khóa học user đã enroll
    enrolled_courses = Course.objects.filter(enrollments__user=request.user)  # hoặc enrollments__user
    quizzes = Quiz.objects.filter(course__in=enrolled_courses).order_by('-created_at')
    
    if not quizzes.exists():
        messages.info(request, 'Bạn chưa có bài ôn luyện nào. Hãy đăng ký khóa học để bắt đầu!')
    
    return render(request, 'quiz_list_all.html', {
        'quizzes': quizzes,
        'title': 'Ôn Luyện Tất Cả'
    })
def teacher_delete_course(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)
    course.delete()

    return redirect('/teacher/courses/')

@login_required
def teacher_course_detail(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)
    lessons = course.lessons.all().order_by('order')

    return render(request, 'teacher/course_detail.html', {
        'course': course,
        'lessons': lessons
    })
@login_required
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
@login_required
def create_quiz(request, id):
    # xử lý tạo bài ôn tập
    return render(request, 'teacher/create_quiz.html')



@login_required
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
                message=f"💰 Học viên {request.user.username} đã thanh toán {enrollment.course.price} VNĐ cho khóa học '{enrollment.course.title}'"
            )

        messages.success(request, "Thanh toán thành công!")
        return redirect('course_detail', course_id=enrollment.course.id)

    return render(request, 'payment.html', {
        'enrollment': enrollment
    })



@login_required
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



@login_required
def mark_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({'status': 'ok'})