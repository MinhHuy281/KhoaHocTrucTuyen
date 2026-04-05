from accounts.auth import SeparateSessionAuth
from django.contrib.auth.models import AnonymousUser

class InjectCurrentUserMiddleware:
    """
    Middleware tự động thêm current_user và current_teacher vào request
    Và override request.user để tương thích với code cũ
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inject current_user cho student views
        request.current_user = SeparateSessionAuth.get_user(request)
        
        # Inject current_teacher cho teacher views  
        request.current_teacher = SeparateSessionAuth.get_teacher(request)
        
        # Thêm helper methods
        request.is_user_authenticated = SeparateSessionAuth.is_user_authenticated(request)
        request.is_teacher_authenticated = SeparateSessionAuth.is_teacher_authenticated(request)
        
        # Override request.user theo khu vực để tách session teacher/user/admin.
        if request.path.startswith('/teacher/'):
            request.user = request.current_teacher or AnonymousUser()
        elif request.path.startswith('/admin/'):
            pass  
        else:
            request.user = request.current_user or AnonymousUser()
        
        response = self.get_response(request)
        return response
