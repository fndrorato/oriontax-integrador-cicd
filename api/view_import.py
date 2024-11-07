from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import zipfile

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import zipfile

class UploadZipView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        if 'file' not in request.FILES:
            return Response(
                {"error": "Arquivo não enviado."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        zip_file = request.FILES['file']

        if not zip_file.name.endswith('.zip'):
            return Response(
                {"error": "O arquivo enviado não é um arquivo .zip."},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploads_dir = 'uploads'
        zips_dir = os.path.join(uploads_dir, 'zips')
        extracted_dir = os.path.join(uploads_dir, 'extracted')

        # Cria os diretórios se não existirem
        os.makedirs(zips_dir, exist_ok=True)
        os.makedirs(extracted_dir, exist_ok=True)

        file_path = os.path.join(zips_dir, zip_file.name)
        path = default_storage.save(file_path, ContentFile(zip_file.read()))

        full_path = default_storage.path(path)
        try:
            with zipfile.ZipFile(full_path, 'r') as zip_ref:
                zip_ref.extractall(os.path.join(extracted_dir, os.path.splitext(zip_file.name)[0]))
        except zipfile.BadZipFile:
            return Response(
                {"error": "O arquivo enviado não é um arquivo ZIP válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Arquivo .zip enviado e extraído com sucesso."},
            status=status.HTTP_201_CREATED
        )


# class UploadZipView(APIView):
#     permission_classes = [IsAuthenticated]  # Apenas usuários autenticados
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request):
#         # Verifica se há um arquivo no request
#         if 'file' not in request.FILES:
#             return Response(
#                 {"error": "Arquivo não enviado."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Recebe o arquivo do request
#         zip_file = request.FILES['file']

#         # Verifica se o arquivo é um ZIP
#         if not zip_file.name.endswith('.zip'):
#             return Response(
#                 {"error": "O arquivo enviado não é um arquivo .zip."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Define o caminho para salvar o arquivo
#         file_path = os.path.join('uploads/zips', zip_file.name)
#         path = default_storage.save(file_path, ContentFile(zip_file.read()))

#         # Processa o arquivo (exemplo: extrair o conteúdo)
#         full_path = default_storage.path(path)
#         with zipfile.ZipFile(full_path, 'r') as zip_ref:
#             zip_ref.extractall(os.path.join('uploads/extracted', os.path.splitext(zip_file.name)[0]))

#         return Response(
#             {"message": "Arquivo .zip enviado e extraído com sucesso."},
#             status=status.HTTP_201_CREATED
#         )
