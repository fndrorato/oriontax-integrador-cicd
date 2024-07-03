from django import template

register = template.Library()

@register.filter(name='zero_to_empty')
def zero_to_empty(value):
    if value == '0':
        return ''
    return value

@register.filter(name='int_filter')
def int_filter(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return value