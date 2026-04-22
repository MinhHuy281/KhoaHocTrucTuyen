from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class SeparateSessionAuth:
    """
    Hệ thống đăng nhập riêng biệt cho User, Teacher, Admin
    Mỗi loại có session key riêng
    """
    
    # Session keys riêng cho từng loại
    USER_SESSION_KEY = '_user_auth_id'
    TEACHER_SESSION_KEY = '_teacher_auth_id'
    # Admin dùng session mặc định của Django
    
    @staticmethod
    def login_user(request, user):
        """Đăng nhập cho USER (học viên)"""
        # Tránh giữ đồng thời session teacher cũ gây nhầm ngữ cảnh user.
        if SeparateSessionAuth.TEACHER_SESSION_KEY in request.session:
            del request.session[SeparateSessionAuth.TEACHER_SESSION_KEY]
        request.session[SeparateSessionAuth.USER_SESSION_KEY] = user.id
        request.session.modified = True
    
    @staticmethod
    def login_teacher(request, user):
        """Đăng nhập cho TEACHER (giảng viên)"""
        # Tránh giữ đồng thời session user cũ gây nhầm ngữ cảnh teacher.
        if SeparateSessionAuth.USER_SESSION_KEY in request.session:
            del request.session[SeparateSessionAuth.USER_SESSION_KEY]
        request.session[SeparateSessionAuth.TEACHER_SESSION_KEY] = user.id
        request.session.modified = True
    
    @staticmethod
    def logout_user(request):
        """Đăng xuất USER"""
        if SeparateSessionAuth.USER_SESSION_KEY in request.session:
            del request.session[SeparateSessionAuth.USER_SESSION_KEY]
            request.session.modified = True
    
    @staticmethod
    def logout_teacher(request):
        """Đăng xuất TEACHER"""
        if SeparateSessionAuth.TEACHER_SESSION_KEY in request.session:
            del request.session[SeparateSessionAuth.TEACHER_SESSION_KEY]
            request.session.modified = True
    
    @staticmethod
    def get_user(request):
        """Lấy USER đã đăng nhập (cho trang học viên)"""
        user_id = request.session.get(SeparateSessionAuth.USER_SESSION_KEY)
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                return None
        return None
    
    @staticmethod
    def get_teacher(request):
        """Lấy TEACHER đã đăng nhập (cho trang giảng viên)"""
        teacher_id = request.session.get(SeparateSessionAuth.TEACHER_SESSION_KEY)
        if teacher_id:
            try:
                return User.objects.get(id=teacher_id)
            except User.DoesNotExist:
                return None
        return None
    
    @staticmethod
    def is_user_authenticated(request):
        """Kiểm tra USER đã đăng nhập chưa"""
        return SeparateSessionAuth.get_user(request) is not None
    
    @staticmethod
    def is_teacher_authenticated(request):
        """Kiểm tra TEACHER đã đăng nhập chưa"""
        return SeparateSessionAuth.get_teacher(request) is not None
