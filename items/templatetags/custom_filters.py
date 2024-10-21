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

@register.filter(name='custom_floatformat')
def custom_floatformat(value, decimal_places=1):
    if value is None:
        return ""
    
    # Formata o número com o número especificado de casas decimais
    formatted_value = f"{value:,.{decimal_places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted_value

@register.filter(name='custom_full_name')
def custom_full_name(name):
    # Divide o nome em palavras
    words = name.split()
    
    # Verifica se há mais de 3 palavras
    if len(words) <= 3:
        return name
    

    return f"{words[0]} {words[1]} {words[-1]}"
    
    # Caso contrário, retorna o nome completo
    return name