from .auth import SeparateSessionAuth

def auth_context(request):
    """
    Context processor để thêm current_user và current_teacher vào templates
    """
    context = {
        'current_user': SeparateSessionAuth.get_user(request),
        'current_teacher': SeparateSessionAuth.get_teacher(request),
        'is_user_authenticated': SeparateSessionAuth.is_user_authenticated(request),
        'is_teacher_authenticated': SeparateSessionAuth.is_teacher_authenticated(request),
    }
    return context
