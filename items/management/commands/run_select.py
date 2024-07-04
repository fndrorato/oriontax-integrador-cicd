import os
import sys
import django
import psycopg2
import pandas as pd
import json
from psycopg2 import sql

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
from clients.models import Client  # Importe o modelo Client
from clients.utils import validateSysmo
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

def connect_and_query(host, user, password, port, database, client_name):
    try:
        connection = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        print(f"Conectado ao banco de dados PostgreSQL em {host}")

        try:
            cursor = connection.cursor()

            query = sql.SQL("""
                SELECT cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms,
                vl_aliquota_final_icms, vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, vl_aliquota_cofins, nr_naturezareceita,
                tx_estadoorigem, tx_estadodestino 
                FROM tb_sysmointegradorenvio 
                ORDER BY cd_sequencial ASC
            """)

            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Convert rows to a pandas DataFrame
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
            print(df.info())
            print(f"Número de linhas retornadas: {len(df)}")
            return df            

        except Exception as query_error:
            print(f"Erro ao executar a consulta: {query_error}")

        finally:
            cursor.close()

    except Exception as connection_error:
        print(f"Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}")      

    finally:
        if connection:
            connection.close()
            print("Conexão com o banco de dados fechada")

if __name__ == "__main__":
    clients = get_clients()
    for client in clients:
        host = client.connection_route
        user = client.user_route
        password = client.password_route
        port = client.port_route
        database = client.database_route
        client_id = client.id
        client_name = client.name

        print(f"Conectando para o cliente {client.name}")
        df_client = connect_and_query(host, user, password, port, database, client_name)
        if df_client is not None:
            print('Agora necessário carregar os produtos da BASE OrionTax já validados ')        
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
            print(items_df.info())
            
            try:
                # Chama a função de validação
                print('Dentro do try')
                validation_result = validateSysmo(client_id, items_df, df_client)
                print('Saiu do validation do try')
                print(json.dumps(validation_result, indent=4))
                        
            except Exception as e:  # Catch any unexpected exceptions
                # self.logger.critical(f"Unexpected error: {e}", exc_info=True)  # Log with traceback
                print(f"Erro ao validar as comparações do cliente {client_name}: {e}")        
