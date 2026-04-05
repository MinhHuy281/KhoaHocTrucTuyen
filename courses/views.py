# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout as django_logout
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
        "lessons": lessons,
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
    django_logout(request)
    messages.success(request, '👋 Đã đăng xuất!')
    return redirect('/')


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

@teacher_required
def teacher_courses(request):
    if not request.user.is_staff:
        return redirect('/')

    courses = Course.objects.filter(teacher=request.user)

    return render(request, 'teacher/teacher_courses.html', {
        'courses': courses
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

    if not quizzes.exists():
        messages.info(request, 'Hiện chưa có bài ôn luyện khả dụng cho các khóa bạn đã mở.')

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

@teacher_required
def teacher_course_detail(request, id):
    if not request.user.is_staff:
        return redirect('/')

    course = get_object_or_404(Course, id=id, teacher=request.user)
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

    # Lấy attempts cho mỗi quiz
    quiz_data = []
    for quiz in quizzes:
        attempts = UserQuizAttempt.objects.filter(quiz=quiz).select_related('user').order_by('-finished_at')
        quiz_data.append({
            'quiz': quiz,
            'attempts': attempts
        })

    return render(request, 'teacher/quiz_results.html', {
        'quiz_data': quiz_data
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

    course = Course.objects.get(id=id)
    lessons = Lesson.objects.filter(course=course)

    if request.method == "POST":

        lesson_id = request.POST.get("lesson_id")
        title = request.POST.get("title")

        lesson = Lesson.objects.get(id=lesson_id)

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
    
