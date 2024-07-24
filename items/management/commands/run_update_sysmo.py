import os
import sys
import django
import psycopg2
import pandas as pd
import json
from psycopg2 import sql
from psycopg2.extras import execute_values  # Para inserção em massa
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
            
            # Consulta SQL para obter os tamanhos máximos das colunas
            cursor.execute("""
                SELECT column_name, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'tb_sysmointegradorrecebimento'
                AND data_type = 'character varying';
            """)
            column_sizes = {row[0]: row[1] for row in cursor.fetchall()}  
            
            # Imprimir a estrutura de colunas e tamanhos máximos
            print("column_name | character_maximum_length")
            print("------------------------+--------------------------")
            for column_name, max_length in column_sizes.items():
                print("{:<24} | {:<25}".format(column_name, max_length))                      
                
            # return False, initial_log

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

            # for _, row in items_df.iterrows():
            #     print(len(row['barcode']), len(row['description']), len(row['ncm']))  # Verifica os comprimentos
            
            # EXECUTAR DELETE ANTES NESSA TABELA
            # Executa a exclusão de todos os registros da tabela
            cursor.execute("DELETE FROM tb_sysmointegradorrecebimento")

            # Executa a inserção em massa
            execute_values(cursor, """
                INSERT INTO tb_sysmointegradorrecebimento (
                    cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, 
                    tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms, vl_aliquota_final_icms, 
                    vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, 
                    vl_aliquota_cofins, nr_naturezareceita, tx_estadoorigem, tx_estadodestino
                ) VALUES %s
            """, values)

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

    except Exception as connection_error:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}\n"
        print(f"Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}")
        return False, initial_log

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
        initial_log += f'[{timestamp}] - Verificando se há atualizações para o cliente: {client.name}... \n'        

        print(f"Verificando se há atualizações para o cliente: {client.name}")
        
        # Pega todos os itens relacionados a esse cliente
        items_queryset = Item.objects.filter(client=client, status_item__in=[1, 2], code='1828').values(
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
        # Substitui None por string vazia na coluna 'cbenef_id'
        items_df['cbenef_id'] = items_df['cbenef_id'].fillna('') 
        # Tenta converter para numérico, valores não numéricos se tornam NaN
        items_df['piscofins_cst_id'] = items_df['piscofins_cst_id'].astype(int)        
        
        # Substitui None por 0 na coluna 'naturezareceita_code'
        items_df['naturezareceita_code'] = items_df['naturezareceita_code'].fillna(0)

        # Converte a coluna 'naturezareceita_code' para inteiro
        items_df['naturezareceita_code'] = items_df['naturezareceita_code'].astype(int)
        
        print(items_df['sequencial'].unique())
        # Supondo que você já tenha o DataFrame items_df
        sequencial_unicos_zero = items_df[items_df['sequencial'] == 0]['sequencial'].unique()
        print(sequencial_unicos_zero)        
        
        # Calcular o tamanho de cada célula na coluna 'description'
        items_df['description_length'] = items_df['description'].apply(len)

        # Encontrar o índice da célula com o maior tamanho
        max_length_index = items_df['description_length'].idxmax()

        # Obter o conteúdo e o tamanho da maior célula
        max_description = items_df.loc[max_length_index, 'description']
        max_description_length = items_df.loc[max_length_index, 'description_length']

        # Obter o 'code' correspondente ao índice da maior célula
        max_description_code = items_df.loc[max_length_index, 'code']

        print(f"O conteúdo da maior célula é: {max_description}")
        print(f"A maior célula tem {max_description_length} caracteres")
        print(f"O 'code' correspondente à maior célula é: {max_description_code}")      
        
        print(len(items_df))
        
        # Verifica se a quantidade de itens é maior que 1
        if len(items_df) == 0:
            # Faça o que for necessário se houver mais de um item
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Não há atualizações para o cliente: {client.name} \n'        
            print(f"Não há atualizações para o cliente: {client.name}")
            save_imported_logs(client_id, initial_log) 
            if args.client_id:
                sys.exit(1)  # Sair com código de erro 1 
        else:              
            try:
                # result, initial_log = connect_and_update(host, user, password, port, database, client_name, items_df, initial_log)
                result = True
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
                    codes_to_update = items_df[items_df['status_item'] == 1]['code'].tolist()
                    num_updated = Item.objects.filter(
                        code__in=codes_to_update, 
                        status_item=1, 
                        client=client
                    ).update(
                        status_item=2,
                        sync_at=F('sync_at')
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
                       
