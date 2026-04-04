from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered
from django.contrib import messages

# Unregister default User admin
try:
    admin.site.unregister(User)
except NotRegistered:
    pass

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Custom User Admin với xử lý xóa an toàn
    """
    
    def delete_queryset(self, request, queryset):
        """Override xóa nhiều users"""
        for user in queryset:
            self.delete_user_safely(request, user)
    
    def delete_model(self, request, obj):
        """Override xóa 1 user"""
        self.delete_user_safely(request, obj)
    
    def delete_user_safely(self, request, user):
        """Xóa user cùng với tất cả dữ liệu liên quan"""
        try:
            # Xóa các related objects trước
            from courses.models import Enrollment, Course, Quiz, UserQuizAttempt, Notification
            
            # Xóa enrollments
            Enrollment.objects.filter(user=user).delete()
            
            # Xóa courses do user tạo
            Course.objects.filter(teacher=user).delete()
            
            # Xóa quiz attempts
            UserQuizAttempt.objects.filter(user=user).delete()
            
            # Xóa notifications
            Notification.objects.filter(user=user).delete()
            
            # Xóa UserProfile nếu có
            try:
                from accounts.models import UserProfile
                UserProfile.objects.filter(user=user).delete()
            except:
                pass
            
            # Cuối cùng xóa user
            user.delete()
            
            messages.success(request, f'✅ Đã xóa user {user.username} và tất cả dữ liệu liên quan.')
            
        except Exception as e:
            messages.error(request, f'❌ Lỗi khi xóa user: {str(e)}')
    
    # Thêm action xóa an toàn
    actions = ['delete_selected_safely']
    
    def delete_selected_safely(self, request, queryset):
        """Action xóa nhiều users an toàn"""
        count = queryset.count()
        for user in queryset:
            self.delete_user_safely(request, user)
        messages.success(request, f'✅ Đã xóa {count} users và dữ liệu liên quan.')
    delete_selected_safely.short_description = "🗑️ Xóa users đã chọn (an toàn)"
