from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Chia value cho arg và trả về phần nguyên (floor division).
    Ví dụ: {{ 600|div:60 }} → 10
    """
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0