import os
import sys
import django
import pandas as pd
import io
import dropbox
import traceback
from io import StringIO
from datetime import datetime
from utils import refresh_access_token, get_access_token_with_auth_code

# Get the absolute path to the directory containing this file (run_select.py)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the project root directory (three levels up from the current directory)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# Add the project root to the Python path
sys.path.append(project_root)

# Configurar o ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.conf import settings
from django.db.models import F, Q
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import save_imported_logs
from items.models import Item
from erp.models import AccessDropbox

def get_clients():
    return Client.objects.filter(
        connection_route__isnull=False,
        user_route__isnull=False,
        password_route__isnull=False
    ).exclude(
        connection_route='',
        user_route='',
        password_route=''
    )  

def convert_df_otx_version_to_df_client(df_client):
    # Caminhos dos arquivos CSV
    path_icms = os.path.join(current_dir, 'relations', 'tilit_icms.csv')

    # Leitura dos arquivos CSV em DataFrames
    df_icms = pd.read_csv(path_icms, delimiter=';', dtype={'icms_cst': str})
    
    df_client['icms_cst_id'] = df_client['icms_cst_id'].astype(str).str.zfill(2)
    df_client = df_client.drop(columns=['id', 'client_id', 'protege_id', 'pis_aliquota', 'cofins_aliquota'])
    df_client = df_client.rename(columns={
        'code': 'PRODUTO',
        'barcode': 'BARRAS',
        'description': 'DESCRICAO',
        'cbenef_id': 'CODBENEFICIOFISCAL',
        'ncm': 'NCM',
        'cest': 'CEST',
        'piscofins_cst_id': 'PIS',
        'cfop_id': 'cfop',
        'icms_cst_id': 'icms_cst',
        'icms_aliquota_id': 'icms_aliquota',
        'naturezareceita_code': 'NATUREZARECEITAPIS'
    })    
    
    # Garantir que os tipos das colunas que serão usadas para o merge sejam compatíveis
    df_client['NATUREZARECEITAPIS'] = df_client['NATUREZARECEITAPIS'].fillna('')
    df_client['NATUREZARECEITAPIS'] = df_client['NATUREZARECEITAPIS'].astype(str)
    df_client['cfop'] = df_client['cfop'].astype(str)
    df_client['icms_cst'] = df_client['icms_cst'].astype(str)
    df_client['icms_aliquota'] = df_client['icms_aliquota'].astype(str)
    df_client['icms_aliquota_reduzida'] = df_client['icms_aliquota_reduzida'].astype(str)

    df_icms['cfop'] = df_icms['cfop'].astype(str)
    df_icms['icms_cst'] = df_icms['icms_cst'].astype(str)
    df_icms['icms_aliquota'] = df_icms['icms_aliquota'].astype(str)
    df_icms['icms_aliquota_reduzida'] = df_icms['icms_aliquota_reduzida'].astype(str)

    # Realizando o merge entre os DataFrames com base nas colunas especificadas
    df_final = df_client.merge(
        df_icms[['icms', 'cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida']],
        on=['cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida'],
        how='left'
    )
    
    df_final = df_final.rename(columns={
            'icms': 'ICMS'
    })   
    
    df_final = df_final.drop(columns=['cfop', 'icms_cst', 'icms_aliquota', 'icms_aliquota_reduzida'])  

    # Definindo a nova ordem das colunas
    nova_ordem = [
        'PRODUTO',
        'BARRAS',
        'DESCRICAO',
        'PIS',
        'ICMS',
        'NCM',
        'CEST',
        'NATUREZARECEITAPIS',
        'CODBENEFICIOFISCAL',
        
    ]
    
    # Reordenando as colunas do DataFrame df_final
    df_final = df_final[nova_ordem]
        
    # # Exibindo o DataFrame resultante
    # print(df_final)
    
    return df_final
          
def connect_and_update(host, token, client_name, items_df, initial_log):
# Substitua pelo seu token de acesso
    DROPBOX_ACCESS_TOKEN = token

    # URL da pasta compartilhada
    SHARED_LINK_URL = host
    
    try:
        # Conectar à API do Dropbox
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        
        # Extrair metadados do link compartilhado
        shared_link_metadata = dbx.sharing_get_shared_link_metadata(SHARED_LINK_URL)
        shared_link = dropbox.files.SharedLink(url=SHARED_LINK_URL)

        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

        # Listar todos os arquivos na pasta raiz do link compartilhado
        result = dbx.files_list_folder('', shared_link=dropbox.files.SharedLink(url=SHARED_LINK_URL))

        # Listar arquivos e pastas na raiz da pasta compartilhada
        items = result.entries
        
        # Exibir todas as pastas e arquivos no diretório base
        print("Pastas e arquivos disponíveis no diretório base:")
        for item in items:
            print(f"- {item.name} ({'Pasta' if isinstance(item, dropbox.files.FolderMetadata) else 'Arquivo'})")
        
        # Verifica se a pasta 'Atualiza' existe
        atualiza_folder = next((folder for folder in result.entries if folder.name.lower() == 'atualiza' and isinstance(folder, dropbox.files.FolderMetadata)), None)
        
        if not atualiza_folder:
            print('nao encontrou a pasta atualiza')
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - A pasta 'Consulta' não foi encontrada.\n"
            return None, initial_log
        else:
            print('pasta atualiza encontrada')
        
        print("\nArquivos dentro de 'Atualiza':")
        # Usa o caminho relativo dentro do link compartilhado para acessar a pasta 'Consulta'
        path_atualiza = f"/{atualiza_folder.name}"
        result_atualiza = dbx.files_list_folder(path=path_atualiza, shared_link=shared_link)
        for file in result_atualiza.entries:
            print(f"- {file.name} ({'Pasta' if isinstance(file, dropbox.files.FolderMetadata) else 'Arquivo'})")      

        # Transformar items_df em CSV com delimitador "|"
        csv_buffer = io.StringIO()
        items_df.to_csv(csv_buffer, sep='|', index=False)
        csv_data = csv_buffer.getvalue()
        
        # Gerar timestamp no formato YYYY-MM-DD-HH-MIN-SEG
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

        # Nome do arquivo CSV com o timestamp e o nome do cliente
        csv_filename = f"{timestamp}-{client_name}_atualizado.csv"        

        path_atualiza = atualiza_folder.path_lower
        dropbox_path = f"{path_atualiza}/{csv_filename}"
        
        # Upload do CSV para a pasta "Atualiza"
        # dbx.files_upload(csv_data.encode(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        dbx.files_upload(csv_data.encode(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
        print(f"Arquivo {csv_filename} carregado com sucesso na pasta 'Atualiza'")
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Arquivo {csv_filename} carregado com sucesso.\n"
        code_mensagem = "Atualização realizada com sucesso."
        
        return True, initial_log, code_mensagem            
            
    except dropbox.exceptions.AuthError as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro de autenticação no Dropbox para o cliente {client_name}: {e}.\n"
        code_mensagem = 4
        return False, initial_log, code_mensagem
    
    except dropbox.exceptions.ApiError as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro de API do Dropbox ao acessar o cliente {client_name}: {e}.\n"
        code_mensagem = 4
        return False, initial_log, code_mensagem
    
    except Exception as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro inesperado ao acessar o cliente {client_name}: {e}.\n"
        code_mensagem = 4
        return False, initial_log, code_mensagem

if __name__ == "__main__":
    import argparse  # Import argparse for command-line arguments

    parser = argparse.ArgumentParser(description='Process data for a specific client.')
    parser.add_argument('--client_id', type=int, help='The ID of the client to process')
    args = parser.parse_args()

    if args.client_id:
        clients = Client.objects.filter(pk=args.client_id)  # Filter by client_id
    else:
        clients = get_clients()
       
    # clients = get_clients()
    initial_log = ''
    for client in clients:
        host = client.connection_route
        user = client.user_route
        password = client.password_route
        port = client.port_route
        database = client.database_route
        client_id = client.id
        client_name = client.name
        client_cnpj = client.cnpj        

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        initial_log += f'[{timestamp}] - Verificando se há atualizações para o cliente: {client.name}... \n'        

        drop_connect = AccessDropbox.objects.last()

        if drop_connect:
            dropbox_client_id = drop_connect.client_id
            dropbox_client_secret = drop_connect.client_secret
            dropbox_authorization_code = drop_connect.code
            dropbox_access_token = drop_connect.access_token
            dropbox_refresh_token = drop_connect.refresh_token

            # Se o refresh_token for nulo ou vazio, gere novos tokens
            if not dropbox_refresh_token:
                access_token, refresh_token = get_access_token_with_auth_code(
                    dropbox_client_id, dropbox_client_secret, dropbox_authorization_code
                )

                # Atualize o modelo com o novo access_token e refresh_token
                drop_connect.access_token = access_token
                drop_connect.refresh_token = refresh_token
                drop_connect.save()
            else:
                # Atualize o access_token usando o refresh_token
                access_token = refresh_access_token(dropbox_client_id, dropbox_client_secret, dropbox_refresh_token)

                # Atualize o modelo com o novo access_token
                drop_connect.access_token = access_token
                drop_connect.save()
        else:
            print("Nenhuma conexão do Dropbox encontrada no banco de dados.") 
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Não existe configuração para conectar ao cliente {client_name}: {e}\n"
            save_imported_logs(client_id, initial_log) 
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1   

        print(f"Verificando se há atualizações para o cliente: {client.name}")
        
        # Lista de colunas a serem removidas
        columns_to_remove = [
            'type_product', 
            'other_information', 
            'history', 
            'estado_origem', 
            'estado_destino', 
            'is_active', 
            'is_pending_sync', 
            'created_at', 
            'updated_at', 
            'sync_at', 
            'await_sync_at', 
            'sync_validate_at', 
            'user_created_id', 
            'user_updated_id', 
            'sequencial'
        ]        
        
        # Pega todos os itens relacionados a esse cliente
        items_queryset = Item.objects.filter(client=client, status_item__in=[1, 2]).values(
            'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
            'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
            'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'sequencial', 
            'estado_origem', 'estado_destino', 'sync_at', 'status_item',
            naturezareceita_code=F('naturezareceita__code')
        )        
        # Converte o queryset em uma lista de dicionários
        items_list = list(items_queryset.values())

        # Cria um DataFrame a partir da lista de dicionários
        items_df = pd.DataFrame(items_list) 

        
        # Verifica se a quantidade de itens é maior que 1
        if len(items_df) == 0:
            # Faça o que for necessário se houver mais de um item
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Não há atualizações para o cliente: {client.name} \n'        
            print(f"Não há atualizações para o cliente: {client.name}")
            save_imported_logs(client_id, initial_log) 
            if args.client_id:
                sys.exit(2)  # Sair com código de erro 1 
        else:   
            items_df = items_df.drop(columns=columns_to_remove)  
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Iniciando conversão  dos dados para o cliente: {client.name} \n'
            items_df_original = items_df
            items_df = convert_df_otx_version_to_df_client(items_df)  

            try:
                timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                initial_log += f'[{timestamp}] - Conectando e atuaizando... \n'                
                result, initial_log, mensagem_resultante = connect_and_update(host, access_token, client_name, items_df, initial_log)
            except Exception as e:  # Catch any unexpected exceptions
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao cliente {client_name}: {e}\n"
                print(f"Erro ao conectar ao cliente {client_name}: {e}") 
                save_imported_logs(client_id, initial_log) 
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1 

            if result == True:
                try:
                    # Realiza o bulk update
                    # Vamos atualizar apenas os itens que estao com staus = 1, ou seja Aguardando Sincronização
                    # os com status 2, apesar de ter sido enviado, não será atualizado novamente para manter
                    # a mesma data de envio original
                    print(items_df_original.columns)  # Verifique os campos disponíveis no DataFrame
                    
                    current_time = timezone.now()
                    codes_to_update = items_df_original[items_df_original['status_item'] == 1]['code'].tolist()
                    num_updated = Item.objects.filter(
                        code__in=codes_to_update, 
                        status_item=1, 
                        client=client
                    ).update(
                        status_item=2,
                        sync_at=current_time
                    )          

                    if num_updated > 0:
                        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - {num_updated} itens aguardando validação.\n"
                        print(f"{num_updated} itens atualizados com sucesso!")
                    else:
                        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum item atualizado\n"
                        print("Nenhum item foi atualizado.")

                    save_imported_logs(client_id, initial_log)
                    if args.client_id:
                        sys.exit(0)  # Sair com código de sucesso
                        
                except Exception as e:
                    error_message = traceback.format_exc()  # Captura o traceback completo
                    initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro durante a atualização dos itens: {e}\n{error_message}\n"
                    print(f"Ocorreu um erro durante a atualização dos itens: {e}\n{error_message}")                
                    save_imported_logs(client_id, initial_log)
                    if args.client_id:
                        sys.exit(1)      
            else:
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro ao inserir as validações\n"
                save_imported_logs(client_id, initial_log)
                print(f"Ocorreu um erro ao inserir as validações")  
                if args.client_id:
                    if mensagem_resultante == 3:
                        sys.exit(3)
                    elif mensagem_resultante == 4:
                        sys.exit(4)
                    else:
                        sys.exit(1)  # Sair com código de erro 1                       
                       
