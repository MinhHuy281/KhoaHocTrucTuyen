from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Kiểm tra user là giáo viên
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.is_teacher()


class IsStudentOrTeacher(permissions.BasePermission):
    """
    Kiểm tra user là học viên hoặc giáo viên
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsTeacherOrReadOnly(permissions.BasePermission):
    """
    Chỉ giáo viên mới được POST, PUT, DELETE
    Một ai cũng có thể GET
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.is_teacher()


class IsTeacherOrOwner(permissions.BasePermission):
    """
    Chỉ giáo viên hoặc chủ sở hữu mới được chỉnh sửa
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.teacher == request.user


class IsEnrolledOrTeacher(permissions.BasePermission):
    """
    Chỉ có thể xem nếu đã đăng ký hoặc là giáo viên dạy khóa học
    """
    def has_object_permission(self, request, view, obj):
        # Giáo viên dạy khóa học
        if hasattr(obj, 'course') and obj.course.teacher == request.user:
            return True
        # Học viên đã đăng ký
        from ..models import Enrollment
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=obj.course if hasattr(obj, 'course') else obj
        ).first()
        return enrollment and enrollment.can_learn()
