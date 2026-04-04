from accounts.auth import SeparateSessionAuth

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
        
        # ✅ QUAN TRỌNG: Override request.user để tương thích với code cũ
        # Ưu tiên: teacher > user > admin
        if request.path.startswith('/teacher/'):
            # Trang teacher → dùng current_teacher
            if request.current_teacher:
                request.user = request.current_teacher
        elif request.path.startswith('/admin/'):
            # Trang admin → giữ nguyên request.user của Django
            pass  
        else:
            # Trang user → dùng current_user
            if request.current_user:
                request.user = request.current_user
        
        response = self.get_response(request)
        return response
