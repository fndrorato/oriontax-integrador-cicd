import os
import sys
import django
import psycopg2
import pandas as pd
import json
from psycopg2 import sql
from datetime import datetime

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
from django.db.models import F
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import (
    validateSysmo, save_imported_logs, update_client_data_get, create_notification
)
from items.models import Item
from django.contrib.auth import get_user_model


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

def connect_and_query(host, user, password, port, database, client_name, initial_log):
    try:
        connection = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
       
        
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

        try:
            cursor = connection.cursor()
            cursor.itersize = 30000  # Define o tamanho do lote para iteração

            query = sql.SQL("""
                SELECT cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms,
                vl_aliquota_final_icms, vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, vl_aliquota_cofins, nr_naturezareceita,
                tx_estadoorigem, tx_estadodestino 
                FROM tb_sysmointegradorenvio
                ORDER BY cd_sequencial ASC
            """)                    

            cursor.execute(query)
            # rows = cursor.fetchall()
            rows = []  # Lista para armazenar todos os resultados
            while True:
                batch = cursor.fetchmany(size=cursor.itersize)  # Busca o próximo lote
                if not batch:  # Sai do loop se não houver mais dados
                    break
                rows.extend(batch)  # Acumula o lote na lista de resultados
            
            # Convert rows to a pandas DataFrame
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Consulta realizada com sucesso para o cliente {client_name}\n"
            return df, initial_log    

        except Exception as query_error:
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao executar a consulta: {query_error}\n"
            print(f"Erro ao executar a consulta: {query_error}")
            return None, initial_log

        finally:
            cursor.close()

    except Exception as connection_error:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}\n"
        print(f"Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}")
        return None, initial_log

    finally:
        if connection:
            connection.close()
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão com o banco de dados fechada para o cliente {client_name}\n"
            print("Conexão com o banco de dados fechada")

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

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        initial_log += f'[{timestamp}] - Conectando para o cliente {client.name}...(SYSMO) \n'        

        print(f"Conectando para o cliente {client.name}")
        try:
            df_client, initial_log = connect_and_query(host, user, password, port, database, client_name, initial_log)
        except Exception as e:  # Catch any unexpected exceptions
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao cliente {client_name}: {e}\n"
            print(f"Erro ao conectar ao cliente {client_name}: {e}") 
            save_imported_logs(client_id, initial_log) 
            message = f"Erro ao conectar ao cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
            title = f"{client_name} - Erro ao conectar"
            create_notification(
                user=user_id,
                title=title,
                message=message,
                notification_type='danger',
            )              
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1 
                    
        if df_client is None:
            save_imported_logs(client_id, initial_log)
            message = f"Erro ao conectar ao cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
            title = f"{client_name} - Erro ao conectar"
            create_notification(
                user=user_id,
                title=title,
                message=message,
                notification_type='danger',
            )              
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1             
        else:
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 
                'sequencial', 'estado_origem', 'estado_destino', 'type_product',
                naturezareceita_code=F('naturezareceita__code')
            )        
            # Verifica se o queryset está vazio
            if items_queryset.exists():
                # Converte o queryset em uma lista de dicionários
                items_list = list(items_queryset)
                # Cria um DataFrame a partir da lista de dicionários
                items_df = pd.DataFrame(items_list)
                items_df = items_df.astype({'icms_aliquota_reduzida': 'float'})

                # Opcional: se quiser preencher com zeros inicialmente
                items_df['icms_aliquota_reduzida'] = items_df['icms_aliquota_reduzida'].fillna(0).round(2)
            else:
                # Define as colunas manualmente
                columns = [
                    'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                    'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                    'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_code',
                    'sequencial', 'estado_origem', 'estado_destino', 'type_product',
                ]
                # Cria um DataFrame vazio com as colunas definidas
                items_df = pd.DataFrame(columns=columns) 
            # print(df_client.head())
            
            # for i, descricao in enumerate(df_client['tx_descricaoproduto']):
            #     print(f"{i+1}. {descricao}")  # Imprime o índice e a descrição            
            
            # sys.exit(1)
            
            try:
                # Chama a função de validação
                validation_result = validateSysmo(client_id, items_df, df_client, initial_log)
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
                title = f"{client_name} - Erro ao receber dados",
                create_notification(
                    user=user_id,
                    title="{client_name} - Erro ao receber dados",
                    message=message,
                    notification_type='danger',
                )                
                print(f"Erro ao validar as comparações do cliente {client_name}: {e}")  
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1                       
                       