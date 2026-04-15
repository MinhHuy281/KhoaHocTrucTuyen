from .auth import SeparateSessionAuth
from .models import UserProfile

def auth_context(request):
    """
    Context processor để thêm current_user và current_teacher vào templates
    """
    current_user = SeparateSessionAuth.get_user(request)
    current_teacher = SeparateSessionAuth.get_teacher(request)

    current_user_avatar_url = None
    current_teacher_avatar_url = None

    if current_user:
        profile = UserProfile.objects.filter(user=current_user).only('avatar').first()
        if profile and profile.avatar:
            current_user_avatar_url = profile.avatar.url

    if current_teacher:
        profile = UserProfile.objects.filter(user=current_teacher).only('avatar').first()
        if profile and profile.avatar:
            current_teacher_avatar_url = profile.avatar.url

    context = {
        'current_user': current_user,
        'current_teacher': current_teacher,
        'is_user_authenticated': SeparateSessionAuth.is_user_authenticated(request),
        'is_teacher_authenticated': SeparateSessionAuth.is_teacher_authenticated(request),
        'current_user_avatar_url': current_user_avatar_url,
        'current_teacher_avatar_url': current_teacher_avatar_url,
    }
    return context
