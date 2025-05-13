import pandas as pd
import csv
import json
import time
import datetime
import logging
import os
import zipfile
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction, connection, IntegrityError
from django.db.models import F, Max
from django.shortcuts import get_object_or_404
from io import BytesIO
from lxml import etree
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from clients.models import Client
from clients.utils import validateSelect, save_imported_logs
from items.models import Item, ImportedItem
from api.authentication import ClientTokenAuthentication, IsAuthenticatedClient
from api.serializers import ItemModelSerializer, ItemImportedModelSerializer
from sales.models import SalesPedido, SalesDetalhe



from django.db import connection
from rest_framework.views import APIView
from django.conf import settings

logger = logging.getLogger(__name__)

class ImportItemView(APIView):
    authentication_classes = [ClientTokenAuthentication]
    permission_classes = [IsAuthenticatedClient]

    def post(self, request):
        client = request.user
        initial_log = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Cliente: {client.name} enviando dados através da API\n"
        data_json = request.data
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
            # Obtendo a data e hora atual para o timestamp
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")  # Formato yyyymmdd_hhmmss
            
            # Diretório para salvar os arquivos
            save_dir = "logs/api"
            os.makedirs(save_dir, exist_ok=True)  # Cria o diretório se não existir
            
            # Criando o nome do arquivo dinâmico (sem a extensão)
            file_base_name = f"{client.id}_{timestamp}"
            
            # Caminho completo para o arquivo CSV
            # csv_file_path = os.path.join(save_dir, f"{file_base_name}.csv")
            # df_json_recebido.to_csv(csv_file_path, sep=';', index=False)
            
            # Caminho completo para o arquivo JSON
            json_file_path = os.path.join(save_dir, f"{file_base_name}.json")
            with open(json_file_path, 'w') as json_file:
                json.dump(data_json, json_file, indent=4)           
            
            df_json_recebido['sequencial'] = 0
            df_json_recebido['estado_origem'] = ''
            df_json_recebido['estado_destino'] = ''            
            
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'type_product',
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
                           
            items_df.drop(columns=['id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 'is_pending_sync', 'history', 'other_information'], inplace=True)            

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

def safe_node_datetime(node, child_name, namespaces=None, default=None):
    """
    Retorna um objeto datetime a partir do texto de um nó filho ou um valor padrão se o nó não existir.

    :param node: Nó XML pai onde será feita a busca.
    :param child_name: Nome do nó filho a ser buscado.
    :param namespaces: Dicionário de namespaces (se necessário).
    :param default: Valor padrão caso o nó não seja encontrado.
    :return: Objeto datetime ou valor padrão.
    """
    if node is None:
        return default
    
    child_text = safe_node_text(node, child_name, namespaces, default=None)
    if child_text:
        try:
            return datetime.fromisoformat(child_text)  # Converte string ISO para datetime
        except ValueError:
            return default  # Retorna default caso a conversão falhe
    
    return default

def safe_node_text(node, child_name, namespaces=None, default=""):
    """
    Retorna o texto de um nó filho ou um valor padrão se o nó não existir.
    
    :param node: Nó XML pai onde será feita a busca.
    :param child_name: Nome do nó filho a ser buscado.
    :param namespaces: Dicionário de namespaces (se necessário).
    :param default: Valor padrão caso o nó não seja encontrado.
    :return: Texto do nó filho ou o valor padrão.
    """
    if node is None:
        return default
    child = node.find(child_name, namespaces=namespaces)
    return child.text.strip() if child is not None and child.text else default

def safe_int(value, default=0):
    """
    Converte um valor para inteiro ou retorna um valor padrão.
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """
    Converte um valor para float ou retorna um valor padrão.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

class ProcessZipView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    
    def delete(self, request):
        arquivo_id = request.query_params.get('arquivo_id')  # Obtendo arquivo_id da query string
        
        if not arquivo_id:
            return Response(
                {"error": "O parâmetro 'arquivo_id' é obrigatório para deletar um pedido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pedidos = SalesPedido.objects.filter(arquivo_id=arquivo_id)  # Obtém todos os registros correspondentes
            
            if not pedidos.exists():
                return Response(
                    {"error": "Nenhum pedido encontrado com esse arquivo_id."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            deletados = pedidos.delete()  # Deleta todos os registros encontrados
            return Response(
                {"message": f"{deletados[0]} pedido(s) deletado(s) com sucesso!"},
                status=status.HTTP_204_NO_CONTENT
            )
        
        except IntegrityError:
            return Response(
                {"error": "Não é possível deletar este(s) pedido(s), pois há registros vinculados."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                {"error": f"Erro ao deletar o pedido: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
 
    def post(self, request, *args, **kwargs):
        arquivos_zip = request.FILES.getlist('file')  # Pega todos os arquivos ZIP enviados
        arquivo_id = request.data.get('arquivo_id')

        if not arquivos_zip:
            return Response({'error': 'Nenhum arquivo ZIP enviado.'}, status=400)

        start_time = time.time()
        pedidos_batch = []  # Lista global para pedidos
        detalhes_batch = []  # Lista global para detalhes
        batch_size = 2000  # Tamanho do lote

        try:
            for zip_file in arquivos_zip:
                logger.info(f"Processando arquivo ZIP: {zip_file.name}")

                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    for file_name in zip_ref.namelist():
                        if file_name.startswith('__MACOSX/') or file_name.endswith('/'):
                            logger.info(f"Ignorando pasta/arquivo: {file_name}")
                            continue

                        if file_name.endswith('.xml'):
                            with zip_ref.open(file_name) as xml_file:
                                xml_content = xml_file.read()
                                logger.info(f"Processando arquivo: {file_name}")

                                pedido, detalhes = self.process_xml(xml_content, arquivo_id, file_name)
                                if pedido:
                                    pedidos_batch.append(pedido)
                                    detalhes_batch.extend(detalhes)

                                    if len(pedidos_batch) >= batch_size:
                                        self.insert_batch(pedidos_batch, detalhes_batch)
                                        pedidos_batch = []
                                        detalhes_batch = []

            # Insere os registros restantes após processar todos os arquivos ZIP
            if pedidos_batch:
                self.insert_batch(pedidos_batch, detalhes_batch)

        except Exception as e:
            logger.error(f"Erro ao processar os arquivos: {str(e)}")
            return Response({'error': f'Erro ao processar os arquivos: {str(e)}'}, status=500)

        end_time = time.time()
        processing_time = end_time - start_time

        return Response({
            'message': 'Todos os arquivos ZIP foram processados com sucesso.',
            'processing_time_seconds': processing_time
        }, status=200)

    def process_xml(self, xml_content, arquivo_id, file_name):
        """
        Processa o conteúdo de um arquivo XML e retorna um pedido e seus detalhes.
        """
        try:
            root = etree.fromstring(xml_content)
            ns = {'': 'http://www.portalfiscal.inf.br/nfe'}

            inf_prot = root.find('.//infProt', namespaces=ns)
            if inf_prot is None:
                return None, []

            ide = root.find('.//ide', namespaces=ns)
            if ide is None:
                raise ValueError("Nó 'ide' não encontrado no XML.")

            emit = root.find('.//emit', namespaces=ns)
            if emit is None:
                raise ValueError("Nó 'emit' não encontrado no XML.")

            dest = root.find('.//dest', namespaces=ns)
            # if dest is None:
            #     logger.warning("Nó 'dest' não encontrado no XML.")

            total = root.find('.//total', namespaces=ns)
            if total is None:
                raise ValueError("Nó 'total' não encontrado no XML.")

            # Cria o objeto SalesPedido
            chave_nfe = safe_node_text(inf_prot, './/chNFe', namespaces=ns)
            pedido = SalesPedido(
                arquivo_id=arquivo_id,
                chNFe=safe_node_text(inf_prot, './/chNFe', namespaces=ns),
                tpAmb=safe_int(safe_node_text(inf_prot, './/tpAmb', namespaces=ns)),
                verAplic=safe_node_text(inf_prot, './/verAplic', namespaces=ns),
                dhRecbto=safe_node_datetime(inf_prot, './/dhRecbto', namespaces=ns),
                nProt=safe_node_text(inf_prot, './/nProt', namespaces=ns),
                digVal=safe_node_text(inf_prot, './/digVal', namespaces=ns),
                cStat=safe_int(safe_node_text(inf_prot, './/cStat', namespaces=ns)),
                xMotivo=safe_node_text(inf_prot, './/xMotivo', namespaces=ns),
                cUF=safe_int(safe_node_text(ide, './/cUF', namespaces=ns)),
                cNF=safe_int(safe_node_text(ide, './/cNF', namespaces=ns)),
                natOp=safe_node_text(ide, './/natOp', namespaces=ns),
                mod=safe_int(safe_node_text(ide, './/mod', namespaces=ns)),
                serie=safe_int(safe_node_text(ide, './/serie', ns)),
                nNF=safe_int(safe_node_text(ide, './/nNF', ns)),
                dhEmi=safe_node_datetime(ide, './/dhEmi', ns),
                dhSaiEnt=safe_node_datetime(ide, './/dhSaiEnt', ns),
                tpNF=safe_int(safe_node_text(ide, './/tpNF', ns)),
                idDest=safe_int(safe_node_text(ide, './/idDest', ns)),
                cMunFG=safe_int(safe_node_text(ide, './/cMunFG', ns)),
                tpImp=safe_int(safe_node_text(ide, './/tpImp', ns)),
                tpEmis=safe_int(safe_node_text(ide, './/tpEmis', ns)),
                cDV=safe_int(safe_node_text(ide, './/cDV', ns)),
                finNFe=safe_int(safe_node_text(ide, './/finNFe', ns)),
                indFinal=safe_int(safe_node_text(ide, './/indFinal', ns)),
                indPres=safe_int(safe_node_text(ide, './/indPres', ns)),
                procEmi=safe_int(safe_node_text(ide, './/procEmi', ns)),
                verProc=safe_node_text(ide, './/verProc', ns),
                CNPJ_Emitente=safe_node_text(emit, './/CNPJ', ns),
                xNome_Emitente=safe_node_text(emit, './/xNome', ns),
                xLgr_Emitente=safe_node_text(emit, './/xLgr', ns),
                nro_Emitente=safe_node_text(emit, './/nro', ns),
                xBairro_Emitente=safe_node_text(emit, './/xBairro', ns),
                cMun_Emitente=safe_int(safe_node_text(emit, './/cMun', ns)),
                xMun_Emitente=safe_node_text(emit, './/xMun', ns),
                UF_Emitente=safe_node_text(emit, './/UF', ns),
                CEP_Emitente=safe_node_text(emit, './/CEP', ns),
                fone_Emitente=safe_node_text(emit, './/fone', ns),
                IE_Emitente=safe_node_text(emit, './/IE', ns),
                CRT_Emitente=safe_int(safe_node_text(emit, './/CRT', ns)),
                CNPJ_Destinatario=safe_node_text(dest, './/CNPJ', ns),
                CPF_Destinatario=safe_node_text(dest, './/CPF', ns),
                xNome_Destinatario=safe_node_text(dest, './/xNome', ns),
                xLgr_Destinatario=safe_node_text(dest, './/xLgr', ns),
                nro_Destinatario=safe_node_text(dest, './/nro', ns),
                xBairro_Destinatario=safe_node_text(dest, './/xBairro', ns),
                cMun_Destinatario=safe_int(safe_node_text(dest, './/cMun', ns)),
                xMun_Destinatario=safe_node_text(dest, './/xMun', ns),
                UF_Destinatario=safe_node_text(dest, './/UF', ns),
                CEP_Destinatario=safe_node_text(dest, './/CEP', ns),
                fone_Destinatario=safe_node_text(dest, './/fone', ns),
                indIEDestinatario=safe_int(safe_node_text(dest, './/indIEDest', ns)),
                IE_Destinatario=safe_node_text(dest, './/IE', ns),
                vBC=safe_float(safe_node_text(total, './/vBC', ns)),
                vICMS=safe_float(safe_node_text(total, './/vICMS', ns)),
                vICMSDeson=safe_float(safe_node_text(total, './/vICMSDeson', ns)),
                vFCP=safe_float(safe_node_text(total, './/vFCP', ns)),
                vBCST=safe_float(safe_node_text(total, './/vBCST', ns)),
                vST=safe_float(safe_node_text(total, './/vST', ns)),
                vFCPST=safe_float(safe_node_text(total, './/vFCPST', ns)),
                vFCPSTRet=safe_float(safe_node_text(total, './/vFCPSTRet', ns)),
                vProd=safe_float(safe_node_text(total, './/vProd', ns)),
                vFrete=safe_float(safe_node_text(total, './/vFrete', ns)),
                vSeg=safe_float(safe_node_text(total, './/vSeg', ns)),
                vDesc=safe_float(safe_node_text(total, './/vDesc', ns)),
                vII=safe_float(safe_node_text(total, './/vII', ns)),
                vIPI=safe_float(safe_node_text(total, './/vIPI', ns)),
                vIPIDevol=safe_float(safe_node_text(total, './/vIPIDevol', ns)),
                vPIS=safe_float(safe_node_text(total, './/vPIS', ns)),
                vCOFINS=safe_float(safe_node_text(total, './/vCOFINS', ns)),
                vOutro=safe_float(safe_node_text(total, './/vOutro', ns)),
                vNF=safe_float(safe_node_text(total, './/vNF', ns)),
            )

            # Processa os itens da NF-e (SalesDetalhe)
            detalhes = []
            det_nodes = root.findall('.//det', namespaces=ns)
            for det in det_nodes:
                prod = det.find('prod', namespaces=ns)
                imposto = det.find('imposto', namespaces=ns)

                detalhe = SalesDetalhe(
                    pedido=pedido,
                    chNFe=chave_nfe,
                    nItem=safe_int(det.attrib['nItem']),
                    cProd=safe_node_text(prod, './/cProd', ns),
                    xProd=safe_node_text(prod, './/xProd', ns),
                    NCM=safe_node_text(prod, './/NCM', ns),
                    cBenef=safe_node_text(prod, './/cBenef', ns),
                    CEST=safe_node_text(prod, './/CEST', ns),
                    CFOP=safe_int(safe_node_text(prod, './/CFOP', ns)),
                    uCom=safe_node_text(prod, './/uCom', ns),
                    qCom=safe_float(safe_node_text(prod, './/qCom', ns)),
                    vUnCom=safe_float(safe_node_text(prod, './/vUnCom', ns)),
                    vProd=safe_float(safe_node_text(prod, './/vProd', ns)),
                    cEAN=safe_node_text(prod, './/cEAN', ns),
                    uTrib=safe_node_text(prod, './/uTrib', ns),
                    qTrib=safe_float(safe_node_text(prod, './/qTrib', ns)),
                    vUnTrib=safe_float(safe_node_text(prod, './/vUnTrib', ns)),
                    cEANTrib=safe_node_text(prod, './/cEANTrib', ns),
                    vFrete=safe_float(safe_node_text(prod, './/vFrete', ns), 0.0),
                    vSeg=safe_float(safe_node_text(prod, './/vSeg', ns), 0.0),
                    vDesc=safe_float(safe_node_text(prod, './/vDesc', ns), 0.0),
                    vOutro=safe_float(safe_node_text(prod, './/vOutro', ns), 0.0),
                    indTot=safe_int(safe_node_text(prod, './/indTot', ns)),
                    orig=safe_int(safe_node_text(imposto, './/orig', ns)),
                    CST_ICMS=safe_node_text(imposto, './/CST', ns),
                    modBC=safe_int(safe_node_text(imposto, './/modBC', ns)),
                    vBC=safe_float(safe_node_text(imposto, './/vBC', ns)),
                    pICMS=safe_float(safe_node_text(imposto, './/pICMS', ns)),
                    vICMS=safe_float(safe_node_text(imposto, './/vICMS', ns)),
                    vICMSDeson=safe_float(safe_node_text(imposto, './/vICMSDeson', ns), 0.0),
                    pRedBC=safe_float(safe_node_text(imposto, './/pRedBC', ns), 0.0),
                    modBCST=safe_int(safe_node_text(imposto, './/modBCST', ns), 0),
                    vBCST=safe_float(safe_node_text(imposto, './/vBCST', ns), 0.0),
                    pICMSST=safe_float(safe_node_text(imposto, './/pICMSST', ns), 0.0),
                    vICMSST=safe_float(safe_node_text(imposto, './/vICMSST', ns), 0.0),
                    vPIS=safe_float(safe_node_text(imposto, './/vPIS', ns)),
                    CST_PIS=safe_node_text(imposto, './/CST', ns),
                    pPIS=safe_float(safe_node_text(imposto, './/pPIS', ns)),
                    vBC_PIS=safe_float(safe_node_text(imposto, './/vBC', ns)),
                    vCOFINS=safe_float(safe_node_text(imposto, './/vCOFINS', ns)),
                    CST_COFINS=safe_node_text(imposto, './/CST', ns),
                    pCOFINS=safe_float(safe_node_text(imposto, './/pCOFINS', ns)),
                    vBC_COFINS=safe_float(safe_node_text(imposto, './/vBC', ns)),

                    motDesICMS = safe_int(safe_node_text(imposto, './/motDesICMS', ns), 0),
                    vFCPST = safe_float(safe_node_text(imposto, './/vFCPST', ns), 0.0),
                    pFCPST = safe_float(safe_node_text(imposto, './/pFCPST', ns), 0.0),
                    vFCP = safe_float(safe_node_text(imposto, './/vFCP', ns), 0.0),
                    pFCP = safe_float(safe_node_text(imposto, './/pFCP', ns), 0.0),
                    vST = safe_float(safe_node_text(imposto, './/vST', ns), 0.0),
                    pST = safe_float(safe_node_text(imposto, './/pST', ns), 0.0),
                    vBCSTRet = safe_float(safe_node_text(imposto, './/vBCSTRet', ns), 0.0),
                )
                detalhes.append(detalhe)

            return pedido, detalhes

        except Exception as e:
            raise ValueError(f"Erro ao processar XML: {str(e)}")

    def insert_batch(self, pedidos_batch, detalhes_batch):
        """
        Insere pedidos e detalhes em lote no banco de dados.
        """
        with transaction.atomic():
            # Insere os pedidos em lote
            SalesPedido.objects.bulk_create(pedidos_batch)

            # Insere os detalhes em lote
            SalesDetalhe.objects.bulk_create(detalhes_batch)

class GenerateCSVGroup(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, code):
        arquivo_id = code
        if not arquivo_id:
            return JsonResponse({'error': 'arquivo_id é obrigatório.'}, status=400)
        
        start_time = time.time()
        file_path = os.path.join(settings.MEDIA_ROOT, f'reg_0000.csv')
        
        query = """
            SELECT 
                a.mod AS modelo, 
                a."tpNF" AS tipo_operacao, 
                a."natOp" AS natureza_operacao, 
                a."xNome_Emitente" AS nome_emitente, 
                a."indFinal" AS indicador_consumidor_final,
                a."CNPJ_Emitente" AS cnpj_emitente, 
                a."UF_Emitente" AS uf_emit, 
                CASE WHEN a."UF_Destinatario" = 'GO' THEN '' ELSE a."UF_Destinatario" END AS uf_dest, 
                MIN(a."nNF") AS numero_nota, 
                MIN(TO_CHAR(a."dhEmi", 'DD/MM/YYYY')) AS data_emissao, 
                b."NCM" AS ncm, 
                b."CFOP" AS cfop, 
                b."CST_ICMS" AS cst_icms, 
                b."vICMSDeson" AS valor_icms_desonerado, 
                AVG(b."vProd") AS valor_total_item, 
                AVG(b."vOutro") AS valor_outros, 
                AVG(b."vDesc") AS valor_desconto, 
                AVG(b."vFrete") AS valor_frete, 
                AVG(b."vBC") AS base_icms, 
                b."pRedBC" AS percentual_reducao, 
                ROUND(((b."vFCP" / NULLIF(b."vBC", 0)) * 100) + b."pICMS", 2) AS aliquota_icms, 
                AVG(b."vICMS" + b."vFCP") AS valor_icms, 
                COUNT(b."qCom") AS quantidade, 
                0 AS iva, 
                AVG(b."vBCST") AS base_icms_st, 
                b."pICMSST" AS aliquota_icms_st, 
                AVG(b."vICMSST") AS valor_icms_st, 
                b."CST_PIS" AS cst_pis, 
                AVG(b."vBC_PIS") AS base_pis, 
                b."pPIS" AS aliquota_pis, 
                AVG(b."vPIS") AS valor_pis, 
                b."CST_COFINS" AS cst_cofins, 
                b."pCOFINS" AS aliquota_cofins, 
                AVG(b."vBC_COFINS") AS base_cofins, 
                AVG(b."vCOFINS") AS valor_cofins, 
                CASE WHEN TRIM(b."CEST") = '' THEN '0' ELSE TRIM(b."CEST") END AS cest, 
                b."xProd" AS descricao_produto, 
                b.orig AS origem_prod, 
                b."cEAN" AS codigo_barra, 
                TRIM(b."NCM" || a.mod || a."natOp" || a."UF_Destinatario" || b."CEST" || b."cEAN" || b."xProd" || b."CFOP" || b."CST_ICMS" || b."pICMS" || b."pICMSST" || b."CST_PIS" || b."pPIS") AS identificador, 
                b."cProd" AS codigo_produto, 
                b."cBenef" AS c_benef 
            FROM sales_salesdetalhe b 
            INNER JOIN sales_salespedido a ON a.id = b.pedido_id
            WHERE a.arquivo_id = %s 
            GROUP BY b."NCM", b."CFOP", b."cProd", b."CST_ICMS", b."vICMSDeson", b."pRedBC", b."pICMS", b."pICMSST", b."CST_PIS", b."pPIS", b."CST_COFINS", 
                    b."pCOFINS", b."CEST", b."xProd", b.orig, b."cEAN", a.mod, a."tpNF", a."natOp", a."UF_Emitente", a."UF_Destinatario", 
                    a."indFinal", a."CNPJ_Emitente", 
                    a."xNome_Emitente", b."vFCP", b."vBC", b."cBenef"
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arquivo_id])
                rows = cursor.fetchall()
                headers = [col[0] for col in cursor.description]
                
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(headers)  # Escrevendo o cabeçalho
                    writer.writerows(rows)   # Escrevendo os dados
            
        except Exception as e:
            logger.error(f"Erro ao gerar CSV: {e}")
            return JsonResponse({'error': f'Erro ao gerar CSV: {str(e)}'}, status=500)
        
        end_time = time.time()
        processing_time = end_time - start_time
        file_url = f"{settings.MEDIA_URL}reg_0000.csv"
        
        return JsonResponse({
            'message': 'Arquivo gerado com sucesso.', 
            'file_url': file_url, 
            'processing_time_seconds': processing_time
        }, status=200)

class GenerateCSVDetail(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, code):
        arquivo_id = code
        if not arquivo_id:
            return JsonResponse({'error': 'arquivo_id é obrigatório.'}, status=400)
        
        start_time = time.time()
        file_path = os.path.join(settings.MEDIA_ROOT, f'reg_0000d.csv')
        
        query = """
            SELECT 
                a."chNFe" AS chave_nota,
                a."nNF" AS numero_nota,
                b."NCM" AS ncm,
                a."mod" AS modelo,
                a."tpNF" AS tipo_operacao,
                a."natOp" AS natureza_operacao,
                a."indFinal" AS indicador_consumidor_final,
                a."UF_Emitente" AS uf_emit,
                CASE 
                    WHEN a."UF_Destinatario" = 'GO' THEN ''
                    ELSE a."UF_Destinatario" 
                END AS uf_dest,
                a."CNPJ_Emitente" AS cnpj_emitente,
                a."xNome_Emitente" AS nome_emitente,
                TO_CHAR(a."dhEmi", 'DD/MM/YYYY') AS data_emissao, -- Conversão de data no PostgreSQL
                b."qCom" AS quantidade,
                b."CFOP" AS cfop,
                b."CST_ICMS" AS cst_icms,
                b."vBC" AS base_icms,
                b."pRedBC" AS percentual_reducao,
                ROUND(((b."vFCP" / NULLIF(b."vBC", 0)) * 100) + b."pICMS", 2) AS aliquota_icms,
                (b."vICMS" + b."vFCP") AS valor_icms,
                0 AS iva,
                b."vBCST" AS base_icms_st,
                b."pICMSST" AS aliquota_icms_st,
                b."vICMSST" AS valor_icms_st,
                b."CST_PIS" AS cst_pis,
                b."vBC_PIS" AS base_pis,
                b."pPIS" AS aliquota_pis,
                b."vPIS" AS valor_pis,
                b."CST_COFINS" AS cst_cofins,
                b."vBC_COFINS" AS base_cofins,
                b."pCOFINS" AS aliquota_cofins,
                b."vCOFINS" AS valor_cofins,
                CASE 
                    WHEN TRIM(b."CEST") = '' THEN '0' 
                    ELSE TRIM(b."CEST") 
                END AS cest,
                b."xProd" AS descricao_produto,
                b."orig" AS origem_prod,
                b."cEAN" AS codigo_barra,
                b."vDesc" AS valor_desconto,
                b."vProd" AS valor_total_item,
                b."vOutro" AS valor_outros,
                b."vFrete" AS valor_frete,
                b."CST_ICMS" AS identificador,
                b."cProd" AS codigo_produto,
                b."cBenef" AS c_benef,
                b."vICMSDeson" AS valor_icms_desonerado
            FROM sales_salespedido AS a
            INNER JOIN sales_salesdetalhe AS b ON a.id = b.pedido_id
            WHERE a.arquivo_id = %s;
            
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arquivo_id])
                rows = cursor.fetchall()
                headers = [col[0] for col in cursor.description]
                
                with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow(headers)  # Escrevendo o cabeçalho
                    writer.writerows(rows)   # Escrevendo os dados
            
        except Exception as e:
            logger.error(f"Erro ao gerar CSV: {e}")
            return JsonResponse({'error': f'Erro ao gerar CSV: {str(e)}'}, status=500)
        
        end_time = time.time()
        processing_time = end_time - start_time
        file_url = f"{settings.MEDIA_URL}reg_0000.csv"
        
        return JsonResponse({
            'message': 'Arquivo gerado com sucesso.', 
            'file_url': file_url, 
            'processing_time_seconds': processing_time
        }, status=200)

class ProcessSPED(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        start_time = time.time()

        # Aqui seria o processamento dos arquivos ZIP
        # (Por enquanto estamos simulando)

        processing_time = round(time.time() - start_time, 2)
        return Response({
            'message': 'Todos os arquivos ZIP foram processados com sucesso.',
            'processing_time_seconds': processing_time
        }, status=200)

class SaveFilesDefinitely(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        start_time = time.time()

        # Aqui seria o salvamento definitivo dos arquivos
        # (Por enquanto estamos simulando também)

        processing_time = round(time.time() - start_time, 2)
        return Response({
            'message': 'Arquivos salvos definitivamente.',
            'processing_time_seconds': processing_time
        }, status=200)
