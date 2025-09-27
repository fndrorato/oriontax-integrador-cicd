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
from django.db.models import F, Q
from django.utils import timezone
from clients.models import Client  # Importe o modelo Client
from clients.utils import save_imported_logs, update_client_data_send, create_notification
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
    
# Função para calcular o valor de 'redbcicms_id' baseado nas regras fornecidas
def calculate_redbcicms_id(row):
    if row['icms_cst_id'] in ['000', '040', '041', '060']:
        return 0
    elif row['icms_cst_id'] == '020':
        if row['icms_aliquota_id'] != 0:
            return round((row['icms_aliquota_reduzida'] / row['icms_aliquota_id']) * 100, 2)
        else:
            return 0  # Evitar divisão por zero
    else:
        return None  # Ou outro valor padrão/adequado se necessário    

def convert_df_otx_version_to_df_client(df_client):
    # Caminhos dos arquivos CSV
    path_icms = os.path.join(current_dir, 'relations', 'mac_sistemas_icms.csv')

    # Leitura dos arquivos CSV em DataFrames
    df_icms = pd.read_csv(path_icms, delimiter=';', dtype={'cst': str})
    
    # Garantir que os valores na coluna 'icms_cst_id' tenham exatamente 3 caracteres
    df_client['icms_cst_int'] = pd.to_numeric(df_client['icms_cst_id'], errors='coerce').astype('Int64')
    df_client['icms_cst_id'] = df_client['icms_cst_id'].str.zfill(3)
    # df_client['icms_aliquota_reduzida'] = pd.to_numeric(df_client['icms_aliquota_reduzida'], errors='coerce').astype('Int64')
    
    df_client['icms_aliquota_reduzida'] = (
        pd.to_numeric(df_client['icms_aliquota_reduzida'], errors='coerce')  # converte para número (float), nulos viram NaN
        .round(2)  # arredonda para 2 casas decimais
    )
    
    # Aplicar a função ao DataFrame para criar a coluna 'redbcicms_id'
    df_client['redbcicms_id'] = df_client.apply(calculate_redbcicms_id, axis=1)   
    df_client['piscofins_cst_id'] = pd.to_numeric(df_client['piscofins_cst_id'], errors='coerce').astype('Int64')

    df_client = df_client.rename(columns={
        'cfop_id': 'cfop',
        'icms_cst_id': 'icms_cst',
        'icms_aliquota_id': 'icms_aliquota',
        'protege_id': 'protege',
        'cbenef_id': 'cbenef',
        'piscofins_cst_id': 'piscofins_cst'
    })
    
    # TRATANDO PIS/COFINS
    df_client['piscofins_cst'] = df_client['piscofins_cst'].astype(str).str.zfill(2)
    df_client['cstpis'] = df_client['piscofins_cst']
    df_client['cstcofins'] = df_client['piscofins_cst']
    df_client['pis'] = df_client['pis_aliquota']
    df_client['cofins'] = df_client['cofins_aliquota']     
    
    df_client = df_client.rename(columns={
        'icms_cst': 'cst',
        'icms_aliquota': 'icms'
    })
    df_client = df_client.rename(columns={
        'icms_cst_int': 'icms_cst'
    })      
    

    df_icms = df_icms.rename(columns={
        'tributacao': 'tributacao_id'
    })
    
    '''
    CAMPOS
    icms = inteiro OK
    cst = char (000) OK
    redbcicms = ver cálculo
    CÁLCULO PARA RedBCICMS
    CST 0  e red 0 = alq red repete
    CST 20 = faz a conta %red * alíq
    CST 40, 60, 41 e red 0 = alq red será 0
    CST 40, 60, 41 e red <>0 = traz o %red na alqred
    FÓRMULA: (icms_aliquota_reduzida / RedBCICMS)/100 = ARREDONDAR PARA CIMA    
    '''
    # Realizar o merge entre df_client e df_icms com base nas colunas de interesse
    df_merged = pd.merge(df_client, df_icms, on=['cfop', 'icms_cst', 'protege'], how='left')
 
    # Realizar o merge entre df_merged e df_client
    df_final = df_merged
    pd.set_option('display.max_columns', None)
    print(df_final.head())
    # Drop redundant columns from the final DataFrame
    df_final.drop(columns=['piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'cfop', 'icms_cst', 'protege'], inplace=True)

    df_final = df_final.rename(columns=lambda x: x.rstrip('_id') if x.endswith('_id') else x)
    
    # Substitui os valores None por strings vazias na coluna 'cbenef'
    df_final['cbenef'] = df_final['cbenef'].fillna('')

    # Ajuste as configurações de exibição para mostrar todas as colunas

    # Imprime as primeiras 5 linhas do DataFrame
    # print(df_final.head())
    # print(df_final.info())

    return df_final       

def connect_and_update(host, user, password, port, database, client_name, client_cnpj, items_df, initial_log):
    try:
        print(f"Conectando ao banco de dados para o cliente {client_name}...")
        connection = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=database
        )
        print("Conexão estabelecida com sucesso")

        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Conexão estabelecida com sucesso para o cliente {client_name}\n"

        try:
            print("Colunas do DataFrame:", items_df.columns)
            print("Primeiras linhas do DataFrame:\n", items_df.head())
            
            cursor = connection.cursor()
            connection.autocommit = False

            # update_query = """
            #     UPDATE oriontax.PRODUTO
            #     SET 
            #         descricao = CASE codigo 
            # """
            # values = []
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['description'])
            # update_query += " ELSE descricao END, ncm = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['ncm'])
            # update_query += " ELSE ncm END, cest = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cest'])
            # update_query += " ELSE cest END, tributacao = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['tributacao'])
            # update_query += " ELSE tributacao END, icms = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['icms'])
            # update_query += " ELSE icms END, cst = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cst'])
            # update_query += " ELSE cst END, cstpis = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cstpis'])
            # update_query += " ELSE cstpis END, pis = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['pis'])
            # update_query += " ELSE pis END, cstcofins = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cstcofins'])
            # update_query += " ELSE cstcofins END, cofins = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cofins'])
            # update_query += " ELSE cofins END, redbcicms = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['redbcicms'])
            # update_query += " ELSE redbcicms END, codbenef = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(row['cbenef'])
            # update_query += " ELSE codbenef END, dt_atualizacao = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            # update_query += " ELSE dt_atualizacao END, alterado_orion = CASE codigo"
            # for _, row in items_df.iterrows():
            #     update_query += f" WHEN '{row['code']}' THEN %s"
            #     values.append('S')
            # update_query += " ELSE alterado_orion END WHERE cnpj = %s"
            # values.append(client_cnpj)
            
            print("Verificando valores NaN no DataFrame:")
            print(items_df.isna().sum())
            
            tributacao_na_df = items_df[items_df['tributacao'].isna()]
            print("Linhas com 'tributacao' como NaN:")
            print(tributacao_na_df)
            
            
            
           # Início da consulta de atualização
            update_query = """
                UPDATE oriontax.PRODUTO
                SET 
                    descricao = CASE 
            """
            values = []
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['description'])

            update_query += " ELSE descricao END, ncm = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['ncm'])

            update_query += " ELSE ncm END, cest = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cest'])

            update_query += " ELSE cest END, tributacao = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['tributacao'])

            update_query += " ELSE tributacao END, icms = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['icms'])

            update_query += " ELSE icms END, cst = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cst'])

            update_query += " ELSE cst END, cstpis = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cstpis'])

            update_query += " ELSE cstpis END, pis = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['pis'])

            update_query += " ELSE pis END, cstcofins = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cstcofins'])

            update_query += " ELSE cstcofins END, cofins = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cofins'])

            update_query += " ELSE cofins END, redbcicms = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['redbcicms'])

            update_query += " ELSE redbcicms END, codbenef = CASE"
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(row['cbenef'])

            update_query += """
                ELSE codbenef END, 
                dt_atualizacao = CASE
            """
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            update_query += """
                ELSE dt_atualizacao END, 
                alterado_orion = CASE
            """
            for _, row in items_df.iterrows():
                update_query += f" WHEN numero = '{row['code']}' AND cnpj = '{client_cnpj}' THEN %s"
                values.append('S')

            update_query += " ELSE alterado_orion END WHERE cnpj = %s"
            values.append(client_cnpj)            
            
            # Print the query and values for debugging
            # print("Query gerada:\n", update_query)
            # print("Valores associados:\n", values)            
            with open("debug_log.txt", "a") as f:
                f.write(f"Query gerada:\n{update_query}\n")
                f.write(f"Valores associados:\n{values}\n")
            
            cursor.execute(update_query, values)
            connection.commit()

            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Atualização realizada com sucesso para o cliente {client_name}\n"
            print(f"Atualização realizada com sucesso para o cliente {client_name}")
            code_mensagem = "Atualização realizada com sucesso."
            return True, initial_log, code_mensagem

        except Exception as query_error:
            connection.rollback()
            initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao executar a atualização em massa: {query_error}\n"
            print(f"Erro ao executar a atualização em massa: {query_error}")
            code_mensagem = 3
            return False, initial_log, code_mensagem

        finally:
            cursor.close()

    except Exception as conn_error:
        initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Erro ao estabelecer conexão: {conn_error}\n"
        print(f"Erro ao estabelecer conexão: {conn_error}")
        code_mensagem = 4
        return False, initial_log, code_mensagem

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
        client_cnpj = client.cnpj        

        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        initial_log += f'[{timestamp}] - Verificando se há atualizações para o cliente: {client.name}... \n'        

        print(f"Verificando se há atualizações para o cliente: {client.name}")
        
        # Lista de colunas a serem removidas
        columns_to_remove = [
            'naturezareceita_id', 
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
            'naturezareceita_code',
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
        
        print('Total de itens em DF:', len(items_df))
        # Verifica se a quantidade de itens é maior que 1
        if len(items_df) == 0:
            # Faça o que for necessário se houver mais de um item
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Não há atualizações para o cliente: {client.name} \n'        
            print(f"Não há atualizações para o cliente: {client.name}")
            save_imported_logs(client_id, initial_log) 
            message = f"Não há atualizações para o cliente {client_name} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
            title = f"{client_name} - Não há atualizações"
            create_notification(
                user=user_id,
                title=title,
                message=message,
                notification_type='warning',
            )                  
            if args.client_id:
                sys.exit(2)  # Sair com código de erro 1 
        else:               
            items_df = items_df.drop(columns=columns_to_remove)  
            items_df = items_df[items_df["code"] == "036916"]
            print('Convertendo o DF para a versao do clinte')
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            initial_log += f'[{timestamp}] - Iniciando conversão  dos dados para o cliente: {client.name} \n'
            items_df = convert_df_otx_version_to_df_client(items_df) 
                     
            try:
                timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                initial_log += f'[{timestamp}] - Conectando e atuaizando... \n' 
                result, initial_log, mensagem_resultante = connect_and_update(host, user, password, port, database, client_name, client_cnpj, items_df, initial_log)
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
            print('Resultado do UPDATE:', result)
            if result == True:
                try:
                    # Realiza o bulk update
                    # Vamos atualizar apenas os itens que estao com staus = 1, ou seja Aguardando Sincronização
                    # os com status 2, apesar de ter sido enviado, não será atualizado novamente para manter
                    # a mesma data de envio original

                    current_time = timezone.now()
                    codes_to_update = items_df[items_df['status_item'] == 1]['code'].tolist()
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
                    update_client_data_send(client_id, '4')
                    message = f"Dados enviados em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ao cliente {client_name}"
                    title = f"{client_name} - Dados enviados com sucesso"
                    create_notification(
                        user=user_id,
                        title=title,
                        message=message,
                        notification_type='success',
                    )                     
                    if args.client_id:
                        sys.exit(0)  # Sair com código de sucesso
                        
                except Exception as e:
                    initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro durante a atualização dos itens: {e}\n"
                    print(f"Ocorreu um erro durante a atualização dos itens: {e}")                
                    save_imported_logs(client_id, initial_log) 
                    message = f"Ocorreu um erro durante a atualização em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} do cliente {client_name}"
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
                initial_log += f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] - Ocorreu um erro ao inserir as validações\n"
                save_imported_logs(client_id, initial_log)
                print(f"Ocorreu um erro ao inserir as validações")  
                if args.client_id:
                    if mensagem_resultante == 3:
                        message = f"Erro ao executar a atualização em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} do cliente {client_name}"
                        title = f"{client_name} - Erro ao atualizar"
                        create_notification(
                            user=user_id,
                            title=title,
                            message=message,
                            notification_type='danger',
                        )                            
                        sys.exit(3)
                    elif mensagem_resultante == 4:
                        message = f"Nao foi possível estabelecer conexão em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} com o cliente {client_name}"
                        title = f"{client_name} - Erro ao atualizar"
                        create_notification(
                            user=user_id,
                            title=title,
                            message=message,
                            notification_type='danger',
                        )                          
                        sys.exit(4)
                    else:
                        message = f"Ocorreu um erro ao executar a sincronização em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} com o cliente {client_name}"
                        title = f"{client_name} - Erro ao sincronizar"
                        create_notification(
                            user=user_id,
                            title=title,
                            message=message,
                            notification_type='danger',
                        )                         
                        sys.exit(1)  # Sair com código de erro 1                       
                       
