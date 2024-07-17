import os
import sys
import django
import mysql.connector
import pandas as pd
import json
from mysql.connector import Error
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
from clients.utils import validateSelect, save_imported_logs
from items.models import Item


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

def convert_df_client_to_df_otx_version(df_client):
    # Caminhos dos arquivos CSV
    path_icms = os.path.join(current_dir, 'relations', 'mac_sistemas_icms.csv')
    path_piscofins = os.path.join(current_dir, 'relations', 'mac_sistemas_piscofins.csv')

    # Leitura dos arquivos CSV em DataFrames
    df_icms = pd.read_csv(path_icms, delimiter=';', dtype={'cst': str})
    df_piscofins = pd.read_csv(path_piscofins, delimiter=';', dtype={'cstpis': str, 'cstcofins': str}) 

    # Converter colunas para os tipos corretos
    df_client['icms'] = pd.to_numeric(df_client['icms'], errors='coerce').astype('Int64') 
    df_client['redbcicms'] = pd.to_numeric(df_client['redbcicms'], errors='coerce').astype(float)
    df_icms['redbcicms'] = pd.to_numeric(df_icms['redbcicms'], errors='coerce').astype(float)
    
    df_client['pis'] = pd.to_numeric(df_client['pis'], errors='coerce').astype(float)
    df_client['cofins'] = pd.to_numeric(df_client['cofins'], errors='coerce').astype(float)
    df_piscofins['pis_aliquota'] = pd.to_numeric(df_piscofins['pis_aliquota'], errors='coerce').astype(float)    
    df_piscofins['cofins_aliquota'] = pd.to_numeric(df_piscofins['cofins_aliquota'], errors='coerce').astype(float)    

    df_icms = df_icms.rename(columns={
        'cfop': 'cfop_id',
        'icms_cst': 'icms_cst_id',
        'icms_aliquota': 'icms_aliquota_id',
        'icms_aliquota_reduzida': 'icms_aliquota_reduzida_id',
        'protege': 'protege_id'
    })
        
    # Realizar o merge entre df_client e df_icms com base nas colunas de interesse
    df_merged = pd.merge(df_client, df_icms[['tributacao', 'icms', 'cst', 'redbcicms', 
                                             'cfop_id', 'icms_cst_id', 'icms_aliquota_id', 
                                             'icms_aliquota_reduzida_id', 'protege_id']], 
                         on=['tributacao', 'icms', 'cst', 'redbcicms'], how='left')
    # Renomear as colunas do df_piscofins para evitar conflitos
    df_piscofins = df_piscofins.rename(columns={
        'piscofins_cst': 'piscofins_cst_id',
        'pis_aliquota': 'pis_aliquota_id',
        'cofins_aliquota': 'cofins_aliquota_id'
    })

    # Realizar o merge entre df_merged e df_piscofins
    df_final = pd.merge(df_merged, df_piscofins[['cstpis', 'pis', 'cstcofins', 'cofins',
                                                 'piscofins_cst_id', 'pis_aliquota_id', 'cofins_aliquota_id']],
                         on=['cstpis', 'pis', 'cstcofins', 'cofins'], how='left')
    
    # Drop redundant columns from the final DataFrame
    df_final.drop(columns=['cnpj','tributacao', 'icms', 'cst', 'redbcicms', 'cstpis', 'pis', 'cstcofins', 'cofins'], inplace=True)

    # Renomear colunas
    df_final = df_final.rename(columns={
        'codigo': 'code',
        'descricao': 'description',
        'codbenef': 'cbenef',
        'cfop_id': 'cfop',
    })
    df_final = df_final.rename(columns=lambda x: x.rstrip('_id') if x.endswith('_id') else x)
    
    
    # Adicionar novas colunas com valores vazios (NaN)
    df_final['barcode'] = ''
    df_final['naturezareceita'] = 0
    df_final['sequencial'] = 0
    df_final['estado_origem'] = ''
    df_final['estado_destino'] = ''
    
    # PARA TESTE
    df_final = df_final.dropna(subset=['cfop'], how='all')
    df_final = df_final.dropna(subset=['piscofins_cst'], how='all')
    df_final = df_final.dropna(subset=['ncm'], how='all')

    return df_final    

def connect_and_query(host, user, password, port, database, client_name, client_cnpj, initial_log):
    try:
        connection = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

        try:
            cursor = connection.cursor()

            query = """
                SELECT 
                    cnpj, codigo, descricao, ncm, cest, tributacao,
                    icms, cst, cstpis, pis, cstcofins, cofins, redbcicms, codbenef
                FROM oriontax.PRODUTO as p
                WHERE p.cnpj = %s
            """

            cursor.execute(query, (client_cnpj,))
            rows = cursor.fetchall()
            
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
    args = parser.parse_args()

    if args.client_id:
        clients = Client.objects.filter(pk=args.client_id)  # Filter by client_id
    else:
        clients = get_clients()
       
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
        try:
            df_client, initial_log = connect_and_query(host, user, password, port, database, client_name, client_cnpj, initial_log)
        except Exception as e:  # Catch any unexpected exceptions
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao cliente {client_name}: {e}\n"
            print(f"Erro ao conectar ao cliente {client_name}: {e}") 
            save_imported_logs(client_id, initial_log) 
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1 
                    
        if df_client is None:
            save_imported_logs(client_id, initial_log)
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1             
        else:
            # converter df_client par versão OrionTAX
            
            df_client_converted = convert_df_client_to_df_otx_version(df_client)
            
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 
                naturezareceita_code=F('naturezareceita__code')
            )        
            # Converte o queryset em uma lista de dicionários
            items_list = list(items_queryset.values())

            # Cria um DataFrame a partir da lista de dicionários
            items_df = pd.DataFrame(items_list)  
            items_df.drop(columns=['id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 'is_pending_sync', 'history', 'other_information', 'type_product'], inplace=True)            
            # print(items_df.info())
            try:
                # Chama a função de validação
                validation_result = validateSelect(client_id, items_df, df_client_converted, initial_log)
                        
            except Exception as e:  # Catch any unexpected exceptions
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client_name}: {e}\n"
                save_imported_logs(client_id, initial_log)
                print(f"Erro ao validar as comparações do cliente {client_name}: {e}")  
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1                       
