import pandas as pd
from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F
from clients.models import Client
from clients.utils import validateSelect, save_imported_logs
from items.models import Item, ImportedItem
from api.authentication import ClientTokenAuthentication, IsAuthenticatedClient
from api.serializers import ItemModelSerializer, ItemImportedModelSerializer

class ImportItemView(APIView):
    authentication_classes = [ClientTokenAuthentication]
    permission_classes = [IsAuthenticatedClient]

    def post(self, request):
        client = request.user
        initial_log = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Cliente: {client.name} enviando dados através da API\n"
        
        # Mapeia os campos do JSON recebido para os campos esperados pelo serializer
        def rename_fields(data):
            return {
                'code': data.get('codigo'),
                'barcode': data.get('codigo_barras'),
                'description': data.get('descricao'),
                'ncm': data.get('ncm'),
                'cest': data.get('cest'),
                'cfop': data.get('cfop'),
                'icms_cst': data.get('icms_cst'),
                'icms_aliquota': data.get('icms_aliquota'),
                'icms_aliquota_reduzida': data.get('icms_aliquota_reduzida'),
                'cbenef': data.get('cbenef'),
                'protege': data.get('protege'),
                'piscofins_cst': data.get('pis_cst'),
                'pis_aliquota': data.get('pis_aliquota'),
                'cofins_aliquota': data.get('cofins_aliquota'),
                'naturezareceita': data.get('natureza_receita'),
            }

        # Renomeia os campos em todos os itens da lista
        renamed_data = [rename_fields(item) for item in request.data]        
        
        # Serializa os dados recebidos
        serializer = ItemImportedModelSerializer(data=renamed_data, many=True)
        
        if not serializer.is_valid():        
            # Consolida os erros em um único objeto
            error_dict = {}
            for i, errors in enumerate(serializer.errors):
                for field, error in errors.items():
                    if field not in error_dict:
                        error_dict[field] = []
                    error_dict[field].extend(error)

            return Response({"errors": error_dict}, status=status.HTTP_400_BAD_REQUEST)            
     
        if serializer.is_valid():
            # Transforma os dados validados em um dataframe
            df_json_recebido = pd.DataFrame(serializer.validated_data)
            df_json_recebido['sequencial'] = 0
            df_json_recebido['estado_origem'] = ''
            df_json_recebido['estado_destino'] = ''            
            
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 
                naturezareceita_code=F('naturezareceita__code')
            )        
            if items_queryset:
                items_df = pd.DataFrame(list(items_queryset.values()))
            else: 
                # Lista das colunas desejadas
                colunas_desejadas = [
                    'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst',
                    'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                    'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_code',
                    'id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 
                    'is_pending_sync', 'history', 'other_information', 'type_product'
                ]

                # Criar um DataFrame vazio com as colunas desejadas
                items_df = pd.DataFrame(columns=colunas_desejadas)
                           
            items_df.drop(columns=['id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 'is_pending_sync', 'history', 'other_information', 'type_product'], inplace=True)            

            try:
                # Chama a função de validação
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Validando dados recebidos através da API\n"
                validation_result = validateSelect(client.id, items_df, df_json_recebido, initial_log)
                
            except Exception as e:  # Catch any unexpected exceptions
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client.name}: {e}\n"
                save_imported_logs(client.id, initial_log)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Finalizando recepção através da API\n"
            return Response({"message": "Dados recebidos e processados com sucesso."}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ClientItemView(APIView):
    authentication_classes = [ClientTokenAuthentication]
    permission_classes = [IsAuthenticatedClient]

    def get(self, request):
        client = request.user
        initial_log = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Verificando se há atualizações para o cliente: {client.name}... executando API\n"  
        
        items_queryset = Item.objects.filter(client=client, status_item__in=[1, 2])
        
        current_time = timezone.now()
        num_updated = Item.objects.filter(
            status_item=1, 
            client=client
        ).update(
            status_item=2,
            sync_at=current_time
        )          

        if num_updated > 0:
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - {num_updated} itens aguardando validação.\n"
        else:
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum item atualizado\n"

        save_imported_logs(client.id, initial_log)        
        
        serializer = ItemModelSerializer(items_queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)  
    
class ClientOneItemView(APIView):
    authentication_classes = [ClientTokenAuthentication]
    permission_classes = [IsAuthenticatedClient]

    def get(self, request, code):
        client = request.user
        initial_log = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Consultando um item específico para o cliente: {client.name}... executando API\n"  
        
        items_queryset = Item.objects.filter(client=client, code=code)  

        item = items_queryset.first()

        if item is None:
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - {code} não encontrado\n"
            save_imported_logs(client.id, initial_log)
            return Response({"message": "Item não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ItemModelSerializer(item)
        return Response(serializer.data, status=status.HTTP_200_OK)   
