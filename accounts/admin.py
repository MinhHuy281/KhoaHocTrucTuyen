from django.contrib import admin
from .models import UserProfile

# Import custom User admin
from .user_admin import CustomUserAdmin

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')
    
    fieldsets = (
        ('👤 Thông tin người dùng', {
            'fields': ('user', 'role')
        }),
        ('📱 Thông tin liên hệ', {
            'fields': ('phone', 'avatar', 'bio')
        }),
    )


