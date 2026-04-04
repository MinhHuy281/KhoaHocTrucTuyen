from django.contrib import admin
from .models import *
from .models import Course, Lesson, Enrollment, Level, Grade, Subject, Quiz, Question, Choice, UserQuizAttempt, Notification

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
    list_display = ('user', 'course', 'status', 'is_paid', 'created')
    list_filter = ('status', 'is_paid', 'course', 'created')
    search_fields = ('user__username', 'course__title')
    readonly_fields = ('created',)
    
    fieldsets = (
        ('👤 Người dùng', {
            'fields': ('user',)
        }),
        ('📚 Khóa học', {
            'fields': ('course',)
        }),
        ('💳 Thanh toán', {
            'fields': ('status', 'is_paid')
        }),
        ('⏰ Thời gian', {
            'fields': ('created',)
        }),
    )

    # 👉 Action duyệt nhanh
    actions = ['approve_enrollments', 'reject_enrollments']

    def approve_enrollments(self, request, queryset):
        updated = queryset.update(status='approved', is_paid=True)
        self.message_user(request, f'✅ Đã duyệt {updated} đăng ký.')
    approve_enrollments.short_description = "✅ Duyệt thanh toán"
    
    def reject_enrollments(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'❌ Đã từ chối {updated} đăng ký.')
    reject_enrollments.short_description = "❌ Từ chối thanh toán"

# ================= LESSON =================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_free_preview')
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

# Customize admin site header
admin.site.site_header = "📚 KhoaHocTrucTuyen Admin"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Chào mừng đến trang quản trị"
