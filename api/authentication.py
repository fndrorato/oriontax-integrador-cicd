import uuid
from django.core.exceptions import ValidationError
from rest_framework.authentication import BaseAuthentication 
from rest_framework.exceptions import AuthenticationFailed 
from rest_framework.permissions import BasePermission
from clients.models import Client


class IsAuthenticatedClient(BasePermission):
    def has_permission(self, request, view):
        # Verifica se o cliente foi autenticado
        return request.user is not None

class ClientTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None
        
        # Verifica se o header começa com 'Bearer '
        if not auth_header.startswith('Bearer '):
            raise AuthenticationFailed({'message': 'Formato de token inválido'})
        
        # Extrai o token
        token = auth_header.split(' ')[1]
        
        try:
            # Verifica se o token é um UUID válido
            uuid_token = uuid.UUID(token)
        except ValueError:
            raise AuthenticationFailed({'message': 'Token inválido'})        

        try:
            client = Client.objects.get(token=uuid_token)
        except (Client.DoesNotExist, ValidationError):
            raise AuthenticationFailed({'message': 'Token inválido'})

        return (client, None)

