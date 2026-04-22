from .auth import SeparateSessionAuth
from .models import UserProfile
from courses.models import Notification
from django.urls import reverse
from urllib.parse import parse_qs


COMMENT_META_TAG = "[[COMMENT_META]]"


def parse_comment_notification_message(raw_message):
    message = raw_message or ""
    if COMMENT_META_TAG not in message:
        return message, None

    content, payload = message.split(COMMENT_META_TAG, 1)
    content = content.strip()
    payload = payload.strip()

    if not payload:
        return content, None

    parsed = parse_qs(payload, keep_blank_values=True)
    meta = {key: values[0] for key, values in parsed.items() if values}
    return content, meta

def auth_context(request):
    """
    Context processor để thêm current_user và current_teacher vào templates
    """
    current_user = SeparateSessionAuth.get_user(request)
    current_teacher = SeparateSessionAuth.get_teacher(request)

    current_user_avatar_url = None
    current_teacher_avatar_url = None
    user_notifications = []
    user_unread_count = 0
    teacher_notifications = []
    teacher_unread_count = 0

    if current_user:
        profile = UserProfile.objects.filter(user=current_user).only('avatar').first()
        if profile and profile.avatar:
            current_user_avatar_url = profile.avatar.url

        user_notifications_qs = Notification.objects.filter(user=current_user).order_by('-created_at')
        user_notifications = []
        for notification in user_notifications_qs[:5]:
            clean_message, _ = parse_comment_notification_message(notification.message)
            user_notifications.append({
                'id': notification.id,
                'message': clean_message,
                'created_at': notification.created_at,
                'reply_url': reverse('user_reply_comment', args=[notification.id]),
            })
        user_unread_count = user_notifications_qs.filter(is_read=False).count()

    if current_teacher:
        profile = UserProfile.objects.filter(user=current_teacher).only('avatar').first()
        if profile and profile.avatar:
            current_teacher_avatar_url = profile.avatar.url

        notifications_qs = Notification.objects.filter(user=current_teacher).order_by('-created_at')
        teacher_notifications = []
        for notification in notifications_qs[:5]:
            clean_message, _ = parse_comment_notification_message(notification.message)
            teacher_notifications.append({
                'id': notification.id,
                'message': clean_message,
                'created_at': notification.created_at,
                'reply_url': reverse('teacher_reply_comment', args=[notification.id]),
            })
        teacher_unread_count = notifications_qs.filter(is_read=False).count()

    context = {
        'current_user': current_user,
        'current_teacher': current_teacher,
        'is_user_authenticated': SeparateSessionAuth.is_user_authenticated(request),
        'is_teacher_authenticated': SeparateSessionAuth.is_teacher_authenticated(request),
        'current_user_avatar_url': current_user_avatar_url,
        'current_teacher_avatar_url': current_teacher_avatar_url,
        'user_notifications': user_notifications,
        'user_unread_count': user_unread_count,
        'notifications': teacher_notifications,
        'unread_count': teacher_unread_count,
    }
    return context
