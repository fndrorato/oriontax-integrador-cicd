from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny

class LoginView(APIView):
    permission_classes = [AllowAny]  # Permite acesso a qualquer um
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        # Autentica o usuário
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Gera ou recupera o token para o usuário
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "first_name": user.first_name,
                "user_id": user.id
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Credenciais inválidas"},
                status=status.HTTP_400_BAD_REQUEST
            )
