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
from django.db import models
from django.db.models import F
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import validateSelect, save_imported_logs, update_client_data_get
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
    
def calcular_icms_aliquota_reduzida(row):
    if row['icms_cst'] == 0 and row['redbcicms'] == 0:
        return row['icms_aliquota']
    elif row['icms_cst'] == 20:
        return round((row['icms_aliquota'] * row['redbcicms']) / 100)
    elif row['icms_cst'] in [40, 41, 60]:
        if row['redbcicms'] == 0:
            return 0
        else:
            return round((row['icms_aliquota'] * row['redbcicms']) / 100)
    else:
        return 9999  # Valor padrão se nenhuma condição for satisfeita
    

def convert_df_client_to_df_otx_version(df_client):
    # Caminhos dos arquivos CSV
    path_icms = os.path.join(current_dir, 'relations', 'mac_sistemas_icms.csv')
    path_piscofins = os.path.join(current_dir, 'relations', 'mac_sistemas_piscofins.csv')

    # Leitura dos arquivos CSV em DataFrames
    df_icms = pd.read_csv(path_icms, delimiter=';', dtype={'cst': str})
    df_piscofins = pd.read_csv(path_piscofins, delimiter=';', dtype={'cstpis': str, 'cstcofins': str})
    
    # Excluir a coluna 'icms_cst'
    df_icms = df_icms.drop(columns=['icms_cst'])

    # Remover linhas duplicadas
    df_icms = df_icms.drop_duplicates()    
    
    '''
    CÁLCULO PARA ALIQUOTA REDUZIDA
    CST 0  e red 0 = alq red repete
    CST 20 = faz a conta %red * alíq
    CST 40, 60, 41 e red 0 = alq red será 0
    CST 40, 60, 41 e red <>0 = traz o %red na alqred
    FÓRMULA: (Alíquota x RedBCICMS)/100 = ARREDONDAR PARA CIMA
    '''     
    print(df_client['icms'].unique())

    # Converter colunas para os tipos corretos
    # ANTES ERA CONVERTER PARA INT64 - agora para float
    # df_client['icms'] = pd.to_numeric(df_client['icms'], errors='coerce').astype('Int64') 
    df_client['icms'] = pd.to_numeric(df_client['icms'].apply(float), errors='coerce').astype('int64')
    
    # df_client['icms'] = pd.to_numeric(df_client['icms'], errors='coerce').astype(float) 
    df_client['redbcicms'] = pd.to_numeric(df_client['redbcicms'], errors='coerce').astype(float)
    df_client['cst'] = pd.to_numeric(df_client['cst'], errors='coerce').astype('Int64') 
    df_client.rename(columns={'cst': 'icms_cst'}, inplace=True)
    df_client.rename(columns={'icms': 'icms_aliquota'}, inplace=True)
    
    df_client['icms_aliquota_reduzida'] = df_client.apply(calcular_icms_aliquota_reduzida, axis=1)

    # df_icms['redbcicms'] = pd.to_numeric(df_icms['redbcicms'], errors='coerce').astype(float)
    
    df_client['pis'] = pd.to_numeric(df_client['pis'], errors='coerce').astype(float)
    df_client['cofins'] = pd.to_numeric(df_client['cofins'], errors='coerce').astype(float)
    df_piscofins['pis_aliquota'] = pd.to_numeric(df_piscofins['pis_aliquota'], errors='coerce').astype(float)    
    df_piscofins['cofins_aliquota'] = pd.to_numeric(df_piscofins['cofins_aliquota'], errors='coerce').astype(float)    

    df_icms = df_icms.rename(columns={
        'cfop': 'cfop_id',
        'protege': 'protege_id'
    })   
        
    # Realizar o merge entre df_client e df_icms com base nas colunas de interesse
    df_merged = pd.merge(df_client, df_icms[['tributacao', 'cfop_id', 'protege_id']], 
                         on=['tributacao'], how='left')
    
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

    # Preencher valores NaN nas colunas piscofins_cst_id, pis_aliquota_id e cofins_aliquota_id
    
    df_final['piscofins_cst_id'] = df_final['piscofins_cst_id'].fillna('00')
    df_final['pis_aliquota_id'] = df_final['pis_aliquota_id'].fillna(99)
    df_final['cofins_aliquota_id'] = df_final['cofins_aliquota_id'].fillna(99)
    
    
    # Drop redundant columns from the final DataFrame
    df_final.drop(columns=['cnpj','tributacao', 'cstpis', 'pis', 'cstcofins', 'cofins'], inplace=True)

    # Renomear colunas
    df_final = df_final.rename(columns={
        'numero': 'code',
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
    
    # Preencher valores None (NaN) nas colunas 'ncm' e 'cest' com string vazia ''
    df_final['ncm'] = df_final['ncm'].fillna('')
    df_final['cest'] = df_final['cest'].fillna('')           
    
    # PARA TESTE
    # df_final = df_final.dropna(subset=['cfop'], how='all')
    # df_final = df_final.dropna(subset=['piscofins_cst'], how='all')
    # df_final = df_final.dropna(subset=['ncm'], how='all')
    
    # Converte 'cfop' e 'icms_cst' para inteiros
    df_final['cfop'] = df_final['cfop'].astype('Int64')
    df_final['icms_cst'] = df_final['icms_cst'].astype('Int64')

    # Converte 'piscofins_cst' para string e adiciona zero à frente se necessário
    df_final['piscofins_cst'] = df_final['piscofins_cst'].astype(int).astype(str)
    df_final['piscofins_cst'] = df_final['piscofins_cst'].apply(lambda x: x.zfill(2))    
    
    pd.set_option('display.max_columns', None)
    print(df_final.head())
    print(df_final.info())
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
                    cnpj, numero, descricao, ncm, cest, tributacao,
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
            # print(items_df.info())
            try:
                # Chama a função de validação
                validation_result = validateSelect(client_id, items_df, df_client_converted, initial_log)
                update_client_data_get(client_id, '4')
                        
            except Exception as e:  # Catch any unexpected exceptions
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client_name}: {e}\n"
                save_imported_logs(client_id, initial_log)
                print(f"Erro ao validar as comparações do cliente {client_name}: {e}")  
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1                       
