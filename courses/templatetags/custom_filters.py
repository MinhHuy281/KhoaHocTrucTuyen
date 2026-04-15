from django import template
import re

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


@register.filter
def decode_escaped_text(value):
    """Decode literal escape sequences (e.g. \u000D\u000A) without breaking existing unicode text."""
    if not isinstance(value, str) or not value:
        return value

    text = value

    # Decode common escaped control sequences first.
    text = text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n').replace('\\t', '\t')

    # Decode escaped unicode sequences like \u0026, \u000A.
    text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)

    # Normalize line endings after unicode decoding.
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove form-encoding artifacts that appear at line starts: "\n+ ...".
    text = re.sub(r'\n\+\s*', '\n', text)

    # Remove lingering encoded control chars if they survived any previous transform.
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)

    return text


@register.filter
def format_vnd(value):
    """Format a numeric value as Vietnamese currency style, e.g. 100000 -> 100.000."""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return value

    return f"{number:,}".replace(",", ".")