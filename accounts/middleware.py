from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class AdminAccessMiddleware:
    """
    Middleware để đảm bảo chỉ superuser hoặc staff được vào /admin/
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Kiểm tra nếu đang truy cập admin
        if request.path.startswith('/admin/'):
            # Cho phép truy cập static files và login page
            if not request.path.startswith('/admin/login/') and \
               not request.path.startswith('/admin/jsi18n/') and \
               not request.path.startswith('/admin/logout/'):
                # Kiểm tra user
                if not request.user.is_authenticated:
                    return redirect('/admin/login/?next=' + request.path)
                
                # Chỉ cho phép superuser hoặc staff vào admin
                if not (request.user.is_superuser or request.user.is_staff):
                    messages.error(request, '❌ Bạn không có quyền truy cập trang quản trị!')
                    return redirect('/')
        
        response = self.get_response(request)
        return response
