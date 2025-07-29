import os
import sys
import django
import dropbox
import pandas as pd
import requests
import time
from io import StringIO
from datetime import datetime
import chardet
from utils import (
    refresh_access_token, 
    get_access_token_with_auth_code, 
)


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
from django.db import models
from django.db.models import F
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import (
    validateSelect, save_imported_logs, update_client_data_get,
    create_notification )
from items.models import Item
from django.contrib.auth import get_user_model
from erp.models import AccessDropbox
from impostos.models import PisCofinsCst
    
def process_csv(data):
    # Dividir as linhas
    lines = data.splitlines()
    
    first_line_pipe_count = lines[0].count('|')
    
    # Ajustar as linhas subsequentes
    adjusted_lines = []
    
    for line in lines:
        current_pipe_count = line.count('|')
        
        if current_pipe_count > first_line_pipe_count:
            # Remover o último '|'
            line = line.rstrip('|')
            # print(f"Removido o último '|' da linha: {line}")
        elif current_pipe_count < first_line_pipe_count:
            # Adicionar um '|' ao final da linha
            line = line + '|'
            # print(f"Adicionado '|' ao final da linha: {line}")
        
        adjusted_lines.append(line)    
    
    # Reunir as linhas de volta em uma única string
    corrected_data = '\n'.join(adjusted_lines)
    
    # Ler o CSV usando o delimitador correto '|'
    try:
        df = pd.read_csv(StringIO(corrected_data), delimiter='|', dtype=str)
    except Exception as e:
        print("Erro ao ler o CSV:", e)
        return None
    
    df.rename(columns={df.columns[0]: 'PRODUTO'}, inplace=True)   
    
    return df

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

def convert_df_client_to_df_otx_version(df_client, initial_log, client_id):
    # Diretório atual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Nome do arquivo específico do cliente
    client_filename = f'tilit_icms_{client_id}.csv'
    default_filename = 'tilit_icms.csv'

    # Caminho do arquivo
    client_path = os.path.join(current_dir, 'relations', client_filename)
    default_path = os.path.join(current_dir, 'relations', default_filename)

    # Verifica se o arquivo do cliente existe
    print('verificando path')
    path_icms = client_path if os.path.exists(client_path) else default_path
    print('passou pelo path')
    
    # Recuperar todos os dados do modelo
    pis_cofins_data = PisCofinsCst.objects.all().values()  # Use .values() para obter um dicionário

    # Transformar em DataFrame
    df_pis_cofins = pd.DataFrame(list(pis_cofins_data))  
    df_pis_cofins = df_pis_cofins.drop(columns=['description'])     

    # Leitura dos arquivos CSV em DataFrames
    df_icms = pd.read_csv(path_icms, delimiter=';', dtype={'cst': str})
    df_pis_cofins['piscofins_cst_id'] = df_pis_cofins['code']

    print('ira converter para os tipos corretos')
    # Converter colunas para os tipos corretos
    df_icms['icms_aliquota_reduzida'] = pd.to_numeric(df_icms['icms_aliquota_reduzida'], errors='coerce').astype(float)

    df_icms = df_icms.rename(columns={
        'cfop': 'cfop_id'
    })   
    
    # Excluir todas as linhas que o ICMS seja igual IMOBILIZADO
    df_client = df_client[df_client['ICMS'] != 'IMOBILIZADO']
        
    # Realizar o merge entre df_client e df_icms com base nas colunas de interesse
    df_merged = df_client.merge(df_icms, left_on='ICMS', right_on='icms', how='left')
    
    # Verificar quais itens não encontraram correspondência (valores NaN em 'icms')
    itens_nao_encontrados = df_merged[df_merged['icms'].isna()]
    print('ira verificar items nao encontrados')
    itens_nao_encontrados.head(10)  # Exibir os primeiros 10 itens não encontrados para depuração
    itens_nao_encontrados.info()
    # Verificar se existem itens não encontrados
    if not itens_nao_encontrados.empty:
        print('00001')
        # Obter os valores únicos da coluna ICMS dos itens não encontrados
        icms_nao_encontrados = itens_nao_encontrados['ICMS'].unique()
        print('00002')
        # Adicionar ao log a mensagem com os valores únicos da coluna ICMS
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - As seguintes alíquotas não foram encontradas: {', '.join(map(str, icms_nao_encontrados))}\n"
        
        # Remover as linhas onde df_merged['icms'] é NaN
        # df_merged = df_merged.dropna(subset=['icms'])
        return 0, initial_log
    else:
        print('00003')
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Todos os itens encontraram correspondência.\n"
 
    print('iniciando print df_final')
    df_final = df_merged.merge(df_pis_cofins, left_on='PIS', right_on='code', how='left')
    # Remover a coluna 'code' do DataFrame df_final
    df_final = df_final.drop(columns=['code', 'PIS', 'ICMS', 'icms'])
    # Adicionar novas colunas com valores vazios (NaN)
    print('adicionando noovos campos')
    df_final['protege'] = 0
    df_final['sequencial'] = 0
    df_final['estado_origem'] = ''
    df_final['estado_destino'] = ''    
    # Renomear colunas
    print('renomeando as colunas')
    df_final = df_final.rename(columns={
        'PRODUTO': 'code',
        'BARRAS': 'barcode',
        'DESCRICAO': 'description',
        'CODBENEFICIOFISCAL': 'cbenef',
        'NCM': 'ncm',
        'cfop_id': 'cfop',
        'piscofins_cst_id': 'piscofins_cst',
        'CEST': 'cest',
        'NATUREZARECEITAPIS': 'naturezareceita'
    })    
    # Definindo a nova ordem das colunas
    print('definindo as ordens')
    nova_ordem = [
        'code',
        'description',
        'ncm',
        'cest',
        'icms_aliquota',
        'icms_cst',
        'cbenef',
        'icms_aliquota_reduzida',
        'cfop',
        'protege',
        'piscofins_cst',
        'pis_aliquota',
        'cofins_aliquota',
        'barcode',
        'naturezareceita',
        'sequencial',
        'estado_origem',
        'estado_destino'
    ]

    # Reordenando as colunas do DataFrame df_final
    df_final = df_final[nova_ordem]

    # Preencher valores NaN nas colunas piscofins_cst_id, pis_aliquota_id e cofins_aliquota_id
    print('Preencher valores NaN')
    df_final['piscofins_cst'] = df_final['piscofins_cst'].fillna('00')
    df_final['pis_aliquota'] = df_final['pis_aliquota'].fillna(99)
    df_final['cofins_aliquota'] = df_final['cofins_aliquota'].fillna(99)
    df_final['naturezareceita'] = df_final['naturezareceita'].fillna(0)
    # Substituir valores não numéricos por NaN e então preencher com 0
    df_final['naturezareceita'] = pd.to_numeric(df_final['naturezareceita'], errors='coerce').fillna(0)
    print('NCM E CEST')
    # Preencher valores None (NaN) nas colunas 'ncm' e 'cest' com string vazia ''
    df_final['ncm'] = df_final['ncm'].fillna('')
    df_final['cest'] = df_final['cest'].fillna('')           
    print('CFOP E ICMS CST')
    # Converte 'cfop' e 'icms_cst' para inteiros
    df_final['cfop'] = df_final['cfop'].astype('Int64')
    df_final['icms_cst'] = df_final['icms_cst'].astype('Int64')
    df_final['icms_aliquota'] = df_final['icms_aliquota'].astype('Int64')
    df_final['icms_aliquota_reduzida'] = pd.to_numeric(
        df_final['icms_aliquota_reduzida'], errors='coerce'
    ).round(2)

    # Converte 'piscofins_cst' para string e adiciona zero à frente se necessário
    df_final['piscofins_cst'] = df_final['piscofins_cst'].astype(int).astype(str)
    df_final['piscofins_cst'] = df_final['piscofins_cst'].apply(lambda x: x.zfill(2))    
    
    pd.set_option('display.max_columns', None)
    # print(df_final.head())
    # print(df_final.info())
    # df_final.to_csv('nome_do_arquivo.csv', sep='|', index=False)    
    return df_final, initial_log    

# def connect_and_query(host, user, password, port, database, client_name, client_cnpj, initial_log):
def connect_and_query(host, token, client_name, initial_log):    
    # Substitua pelo seu token de acesso
    # DROPBOX_ACCESS_TOKEN = 'sl.B9lW1B5bg9J7f7gNb5Jiqpuh3Y7ITSnkruxl5NkibyZUmSRpBBnzv1DiH-w8RVVsylp4h--oE6ApUl6viFYFMFVjdgM0SICHS6y2RK3oVZP2xfzEYyLjRrOi5Bfp_2EZaJ73Z4JL3ZNhcGk'
    DROPBOX_ACCESS_TOKEN = token

    # URL da pasta compartilhada
    # SHARED_LINK_URL = 'https://www.dropbox.com/scl/fo/yclr9n5nf3igro23ayufj/AFAYQQxEjL8-D7JbuGzKSfY?rlkey=s7p50hr27tskudfwnb0twbfcx&st=es9a30u4&dl=0'
    
    SHARED_LINK_URL = host
    # SHARED_LINK_URL = 'https://www.dropbox.com/scl/fo/2hnc28dnfmq4ra19ysa10/AJvuLMvKH_UOEdT_3ieRGC0?rlkey=k5u81q8iiwohm6yf0wz05f2zj&dl=0'
    try:
        # Conectar à API do Dropbox
        dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
        
        # Extrair metadados do link compartilhado
        shared_link_metadata = dbx.sharing_get_shared_link_metadata(SHARED_LINK_URL)
        shared_link = dropbox.files.SharedLink(url=SHARED_LINK_URL)

        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

        # Listar todos os arquivos na pasta raiz do link compartilhado
        # result = dbx.files_list_folder(path='', shared_link=dropbox.sharing.SharedLinkMetadata(url=SHARED_LINK_URL))
        result = dbx.files_list_folder('', shared_link=dropbox.files.SharedLink(url=SHARED_LINK_URL))

        # Listar arquivos e pastas na raiz da pasta compartilhada
        items = result.entries
        
        # Exibir todas as pastas e arquivos no diretório base
        print("Pastas e arquivos disponíveis no diretório base:")
        for item in items:
            print(f"- {item.name} ({'Pasta' if isinstance(item, dropbox.files.FolderMetadata) else 'Arquivo'})")
        
        # Verifica se a pasta 'Consulta' existe
        # consulta_folder = next((folder for folder in items if folder.name.lower() == 'consulta' and isinstance(folder, dropbox.files.FolderMetadata)), None)
        consulta_folder = next((folder for folder in result.entries if folder.name.lower() == 'export' and isinstance(folder, dropbox.files.FolderMetadata)), None)
        
        if not consulta_folder:
            print('nao encontrou a pasta consulta')
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - A pasta 'Consulta' não foi encontrada.\n"
            return None, initial_log
        else:
            print('pasta export encontrada')
        
        print("\nArquivos dentro de 'export':")
        # Usa o caminho relativo dentro do link compartilhado para acessar a pasta 'Consulta'
        path_consulta = f"/{consulta_folder.name}"
        result_consulta = dbx.files_list_folder(path=path_consulta, shared_link=shared_link)
        for file in result_consulta.entries:
            # print(f"- {file.name}")  
            print(f"- {file.name} ({'Pasta' if isinstance(file, dropbox.files.FolderMetadata) else 'Arquivo'})")      
        
        # Filtrar arquivos CSV na pasta 'Consulta'
        # csv_files = [file for file in result_consulta if file.name.endswith('.csv')]
        csv_files = [file for file in result_consulta.entries if isinstance(file, dropbox.files.FileMetadata) and file.name.endswith('.csv')]
        
        if not csv_files:
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum arquivo CSV encontrado na pasta 'Consulta'.\n"
            return None, initial_log
        else:
            print(f"Quantidade de arquivos CSV encontrados: {len(csv_files)}")
            
        # Criar um DataFrame para armazenar os dados de todos os arquivos CSV
        all_data = []
        for csv_file in csv_files:
            try:
                print(f"Lendo arquivo: {csv_file.name}")
                # Faz o download do arquivo CSV usando o link compartilhado
                _, response = dbx.files_download(path=csv_file.path_lower)
                time.sleep(1)

                # Detectar a codificação do arquivo
                raw_data = response.content
                detected_encoding = chardet.detect(raw_data)['encoding']

                # Decodifica os dados brutos
                data = raw_data.decode(detected_encoding)

                # Ler o CSV usando o delimitador correto '|'
                df = process_csv(data)
                all_data.append(df)
            except Exception as e:
                print(f"Erro ao baixar ou processar o arquivo {csv_file.name}: {e}")
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao baixar ou processar o arquivo {csv_file.name}: {e}.\n"
                return None, initial_log                

        # Concatenar todos os DataFrames em um único DataFrame
        final_df = pd.concat(all_data, ignore_index=True)
        print("Dados dos arquivos CSV foram lidos com sucesso.")
        return final_df, initial_log 
    
    except dropbox.exceptions.AuthError as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro de autenticação no Dropbox para o cliente {client_name}: {e}.\n"
        return None, initial_log
    
    except dropbox.exceptions.ApiError as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro de API do Dropbox ao acessar o cliente {client_name}: {e}.\n"
        return None, initial_log
    
    except Exception as e:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro inesperado ao acessar o cliente {client_name}: {e}.\n"
        return None, initial_log


if __name__ == "__main__":
    import argparse  # Import argparse for command-line arguments

    parser = argparse.ArgumentParser(description='Process data for a specific client.')
    parser.add_argument('--client_id', type=int, help='The ID of the client to process')
    parser.add_argument('--user_id', type=int, help='The ID of the Django user executing the command (optional)')
    args = parser.parse_args()

    if args.client_id:
        clients = Client.objects.filter(pk=args.client_id)  # Filter by client_id        
    else:
        clients = get_clients()
        
    # Carregar usuário, se fornecido
    if args.user_id:
        User = get_user_model()
        try:
            user = User.objects.get(pk=args.user_id)
            user_id = user.id
        except User.DoesNotExist:
            print(f"⚠️ Usuário com ID {args.user_id} não encontrado.")
            user = None
            user_id = None
    else:
        print("ℹ️ Nenhum usuário fornecido. Executando como processo do sistema.")
        user = None   
        user_id = None   
       
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
        initial_log += f'[{timestamp}] - Conectando para o cliente {client.name}... \n'             

        print(f"Conectando para o cliente {client.name}")
        
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
        
        try: 
            df_client, initial_log = connect_and_query(host, access_token, client_name, initial_log)
        except Exception as e:  # Catch any unexpected exceptions
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao cliente {client_name}: {e}\n"
            print(f"Erro ao conectar ao cliente {client_name}: {e}") 
            save_imported_logs(client_id, initial_log) 
            message = f"Erro ao conectar ao cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
            title = f"{client_name} - Erro ao receber dados"
            create_notification(
                user=user_id,
                title=title,
                message=message,
                notification_type='danger',
            )                 
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1 
                   
        if df_client is None:
            print('Nada a ser importado')
            save_imported_logs(client_id, initial_log)
            message = f"Erro ao consultar os dados do cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
            title = f"{client_name} - Erro ao receber dados"
            create_notification(
                user=user_id,
                title=title,
                message=message,
                notification_type='danger',
            )              
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1             
        else:

            # converter df_client par versão OrionTAX
            print('vai iniciar a conversao de dados')
            df_client_converted, initial_log = convert_df_client_to_df_otx_version(df_client, initial_log, client_id)
            
            if not isinstance(df_client_converted, pd.DataFrame) and df_client_converted == 0:
                # Encontrou alguma linha do ICMS que não tem relação
                save_imported_logs(client_id, initial_log)
                message = f"Erro ao converter os dados do cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
                title = f"{client_name} - Erro ao converter dados"
                create_notification(
                    user=user_id,
                    title=title,
                    message=message,
                    notification_type='danger',
                )                    
                sys.exit(1)

            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'type_product',
                naturezareceita_code=F('naturezareceita__code')
            )        
            if items_queryset:
                items_df = pd.DataFrame(list(items_queryset.values()))
                
                items_df = items_df.astype({'icms_aliquota_reduzida': 'float'})
                items_df['icms_aliquota_reduzida'] = items_df['icms_aliquota_reduzida'].fillna(0).round(2)
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
            # print('items_df')
            # print(items_df.info())
            # print('df_client_converted')
            # print(df_client_converted.info())
            # sys.exit(0)  # Sair com código de sucesso 0
            try:
                # Chama a função de validação
                validation_result = validateSelect(client_id, items_df, df_client_converted, initial_log)
                update_client_data_get(client_id, '4')
                message = f"Dados recebidos em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} do cliente {client_name}"
                title = f"{client_name} - Dados recebidos com sucesso"
                create_notification(
                    user=user_id,
                    title=title,
                    message=message,
                    notification_type='success',
                )                  
                        
            except Exception as e:  # Catch any unexpected exceptions
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client_name}: {e}\n"
                save_imported_logs(client_id, initial_log)
                message = f"Erro ao receber dados em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} do cliente {client_name}"
                title = f"{client_name} - Erro ao receber dados"
                create_notification(
                    user=user_id,
                    title=title,
                    message=message,
                    notification_type='danger',
                )  
                print(f"Erro ao validar as comparações do cliente {client_name}: {e}")  
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1                       
