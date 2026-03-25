# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

# Import tất cả model một lần
from .models import (
    Course, Lesson, Enrollment, Quiz, Question, Choice, UserQuizAttempt,
    Level, Grade, Subject
)


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

    enrolled = False
    if request.user.is_authenticated:
        enrolled = course.enrollments.filter(user=request.user).exists()

    return render(request, "course_detail.html", {
        "course": course,
        "lessons": lessons,
        "enrolled": enrolled,
    })


# Xem bài học (lesson)
def lesson_view(request, id):
    lesson = get_object_or_404(Lesson, id=id)

    video_id = None
    if lesson.video_url:
        if "watch?v=" in lesson.video_url:
            video_id = lesson.video_url.split("watch?v=")[1].split('&')[0]
        elif "youtu.be/" in lesson.video_url:
            video_id = lesson.video_url.split("youtu.be/")[1].split('?')[0]
        else:
            video_id = lesson.video_url

    return render(request, "lesson.html", {
        "lesson": lesson,
        "video_id": video_id
    })


# ĐĂNG KÝ KHÓA HỌC (version cũ)
def enroll(request, id):
    if not request.user.is_authenticated:
        return redirect('login')

    course = get_object_or_404(Course, id=id)
    Enrollment.objects.get_or_create(user=request.user, course=course)
    messages.success(request, f'Đăng ký khóa học "{course.title}" thành công!')
    return redirect('course_detail', course_id=id)

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course
    )
    
    if created:
        messages.success(request, f'Bạn đã đăng ký khóa học "{course.title}" thành công!')
    else:
        messages.info(request, f'Bạn đã đăng ký khóa học này trước đó.')
    
    return redirect('course_detail', course_id=course.id)


# ĐĂNG NHẬP
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        role = request.POST.get('role')  # ✅ THÊM

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # ✅ THÊM PHẦN XỬ LÝ GIẢNG VIÊN
            if role == "teacher":
                if user.is_staff:
                    return redirect('/teacher/')
                else:
                    return render(request, 'login.html', {
                        'error': 'Tài khoản này không phải giảng viên!'
                    })

            return redirect('/')   # 👉 giữ nguyên
        else:
            return render(request, 'login.html', {
                'error': 'Tên đăng nhập hoặc mật khẩu sai!'
            })

    return render(request, 'login.html')


# ĐĂNG KÝ
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        role = request.POST.get('role')  # ✅ THÊM DÒNG NÀY

        if password != password2:
            return render(request, 'register.html', {
                'error': 'Mật khẩu không khớp!'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {
                'error': 'Tên đăng nhập đã tồn tại!'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # ✅ THÊM PHÂN QUYỀN (KHÔNG ẢNH HƯỞNG CODE CŨ)
        if role == "teacher":
            user.is_staff = True
            user.save()

        login(request, user)

        # ✅ THÊM REDIRECT RIÊNG
        if role == "teacher":
            return redirect('/teacher/')

        return redirect('/')   # 👉 giữ nguyên

    return render(request, 'register.html')


# ĐĂNG XUẤT
def logout_view(request):
    logout(request)
    messages.info(request, 'Bạn đã đăng xuất.')
    return redirect('login')


# === PHẦN ÔN LUYỆN (QUIZ) ===
@login_required
def quiz_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Kiểm tra enroll - nếu chưa thì redirect
    if not course.enrollments.filter(user=request.user).exists():
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
    
    if not quiz.course.enrollments.filter(user=request.user).exists():
        return redirect('course_detail', course_id=quiz.course.id)
    
    # Đếm số attempt đã hoàn thành của user cho quiz này
    previous_attempts = UserQuizAttempt.objects.filter(
        user=request.user,
        quiz=quiz,
        completed=True
    ).count()
    
    if previous_attempts >= 3:  # Giới hạn 3 lần
        messages.warning(request, 'Bạn đã hết lượt làm lại bài này (tối đa 3 lần).')
        return redirect('quiz_list', course_id=quiz.course.id)
    
    # Tạo attempt mới
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

    return render(request, 'teacher/index_teacher.html', {
    'total_courses': courses.count(),
    'total_students': 0,
    'courses': courses
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
