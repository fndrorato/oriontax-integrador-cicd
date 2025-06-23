from django import template

register = template.Library()

@register.filter(name='has_role')
def has_role(user, role_name):
    return user.groups.filter(name=role_name).exists()

@register.filter(name='has_any_role')
def has_any_role(user, role_names):
    # Se role_names não for uma lista, divide a string em uma lista de roles
    if isinstance(role_names, str):
        role_names = [role.strip() for role in role_names.split(',')]
    return any(user.groups.filter(name=role_name).exists() for role_name in role_names)
