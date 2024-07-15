from django import template
from app.utils import get_cleaned_query_params

register = template.Library()

@register.filter(name='zero_to_empty')
def zero_to_empty(value):
    if value == '0':
        return ''
    return value
    
@register.filter(name='default_if_none_or_zero')
def default_if_none_or_zero(value, default=""):
    return default if value is None or value == 0 else value    

@register.filter(name='int_filter')
def int_filter(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return value

@register.filter(name='cleaned_query_params')
def cleaned_query_params(request, remove_param):
    return get_cleaned_query_params(request.GET, remove_param)  