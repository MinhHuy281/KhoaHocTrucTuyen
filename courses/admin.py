from django.contrib import admin
from django.db.models import Avg, Count
from django.utils import timezone
from .models import *
from .models import Course, Lesson, Enrollment, Level, Grade, Subject, Quiz, Question, Choice, UserQuizAttempt, Notification, LessonComment, CourseComment, ContactRequest

# ================= LEVEL, GRADE, SUBJECT =================
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_filter = ('level',)
    search_fields = ('name',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# ================= COURSE =================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'level', 'grade', 'subject', 'price', 'is_published')
    list_filter = ('is_published', 'level', 'grade', 'subject')
    search_fields = ('title', 'teacher__username', 'description')
    list_editable = ('is_published', 'price')
    
    fieldsets = (
        ('📚 Thông tin cơ bản', {
            'fields': ('title', 'teacher', 'description')
        }),
        ('🎯 Phân loại', {
            'fields': ('level', 'grade', 'subject')
        }),
        ('💰 Giá & Trạng thái', {
            'fields': ('price', 'is_free', 'is_published')
        }),
        ('🖼️ Hình ảnh', {
            'fields': ('image',)
        }),
    )

# ✅ ENROLLMENT ADMIN
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'status', 'is_paid', 'created', 'paid_at')
    list_filter = ('status', 'is_paid', 'course', 'created', 'paid_at')
    search_fields = ('user__username', 'course__title')
    readonly_fields = ('created', 'paid_at')
    
    fieldsets = (
        ('👤 Người dùng', {
            'fields': ('user',)
        }),
        ('📚 Khóa học', {
            'fields': ('course',)
        }),
        ('💳 Thanh toán', {
            'fields': ('status', 'is_paid', 'paid_at')
        }),
        ('⏰ Thời gian', {
            'fields': ('created',)
        }),
    )

    # 👉 Action duyệt nhanh
    actions = ['approve_enrollments', 'reject_enrollments']

    def approve_enrollments(self, request, queryset):
        updated = queryset.update(status='approved', is_paid=True, paid_at=timezone.now())
        self.message_user(request, f'✅ Đã duyệt {updated} đăng ký.')
    approve_enrollments.short_description = "✅ Duyệt thanh toán"
    
    def reject_enrollments(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'❌ Đã từ chối {updated} đăng ký.')
    reject_enrollments.short_description = "❌ Từ chối thanh toán"

# ================= LESSON =================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_free_preview', 'avg_rating_display', 'rating_count')
    list_filter = ('course', 'is_free_preview')
    search_fields = ('title', 'course__title')
    list_editable = ('order', 'is_free_preview')
    
    fieldsets = (
        ('📖 Thông tin bài học', {
            'fields': ('course', 'title', 'order')
        }),
        ('📝 Nội dung', {
            'fields': ('content', 'video_url', 'video_file')
        }),
        ('🔓 Quyền truy cập', {
            'fields': ('is_free_preview',)
        }),
    )

    def avg_rating_display(self, obj):
        lesson_avg = obj.comments.filter(rating__isnull=False).aggregate(avg=Avg('rating'))['avg']
        if lesson_avg is not None:
            return f"{lesson_avg:.1f}"

        # Fallback: nếu user đánh giá ở cấp khóa học, vẫn phản ánh cho bài học thuộc khóa đó.
        course_avg = CourseComment.objects.filter(
            course=obj.course,
            rating__isnull=False,
        ).aggregate(avg=Avg('rating'))['avg']

        if course_avg is None:
            return '0.0'

        return f"{course_avg:.1f}"

    avg_rating_display.short_description = 'Đánh giá TB'
    avg_rating_display.admin_order_field = 'id'

    def rating_count(self, obj):
        lesson_count = obj.comments.filter(rating__isnull=False).count()
        if lesson_count:
            return lesson_count

        return CourseComment.objects.filter(
            course=obj.course,
            rating__isnull=False,
        ).count()

    rating_count.short_description = 'Lượt đánh giá'
    rating_count.admin_order_field = 'id'

# ================= QUIZ =================
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ('text', 'is_correct')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'points', 'order')
    list_filter = ('quiz',)
    search_fields = ('text', 'quiz__title')
    list_editable = ('points', 'order')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'time_limit', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('📝 Thông tin Quiz', {
            'fields': ('title', 'course', 'lesson', 'description')
        }),
        ('⚙️ Cài đặt', {
            'fields': ('time_limit',)
        }),
        ('⏰ Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'score', 'total_points', 'percentage', 'completed', 'started_at')
    list_filter = ('completed', 'quiz', 'started_at')
    search_fields = ('user__username', 'quiz__title')
    readonly_fields = ('started_at', 'finished_at', 'percentage')
    
    fieldsets = (
        ('👤 Thông tin', {
            'fields': ('user', 'quiz')
        }),
        ('📊 Kết quả', {
            'fields': ('score', 'total_points', 'percentage', 'correct_answers', 'wrong_answers', 'completed')
        }),
        ('⏰ Thời gian', {
            'fields': ('started_at', 'finished_at')
        }),
    )

# ================= NOTIFICATION =================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)


@admin.register(LessonComment)
class LessonCommentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'lesson')
    search_fields = ('lesson__title', 'user__username', 'content')
    readonly_fields = ('created_at',)


@admin.register(CourseComment)
class CourseCommentAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at', 'course')
    search_fields = ('course__title', 'user__username', 'content')
    readonly_fields = ('created_at',)


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'subject', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at', 'user')
    list_editable = ('status',)

    fieldsets = (
        ('👤 Người gửi', {
            'fields': ('user', 'full_name', 'phone', 'email')
        }),
        ('📝 Nội dung tư vấn', {
            'fields': ('subject', 'message')
        }),
        ('⚙️ Xử lý', {
            'fields': ('status', 'admin_note')
        }),
        ('⏰ Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )

# Customize admin site header
admin.site.site_header = "📚 KhoaHocTrucTuyen Admin"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Chào mừng đến trang quản trị"
