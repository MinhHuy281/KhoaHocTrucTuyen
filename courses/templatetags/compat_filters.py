from django import template

register = template.Library()


@register.filter
def length_is(value, arg):
    """Compatibility filter for third-party templates expecting Django's old `length_is`."""
    try:
        return len(value) == int(arg)
    except (TypeError, ValueError):
        return False
