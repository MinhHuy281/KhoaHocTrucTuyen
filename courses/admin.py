from django.contrib import admin
from .models import *
from .models import Course, Lesson, Enrollment, Level, Grade, Subject

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