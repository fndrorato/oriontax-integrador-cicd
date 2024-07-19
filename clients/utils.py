import pandas as pd
import openpyxl
import logging
from datetime import datetime
from django.db import transaction
from items.models import ImportedItem, Item
from .models import Client, LogIntegration
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)  # Obtenha um logger

def save_imported_logs(client_id, log_result):
    client_instance = Client.objects.get(id=client_id)
    # Cria uma nova instância de LogIntegration
    log_integration = LogIntegration(
        client=client_instance,
        result_integration=log_result,
        created_at=timezone.now()  # opcional, pois auto_now_add deve preencher automaticamente
    )
    
    # Salva a nova instância no banco de dados
    log_integration.save()    
    
def delete_imported_items(client_id):
    try:
        # Obtenha a instância do cliente
        client_instance = Client.objects.get(id=client_id)
        
        # Filtre e delete todos os ImportedItems associados a este cliente
        ImportedItem.objects.filter(client=client_instance).delete()
        
        print(f"Todos os itens do cliente com ID {client_id} foram deletados com sucesso.")
    except Client.DoesNotExist:
        return {'message': f'Erro ao deletar itens: {e}', 'status': 'error'}

def insert_new_items(client_id, df, status_id, batch_size=5000):
    client_instance = Client.objects.get(id=client_id)
    current_time = timezone.now()

    for i in range(0, len(df), batch_size):
        try:
            with transaction.atomic():
                batch = df.iloc[i: i + batch_size]
                new_items_list = [
                    ImportedItem(
                        client=client_instance,
                        code=row['code'],
                        barcode=row['barcode'],
                        description=row['description'],
                        ncm=row['ncm'],
                        cest=row['cest'],
                        cfop=row['cfop'],
                        icms_cst=row['icms_cst'],
                        icms_aliquota=row['icms_aliquota'],
                        icms_aliquota_reduzida=row['icms_aliquota_reduzida'],
                        protege=row['protege'],
                        cbenef=row['cbenef'],
                        piscofins_cst=row['piscofins_cst'],
                        pis_aliquota=row['pis_aliquota'],
                        cofins_aliquota=row['cofins_aliquota'],
                        naturezareceita=row['naturezareceita'],
                        sequencial=row['sequencial'],
                        estado_origem=row['estado_origem'],
                        estado_destino=row['estado_destino'],
                        created_at=current_time,
                        status_item=status_id
                    )
                    for _, row in batch.iterrows()
                ]
                # for index, row in batch.iterrows():
                #     print(row)     

                ImportedItem.objects.bulk_create(new_items_list)

                if status_id == 1:
                    # Atualizar itens no modelo Item
                    imported_items_dict = { (item.code, item.client_id): item for item in new_items_list }
                    items_to_update = Item.objects.filter(
                        client_id=client_id,
                        code__in=[item.code for item in new_items_list]
                    )
                    for item in items_to_update:
                        imported_item = imported_items_dict.get((item.code, item.client_id))
                        if imported_item:
                            if not item.sequencial:
                                item.sequencial = imported_item.sequencial
                            if not item.estado_origem:
                                item.estado_origem = imported_item.estado_origem
                            if not item.estado_destino:
                                item.estado_destino = imported_item.estado_destino                            
                    Item.objects.bulk_update(items_to_update, ['sequencial', 'estado_origem', 'estado_destino'])

                print(f'Lote {i // batch_size + 1} de {len(df) // batch_size + 1} inserido e atualizado com sucesso')

        except ValueError as ve:
            logger.error(f"Erro ao converter valor para float: {ve}")
            return {'message': f"Erro ao converter valor para float. Verifique os logs para mais detalhes.", 'status': 'error'}

        except Exception as e:
            logger.error(f"Erro ao inserir/atualizar lote (iniciando em índice {i}): {e}")
            return {'message': f"Erro ao inserir/atualizar lote de itens. Verifique os logs para mais detalhes.", 'status': 'error'}

    return {'message': 'Todos os itens foram inseridos e atualizados com sucesso', 'status': 'success'}

# def insert_new_items(client_id, df, status_id, batch_size=5000):
#     client_instance = Client.objects.get(id=client_id)

#     for i in range(0, len(df), batch_size):
#         try:
#             batch = df.iloc[i: i + batch_size]
#             new_items_list = [
#                 ImportedItem(
#                     client=client_instance,
#                     code=row['code'],
#                     barcode=row['barcode'],
#                     description=row['description'],
#                     ncm=row['ncm'],
#                     cest=row['cest'],
#                     cfop=row['cfop'],
#                     icms_cst=row['icms_cst'],
#                     icms_aliquota=row['icms_aliquota'],
#                     icms_aliquota_reduzida=row['icms_aliquota_reduzida'],
#                     protege=row['protege'],
#                     cbenef=row['cbenef'],
#                     piscofins_cst=row['piscofins_cst'],
#                     pis_aliquota=row['pis_aliquota'],
#                     cofins_aliquota=row['cofins_aliquota'],
#                     naturezareceita=row['naturezareceita'],
#                     status_item=status_id
#                 )
#                 for _, row in batch.iterrows()
#             ]

#             ImportedItem.objects.bulk_create(new_items_list)
#             print(f'Lote {i // batch_size + 1} de {len(df) // batch_size + 1} inserido com sucesso')

#         except Exception as e:
#             logger.error(f"Erro ao inserir lote de itens (iniciando em índice {i}): {e}")
#             return {'message': f"Erro ao inserir lote de itens. Verifique os logs para mais detalhes.", 'status': 'error'}

#     return {'message': 'Todos os itens foram inseridos com sucesso', 'status': 'success'}

def validateSysmo(client_id, items_df, df, initial_log=None):
    """
    Função para validar dados entre items_df e df para um cliente específico.

    Args:
        client_id (int): O ID do cliente.
        items_df (pd.DataFrame): DataFrame contendo os itens cadastrado na Base OrionTax.
        df (pd.DataFrame): DataFrame contendo os dados do cliente para validação.

    Returns:
        dict: Um dicionário com os resultados da validação.
    """
    print('1-Entrou no validate')
    if initial_log is None:
        result_integration = ''
    else: 
        result_integration = initial_log
        
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Dados Recebidos para o Sistema Sysmo \n'
    
    # Eliminar as colunas indesejadas
    df = df.drop(columns=['nr_cst_cofins'])
    print('2-Colunas indesejadas do client DF')
    # Renomear as colunas
    df = df.rename(columns={
        'cd_produto': 'code',
        'tx_codigobarras': 'barcode',
        'tx_descricaoproduto': 'description',
        'tx_ncm': 'ncm',
        'tx_cest': 'cest',
        'nr_cfop': 'cfop',
        'nr_cst_icms': 'icms_cst',
        'vl_aliquota_integral_icms': 'icms_aliquota',
        'vl_aliquota_final_icms': 'icms_aliquota_reduzida',
        'vl_aliquota_fcp': 'protege',
        'tx_cbenef': 'cbenef',
        'nr_cst_pis': 'piscofins_cst',
        'vl_aliquota_pis': 'pis_aliquota',
        'vl_aliquota_cofins': 'cofins_aliquota',
        'nr_naturezareceita': 'naturezareceita',
        'cd_sequencial': 'sequencial',
        'tx_estadoorigem': 'estado_origem',
        'tx_estadodestino': 'estado_destino',
    }) 
    print('3-Rename colunas')
    df['protege'] = df['protege'].apply(lambda x: int(x))
    unique_values = df['protege'].unique()
    print(unique_values)

    
    # Verificar se as colunas existem
    expected_columns = ['barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst',
                        'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                        'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita', 
                        'sequencial', 'estado_origem', 'estado_destino']

    # Lista de colunas que queremos remover
    columns_to_drop = [
        'id', 'client_id', 'type_product', 'other_information', 
        'is_active', 'is_pending_sync', 'created_at', 'updated_at', 
        'user_created_id', 'user_updated_id', 'natureza_id'
    ]

    print('4-Quais colunas da lista estao no DataFrame Items_DF')

    # Verificar quais colunas da lista estão realmente presentes no DataFrame
    existing_columns_to_drop = [col for col in columns_to_drop if col in items_df.columns]

    print('5-Remover colunas nao pertencentes')

    # Remover apenas as colunas que existem no DataFrame
    if existing_columns_to_drop:
        items_df = items_df.drop(columns=existing_columns_to_drop)

    print('6-Rename colunas do ItemsDF')
    # Renomear as colunas
    items_df = items_df.rename(columns={
        'cfop_id': 'cfop',
        'icms_cst_id': 'icms_cst',
        'icms_aliquota_id': 'icms_aliquota',
        'protege_id': 'protege',
        'cbenef_id': 'cbenef',
        'piscofins_cst_id': 'piscofins_cst',
        'naturezareceita_code': 'naturezareceita',
    }) 
    
    ## TRATANDO OS DADOS DA BASE
    # Preencher valores nulos na coluna 'naturezareceita' com 0
    items_df['naturezareceita'] = items_df['naturezareceita'].fillna(0)
    df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float).astype(int)
    df['icms_aliquota_reduzida'] = pd.to_numeric(df['icms_aliquota_reduzida'], errors='coerce').fillna(0).astype(float).astype(int)
    df['pis_aliquota'] = pd.to_numeric(df['pis_aliquota'], errors='coerce').fillna(0.0).astype(float)
    df['cofins_aliquota'] = pd.to_numeric(df['cofins_aliquota'], errors='coerce').fillna(0.0).astype(float)    
    # Preenchendo com 0 a esquerda para o código do piscofins cst
    df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
    # Tratar valores None na coluna 'cbenef'
    items_df['cbenef'] = items_df['cbenef'].fillna('')    

    print('7-Encontrando os novos produtos... ')
    # print(items_df.head())
    # print(df.head())
    print(df.head(2).transpose())
    print(items_df.head(2).transpose())    
    ################################
    # 1- Encontrar os novos produtos
    # Realizar a junção para encontrar os itens presentes em df mas não em items_df
    print('Mostrando a info das duas DF')
    print(items_df.info())
    print(df.info())
    # Remover espaços extras da coluna 'code' em ambos os DataFrames
    df['code'] = df['code'].astype(str).str.strip()
    items_df['code'] = items_df['code'].astype(str).str.strip()
    
    df['description'] = df['description'].astype(str).str.strip()
    items_df['description'] = items_df['description'].astype(str).str.strip()
    
    merged_df = df.merge(items_df[['code']], on='code', how='left', indicator=True)
    # Filtrar os itens que estão em df mas não em items_df
    new_items_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    print('8-Limpando os novos produtos ')
    ## limpando os dados
    new_items_df['barcode'] = new_items_df['barcode'].fillna('')  
    new_items_df['cest'] = new_items_df['cest'].fillna('') 
    new_items_df['cbenef'] = new_items_df['cbenef'].fillna('') 
     
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - executado função dos novos itens. Foram encontrados {len(new_items_df)} novos produtos \n'
    print('9-executado função dos novos itens. Foram encontrados:', len(new_items_df))
    ################################
    # 2- Encontrar os itens divergentes
    # Remover os itens encontrados em new_items_df do dataframe original df
    df = df[df['code'].isin(new_items_df['code']) == False]
    
    # Realizar a junção para verificar todos os itens e identificar divergências
    merged_df = df.merge(items_df, on='code', suffixes=('_df', '_items_df'))
    # Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)
    print('10-Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)')
    missing_columns = []
    for col in expected_columns:
        if f"{col}_df" not in merged_df.columns or f"{col}_items_df" not in merged_df.columns:
            missing_columns.append(col)
    print('11-verificando colunas ausentes')
    if missing_columns:
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Colunas ausentes na importação do cliente: {missing_columns} \n'
        save_imported_logs(client_id, result_integration)
        raise ValueError(f"Colunas ausentes no DataFrame merged_df: {missing_columns}")

    print('12-comparando as colunas- gerando _df e _items_df')
    # Comparar as colunas
    # Lidar com valores nulos e tipos de dados diferentes
    for col in expected_columns:
        # Preencher valores nulos com strings vazias
        merged_df[f'{col}_df'] = merged_df[f'{col}_df'].fillna('').astype(str)
        merged_df[f'{col}_items_df'] = merged_df[f'{col}_items_df'].fillna('').astype(str)

    divergence_mask = pd.Series(False, index=merged_df.index)  # Inicializa a máscara como False
    problematic_columns = []
    divergence_counts = {col: 0 for col in expected_columns}

    columns_not_compare = ['sequencial', 'estado_origem', 'estado_destino']
    # Filtrar as colunas esperadas para remover as colunas que não devem ser comparadas
    filtered_columns = [col for col in expected_columns if col not in columns_not_compare]    
    for col in filtered_columns:
        try:
            col_mask = merged_df[f'{col}_df'] != merged_df[f'{col}_items_df']
            divergence_counts[col] = col_mask.sum()  # Conta as divergências na coluna
            divergence_mask |= col_mask
        except Exception as e:
            # print(f"Erro na comparação da coluna '{col}': {e}")
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            result_integration += f'[{timestamp}] - Erro na comparação da coluna \'{col}\': {e} \n'
            save_imported_logs(client_id, result_integration)
            problematic_columns.append(col)

    # Cria um DataFrame com os itens que NÃO divergiram
    # com isso sera possivel atualizar o status dos itens que estao como 2
    print('XX-items NAO divergentes')
    df_items_not_divergent = merged_df[~divergence_mask]
    # 1. Extrair os códigos
    codes_to_update = df_items_not_divergent['code'].unique().tolist()
    # Contagem de itens a serem atualizados
    num_to_update = Item.objects.filter(
        code__in=codes_to_update, 
        status_item=2, 
        client_id=client_id
    ).count()

    print(f"Número de itens que serão atualizados: {num_to_update}")    
    
    
    current_time = timezone.now() 
    num_updated = Item.objects.filter(
        code__in=codes_to_update, 
        status_item=2, 
        client_id=client_id
    ).update(
        status_item=3,
        sync_validate_at=current_time
    )

    df_items_divergent = merged_df[divergence_mask]
    # Ordenar colunas do df_items_divergent, exceto a primeira coluna
    first_column = df_items_divergent.columns[0]
    other_columns = sorted(df_items_divergent.columns[1:])
    df_items_divergent = df_items_divergent[[first_column] + other_columns]
    
    # print(df_items_divergent.head())
    # df_items_divergent.to_excel('df_items_divergent.xlsx', index=False) 
    print('13-montando o message')
    if len(new_items_df) > 0 or len(df_items_divergent) > 0 or num_updated > 0:
        message = (f"Foram encontrados {len(new_items_df)} novos produtos "
                f"e {len(df_items_divergent)} linhas com divergência no cadastro "
                f"e {num_updated} produtos passaram para validados e sincronizados. ")
    else:
        message = "Nenhum novo produto, divergência encontrada ou produtos para ser validado e sincronizado"  
        
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - {message} \n'   
    #############################################
    ## 3 - GRAVANDO NA TABELA DE ITENS IMPORTADOS
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Deletando itens importados antigos \n'        
    delete_result = delete_imported_items(client_id)
    if delete_result and delete_result.get('status') == 'error':
        return delete_result
    
    print('14-inserindo os novos itens')
    print(message)
    # Inserindo os itens novos na tabela de importacao
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando novos itens \n'            
    try:
        insert_result = insert_new_items(client_id, new_items_df, 0)
    except Exception as e:
        print(f"Erro ao inserir novos itens: {e}")
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Erro ao gravar os novos itens: {e} \n'
        save_imported_logs(client_id, result_integration)        
        return {'message': f"Erro ao inserir novos itens: {e}", 'status': 'error'}
    
    # Filtrar colunas que não terminam com '_items_df'
    df_items_divergent = df_items_divergent[[col for col in df_items_divergent.columns if not col.endswith('_items_df')]]
    # Remover o sufixo '_df' das colunas restantes
    df_items_divergent.columns = [col.replace('_df', '') for col in df_items_divergent.columns]

    # Agora df_items_divergent contém apenas as colunas desejadas  
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando itens com divergência \n' 
    # df_items_divergent['protege'] = df_items_divergent['protege'].apply(lambda x: int(x))           
    
    print('15-inserindo os itens com divergencia')
    try:
        insert_result = insert_new_items(client_id, df_items_divergent, 1)
    except Exception as e:
        print(f"Erro ao inserir itens divergentes: {e}")
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Erro ao gravar os itens divergentes: {e} \n'
        save_imported_logs(client_id, result_integration)        
        return {'message': f"Erro ao inserir itens divergentes: {e}", 'status': 'error'}    
    
    print(result_integration) 
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - FIM \n'  
    save_imported_logs(client_id, result_integration)         

    return {'message': message, 'status': 'success'}


def validateSelect(client_id, items_df, df, initial_log=None):
    """
    Função para validar dados entre items_df e df para um cliente específico.

    Args:
        client_id (int): O ID do cliente.
        items_df (pd.DataFrame): DataFrame contendo os itens cadastrado na Base OrionTax.
        df (pd.DataFrame): DataFrame contendo os dados do cliente para validação.

    Returns:
        dict: Um dicionário com os resultados da validação.
    """
    print('1-Entrou no validate')
    if initial_log is None:
        result_integration = ''
    else: 
        result_integration = initial_log
        
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Dados Recebidos \n'
    
    unique_values = df['protege'].unique()
    print('3-Rename colunas')
    print(unique_values)
    df['protege'] = df['protege'].fillna(0)
    unique_values = df['protege'].unique()
    print(unique_values)
    
    df['protege'] = df['protege'].apply(lambda x: int(x))
    unique_values = df['protege'].unique()
    print('3-Rename colunas2')
    
    # Verificar se as colunas existem
    expected_columns = ['barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst',
                        'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                        'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita']

    # Lista de colunas que queremos remover
    columns_to_drop = [
        'id', 'client_id', 'type_product', 'other_information', 
        'is_active', 'is_pending_sync', 'created_at', 'updated_at', 
        'user_created_id', 'user_updated_id', 'natureza_id'
    ]

    print('4-Quais colunas da lista estao no DataFrame Items_DF')

    # Verificar quais colunas da lista estão realmente presentes no DataFrame
    existing_columns_to_drop = [col for col in columns_to_drop if col in items_df.columns]

    print('5-Remover colunas nao pertencentes')

    # Remover apenas as colunas que existem no DataFrame
    if existing_columns_to_drop:
        items_df = items_df.drop(columns=existing_columns_to_drop)

    print('6-Rename colunas do ItemsDF')
    # Renomear as colunas
    items_df = items_df.rename(columns={
        'cfop_id': 'cfop',
        'icms_cst_id': 'icms_cst',
        'icms_aliquota_id': 'icms_aliquota',
        'protege_id': 'protege',
        'cbenef_id': 'cbenef',
        'piscofins_cst_id': 'piscofins_cst',
        'naturezareceita_code': 'naturezareceita',
    }) 
    
    ## TRATANDO OS DADOS DA BASE
    # Preencher valores nulos na coluna 'naturezareceita' com 0
    items_df['naturezareceita'] = items_df['naturezareceita'].fillna(0)
    df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float).astype(int)
    df['icms_aliquota_reduzida'] = pd.to_numeric(df['icms_aliquota_reduzida'], errors='coerce').fillna(0).astype(float).astype(int)
    df['pis_aliquota'] = pd.to_numeric(df['pis_aliquota'], errors='coerce').fillna(0.0).astype(float)
    df['cofins_aliquota'] = pd.to_numeric(df['cofins_aliquota'], errors='coerce').fillna(0.0).astype(float)    
    # Preenchendo com 0 a esquerda para o código do piscofins cst
    df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
    # Tratar valores None na coluna 'cbenef'
    items_df['cbenef'] = items_df['cbenef'].fillna('')    

    print('7-Encontrando os novos produtos... ')
    # print(items_df.head())
    # print(df.head())
    # print(df.head(2).transpose())
    # print(items_df.head(2).transpose())    
    ################################
    # 1- Encontrar os novos produtos
    # Realizar a junção para encontrar os itens presentes em df mas não em items_df
    merged_df = df.merge(items_df[['code']], on='code', how='left', indicator=True)
    # Filtrar os itens que estão em df mas não em items_df
    new_items_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    print('8-Limpando os novos produtos ')
    ## limpando os dados
    new_items_df['barcode'] = new_items_df['barcode'].fillna('')  
    new_items_df['cest'] = new_items_df['cest'].fillna('') 
    new_items_df['cbenef'] = new_items_df['cbenef'].fillna('') 
     
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - executado função dos novos itens. Foram encontrados {len(new_items_df)} novos produtos \n'
    print('9-executado função dos novos itens. Foram encontrados:', len(new_items_df))
    ################################
    # 2- Encontrar os itens divergentes
    # Remover os itens encontrados em new_items_df do dataframe original df
    df = df[df['code'].isin(new_items_df['code']) == False]
    
    # Realizar a junção para verificar todos os itens e identificar divergências
    merged_df = df.merge(items_df, on='code', suffixes=('_df', '_items_df'))
    # Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)
    print('10-Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)')
    missing_columns = []
    for col in expected_columns:
        if f"{col}_df" not in merged_df.columns or f"{col}_items_df" not in merged_df.columns:
            missing_columns.append(col)
    print('11-verificando colunas ausentes')
    if missing_columns:
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Colunas ausentes na importação do cliente: {missing_columns} \n'
        save_imported_logs(client_id, result_integration)
        raise ValueError(f"Colunas ausentes no DataFrame merged_df: {missing_columns}")

    print('12-comparando as colunas- gerando _df e _items_df')
    # Comparar as colunas
    # Lidar com valores nulos e tipos de dados diferentes
    for col in expected_columns:
        # Preencher valores nulos com strings vazias
        merged_df[f'{col}_df'] = merged_df[f'{col}_df'].fillna('').astype(str)
        # merged_df[f'{col}_items_df'] = merged_df[f'{col}_items_df'].fillna('').astype(str)
        # a versao com infer_objects atende a versao futura do pandas
        merged_df[f'{col}_items_df'] = merged_df[f'{col}_items_df'].fillna('').astype(str).infer_objects(copy=False)

    divergence_mask = pd.Series(False, index=merged_df.index)  # Inicializa a máscara como False
    problematic_columns = []
    divergence_counts = {col: 0 for col in expected_columns}

    columns_not_compare = ['sequencial', 'estado_origem', 'estado_destino']
    # Filtrar as colunas esperadas para remover as colunas que não devem ser comparadas
    filtered_columns = [col for col in expected_columns if col not in columns_not_compare]    
    for col in filtered_columns:
        try:
            col_mask = merged_df[f'{col}_df'] != merged_df[f'{col}_items_df']
            divergence_counts[col] = col_mask.sum()  # Conta as divergências na coluna
            divergence_mask |= col_mask
        except Exception as e:
            # print(f"Erro na comparação da coluna '{col}': {e}")
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            result_integration += f'[{timestamp}] - Erro na comparação da coluna \'{col}\': {e} \n'
            save_imported_logs(client_id, result_integration)
            problematic_columns.append(col)

    df_items_divergent = merged_df[divergence_mask]
    # Ordenar colunas do df_items_divergent, exceto a primeira coluna
    first_column = df_items_divergent.columns[0]
    other_columns = sorted(df_items_divergent.columns[1:])
    df_items_divergent = df_items_divergent[[first_column] + other_columns]
    
    # print(df_items_divergent.head())
    # df_items_divergent.to_excel('df_items_divergent.xlsx', index=False) 
    print('13-montando o message')
    if len(new_items_df) > 0 and len(df_items_divergent) > 0:
        message = (f"Foram encontrados {len(new_items_df)} novos produtos "
                f"e {len(df_items_divergent)} linhas com divergência no cadastro.")
    elif len(new_items_df) > 0:
        message = f"Foram encontrados {len(new_items_df)} novos produtos."
    elif len(df_items_divergent) > 0:
        message = f"Foram encontradas {len(df_items_divergent)} linhas com divergência no cadastro."
    else:
        message = "Nenhum novo produto ou divergência encontrada."  
        
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - {message} \n'   
    #############################################
    ## 3 - GRAVANDO NA TABELA DE ITENS IMPORTADOS
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Deletando itens importados antigos \n'        
    delete_result = delete_imported_items(client_id)
    if delete_result and delete_result.get('status') == 'error':
        return delete_result
    
    print('14-inserindo os novos itens')

    new_items_df['cfop'] = new_items_df['cfop'].apply(lambda x: round(x) if not pd.isnull(x) else x)    
    new_items_df['cfop'] = new_items_df['cfop'].astype('Int64')  # Converte para tipo Int64 
    new_items_df['icms_cst'] = new_items_df['icms_cst'].astype(int)
    # Converter a coluna 'piscofins_cst' de object para float
    new_items_df['piscofins_cst'] = new_items_df['piscofins_cst'].astype(float)
    # Converter a coluna 'piscofins_cst' de float para int
    new_items_df['piscofins_cst'] = new_items_df['piscofins_cst'].astype(int)
    # print(new_items_df.info())
    # print(new_items_df.head(2).transpose())    
    new_items_df.to_excel('new_items_df17jul.xlsx', index=False) 
    
    print(message)
    # Inserindo os itens novos na tabela de importacao
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando novos itens \n'            
    try:
        insert_result = insert_new_items(client_id, new_items_df, 0)
    except Exception as e:
        print(f"Erro ao inserir novos itens: {e}")
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Erro ao gravar os novos itens: {e} \n'
        save_imported_logs(client_id, result_integration)        
        return {'message': f"Erro ao inserir novos itens: {e}", 'status': 'error'}
    
    # Filtrar colunas que não terminam com '_items_df'
    df_items_divergent = df_items_divergent[[col for col in df_items_divergent.columns if not col.endswith('_items_df')]]
    # Remover o sufixo '_df' das colunas restantes
    df_items_divergent.columns = [col.replace('_df', '') for col in df_items_divergent.columns]

    # Agora df_items_divergent contém apenas as colunas desejadas  
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando itens com divergência \n' 

    # Converter a coluna 'cfop' para numérico, lidando com erros de conversão
    df_items_divergent['cfop'] = pd.to_numeric(df_items_divergent['cfop'], errors='coerce')

    # Arredondar os valores numéricos
    df_items_divergent['cfop'] = df_items_divergent['cfop'].round()

    # Converter a coluna 'cfop' para Int64, permitindo valores nulos
    df_items_divergent['cfop'] = df_items_divergent['cfop'].astype('Int64')

    # Exibir os valores únicos convertidos
    df_items_divergent['piscofins_cst'] = df_items_divergent['piscofins_cst'].astype(float).astype('Int64')
    df_items_divergent['icms_cst'] = df_items_divergent['icms_cst'].astype(float).astype('Int64')
        
    print('15-inserindo os itens com divergencia')
    # df_items_divergent.to_excel('df_items_divergent17jul.xlsx', index=False)
    try:
        insert_result = insert_new_items(client_id, df_items_divergent, 1)
    except Exception as e:
        print(f"Erro ao inserir itens divergentes: {e}")
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Erro ao gravar os itens divergentes: {e} \n'
        save_imported_logs(client_id, result_integration)        
        return {'message': f"Erro ao inserir itens divergentes: {e}", 'status': 'error'}    
    
    print(result_integration) 
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - FIM \n'  
    save_imported_logs(client_id, result_integration)         

    return {'message': message, 'status': 'success'}


