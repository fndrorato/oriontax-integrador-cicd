import os
import sys
import django
import psycopg2
import pandas as pd
import json
from psycopg2 import sql
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from clients.models import Client  # Importe o modelo Client
from clients.utils import validateSysmo, save_imported_logs
from items.models import Item
from django.db.models import F

class Command(BaseCommand):
    help = 'Run select queries for specific client'

    def add_arguments(self, parser):
        parser.add_argument('client_id', type=int, help='ID of the client to run the select query for')

    def handle(self, *args, **kwargs):
        client_id = kwargs['client_id']
        print(f"Received client_id: {client_id}")
        try:
            client = Client.objects.get(id=client_id)
            print(f"Found client: {client.name}")
        except Client.DoesNotExist:
            print(f"Client with id {client_id} does not exist")
            raise CommandError(f'Client with id {client_id} does not exist')

        initial_log = ''
        host = client.connection_route
        user = client.user_route
        password = client.password_route
        port = client.port_route
        database = client.database_route
        client_name = client.name

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        initial_log += f'[{timestamp}] - Conectando para o cliente {client.name}... \n'        

        print(f"Connecting to database for client: {client.name}")
        try:
            df_client, initial_log = self.connect_and_query(host, user, password, port, database, client_name, initial_log)
            print(f"Query result for client {client_name}: {df_client}")
        except Exception as e:
            print(f"Error during connection/query for client {client_name}: {e}")
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client_name}: {e}\n"
            save_imported_logs(client_id, initial_log)
            return
        
        if df_client is None or df_client.empty:
            print(f"No data returned from query for client {client_name}")
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum dado retornado da consulta para o cliente {client_name}\n"
            save_imported_logs(client_id, initial_log)
        else:
            items_queryset = Item.objects.filter(client=client).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 
                naturezareceita_code=F('naturezareceita__code')
            )        
            items_list = list(items_queryset)
            print(f"Items list for client {client_name}: {items_list}")

            if not items_list:
                print(f"No items found for client {client_name}")
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum item encontrado para o cliente {client_name}\n"
                save_imported_logs(client_id, initial_log)
            else:
                items_df = pd.DataFrame(items_list)  
                print(f"Items DataFrame for client {client_name}: {items_df}")
                
                try:
                    validation_result = validateSysmo(client_id, items_df, df_client, initial_log)
                    print(f"Validation result for client {client_name}: {validation_result}")
                except Exception as e:
                    print(f"Error during validation for client {client_name}: {e}")
                    initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao validar as comparações do cliente {client_name}: {e}\n"
                    save_imported_logs(client_id, initial_log)

    def connect_and_query(self, host, user, password, port, database, client_name, initial_log):
        print(f"Attempting to connect to database: {host}, {database}")
        try:
            connection = psycopg2.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                database=database
            )
            print(f"Connection established for client {client_name}")
            
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

            try:
                cursor = connection.cursor()
                print(f"Executing query for client {client_name}")

                query = sql.SQL("""
                    SELECT cd_sequencial, cd_produto, tx_codigobarras, tx_descricaoproduto, tx_ncm, tx_cest, nr_cfop, nr_cst_icms, vl_aliquota_integral_icms,
                    vl_aliquota_final_icms, vl_aliquota_fcp, tx_cbenef, nr_cst_pis, vl_aliquota_pis, nr_cst_cofins, vl_aliquota_cofins, nr_naturezareceita,
                    tx_estadoorigem, tx_estadodestino 
                    FROM tb_sysmointegradorenvio 
                    ORDER BY cd_sequencial ASC
                """)

                cursor.execute(query)
                rows = cursor.fetchall()
                print(f"Query executed for client {client_name}, rows fetched: {len(rows)}")
                
                if not rows:
                    print(f"No rows returned for client {client_name}")
                    initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Nenhum dado retornado da consulta\n"
                    return None, initial_log

                df = pd.DataFrame(rows, columns=[desc[0] for desc in cursor.description])
                print(f"DataFrame created for client {client_name}: {df}")
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Consulta realizada com sucesso para o cliente {client_name}\n"
                return df, initial_log    

            except Exception as query_error:
                print(f"Error executing query for client {client_name}: {query_error}")
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao executar a consulta: {query_error}\n"
                return None, initial_log

            finally:
                cursor.close()

        except Exception as connection_error:
            print(f"Error connecting to database for client {client_name}: {connection_error}")
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao conectar ao banco de dados do cliente {client_name}: {connection_error}\n"
            return None, initial_log

        finally:
            if connection:
                connection.close()
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão com o banco de dados fechada para o cliente {client_name}\n"
                print(f"Database connection closed for client {client_name}")
