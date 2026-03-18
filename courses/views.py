from django.shortcuts import render
from .models import Course, Lesson
from .models import Course,Level,Grade,Subject
from django.db.models import Q
from django.shortcuts import render,get_object_or_404,redirect
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, Enrollment
# Trang chủ
def index(request):

    courses = Course.objects.all()

    return render(request, "index.html", {
        "courses": courses
    })


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

    return render(request,"courses.html",{
        "courses":courses,
        "levels":levels,
        "grades":grades,
        "subjects":subjects,
        "q": q
    })


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id) 
    lessons = course.lessons.all().order_by('order')

    enrolled = False
    if request.user.is_authenticated:
        enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    return render(request, "course_detail.html", {
        "course": course,
        "lessons": lessons,
        "enrolled": enrolled,
    })


def lesson_view(request, id):

    lesson = Lesson.objects.get(id=id)

    video_id = None

    if lesson.video_url:
        if "watch?v=" in lesson.video_url:
            video_id = lesson.video_url.split("watch?v=")[1]
        elif "youtu.be/" in lesson.video_url:
            video_id = lesson.video_url.split("youtu.be/")[1]
        else:
            video_id = lesson.video_url

    return render(request, "lesson.html", {
        "lesson": lesson,
        "video_id": video_id
    })


def enroll(request,id):

    course = Course.objects.get(id=id)

    Enrollment.objects.create(
        user=request.user,
        course=course
    )

    return redirect("/course/"+str(id))

def enroll_course(request,id):

    course = get_object_or_404(Course,id=id)

    Enrollment.objects.get_or_create(
        user=request.user,
        course=course
    )

    return redirect("/course/"+str(id))


# LOGIN
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')   # 👉 tránh lỗi /accounts/profile/
        else:
            return render(request, 'login.html', {
                'error': 'Tên đăng nhập hoặc mật khẩu sai!'
            })

    return render(request, 'login.html')


# REGISTER
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

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

        login(request, user)
        return redirect('/')   # 👉 đăng ký xong login luôn

    return render(request, 'register.html')


# LOGOUT
def logout_view(request):
    logout(request)
    return redirect('/login/')