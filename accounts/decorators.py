from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode
from functools import wraps
from .auth import SeparateSessionAuth

def teacher_required(view_func):
    """
    Decorator yêu cầu đăng nhập TEACHER (session riêng)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not SeparateSessionAuth.is_teacher_authenticated(request):
            messages.warning(request, '⚠️ Vui lòng đăng nhập tài khoản giảng viên!')
            next_url = request.get_full_path()
            query = urlencode({'next': next_url})
            return redirect(f"{reverse('teacher_login')}?{query}")
        
        # Gán current_user vào request để dễ sử dụng
        request.current_teacher = SeparateSessionAuth.get_teacher(request)
        return view_func(request, *args, **kwargs)
    
    return wrapper


def student_required(view_func):
    """
    Decorator yêu cầu đăng nhập USER/STUDENT (session riêng)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not SeparateSessionAuth.is_user_authenticated(request):
            messages.warning(request, '⚠️ Vui lòng đăng nhập để tiếp tục!')
            next_url = request.get_full_path()
            query = urlencode({'next': next_url})
            return redirect(f"{reverse('login')}?{query}")
        
        # Gán current_user vào request
        request.current_user = SeparateSessionAuth.get_user(request)
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_required(view_func):
    """
    Decorator yêu cầu đăng nhập ADMIN (dùng session mặc định Django)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Admin dùng request.user mặc định của Django
        if not request.user.is_authenticated:
            return redirect('/admin/login/')
        
        if not request.user.is_superuser:
            messages.error(request, '❌ Bạn không có quyền admin!')
            return redirect('/')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

