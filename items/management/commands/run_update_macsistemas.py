import os
import sys
import django
import mysql.connector
import pandas as pd
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
from django.db.models import F, Q
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import save_imported_logs
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

def connect_and_update(host, user, password, port, database, client_name, items_df, initial_log):
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

            # Prepara os dados para inserção em massa
            values = [
                (
                    row['sequencial'], row['code'], row['barcode'], row['description'], row['ncm'],
                    row['cest'], row['cfop_id'], row['icms_cst_id'], row['icms_aliquota_id'],
                    row['icms_aliquota_reduzida'], row['protege_id'], row['cbenef_id'], row['piscofins_cst_id'],
                    row['pis_aliquota'], row['piscofins_cst_id'], row['cofins_aliquota'], 
                    row['naturezareceita_code'], row['estado_origem'], row['estado_destino']
                )
                for _, row in items_df.iterrows()
            ]

            # Executa a inserção em massa
            insert_query = """
                INSERT INTO tb_sysmointegradorrecebimento (
                    cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, 
                    tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms, vl_aliquota_final_icms, 
                    vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, 
                    vl_aliquota_cofins, nr_naturezareceita, tx_estadoorigem, tx_estadodestino
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(insert_query, values)

            connection.commit()  # Confirma a transação
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Atualização realizada com sucesso para o cliente {client_name}\n"
            print(f"Atualização realizada com sucesso para o cliente {client_name}")
            return True, initial_log

        except Exception as query_error:
            connection.rollback()  # Desfaz a transação em caso de erro
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao executar a inserção em massa: {query_error}\n"
            print(f"Erro ao executar a inserção em massa: {query_error}")
            return False, initial_log

        finally:
            cursor.close()

    except Error as connection_error:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}\n"
        print(f"Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}")
        return False, initial_log

    finally:
        if connection.is_connected():
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

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        initial_log += f'[{timestamp}] - Verificando se há atualizações para o cliente: {client.name}... \n'        

        print(f"Verificando se há atualizações para o cliente: {client.name}")
        
        items_queryset = Item.objects.filter(client=client, status_item=2).values(
            'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
            'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
            'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'sequencial', 
            'estado_origem', 'estado_destino',
            naturezareceita_code=F('naturezareceita__code')
        )        

        items_list = list(items_queryset.values())
        items_df = pd.DataFrame(items_list) 
        items_df['cbenef_id'] = items_df['cbenef_id'].fillna('') 
        items_df['piscofins_cst_id'] = items_df['piscofins_cst_id'].astype(int)        
        items_df['naturezareceita_code'] = items_df['naturezareceita_code'].fillna(0)
        items_df['naturezareceita_code'] = items_df['naturezareceita_code'].astype(int)
        
        print(items_df['sequencial'].unique())
        sequencial_unicos_zero = items_df[items_df['sequencial'] == 0]['sequencial'].unique()
        print(sequencial_unicos_zero)        
        
        print(len(items_df))
        
        if len(items_df) == 0:
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Não há atualizações para o cliente: {client.name} \n'        
            print(f"Não há atualizações para o cliente: {client.name}")
            save_imported_logs(client_id, initial_log) 
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1 
        else:              
            try:
                result, initial_log = connect_and_update(host, user, password, port, database, client_name, items_df, initial_log)
            except Exception as e:  
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao cliente {client_name}: {e}\n"
                print(f"Erro ao conectar ao cliente {client_name}: {e}") 
                save_imported_logs(client_id, initial_log) 
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1 
                    
            if result == True:
                try:
                    num_updated = Item.objects.filter(client=client, status_item=2).update(status_item=3)

                    if num_updated > 0:
                        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - {num_updated} itens validados com sucesso\n"
                        print(f"{num_updated} itens atualizados com sucesso!")
                    else:
                        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum item validado\n"
                        print("Nenhum item foi atualizado.")

                    save_imported_logs(client_id, initial_log)
                    if args.client_id:
                        sys.exit(0)  # Sair com código de sucesso
                except Exception as e:
                    initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro durante a atualização dos itens: {e}\n"
                    print(f"Ocorreu um erro durante a atualização dos itens: {e}")                
                    save_imported_logs(client_id, initial_log) 
                    if args.client_id: 
                        sys.exit(1)  # Sair com código de erro 1        
            else:
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro ao inserir as validações\n"
                save_imported_logs(client_id, initial_log)
                print(f"Ocorreu um erro ao inserir as validações")  
                if args.client_id:
                    sys.exit(1)  # Sair com código de erro 1 