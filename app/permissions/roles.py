from rolepermissions.roles import AbstractUserRole

class Administrador(AbstractUserRole):
    available_permissions = {
        'clients_add': True,
        'clients_edit': True,
        'clients_delete': True,
        'clients_view': True,
        'clients_config_connection': True,
        'taxes_add': True,
        'taxes_edit': True,
        'taxes_delete': True,
        'taxes_view': True,
        'users_add': True,
        'users_edit': True,
        'users_delete': True,
        'users_view': True,
        'only_his_client': False,
    }

class Gerente(AbstractUserRole):
    available_permissions = {
        'clients_add': True,
        'clients_edit': True,
        'clients_delete': False,
        'clients_view': True,
        'clients_config_connection': False,
        'taxes_add': True,
        'taxes_edit': True,
        'taxes_delete': False,
        'taxes_view': True,
        'users_add': False,
        'users_edit': False,
        'users_delete': False,
        'users_view': True,
        'only_his_client': False,
    }

class Analista(AbstractUserRole):
    available_permissions = {
        'clients_add': False,
        'clients_edit': False,
        'clients_delete': False,
        'clients_view': True,
        'clients_config_connection': False,
        'taxes_add': False,
        'taxes_edit': False,
        'taxes_delete': False,
        'taxes_view': True,
        'users_add': False,
        'users_edit': False,
        'users_delete': False,
        'users_view': False,
        'only_his_client': True,
        'view_accountings': False,
    }

class Supervisor(AbstractUserRole):
    available_permissions = {
        'can_add': False,
        'can_edit': False,
        'can_delete': False,
        'can_view': True,
    }
