def active_module_context(request):
    active_module = request.session.get('active_module')
    permissions = []

    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile

        # Verifica se é administrador
        is_admin = request.user.groups.filter(name__iexact='administrador').exists()

        if is_admin:
            # Admin tem acesso a todos os módulos
            permissions = [
                'cattle_permission',
                'shop_simulation_permission',
                'pricing_permission',
                'tax_management_permission',
            ]
        else:
            # Permissões normais baseadas no profile
            permission_map = {
                'cattle_permission': profile.cattle_permission,
                'shop_simulation_permission': profile.shop_simulation_permission,
                'pricing_permission': profile.pricing_permission,
                'tax_management_permission': profile.tax_management_permission,
            }
            permissions = [key for key, value in permission_map.items() if value]

    return {
        'active_module': active_module,
        'active_permissions': permissions,
    }
