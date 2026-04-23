# courses/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.html import escape
from django.urls import reverse
from django.conf import settings
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q, Count, Prefetch, Avg
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, logout as django_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError, DatabaseError
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
import json
import re
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlencode, parse_qs, urlparse
from urllib.request import Request, urlopen

# Import models
from .models import (
    Course, Lesson, Enrollment, Quiz, Question, Choice, UserQuizAttempt, UserAnswer,
    Level, Grade, Subject, Notification, LessonComment, CourseComment
)

# Import accounts
from accounts.models import UserProfile
from accounts.auth import SeparateSessionAuth
from accounts.decorators import teacher_required, student_required


COMMENT_META_TAG = "[[COMMENT_META]]"


def get_payment_success_url(enrollment):
    first_lesson = enrollment.course.lessons.order_by('order', 'id').first()
    if first_lesson:
        return reverse('lesson_view', args=[first_lesson.id])

    return reverse('course_detail', args=[enrollment.course.id])


def get_payment_reference(enrollment):
    # Unique transfer reference embedded into QR content.
    return f"PAYE{enrollment.id}"


def _create_payment_notification(enrollment):
    course_price = Decimal(str(enrollment.course.price or 0))
    admin_share = (course_price * Decimal('0.10')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    teacher_share = course_price - admin_share

    teacher = enrollment.course.teacher
    if teacher and teacher != enrollment.user:
        Notification.objects.create(
            user=teacher,
            message=(
                f"Học viên {enrollment.user.username} đã thanh toán {course_price} VNĐ cho khóa học "
                f"'{enrollment.course.title}'. Admin nhận {admin_share} VNĐ (10%), "
                f"giảng viên nhận {teacher_share} VNĐ."
            )
        )

    admin_users = User.objects.filter(is_superuser=True, is_active=True)
    for admin_user in admin_users:
        Notification.objects.create(
            user=admin_user,
            message=(
                f"Đã nhận {admin_share} VNĐ (10%) từ khóa học '{enrollment.course.title}' "
                f"sau thanh toán của học viên {enrollment.user.username}."
            )
        )


def _extract_transfer_content(payload):
    if not isinstance(payload, dict):
        return ""

    transfer_data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    candidates = [
        payload.get('content'),
        payload.get('description'),
        payload.get('transferContent'),
        payload.get('transactionContent'),
        payload.get('addInfo'),
        transfer_data.get('content'),
        transfer_data.get('description'),
        transfer_data.get('transferContent'),
        transfer_data.get('transactionContent'),
        transfer_data.get('addInfo'),
    ]

    for value in candidates:
        if value:
            return str(value)
    return ""


def _extract_transfer_amount(payload):
    if not isinstance(payload, dict):
        return None

    transfer_data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    candidates = [
        payload.get('amount'),
        payload.get('transferAmount'),
        payload.get('creditAmount'),
        transfer_data.get('amount'),
        transfer_data.get('transferAmount'),
        transfer_data.get('creditAmount'),
    ]

    for value in candidates:
        if value in (None, ""):
            continue

        raw_value = str(value).replace(',', '').strip()
        try:
            return Decimal(raw_value)
        except (InvalidOperation, ValueError):
            continue

    return None


def _find_enrollment_from_transfer_content(transfer_content):
    if not transfer_content:
        return None

    ref_match = re.search(r'PAYE(\d+)', transfer_content, flags=re.IGNORECASE)
    if ref_match:
        return Enrollment.objects.filter(id=int(ref_match.group(1))).select_related('course', 'user').first()

    legacy_match = re.search(r'ThanhToan_(.+)_(\d+)', transfer_content, flags=re.IGNORECASE)
    if legacy_match:
        username = legacy_match.group(1)
        course_id = int(legacy_match.group(2))
        return (
            Enrollment.objects
            .filter(user__username=username, course_id=course_id)
            .order_by('-created')
            .select_related('course', 'user')
            .first()
        )

    return None


def append_reply_history(existing_reply, new_reply, replied_at):
    existing_text = (existing_reply or '').strip()
    new_text = (new_reply or '').strip()

    timestamp = replied_at.strftime('%d/%m/%Y %H:%M') if replied_at else timezone.now().strftime('%d/%m/%Y %H:%M')
    entry = f"[{timestamp}] {new_text}"

    if not existing_text:
        return entry

    return f"{existing_text}\n\n{entry}"


def build_comment_notification_message(base_message, meta):
    payload = urlencode(meta)
    return f"{base_message} {COMMENT_META_TAG}{payload}"


def parse_comment_notification_message(raw_message):
    message = raw_message or ""
    if COMMENT_META_TAG not in message:
        return message, None

    content, payload = message.split(COMMENT_META_TAG, 1)
    content = content.strip()
    payload = payload.strip()

    if not payload:
        return content, None

    parsed = parse_qs(payload, keep_blank_values=True)
    meta = {key: values[0] for key, values in parsed.items() if values}
    return content, meta


def infer_comment_meta_from_legacy_message(message, teacher):
    """Infer notification metadata from old plain-text comment messages."""
    text = (message or '').strip()

    lesson_reply_match = re.search(
        r"Học viên\s+([^\s]+)\s+đã phản hồi lại ở bài\s+'([^']+)'\s+trong khóa\s+'([^']+)'",
        text,
        flags=re.IGNORECASE,
    )
    if lesson_reply_match:
        username, lesson_title, course_title = lesson_reply_match.groups()
        student = User.objects.filter(username=username).first()
        if not student:
            return None

        lesson_comment = (
            LessonComment.objects.filter(
                user=student,
                lesson__title=lesson_title,
                lesson__course__title=course_title,
                lesson__course__teacher=teacher,
            )
            .select_related('lesson')
            .order_by('-user_replied_at', '-created_at')
            .first()
        )
        if not lesson_comment:
            return None

        return {
            'type': 'lesson',
            'comment_id': str(lesson_comment.id),
            'student_id': str(student.id),
            'lesson_id': str(lesson_comment.lesson_id),
            'course_id': str(lesson_comment.lesson.course_id),
        }

    course_reply_match = re.search(
        r"Học viên\s+([^\s]+)\s+đã phản hồi lại\s+trong khóa\s+'([^']+)'",
        text,
        flags=re.IGNORECASE,
    )
    if course_reply_match:
        username, course_title = course_reply_match.groups()
        student = User.objects.filter(username=username).first()
        if not student:
            return None

        course_comment = (
            CourseComment.objects.filter(
                user=student,
                course__title=course_title,
                course__teacher=teacher,
            )
            .select_related('course')
            .order_by('-user_replied_at', '-created_at')
            .first()
        )
        if not course_comment:
            return None

        return {
            'type': 'course',
            'comment_id': str(course_comment.id),
            'student_id': str(student.id),
            'course_id': str(course_comment.course_id),
        }

    lesson_match = re.search(
        r"Học viên\s+([^\s]+)\s+đã bình luận ở bài\s+'([^']+)'\s+trong khóa\s+'([^']+)'",
        text,
        flags=re.IGNORECASE,
    )
    if lesson_match:
        username, lesson_title, course_title = lesson_match.groups()
        student = User.objects.filter(username=username).first()
        if not student:
            return None

        lesson_comment = (
            LessonComment.objects.filter(
                user=student,
                lesson__title=lesson_title,
                lesson__course__title=course_title,
                lesson__course__teacher=teacher,
            )
            .select_related('lesson')
            .order_by('-created_at')
            .first()
        )
        if not lesson_comment:
            return None

        return {
            'type': 'lesson',
            'comment_id': str(lesson_comment.id),
            'student_id': str(student.id),
            'lesson_id': str(lesson_comment.lesson_id),
            'course_id': str(lesson_comment.lesson.course_id),
        }

    course_match = re.search(
        r"Học viên\s+([^\s]+)\s+đã bình luận\s+trong khóa\s+'([^']+)'",
        text,
        flags=re.IGNORECASE,
    )
    if course_match:
        username, course_title = course_match.groups()
        student = User.objects.filter(username=username).first()
        if not student:
            return None

        course_comment = (
            CourseComment.objects.filter(
                user=student,
                course__title=course_title,
                course__teacher=teacher,
            )
            .select_related('course')
            .order_by('-created_at')
            .first()
        )
        if not course_comment:
            return None

        return {
            'type': 'course',
            'comment_id': str(course_comment.id),
            'student_id': str(student.id),
            'course_id': str(course_comment.course_id),
        }

    return None


def infer_student_comment_meta_from_legacy_message(message, student):
    """Infer student-side reply metadata from old plain-text teacher notifications."""
    text = (message or '').strip()

    match = re.search(
        r"Giảng viên\s+([^\s]+)\s+đã phản hồi bình luận của bạn ở\s+'([^']+)'",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    teacher_username, destination = match.groups()

    lesson_comment = (
        LessonComment.objects.filter(
            user=student,
            lesson__title=destination,
            lesson__course__teacher__username=teacher_username,
            teacher_reply__isnull=False,
        )
        .exclude(teacher_reply='')
        .select_related('lesson')
        .order_by('-teacher_replied_at', '-created_at')
        .first()
    )
    if lesson_comment:
        return {
            'type': 'lesson',
            'comment_id': str(lesson_comment.id),
            'student_id': str(student.id),
            'teacher_id': str(lesson_comment.lesson.course.teacher_id),
            'course_id': str(lesson_comment.lesson.course_id),
            'lesson_id': str(lesson_comment.lesson_id),
        }

    course_comment = (
        CourseComment.objects.filter(
            user=student,
            course__title=destination,
            course__teacher__username=teacher_username,
            teacher_reply__isnull=False,
        )
        .exclude(teacher_reply='')
        .select_related('course')
        .order_by('-teacher_replied_at', '-created_at')
        .first()
    )
    if course_comment:
        return {
            'type': 'course',
            'comment_id': str(course_comment.id),
            'student_id': str(student.id),
            'teacher_id': str(course_comment.course.teacher_id),
            'course_id': str(course_comment.course_id),
        }

    return None


def ensure_comment_tables():
    """Create comment tables and missing reply columns if migrations cannot be applied."""
    try:
        existing_tables = set(connection.introspection.table_names())

        models_to_create = []
        if CourseComment._meta.db_table not in existing_tables:
            models_to_create.append(CourseComment)
        if LessonComment._meta.db_table not in existing_tables:
            models_to_create.append(LessonComment)

        with connection.schema_editor() as schema_editor:
            for model in models_to_create:
                schema_editor.create_model(model)

            # Some environments block migration file writes; add missing columns at runtime.
            refreshed_tables = set(connection.introspection.table_names())
            column_updates = [
                (CourseComment, 'teacher_reply'),
                (CourseComment, 'teacher_replied_at'),
                (CourseComment, 'user_reply'),
                (CourseComment, 'user_replied_at'),
                (LessonComment, 'teacher_reply'),
                (LessonComment, 'teacher_replied_at'),
                (LessonComment, 'user_reply'),
                (LessonComment, 'user_replied_at'),
            ]

            for model, field_name in column_updates:
                table_name = model._meta.db_table
                if table_name not in refreshed_tables:
                    continue

                model_fields = connection.introspection.get_table_description(connection.cursor(), table_name)
                existing_columns = {field.name for field in model_fields}
                if field_name in existing_columns:
                    continue

                schema_editor.add_field(model, model._meta.get_field(field_name))

        return True
    except DatabaseError:
        return False


def notify_teacher_for_comment(*, course, actor, rating, content, comment_kind, comment_id, lesson=None):
    """Push a notification to the course teacher when a student comments/rates."""
    teacher = course.teacher
    if not teacher or teacher == actor:
        return

    snippet = (content or "").strip().replace("\n", " ")[:80]
    lesson_part = f" ở bài '{lesson.title}'" if lesson else ""

    human_message = (
        f"Học viên {actor.username} đã bình luận{lesson_part} trong khóa '{course.title}' "
        f"({rating} sao). Nội dung: \"{snippet}\""
    )

    meta = {
        'type': comment_kind,
        'course_id': str(course.id),
        'comment_id': str(comment_id),
        'student_id': str(actor.id),
    }
    if lesson:
        meta['lesson_id'] = str(lesson.id)

    Notification.objects.create(
        user=teacher,
        message=build_comment_notification_message(human_message, meta)
    )


def notify_teacher_for_user_reply(*, course, actor, reply_text, comment_kind, comment_id, lesson=None):
    teacher = course.teacher
    if not teacher or teacher == actor:
        return

    snippet = (reply_text or "").strip().replace("\n", " ")[:120]
    lesson_part = f" ở bài '{lesson.title}'" if lesson else ""
    human_message = f"Học viên {actor.username} đã phản hồi lại{lesson_part} trong khóa '{course.title}': \"{snippet}\""

    meta = {
        'type': comment_kind,
        'course_id': str(course.id),
        'comment_id': str(comment_id),
        'student_id': str(actor.id),
    }
    if lesson:
        meta['lesson_id'] = str(lesson.id)

    Notification.objects.create(
        user=teacher,
        message=build_comment_notification_message(human_message, meta)
    )


def notify_comment_owner_for_reply(*, parent_comment, actor, reply_text, comment_kind, lesson=None, course=None):
    recipient = parent_comment.user
    if not recipient or recipient == actor:
        return

    snippet = (reply_text or "").strip().replace("\n", " ")[:120]
    if lesson:
        location_text = f"ở bài '{lesson.title}' trong khóa '{lesson.course.title}'"
    elif course:
        location_text = f"trong khóa '{course.title}'"
    else:
        location_text = ""

    human_message = f"Học viên {actor.username} đã phản hồi bình luận của bạn {location_text}: \"{snippet}\""

    meta = {
        'type': comment_kind,
        'course_id': str(course.id if course else parent_comment.course_id),
        'comment_id': str(parent_comment.id),
        'student_id': str(actor.id),
    }
    if lesson:
        meta['lesson_id'] = str(lesson.id)

    Notification.objects.create(
        user=recipient,
        message=build_comment_notification_message(human_message, meta)
    )


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


def build_slide_urls(raw_url):
    """Chuan hoa link slide de uu tien embed truc tiep va co link tai."""
    if not raw_url:
        return "", ""

    slide_url = raw_url.strip()

    # Canva short links redirect to the real design URL.
    if 'canva.link' in slide_url:
        try:
            request = Request(slide_url, method='HEAD')
            request.add_header('User-Agent', 'Mozilla/5.0')
            with urlopen(request, timeout=5) as response:
                redirected_url = response.geturl()
                if redirected_url:
                    slide_url = redirected_url
        except Exception:
            pass

    parsed = urlparse(slide_url)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""
    query = parse_qs(parsed.query or "")

    slide_embed_url = slide_url
    slide_download_url = slide_url

    # Canva
    if 'canva.com' in host or 'canva.link' in host:
        if '/view' in slide_url and 'embed' not in slide_url:
            sep = '&' if '?' in slide_url else '?'
            slide_embed_url = f"{slide_url}{sep}embed"
        elif '/design/' in slide_url and '/view' not in slide_url:
            slide_embed_url = slide_url.rstrip('/') + '/view?embed'
        elif '/edit' in slide_url:
            base_url = slide_url.split('/edit')[0]
            slide_embed_url = f"{base_url}/view?embed"

        sep = '&' if '?' in slide_url else '?'
        slide_download_url = f"{slide_url}{sep}download=1"
        return slide_embed_url, slide_download_url

    # Google Slides
    if 'docs.google.com' in host and '/presentation/' in path:
        if '/edit' in path:
            slide_embed_url = slide_url.replace('/edit', '/embed').split('?')[0]
        elif '/pub' in path:
            slide_embed_url = slide_url.replace('/pub', '/embed').split('?')[0]
        elif '/embed' not in path:
            slide_embed_url = slide_url.rstrip('/') + '/embed'

        slide_download_url = slide_url.replace('/embed', '/export/pdf').replace('/edit', '/export/pdf')
        return slide_embed_url, slide_download_url

    # Google Drive file preview
    if 'drive.google.com' in host and '/file/d/' in path:
        match = re.search(r"/file/d/([^/]+)", path)
        if match:
            file_id = match.group(1)
            slide_embed_url = f"https://drive.google.com/file/d/{file_id}/preview"
            slide_download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            return slide_embed_url, slide_download_url

    # PDF online: dung Google Docs viewer de tang kha nang nhung
    if slide_url.lower().endswith('.pdf'):
        slide_embed_url = f"https://docs.google.com/gview?embedded=1&url={slide_url}"
        slide_download_url = slide_url
        return slide_embed_url, slide_download_url

    return slide_embed_url, slide_download_url


# Trang chủ
def index(request):
    courses = (
        Course.objects
        .annotate(
            avg_rating=Avg(
                'comments__rating',
                filter=Q(comments__parent_comment__isnull=True)
            ),
            rating_count=Count(
                'comments__id',
                filter=Q(
                    comments__parent_comment__isnull=True,
                    comments__rating__isnull=False,
                ),
                distinct=True,
            ),
        )
        .order_by('-id')
    )
    page_obj, query_string = paginate_request_queryset(request, courses, per_page=6)
    return render(request, "index.html", {
        "courses": page_obj,
        "page_obj": page_obj,
        "query_string": query_string,
    })


# Danh sách khóa học
def courses(request):
    courses = (
        Course.objects
        .annotate(
            avg_rating=Avg(
                'comments__rating',
                filter=Q(comments__parent_comment__isnull=True)
            ),
            rating_count=Count(
                'comments__id',
                filter=Q(
                    comments__parent_comment__isnull=True,
                    comments__rating__isnull=False,
                ),
                distinct=True,
            ),
        )
        .order_by('-id')
    )

    level = request.GET.get("level")
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    teacher = request.GET.get("teacher")
    q = request.GET.get("q")

    if level:
        courses = courses.filter(level_id=level)
    if grade:
        courses = courses.filter(grade_id=grade)
    if subject:
        courses = courses.filter(subject_id=subject)
    if teacher:
        courses = courses.filter(teacher_id=teacher)
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


def teachers_statistics(request):
    teacher_profiles = UserProfile.objects.filter(role='teacher').select_related('user').annotate(
        courses_count=Count('user__courses_teaching', distinct=True),
        approved_students=Count(
            'user__courses_teaching__enrollments',
            filter=Q(user__courses_teaching__enrollments__status='approved'),
            distinct=True,
        ),
        quizzes_count=Count('user__courses_teaching__quizzes', distinct=True),
    )

    level = request.GET.get("level")
    grade = request.GET.get("grade")
    subject = request.GET.get("subject")
    q = request.GET.get("q")

    if level:
        teacher_profiles = teacher_profiles.filter(user__courses_teaching__level_id=level)
    if grade:
        teacher_profiles = teacher_profiles.filter(user__courses_teaching__grade_id=grade)
    if subject:
        teacher_profiles = teacher_profiles.filter(user__courses_teaching__subject_id=subject)
    if q:
        teacher_profiles = teacher_profiles.filter(
            Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(bio__icontains=q)
            | Q(user__courses_teaching__title__icontains=q)
        )

    teacher_profiles = teacher_profiles.distinct().order_by('-courses_count', 'user__username')

    levels = Level.objects.all()
    grades = Grade.objects.all()
    subjects = Subject.objects.all()

    page_obj, query_string = paginate_request_queryset(request, teacher_profiles, per_page=6)

    return render(request, "teachers.html", {
        "teachers": page_obj,
        "page_obj": page_obj,
        "query_string": query_string,
        "levels": levels,
        "grades": grades,
        "subjects": subjects,
        "q": q,
    })


# Chi tiết khóa học
def course_detail(request, course_id):
    comments_available = ensure_comment_tables()

    course = get_object_or_404(Course, id=course_id)
    lessons = course.lessons.all().order_by('order')
    first_lesson = lessons.first()
    slide_embed_url = ""
    slide_download_url = ""

    if first_lesson and first_lesson.slide_url:
        slide_embed_url, slide_download_url = build_slide_urls(first_lesson.slide_url)

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
        # ✅ Chỉ kiểm tra enrollment nếu user đã chủ động đăng ký
        enrollment = course.enrollments.filter(user=request.user).first()

        if enrollment:
            enrolled = True

            if enrollment and enrollment.status == 'approved':
                approved = True
            elif enrollment.status == 'paid':
                pending = True

    can_comment = bool(enrollment and enrollment.status == 'approved')

    comments_enabled = comments_available
    comments = []
    average_rating = 0
    total_ratings = 0
    rating_rows = [{'star': star, 'count': 0, 'percent': 0} for star in range(5, 0, -1)]

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, 'Vui lòng đăng nhập để bình luận khóa học.')
            return redirect('login')

        if not can_comment:
            messages.error(request, 'Bạn cần đăng ký và thanh toán thành công trước khi được bình luận và đánh giá khóa học.')
            return redirect('course_detail', course_id=course.id)

        action = (request.POST.get('action') or 'comment').strip()

        if action == 'reply_comment':
            reply_text = (request.POST.get('reply_content') or '').strip()
            parent_comment_id = request.POST.get('comment_id')

            parent_comment = CourseComment.objects.filter(
                id=parent_comment_id,
                course=course,
                parent_comment__isnull=True,
            ).first()

            if not parent_comment:
                messages.error(request, 'Không tìm thấy bình luận để phản hồi.')
                return redirect('course_detail', course_id=course.id)

            if not reply_text:
                messages.error(request, 'Nội dung phản hồi không được để trống.')
                return redirect('course_detail', course_id=course.id)

            reply_model = CourseComment
            fallback_rating = parent_comment.rating if getattr(parent_comment, 'rating', None) else 5
            reply_model.objects.create(
                course=course,
                user=request.user,
                content=reply_text,
                rating=fallback_rating,
                parent_comment=parent_comment,
            )

            notify_comment_owner_for_reply(
                parent_comment=parent_comment,
                actor=request.user,
                reply_text=reply_text,
                comment_kind='course',
                course=course,
            )

            messages.success(request, 'Đã gửi phản hồi cho bình luận này.')
            return redirect('course_detail', course_id=course.id)

        if action == 'reply_teacher':
            reply_text = (request.POST.get('reply_content') or '').strip()
            comment_id = request.POST.get('comment_id')

            comment_obj = CourseComment.objects.filter(
                id=comment_id,
                user=request.user,
                course=course,
            ).first()

            if not comment_obj:
                messages.error(request, 'Không tìm thấy bình luận để phản hồi.')
                return redirect('course_detail', course_id=course.id)

            if not comment_obj.teacher_reply:
                messages.warning(request, 'Bình luận này chưa có phản hồi từ giảng viên.')
                return redirect('course_detail', course_id=course.id)

            if not reply_text:
                messages.error(request, 'Nội dung phản hồi không được để trống.')
                return redirect('course_detail', course_id=course.id)

                replied_at = timezone.now()
                comment_obj.user_reply = append_reply_history(
                    comment_obj.user_reply,
                    reply_text,
                    replied_at,
                )
                comment_obj.user_replied_at = replied_at
            comment_obj.save(update_fields=['user_reply', 'user_replied_at'])

            notify_teacher_for_user_reply(
                course=course,
                actor=request.user,
                reply_text=reply_text,
                comment_kind='course',
                comment_id=comment_obj.id,
            )
            messages.success(request, 'Đã gửi phản hồi lại cho giảng viên.')
            return redirect('course_detail', course_id=course.id)

        content = (request.POST.get('content') or '').strip()
        rating_raw = request.POST.get('rating')

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            rating = 0

        if not content:
            messages.error(request, 'Nội dung bình luận không được để trống.')
        elif not 1 <= rating <= 5:
            messages.error(request, 'Vui lòng chọn số sao từ 1 đến 5.')
        else:
            try:
                course_comment = CourseComment.objects.create(
                    course=course,
                    user=request.user,
                    content=content,
                    rating=rating,
                )
                notify_teacher_for_comment(
                    course=course,
                    actor=request.user,
                    rating=rating,
                    content=content,
                    comment_kind='course',
                    comment_id=course_comment.id,
                )
                messages.success(request, 'Đã gửi bình luận khóa học của bạn.')
                return redirect('course_detail', course_id=course.id)
            except (ProgrammingError, OperationalError):
                comments_enabled = False
                messages.warning(request, 'Chức năng bình luận đang tạm thời chưa sẵn sàng. Vui lòng chạy migrate.')

    try:
        comments = (
            course.comments
            .filter(parent_comment__isnull=True)
            .select_related('user')
            .prefetch_related(
                Prefetch(
                    'replies',
                    queryset=CourseComment.objects.select_related('user').order_by('created_at')
                )
            )
            .order_by('-created_at')
        )
        rating_summary = comments.aggregate(avg_rating=Avg('rating'), total_ratings=Count('id'))

        average_rating = rating_summary['avg_rating'] or 0
        total_ratings = rating_summary['total_ratings'] or 0

        rating_counts_raw = comments.values('rating').annotate(total=Count('id'))
        rating_counts = {star: 0 for star in range(1, 6)}
        for item in rating_counts_raw:
            if item['rating'] in rating_counts:
                rating_counts[item['rating']] = item['total']

        rating_rows = []
        for star in range(5, 0, -1):
            count = rating_counts[star]
            percent = (count / total_ratings * 100) if total_ratings else 0
            rating_rows.append({
                'star': star,
                'count': count,
                'percent': round(percent, 2),
            })
    except (ProgrammingError, OperationalError):
        comments_enabled = False

    return render(request, "course_detail.html", {
        "course": course,
        "lessons": lesson_page_obj,
        "lessons_total": lessons.count(),
        "first_lesson": first_lesson,
        "slide_embed_url": slide_embed_url,
        "slide_download_url": slide_download_url,
        "lesson_query_string": lesson_query_string,
        "quiz_count": quiz_count,
        "enrollment": enrollment,
        "enrolled": enrolled,
        "approved": approved,
        "pending": pending,
        "can_comment": can_comment,
        "comments": comments,
        "comments_enabled": comments_enabled,
        "average_rating": round(average_rating, 1),
        "total_ratings": total_ratings,
        "rating_rows": rating_rows,
        "rating_scale": range(5, 0, -1),
    })

# Xem bài học (lesson)
def lesson_view(request, lesson_id):
    comments_available = ensure_comment_tables()

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

    if request.method == 'POST':
        if not comments_available:
            messages.warning(request, 'Chức năng bình luận đang tạm thời chưa sẵn sàng. Vui lòng kiểm tra quyền cơ sở dữ liệu.')
            return redirect('lesson_view', lesson_id=lesson.id)

        if not request.user.is_authenticated:
            messages.warning(request, 'Vui lòng đăng nhập để bình luận bài học.')
            return redirect('login')

        # ✅ Bắt buộc phải enrolled và đã duyệt/thanh toán xong mới được bình luận
        if not enrollment:
            messages.error(request, 'Bạn cần đăng ký và thanh toán thành công trước khi được bình luận và đánh giá bài học.')
            return redirect('course_detail', course_id=course.id)

        action = (request.POST.get('action') or 'comment').strip()

        if action == 'reply_comment':
            reply_text = (request.POST.get('reply_content') or '').strip()
            parent_comment_id = request.POST.get('comment_id')

            parent_comment = LessonComment.objects.filter(
                id=parent_comment_id,
                lesson=lesson,
                parent_comment__isnull=True,
            ).first()

            if not parent_comment:
                messages.error(request, 'Không tìm thấy bình luận để phản hồi.')
                return redirect('lesson_view', lesson_id=lesson.id)

            if not reply_text:
                messages.error(request, 'Nội dung phản hồi không được để trống.')
                return redirect('lesson_view', lesson_id=lesson.id)

            reply_model = LessonComment
            fallback_rating = parent_comment.rating if getattr(parent_comment, 'rating', None) else 5
            reply_model.objects.create(
                lesson=lesson,
                user=request.user,
                content=reply_text,
                rating=fallback_rating,
                parent_comment=parent_comment,
            )

            notify_comment_owner_for_reply(
                parent_comment=parent_comment,
                actor=request.user,
                reply_text=reply_text,
                comment_kind='lesson',
                lesson=lesson,
                course=course,
            )

            messages.success(request, 'Đã gửi phản hồi cho bình luận này.')
            return redirect('lesson_view', lesson_id=lesson.id)

        if action == 'reply_teacher':
            reply_text = (request.POST.get('reply_content') or '').strip()
            comment_id = request.POST.get('comment_id')

            comment_obj = LessonComment.objects.filter(
                id=comment_id,
                user=request.user,
                lesson=lesson,
            ).first()

            if not comment_obj:
                messages.error(request, 'Không tìm thấy bình luận để phản hồi.')
                return redirect('lesson_view', lesson_id=lesson.id)

            if not comment_obj.teacher_reply:
                messages.warning(request, 'Bình luận này chưa có phản hồi từ giảng viên.')
                return redirect('lesson_view', lesson_id=lesson.id)

            if not reply_text:
                messages.error(request, 'Nội dung phản hồi không được để trống.')
                return redirect('lesson_view', lesson_id=lesson.id)

            replied_at = timezone.now()
            comment_obj.user_reply = append_reply_history(
                comment_obj.user_reply,
                reply_text,
                replied_at,
            )
            comment_obj.user_replied_at = replied_at
            comment_obj.save(update_fields=['user_reply', 'user_replied_at'])

            notify_teacher_for_user_reply(
                course=course,
                actor=request.user,
                reply_text=reply_text,
                comment_kind='lesson',
                comment_id=comment_obj.id,
                lesson=lesson,
            )
            messages.success(request, 'Đã gửi phản hồi lại cho giảng viên.')
            return redirect('lesson_view', lesson_id=lesson.id)

        content = (request.POST.get('content') or '').strip()
        rating_raw = request.POST.get('rating')

        try:
            rating = int(rating_raw)
        except (TypeError, ValueError):
            rating = 0

        if not content:
            messages.error(request, 'Nội dung bình luận không được để trống.')
        elif not 1 <= rating <= 5:
            messages.error(request, 'Vui lòng chọn số sao từ 1 đến 5.')
        else:
            lesson_comment = LessonComment.objects.create(
                lesson=lesson,
                user=request.user,
                content=content,
                rating=rating,
            )
            notify_teacher_for_comment(
                course=course,
                actor=request.user,
                rating=rating,
                content=content,
                comment_kind='lesson',
                comment_id=lesson_comment.id,
                lesson=lesson,
            )
            messages.success(request, 'Đã gửi bình luận của bạn.')
            return redirect('lesson_view', lesson_id=lesson.id)

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

    slide_embed_url = ""
    slide_download_url = ""

    if lesson.slide_url:
        slide_embed_url, slide_download_url = build_slide_urls(lesson.slide_url)

    comments = []
    average_rating = 0
    total_ratings = 0
    rating_rows = [{'star': star, 'count': 0, 'percent': 0} for star in range(5, 0, -1)]

    if comments_available:
        comments = (
            lesson.comments
            .filter(parent_comment__isnull=True)
            .select_related('user')
            .prefetch_related(
                Prefetch(
                    'replies',
                    queryset=LessonComment.objects.select_related('user').order_by('created_at')
                )
            )
            .order_by('-created_at')
        )
        rating_summary = comments.aggregate(avg_rating=Avg('rating'), total_ratings=Count('id'))

        average_rating = rating_summary['avg_rating'] or 0
        total_ratings = rating_summary['total_ratings'] or 0

        rating_counts_raw = comments.values('rating').annotate(total=Count('id'))
        rating_counts = {star: 0 for star in range(1, 6)}
        for item in rating_counts_raw:
            if item['rating'] in rating_counts:
                rating_counts[item['rating']] = item['total']

        rating_rows = []
        for star in range(5, 0, -1):
            count = rating_counts[star]
            percent = (count / total_ratings * 100) if total_ratings else 0
            rating_rows.append({
                'star': star,
                'count': count,
                'percent': round(percent, 2),
            })

    # Kiểm tra xem user có thể bình luận hay không: bắt buộc phải enrolled (đã approved)
    can_comment = bool(enrollment)

    return render(request, "lesson.html", {
        "lesson": lesson,
        "course": course,
        "enrollment": enrollment,
        "can_comment": can_comment,
        "video_id": video_id,
        "slide_embed_url": slide_embed_url,
        "slide_download_url": slide_download_url,
        "comments": comments,
        "comments_enabled": comments_available,
        "average_rating": round(average_rating, 1),
        "total_ratings": total_ratings,
        "rating_rows": rating_rows,
        "rating_scale": range(5, 0, -1),
    })

# ĐĂNG NHẬP HỌC VIÊN
def login_view(request):
    """Đăng nhập USER/STUDENT tại /login/."""
    if request.method == 'POST':
        # Luôn xóa session cũ trước khi thử đăng nhập tài khoản khác.
        SeparateSessionAuth.logout_user(request)
        SeparateSessionAuth.logout_teacher(request)

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
        # Luôn xóa session cũ trước khi thử đăng nhập tài khoản khác.
        SeparateSessionAuth.logout_user(request)
        SeparateSessionAuth.logout_teacher(request)

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
        
        # ✅ Kiểm tra số điện thoại (nếu có)
        if phone and (not phone.isdigit() or len(phone) < 9 or len(phone) > 15):
            messages.error(request, '❌ Số điện thoại không hợp lệ. Vui lòng nhập 9-15 chữ số!')
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
        'current_user': user,
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

def build_teacher_daily_report_context(request, teacher):
    raw_report_date = (request.GET.get('report_date') or '').strip()

    if raw_report_date:
        try:
            report_date = datetime.strptime(raw_report_date, '%Y-%m-%d').date()
            has_invalid_report_date = False
        except ValueError:
            report_date = timezone.localdate()
            has_invalid_report_date = True
    else:
        report_date = timezone.localdate()
        has_invalid_report_date = False

    if has_invalid_report_date:
        messages.warning(request, 'Ngày báo cáo không hợp lệ, đã chuyển về ngày hiện tại.')

    day_start = timezone.make_aware(datetime.combine(report_date, time.min))
    day_end = day_start + timedelta(days=1)

    daily_registered_enrollments = Enrollment.objects.filter(
        course__teacher=teacher,
        created__gte=day_start,
        created__lt=day_end,
    ).select_related('course')

    daily_paid_enrollments = Enrollment.objects.filter(
        course__teacher=teacher,
        status='approved',
    ).filter(
        Q(paid_at__gte=day_start, paid_at__lt=day_end)
        | (Q(paid_at__isnull=True) & Q(created__gte=day_start) & Q(created__lt=day_end))
    ).select_related('course')

    daily_report_map = {}
    for enrollment in daily_registered_enrollments:
        report_row = daily_report_map.setdefault(enrollment.course_id, {
            'course': enrollment.course,
            'registered_count': 0,
            'paid_count': 0,
            'revenue': Decimal('0'),
        })
        report_row['registered_count'] += 1

    for enrollment in daily_paid_enrollments:
        report_row = daily_report_map.setdefault(enrollment.course_id, {
            'course': enrollment.course,
            'registered_count': 0,
            'paid_count': 0,
            'revenue': Decimal('0'),
        })
        report_row['paid_count'] += 1
        report_row['revenue'] += Decimal(str(enrollment.course.price or 0))

    daily_report_rows = []
    for course in Course.objects.filter(teacher=teacher).only('id', 'title', 'price').order_by('-id'):
        report_row = daily_report_map.get(course.id)
        if not report_row:
            continue

        revenue = report_row['revenue']
        admin_share = (revenue * Decimal('0.10')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        daily_report_rows.append({
            'course': course,
            'registered_count': report_row['registered_count'],
            'paid_count': report_row['paid_count'],
            'revenue': revenue,
            'admin_share': admin_share,
        })

    daily_registered_total = sum(row['registered_count'] for row in daily_report_rows)
    daily_paid_total = sum(row['paid_count'] for row in daily_report_rows)
    daily_revenue_total = sum((row['revenue'] for row in daily_report_rows), Decimal('0'))
    daily_admin_share_total = sum((row['admin_share'] for row in daily_report_rows), Decimal('0'))

    return {
        'daily_report_date': report_date,
        'daily_report_date_value': report_date.strftime('%Y-%m-%d'),
        'daily_report_rows': daily_report_rows,
        'daily_registered_total': daily_registered_total,
        'daily_paid_total': daily_paid_total,
        'daily_revenue_total': daily_revenue_total,
        'daily_admin_share_total': daily_admin_share_total,
    }

@teacher_required
def teacher_dashboard(request):
    if not request.user.is_staff:
        return redirect('/')

    teacher = request.user
    courses = Course.objects.filter(teacher=teacher).annotate(
        avg_rating=Avg('comments__rating', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False)),
        rating_count=Count('comments', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False), distinct=True),
    )

    course_page_obj, course_query_string = paginate_request_queryset(
        request,
        courses,
        per_page=6,
        page_param='course_page'
    )

    return render(request, 'teacher/index_teacher.html', {
        'courses': course_page_obj,
        'course_page_obj': course_page_obj,
        'course_query_string': course_query_string,
    })


@teacher_required
def teacher_report(request):
    if not request.user.is_staff:
        return redirect('/')

    report_context = build_teacher_daily_report_context(request, request.user)
    return render(request, 'teacher/report.html', report_context)


@teacher_required
def teacher_students(request):
    teacher = request.current_teacher
    q = (request.GET.get('q') or '').strip()

    enrollment_queryset = Enrollment.objects.filter(
        course__teacher=teacher
    ).select_related(
        'course'
    ).order_by('-created')

    if q:
        enrollment_queryset = enrollment_queryset.filter(
            Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(course__title__icontains=q)
        )

    students_queryset = User.objects.filter(
        enrollment__in=enrollment_queryset
    ).distinct().order_by('username').select_related('profile').prefetch_related(
        Prefetch('enrollment_set', queryset=enrollment_queryset, to_attr='teacher_enrollments')
    )

    students_data = []
    for student in students_queryset:
        student_enrollments = list(getattr(student, 'teacher_enrollments', []))
        if not student_enrollments:
            continue

        avatar_url = ''
        try:
            profile = student.profile
            if profile and profile.avatar:
                avatar_url = profile.avatar.url
        except UserProfile.DoesNotExist:
            profile = None

        course_items = []
        approved_count = 0
        for enrollment in student_enrollments:
            course_items.append({
                'course_id': enrollment.course_id,
                'course_title': enrollment.course.title,
                'status': enrollment.get_status_display(),
                'status_code': enrollment.status,
                'created': enrollment.created,
            })
            if enrollment.status == 'approved':
                approved_count += 1

        students_data.append({
            'student': student,
            'avatar_url': avatar_url,
            'display_name': f"{student.first_name} {student.last_name}".strip() if (student.first_name or student.last_name) else student.username,
            'email': student.email,
            'total_registered': len(course_items),
            'total_approved': approved_count,
            'courses': course_items,
        })

    page_obj, query_string = paginate_request_queryset(
        request,
        students_data,
        per_page=8,
        page_param='student_page'
    )

    return render(request, 'teacher/students.html', {
        'students': page_obj,
        'page_obj': page_obj,
        'query_string': query_string,
        'q': q,
        'total_students': len(students_data),
        'total_registrations': enrollment_queryset.count(),
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
        
        # ✅ Kiểm tra số điện thoại (nếu có)
        if phone and (not phone.isdigit() or len(phone) < 9 or len(phone) > 15):
            messages.error(request, '❌ Số điện thoại không hợp lệ. Vui lòng nhập 9-15 chữ số!')
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
        quizzes_count=Count('quizzes', distinct=True),
        avg_rating=Avg('comments__rating', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False)),
        rating_count=Count('comments', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False), distinct=True),
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
            'current_teacher': teacher,
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

    courses = Course.objects.filter(teacher=request.user).annotate(
        avg_rating=Avg('comments__rating', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False)),
        rating_count=Count('comments', filter=Q(comments__parent_comment__isnull=True, comments__rating__isnull=False), distinct=True),
    )
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
        slide_url = request.POST.get('slide_url')
        content = request.POST.get('content')

        if video_url or slide_url or content:
            Lesson.objects.create(
                course=course,
                title="Bài học 1",
                video_url=video_url,
                slide_url=slide_url,
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

        video_url = request.POST.get('video_url')
        slide_url = request.POST.get('slide_url')
        content = request.POST.get('content')

        first_lesson = course.lessons.order_by('order').first()
        if first_lesson is None:
            first_lesson = Lesson.objects.create(
                course=course,
                title='Bài học 1',
                order=1,
                is_free_preview=True,
            )

        first_lesson.video_url = video_url
        first_lesson.slide_url = slide_url
        first_lesson.content = content
        first_lesson.save()
        

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
    first_lesson = lessons.first()
    slide_embed_url = ""
    slide_download_url = ""

    if first_lesson and first_lesson.slide_url:
        slide_embed_url, slide_download_url = build_slide_urls(first_lesson.slide_url)

    # Calculate rating statistics
    comments = course.comments.filter(parent_comment__isnull=True).select_related('user').prefetch_related(
        Prefetch(
            'replies',
            queryset=CourseComment.objects.select_related('user').order_by('created_at')
        )
    )
    rating_summary = comments.aggregate(avg_rating=Avg('rating'), total_ratings=Count('id'))
    
    average_rating = rating_summary['avg_rating'] or 0
    total_ratings = rating_summary['total_ratings'] or 0
    
    rating_counts_raw = comments.values('rating').annotate(total=Count('id'))
    rating_counts = {star: 0 for star in range(1, 6)}
    for item in rating_counts_raw:
        if item['rating'] in rating_counts:
            rating_counts[item['rating']] = item['total']
    
    rating_rows = []
    for star in range(5, 0, -1):
        count = rating_counts[star]
        percent = (count / total_ratings * 100) if total_ratings else 0
        rating_rows.append({
            'star': star,
            'count': count,
            'percent': round(percent, 2),
        })
    
    # Recalculate course rating stats for inline display
    course.avg_rating = round(average_rating, 1)
    course.rating_count = total_ratings

    return render(request, 'teacher/course_detail.html', {
        'course': course,
        'lessons': lessons,
        'first_lesson': first_lesson,
        'slide_embed_url': slide_embed_url,
        'slide_download_url': slide_download_url,
        'comments': comments,
        'average_rating': round(average_rating, 1),
        'total_ratings': total_ratings,
        'rating_rows': rating_rows,
    })

@teacher_required
def teacher_quiz_results(request):
    if not request.user.is_staff:
        return redirect('/')

    # Lấy tất cả quiz của teacher
    quizzes = Quiz.objects.filter(course__teacher=request.user).select_related('course').annotate(
        question_count=Count('questions', distinct=True),
        attempt_count=Count('userquizattempt', distinct=True)
    ).order_by('-created_at')
    quiz_page_obj, quiz_query_string = paginate_request_queryset(
        request,
        quizzes,
        per_page=10,
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
        'quizzes': quiz_page_obj,
        'quiz_count': quizzes.count(),
        'quiz_page_obj': quiz_page_obj,
        'quiz_query_string': quiz_query_string,
    })

@teacher_required
@teacher_required
def teacher_attempt_detail(request, attempt_id):
    """Xem chi tiết câu trả lời của học viên"""
    teacher = request.current_teacher
    
    # Lấy attempt và kiểm tra quyền (phải là teacher của quiz này)
    attempt = get_object_or_404(UserQuizAttempt, id=attempt_id)
    
    # Kiểm tra xem người dùng có phải là teacher của khóa học chứa quiz này không
    if attempt.quiz.course.teacher != teacher:
        messages.error(request, '❌ Bạn không có quyền xem chi tiết này.')
        return redirect('/teacher/')

    # Lấy tất cả câu trả lời của attempt
    answers = attempt.answers.all().select_related('question', 'selected_choice')

    # Lấy slide của lesson gắn với quiz, fallback lesson đầu tiên của course nếu quiz chưa gắn lesson
    lesson = attempt.quiz.lesson or attempt.quiz.course.lessons.order_by('order').first()
    slide_embed_url = ""
    slide_download_url = ""

    if lesson and lesson.slide_url:
        slide_embed_url, slide_download_url = build_slide_urls(lesson.slide_url)

    return render(request, 'teacher/attempt_detail.html', {
        'attempt': attempt,
        'answers': answers,
        'lesson': lesson,
        'slide_embed_url': slide_embed_url,
        'slide_download_url': slide_download_url,
    })


@teacher_required
def teacher_quiz_management(request):
    """Quản lý bài ôn luyện - Xem danh sách, tạo, sửa, xóa"""
    return redirect('teacher_quiz_results')


@teacher_required
def teacher_create_quiz_standalone(request):
    """Tạo bài ôn luyện mới"""
    if not request.user.is_staff:
        return redirect('/')

    # Lấy các khóa học của teacher
    courses = Course.objects.filter(teacher=request.user).order_by('-id')
    courses_data = {}

    for course in courses:
        courses_data[str(course.id)] = [
            {
                'id': lesson.id,
                'title': lesson.title,
            }
            for lesson in Lesson.objects.filter(course=course).order_by('order')
        ]

    if request.method == "POST":
        course_id = request.POST.get("course_id")
        lesson_id = request.POST.get("lesson_id")
        title = request.POST.get("title")
        description = request.POST.get("description", "")
        time_limit = request.POST.get("time_limit", 10)

        try:
            course = Course.objects.get(id=course_id, teacher=request.user)
        except Course.DoesNotExist:
            messages.error(request, "Khóa học không tồn tại hoặc bạn không có quyền truy cập")
            return redirect('teacher_quiz_management')

        lesson = None
        if lesson_id:
            try:
                lesson = Lesson.objects.get(id=lesson_id, course=course)
            except Lesson.DoesNotExist:
                lesson = None

        # Tạo quiz
        quiz = Quiz.objects.create(
            course=course,
            lesson=lesson,
            title=title,
            description=description,
            time_limit=max(int(time_limit), 0) * 60
        )

        # Xử lý câu hỏi
        questions = request.POST.getlist("question[]")
        option_a = request.POST.getlist("option_a[]")
        option_b = request.POST.getlist("option_b[]")
        option_c = request.POST.getlist("option_c[]")
        option_d = request.POST.getlist("option_d[]")
        correct = request.POST.getlist("correct_answer[]")
        points = request.POST.getlist("points[]")

        for i in range(len(questions)):
            question_text = questions[i].strip() if i < len(questions) and questions[i] else ""
            if question_text:  # Kiểm tra câu hỏi không trống
                point_value = points[i] if i < len(points) else 1
                question = Question.objects.create(
                    quiz=quiz,
                    text=question_text,
                    order=i+1,
                    points=int(point_value) if str(point_value).strip() else 1
                )

                Choice.objects.create(
                    question=question,
                    text=option_a[i] if i < len(option_a) else "",
                    is_correct=(correct[i] == "A") if i < len(correct) else False
                )
                Choice.objects.create(
                    question=question,
                    text=option_b[i] if i < len(option_b) else "",
                    is_correct=(correct[i] == "B") if i < len(correct) else False
                )
                Choice.objects.create(
                    question=question,
                    text=option_c[i] if i < len(option_c) else "",
                    is_correct=(correct[i] == "C") if i < len(correct) else False
                )
                Choice.objects.create(
                    question=question,
                    text=option_d[i] if i < len(option_d) else "",
                    is_correct=(correct[i] == "D") if i < len(correct) else False
                )

        messages.success(request, "Tạo bài ôn luyện thành công!")
        return redirect('teacher_quiz_management')

    return render(request, 'teacher/create_quiz_form.html', {
        'courses': courses,
        'courses_data': courses_data,
        'action': 'create'
    })


@teacher_required
def teacher_edit_quiz(request, quiz_id):
    """Chỉnh sửa bài ôn luyện"""
    if not request.user.is_staff:
        return redirect('/')

    quiz = get_object_or_404(Quiz, id=quiz_id, course__teacher=request.user)
    courses = Course.objects.filter(teacher=request.user).order_by('-id')
    courses_data = {}

    for course in courses:
        courses_data[str(course.id)] = [
            {
                'id': lesson.id,
                'title': lesson.title,
            }
            for lesson in Lesson.objects.filter(course=course).order_by('order')
        ]

    questions = []
    for question in quiz.questions.all().order_by('order'):
        choices = list(question.choices.all().order_by('id'))
        option_map = {'A': '', 'B': '', 'C': '', 'D': ''}
        correct_answer = 'A'
        for letter, choice in zip(['A', 'B', 'C', 'D'], choices):
            option_map[letter] = choice.text
            if choice.is_correct:
                correct_answer = letter
        questions.append({
            'text': question.text,
            'points': question.points,
            'options': option_map,
            'correct_answer': correct_answer,
        })

    if request.method == "POST":
        quiz.title = request.POST.get("title")
        quiz.description = request.POST.get("description", "")
        quiz.time_limit = max(int(request.POST.get("time_limit", 10)), 0) * 60

        course_id = request.POST.get("course_id")
        lesson_id = request.POST.get("lesson_id")
        if course_id:
            course = get_object_or_404(Course, id=course_id, teacher=request.user)
            quiz.course = course
            quiz.lesson = Lesson.objects.filter(id=lesson_id, course=course).first() if lesson_id else None

        quiz.save()

        questions = request.POST.getlist("question[]")
        option_a = request.POST.getlist("option_a[]")
        option_b = request.POST.getlist("option_b[]")
        option_c = request.POST.getlist("option_c[]")
        option_d = request.POST.getlist("option_d[]")
        correct = request.POST.getlist("correct_answer[]")
        points = request.POST.getlist("points[]")

        normalized_questions = []
        for i in range(len(questions)):
            question_text = questions[i].strip() if i < len(questions) and questions[i] else ""
            if not question_text:
                continue

            normalized_questions.append({
                'text': question_text,
                'points': int(points[i]) if i < len(points) and str(points[i]).strip() else 1,
                'option_a': option_a[i] if i < len(option_a) else "",
                'option_b': option_b[i] if i < len(option_b) else "",
                'option_c': option_c[i] if i < len(option_c) else "",
                'option_d': option_d[i] if i < len(option_d) else "",
                'correct': correct[i] if i < len(correct) else "A",
            })

        existing_questions = list(quiz.questions.all().order_by('order'))

        for idx, question_data in enumerate(normalized_questions, start=1):
            if idx <= len(existing_questions):
                question = existing_questions[idx - 1]
                question.text = question_data['text']
                question.order = idx
                question.points = question_data['points']
                question.save()
                question.choices.all().delete()
            else:
                question = Question.objects.create(
                    quiz=quiz,
                    text=question_data['text'],
                    order=idx,
                    points=question_data['points']
                )

            Choice.objects.create(
                question=question,
                text=question_data['option_a'],
                is_correct=(question_data['correct'] == "A")
            )
            Choice.objects.create(
                question=question,
                text=question_data['option_b'],
                is_correct=(question_data['correct'] == "B")
            )
            Choice.objects.create(
                question=question,
                text=question_data['option_c'],
                is_correct=(question_data['correct'] == "C")
            )
            Choice.objects.create(
                question=question,
                text=question_data['option_d'],
                is_correct=(question_data['correct'] == "D")
            )

        for question in existing_questions[len(normalized_questions):]:
            question.delete()

        messages.success(request, "Cập nhật bài ôn luyện thành công!")
        return redirect('teacher_quiz_management')

    return render(request, 'teacher/create_quiz_form.html', {
        'quiz': quiz,
        'courses': courses,
        'courses_data': courses_data,
        'questions': questions,
        'action': 'edit'
    })


@teacher_required
def teacher_delete_quiz(request, quiz_id):
    """Xóa bài ôn luyện"""
    if not request.user.is_staff:
        return redirect('/')

    quiz = get_object_or_404(Quiz, id=quiz_id, course__teacher=request.user)
    
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Xóa bài ôn luyện thành công!")
        return redirect('teacher_quiz_management')

    return render(request, 'teacher/delete_quiz_confirm.html', {
        'quiz': quiz
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
        slide_url = request.POST.get('slide_url')
        content = request.POST.get('content')

        lesson = course.lessons.first()

        if lesson:
            lesson.video_url = video_url
            lesson.slide_url = slide_url
            lesson.content = content
            lesson.save()
        else:
            Lesson.objects.create(
                course=course,
                title="Bài học 1",
                video_url=video_url,
                slide_url=slide_url,
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
    success_url = get_payment_success_url(enrollment)
    payment_reference = get_payment_reference(enrollment)

    if enrollment.status == 'approved' or enrollment.is_paid:
        return redirect(success_url)

    if request.method == "POST":
        if enrollment.status != 'approved':
            enrollment.approve()
            _create_payment_notification(enrollment)

        messages.success(request, "Thanh toán thành công!")
        return redirect(success_url)

    return render(request, 'payment.html', {
        'enrollment': enrollment,
        'success_url': success_url,
        'payment_reference': payment_reference,
    })


@student_required
def payment_status(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    success_url = get_payment_success_url(enrollment)

    return JsonResponse({
        'status': enrollment.status,
        'is_paid': enrollment.is_paid,
        'redirect_url': success_url if (enrollment.status == 'approved' or enrollment.is_paid) else None,
    })


@csrf_exempt
def payment_webhook(request):
    """Receive payment notifications from bank gateway and auto-approve enrollment."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    webhook_secret = (getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '') or '').strip()
    provided_secret = (request.headers.get('X-Webhook-Secret') or request.headers.get('x-webhook-secret') or '').strip()

    if webhook_secret and provided_secret != webhook_secret:
        return JsonResponse({'status': 'error', 'message': 'Invalid webhook secret'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)

    transfer_content = _extract_transfer_content(payload)
    if not transfer_content:
        return JsonResponse({'status': 'ignored', 'message': 'Transfer content not found'}, status=200)

    enrollment = _find_enrollment_from_transfer_content(transfer_content)
    if not enrollment:
        return JsonResponse({'status': 'ignored', 'message': 'No matching enrollment'}, status=200)

    transfer_amount = _extract_transfer_amount(payload)
    course_price = Decimal(str(enrollment.course.price or 0))
    if transfer_amount is not None and transfer_amount < course_price:
        return JsonResponse({'status': 'ignored', 'message': 'Transferred amount is less than course price'}, status=200)

    if enrollment.status != 'approved':
        enrollment.approve()
        _create_payment_notification(enrollment)

    return JsonResponse({'status': 'success', 'message': 'Payment confirmed', 'enrollment_id': enrollment.id})


@student_required
def payment_confirm(request, enrollment_id):
    """Xác nhận thanh toán và cập nhật trạng thái enrollment"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)
    
    if request.method == "POST":
        if enrollment.status != 'approved':
            enrollment.approve()
            _create_payment_notification(enrollment)
        
        success_url = get_payment_success_url(enrollment)
        return JsonResponse({
            'status': 'success',
            'message': 'Thanh toán đã được xác nhận',
            'redirect_url': success_url,
        })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@student_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course
    )

    # ===== LẤY THÔNG TIN NGƯỜI DÙNG TỰ ĐỘNG =====
    user = request.user
    full_name = f"{user.first_name} {user.last_name}".strip() or user.username
    email = user.email or ""
    
    # Lấy số điện thoại từ UserProfile nếu có
    phone = ""
    try:
        user_profile = getattr(user, 'profile', None)
        if user_profile:
            phone = user_profile.phone or ""
    except Exception:
        pass

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        payment_method = request.POST.get("payment_method")

        # 👉 validate đơn giản
        if not full_name or not email or not phone or not payment_method:
            return render(request, 'enroll_confirm.html', {
                'enrollment': enrollment,
                'error': 'Vui lòng nhập đầy đủ thông tin!',
                'full_name': full_name,
                'email': email,
                'phone': phone,
            })
        
        # ✅ Kiểm tra số điện thoại chỉ chứa số
        if not phone.isdigit() or len(phone) < 9 or len(phone) > 15:
            return render(request, 'enroll_confirm.html', {
                'enrollment': enrollment,
                'error': 'Số điện thoại không hợp lệ. Vui lòng nhập 9-15 chữ số!',
                'full_name': full_name,
                'email': email,
                'phone': phone,
            })

        # 👉 redirect qua payment sau khi nhập xong (khóa học có phí)
        if course.price and course.price > 0:
            return redirect('payment', enrollment_id=enrollment.id)

        # ✅ Khóa học miễn phí: duyệt sau khi đã xác nhận đăng ký
        if course.price == 0 and enrollment.status != 'approved':
            enrollment.approve()

        messages.success(request, 'Đăng ký khóa học thành công.')
        return redirect('course_detail', course_id=course.id)

    return render(request, 'enroll_confirm.html', {
        'enrollment': enrollment,
        'full_name': full_name,
        'email': email,
        'phone': phone,
    })



@teacher_required
def mark_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({'status': 'ok'})


@student_required
def mark_user_notifications_read(request):
    if request.method == "POST":
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return JsonResponse({'status': 'ok'})


@student_required
def user_reply_comment(request, notification_id):
    current_user = getattr(request, 'current_user', None) or request.user
    notification = Notification.objects.filter(id=notification_id, user=current_user).first()
    if not notification:
        messages.info(request, 'Thông báo này không còn tồn tại hoặc không thuộc tài khoản của bạn.')
        return redirect('user_profile')
    clean_message, meta = parse_comment_notification_message(notification.message)

    if not meta:
        meta = infer_student_comment_meta_from_legacy_message(clean_message, current_user)
        if not meta:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            messages.info(request, 'Thông báo này không có nội dung trả lời trực tiếp.')
            return redirect('user_profile')

    comment_type = meta.get('type')
    comment_id = meta.get('comment_id')
    teacher_id = meta.get('teacher_id')

    if not comment_type or not comment_id:
        messages.warning(request, 'Dữ liệu thông báo không hợp lệ.')
        return redirect('user_profile')

    comment_obj = None
    target_url = '/'

    try:
        if comment_type == 'lesson':
            comment_obj = LessonComment.objects.select_related('lesson', 'lesson__course').get(
                id=comment_id,
                user=current_user,
            )
            target_url = f"/lesson/{comment_obj.lesson_id}/"
            if not teacher_id:
                teacher_id = comment_obj.lesson.course.teacher_id
        else:
            comment_obj = CourseComment.objects.select_related('course').get(
                id=comment_id,
                user=current_user,
            )
            target_url = f"/course/{comment_obj.course_id}/"
            if not teacher_id:
                teacher_id = comment_obj.course.teacher_id
    except (LessonComment.DoesNotExist, CourseComment.DoesNotExist):
        comment_obj = None

    if not comment_obj:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        messages.warning(request, 'Không tìm thấy bình luận gốc để phản hồi.')
        return redirect('user_profile')

    if request.method == 'POST':
        reply_content = (request.POST.get('reply_content') or '').strip()

        if not reply_content:
            messages.error(request, 'Nội dung phản hồi không được để trống.')
        else:
            model_field_names = {field.name for field in comment_obj._meta.concrete_fields}
            if 'user_reply' in model_field_names and 'user_replied_at' in model_field_names:
                replied_at = timezone.now()
                comment_obj.user_reply = append_reply_history(
                    comment_obj.user_reply,
                    reply_content,
                    replied_at,
                )
                comment_obj.user_replied_at = replied_at
                comment_obj.save(update_fields=['user_reply', 'user_replied_at'])
            else:
                reply_model = LessonComment if comment_type == 'lesson' else CourseComment
                fallback_rating = comment_obj.rating if getattr(comment_obj, 'rating', None) else 5
                create_kwargs = {
                    'user': current_user,
                    'content': reply_content,
                    'rating': fallback_rating,
                    'parent_comment': comment_obj,
                }
                if comment_type == 'lesson':
                    create_kwargs['lesson'] = comment_obj.lesson
                else:
                    create_kwargs['course'] = comment_obj.course

                reply_model.objects.create(**create_kwargs)

            teacher = User.objects.filter(id=teacher_id).first() if teacher_id else None
            if teacher:
                if comment_type == 'lesson':
                    course = comment_obj.lesson.course
                    lesson = comment_obj.lesson
                else:
                    course = comment_obj.course
                    lesson = None

                notify_teacher_for_user_reply(
                    course=course,
                    actor=current_user,
                    reply_text=reply_content,
                    comment_kind=comment_type,
                    comment_id=comment_obj.id,
                    lesson=lesson,
                )

            notification.is_read = True
            notification.save(update_fields=['is_read'])
            messages.success(request, 'Đã gửi phản hồi lại cho giảng viên.')
            return redirect(target_url)

    csrf_token = get_token(request)
    comment_preview = escape(comment_obj.content)
    model_field_names = {field.name for field in comment_obj._meta.concrete_fields}
    if 'teacher_reply' in model_field_names:
        teacher_reply_preview = escape(getattr(comment_obj, 'teacher_reply', '') or '')
    else:
        teacher_reply_preview = ''
        latest_teacher_reply = None
        if teacher_id:
            latest_teacher_reply = comment_obj.replies.filter(user_id=teacher_id).order_by('-created_at').first()
        if latest_teacher_reply:
            teacher_reply_preview = escape(latest_teacher_reply.content or '')
    notification_text = escape(clean_message)

    html = f"""
<!DOCTYPE html>
<html lang=\"vi\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Phản hồi giảng viên</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; padding: 24px; color: #0f172a; }}
        .box {{ max-width: 860px; margin: 0 auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 22px; }}
        .note {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 14px; }}
        textarea {{ width: 100%; min-height: 130px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px 12px; margin: 8px 0 12px; }}
        .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .btn {{ display: inline-flex; align-items: center; padding: 10px 16px; border-radius: 10px; text-decoration: none; font-weight: 600; }}
        .btn-primary {{ border: 0; background: #1d4ed8; color: #fff; cursor: pointer; }}
        .btn-muted {{ border: 1px solid #cbd5e1; color: #334155; background: #fff; }}
    </style>
</head>
<body>
    <div class=\"box\">
        <h2 style=\"margin: 0 0 14px;\">Phản hồi lại giảng viên</h2>
        <div class=\"note\">
            <p style=\"margin: 0;\"><strong>Thông báo:</strong> {notification_text}</p>
            <p style=\"margin: 10px 0 0;\"><strong>Bình luận gốc:</strong> {comment_preview}</p>
            {f'<p style="margin: 10px 0 0;"><strong>Phản hồi của giảng viên:</strong> {teacher_reply_preview}</p>' if teacher_reply_preview else ''}
        </div>

        <form method=\"post\">
            <input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\"{csrf_token}\">
            <label for=\"reply_content\" style=\"font-weight: 600;\">Nội dung phản hồi</label>
            <textarea id=\"reply_content\" name=\"reply_content\" maxlength=\"1000\" required></textarea>
            <div class=\"actions\">
                <button class=\"btn btn-primary\" type=\"submit\">Gửi phản hồi</button>
                <a class=\"btn btn-muted\" href=\"{escape(target_url)}\">Quay lại</a>
            </div>
        </form>
    </div>
</body>
</html>
"""

    return HttpResponse(html)


@teacher_required
def teacher_reply_comment(request, notification_id):
    current_teacher = getattr(request, 'current_teacher', None) or request.user
    notification = Notification.objects.filter(id=notification_id, user=current_teacher).first()
    if not notification:
        messages.info(request, 'Thông báo này không còn tồn tại hoặc không thuộc tài khoản giảng viên hiện tại.')
        return redirect('teacher_dashboard')
    clean_message, meta = parse_comment_notification_message(notification.message)

    if not meta:
        meta = infer_comment_meta_from_legacy_message(clean_message, request.user)
        if not meta:
            messages.warning(request, 'Thông báo này không hỗ trợ trả lời trực tiếp.')
            return redirect('teacher_dashboard')

    comment_type = meta.get('type')
    comment_id = meta.get('comment_id')
    student_id = meta.get('student_id')

    if not comment_type or not comment_id or not student_id:
        messages.warning(request, 'Dữ liệu thông báo không hợp lệ.')
        return redirect('teacher_dashboard')

    comment_obj = None
    target_url = None

    try:
        if comment_type == 'lesson':
            comment_obj = LessonComment.objects.select_related('lesson', 'user').get(id=comment_id)
            target_url = f"/lesson/{comment_obj.lesson_id}/"
        else:
            comment_obj = CourseComment.objects.select_related('course', 'user').get(id=comment_id)
            target_url = f"/course/{comment_obj.course_id}/"
    except (LessonComment.DoesNotExist, CourseComment.DoesNotExist):
        comment_obj = None

    if not comment_obj:
        messages.warning(request, 'Không tìm thấy bình luận gốc để phản hồi. Vui lòng mở lại từ thông báo mới nhất.')
        return redirect('teacher_dashboard')

    if request.method == 'POST':
        reply_content = (request.POST.get('reply_content') or '').strip()

        if not reply_content:
            messages.error(request, 'Nội dung phản hồi không được để trống.')
        else:
            # New schema: teacher reply is stored as a child comment.
            # Legacy schema fallback keeps older deployments working.
            model_field_names = {field.name for field in comment_obj._meta.concrete_fields}
            if 'teacher_reply' in model_field_names and 'teacher_replied_at' in model_field_names:
                comment_obj.teacher_reply = reply_content
                comment_obj.teacher_replied_at = timezone.now()
                comment_obj.save(update_fields=['teacher_reply', 'teacher_replied_at'])
            else:
                reply_model = LessonComment if comment_type == 'lesson' else CourseComment
                fallback_rating = comment_obj.rating if getattr(comment_obj, 'rating', None) else 5
                create_kwargs = {
                    'user': request.user,
                    'content': reply_content,
                    'rating': fallback_rating,
                    'parent_comment': comment_obj,
                }
                if comment_type == 'lesson':
                    create_kwargs['lesson'] = comment_obj.lesson
                else:
                    create_kwargs['course'] = comment_obj.course

                reply_model.objects.create(**create_kwargs)

            student = User.objects.filter(id=student_id).first()
            if student:
                destination = comment_obj.lesson.title if comment_type == 'lesson' else comment_obj.course.title
                student_meta = {
                    'type': comment_type,
                    'comment_id': str(comment_obj.id),
                    'student_id': str(student.id),
                    'teacher_id': str(request.user.id),
                    'course_id': str(comment_obj.lesson.course_id) if comment_type == 'lesson' else str(comment_obj.course_id),
                }
                if comment_type == 'lesson':
                    student_meta['lesson_id'] = str(comment_obj.lesson_id)

                Notification.objects.create(
                    user=student,
                    message=build_comment_notification_message(
                        f"Giảng viên {request.user.username} đã phản hồi bình luận của bạn ở '{destination}': \"{reply_content[:150]}\"",
                        student_meta,
                    )
                )

            notification.is_read = True
            notification.save(update_fields=['is_read'])
            messages.success(request, 'Đã gửi phản hồi cho học viên.')
            return redirect('teacher_dashboard')

    csrf_token = get_token(request)
    comment_preview = escape(comment_obj.content) if comment_obj else ''
    notification_text = escape(clean_message)
    back_url = target_url or '/teacher/'

    html = f"""
<!DOCTYPE html>
<html lang=\"vi\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Phản hồi bình luận</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f1f5f9; padding: 24px; color: #0f172a; }}
        .box {{ max-width: 860px; margin: 0 auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 22px; }}
        .note {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; margin-bottom: 14px; }}
        textarea {{ width: 100%; min-height: 130px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 10px 12px; margin: 8px 0 12px; }}
        .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .btn {{ display: inline-flex; align-items: center; padding: 10px 16px; border-radius: 10px; text-decoration: none; font-weight: 600; }}
        .btn-primary {{ border: 0; background: #1d4ed8; color: #fff; cursor: pointer; }}
        .btn-muted {{ border: 1px solid #cbd5e1; color: #334155; background: #fff; }}
    </style>
</head>
<body>
    <div class=\"box\">
        <h2 style=\"margin: 0 0 14px;\">Phản hồi bình luận học viên</h2>
        <div class=\"note\">
            <p style=\"margin: 0;\"><strong>Thông báo:</strong> {notification_text}</p>
            {f'<p style="margin: 10px 0 0;"><strong>Bình luận gốc:</strong> {comment_preview}</p>' if comment_obj else ''}
        </div>

        <form method=\"post\">
            <input type=\"hidden\" name=\"csrfmiddlewaretoken\" value=\"{csrf_token}\">
            <label for=\"reply_content\" style=\"font-weight: 600;\">Nội dung phản hồi</label>
            <textarea id=\"reply_content\" name=\"reply_content\" maxlength=\"1000\" required></textarea>
            <div class=\"actions\">
                <button class=\"btn btn-primary\" type=\"submit\">Gửi phản hồi</button>
                <a class=\"btn btn-muted\" href=\"{escape(back_url)}\">Quay lại</a>
            </div>
        </form>
    </div>
</body>
</html>
"""
    return HttpResponse(html)
    
