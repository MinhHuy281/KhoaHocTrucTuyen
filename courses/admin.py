from django.contrib import admin
from .models import *
from .models import Course, Lesson, Enrollment, Level, Grade, Subject, Quiz, Question, Choice, UserQuizAttempt

admin.site.register(Level)
admin.site.register(Grade)
admin.site.register(Subject)
admin.site.register(Course)

# ✅ FIX ENROLLMENT ADMIN (QUAN TRỌNG)
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'status', 'is_paid', 'created')
    list_filter = ('status', 'is_paid', 'course')
    search_fields = ('user__username', 'course__title')

    # 👉 Action duyệt nhanh
    actions = ['approve_enrollments']

    def approve_enrollments(self, request, queryset):
        queryset.update(status='approved', is_paid=True)
    approve_enrollments.short_description = "Duyệt thanh toán (Approved)"

# ================= LESSON =================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_free_preview')
    list_filter = ('course', 'is_free_preview')
    search_fields = ('title',)

# ================= QUIZ =================
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'points', 'order')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'time_limit', 'created_at')
    list_filter = ('course',)

admin.site.register(UserQuizAttempt)