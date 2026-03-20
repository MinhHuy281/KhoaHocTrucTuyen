from django.contrib import admin
from .models import *
from .models import Course, Lesson, Enrollment, Level, Grade, Subject, Quiz, Question, Choice, UserQuizAttempt

admin.site.register(Level)
admin.site.register(Grade)
admin.site.register(Subject)
admin.site.register(Course)
admin.site.register(Enrollment)
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_free_preview')
    list_filter = ('course', 'is_free_preview')
    search_fields = ('title',)
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4  # Mặc định 4 lựa chọn

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'points', 'order')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'time_limit', 'created_at')
    list_filter = ('course',)

admin.site.register(UserQuizAttempt)