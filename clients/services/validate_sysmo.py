import pandas as pd
import openpyxl
import logging
import uuid
from clients.utils import save_imported_logs, delete_imported_items, insert_new_items
from datetime import datetime
from django.db import transaction
from items.models import ImportedItem, Item
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from decimal import Decimal


logger = logging.getLogger(__name__)  # Obtenha um logger
User = get_user_model()

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
    if initial_log is None:
        result_integration = ''
    else: 
        result_integration = initial_log
        
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Dados Recebidos para o Sistema Sysmo \n'
    
    # Excluindo os items que estão marcados como INSUMOS OU IMOBILIZADOS
    filtered_df = items_df[items_df['type_product'] != 'Revenda']
    # Excluindo as linhas de df em que o 'code' também está presente em filtered_df['code']
    df_filtered = df[~df['cd_produto'].isin(filtered_df['code'])]
    # Verifica se o número de linhas foi reduzido após a filtragem
    if len(df) > len(df_filtered):
        # Calcula quantos itens foram excluídos
        itens_excluidos = len(df) - len(df_filtered) 
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')    
        result_integration += f'[{timestamp}] - {itens_excluidos} itens excluídos por serem classificados como Insumos ou Imobilizados.\n'
   
    # Substitui df pelo df_filtered após a filtragem
    df = df_filtered
    # Exclui a coluna 'type_product' de items_df
    items_df = items_df.drop('type_product', axis=1)       
    
    # Eliminar as colunas indesejadas
    df = df.drop(columns=['nr_cst_cofins'])

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

    df['protege'] = df['protege'].apply(lambda x: int(x))
    unique_values = df['protege'].unique()

    # Verificar se as colunas existem
    expected_columns = ['barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst',
                        'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                        'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita', 
                        'sequencial', 'estado_origem', 'estado_destino']

    columns_reforma_tributaria = ['cst_ibs_cbs', 'c_class_trib', 'aliquota_ibs', 'aliquota_cbs', 'p_red_aliq_ibs', 'p_red_aliq_cbs']
    missing_columns = []
    for col in columns_reforma_tributaria:
        if col not in df.columns:
            missing_columns.append(col)
    
    use_reforma_tributaria = True
    if missing_columns:
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Colunas da Reforma Tributaria ausentes na importação do cliente: {missing_columns} \n'
        use_reforma_tributaria = False

    if use_reforma_tributaria:
        columns_to_drop = [
            'id', 'client_id', 'type_product', 'other_information', 
            'is_active', 'is_pending_sync', 'created_at', 'updated_at', 
            'user_created_id', 'user_updated_id', 'natureza_id'
        ]
    else:
        columns_to_drop = [
            'id', 'client_id', 'type_product', 'other_information', 
            'is_active', 'is_pending_sync', 'created_at', 'updated_at', 
            'user_created_id', 'user_updated_id', 'natureza_id',
            'cst_ibs_cbs', 'c_class_trib', 'aliquota_ibs', 'aliquota_cbs', 
            'p_red_aliq_ibs', 'p_red_aliq_cbs'
        ]


    # Verificar quais colunas da lista estão realmente presentes no DataFrame
    existing_columns_to_drop = [col for col in columns_to_drop if col in items_df.columns]

    # Remover apenas as colunas que existem no DataFrame
    if existing_columns_to_drop:
        items_df = items_df.drop(columns=existing_columns_to_drop)

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
    items_df['naturezareceita'] = items_df['naturezareceita'].astype(int)
    df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float).astype(int)
    # df['icms_aliquota_reduzida'] = pd.to_numeric(df['icms_aliquota_reduzida'], errors='coerce').fillna(0).astype(float).astype(int)
    df['icms_aliquota_reduzida'] = (
        pd.to_numeric(df['icms_aliquota_reduzida'], errors='coerce')
        .fillna(0)
        .astype(float)
        .round(2)
    )
    df['pis_aliquota'] = pd.to_numeric(df['pis_aliquota'], errors='coerce').fillna(0.0).astype(float)
    df['cofins_aliquota'] = pd.to_numeric(df['cofins_aliquota'], errors='coerce').fillna(0.0).astype(float)    
    # Preenchendo com 0 a esquerda para o código do piscofins cst
    df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
    # Tratar valores None na coluna 'cbenef'
    items_df['cbenef'] = items_df['cbenef'].fillna('')    

    # Remover espaços extras da coluna 'code' em ambos os DataFrames
    df['code'] = df['code'].astype(str).str.strip()
    items_df['code'] = items_df['code'].astype(str).str.strip()
    
    df['description'] = df['description'].astype(str).str.strip()
    items_df['description'] = items_df['description'].astype(str).str.strip()
    
    merged_df = df.merge(items_df[['code']], on='code', how='left', indicator=True)
    # Filtrar os itens que estão em df mas não em items_df
    new_items_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    ## limpando os dados
    new_items_df['barcode'] = new_items_df['barcode'].fillna('')  
    new_items_df['cest'] = new_items_df['cest'].fillna('') 
    new_items_df['cbenef'] = new_items_df['cbenef'].fillna('') 
     
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - executado função dos novos itens. Foram encontrados {len(new_items_df)} novos produtos \n'
    ################################
    # 2- Encontrar os itens divergentes
    # Remover os itens encontrados em new_items_df do dataframe original df
    df = df[df['code'].isin(new_items_df['code']) == False]
    
    # Realizar a junção para verificar todos os itens e identificar divergências
    merged_df = df.merge(items_df, on='code', suffixes=('_df', '_items_df'))
    # Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)
    missing_columns = []
    for col in expected_columns:
        if f"{col}_df" not in merged_df.columns or f"{col}_items_df" not in merged_df.columns:
            missing_columns.append(col)

    if missing_columns:
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Colunas ausentes na importação do cliente: {missing_columns} \n'
        save_imported_logs(client_id, result_integration)
        raise ValueError(f"Colunas ausentes no DataFrame merged_df: {missing_columns}")

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
    # Criar uma nova coluna vazia para armazenar as colunas divergentes
    merged_df["divergent_columns_df"] = [[] for _ in range(len(merged_df))]    
    
    # Itera sobre as linhas do DataFrame
    for idx, row in merged_df.iterrows():
        try:
            # Recupera o código para imprimir
            code = row.get('code', 'N/A')
            
            # Obtém os valores icms_cst
            icms_cst_df_value = int(row['icms_cst_df'])
            icms_cst_items_df_value = int(row['icms_cst_items_df'])

            # Flag para indicar se deve pular a comparação de 'icms_aliquota' e 'icms_aliquota_reduzida'
            skip_icms_comparison = False
            
            if icms_cst_df_value == icms_cst_items_df_value and icms_cst_df_value in [40, 41, 60]:
                skip_icms_comparison = True
            
            # Lista para armazenar os resultados da comparação
            comparison_results = []
            
            # Comparar todas as colunas, exceto 'icms_aliquota' e 'icms_aliquota_reduzida' se a flag for True
            for col in filtered_columns:
                if skip_icms_comparison and col in ['icms_aliquota', 'icms_aliquota_reduzida']:
                    continue  # Pular comparação dessas colunas
                
                # Verifica se há divergência na coluna
                col_df_value = row[f'{col}_df']
                col_items_df_value = row[f'{col}_items_df']
                col_mask = col_df_value != col_items_df_value
                
                # Atualiza a máscara de divergência
                divergence_mask.at[idx] = divergence_mask.at[idx] or col_mask                
                
                # Armazena o resultado da comparação
                comparison_results.append({
                    'column': col,
                    'df_value': col_df_value,
                    'items_df_value': col_items_df_value,
                    'divergence': col_mask
                })
                
                if col_mask:
                    # Adiciona o nome da coluna nas divergências para a linha
                    merged_df.at[idx, "divergent_columns_df"].append(col)
                    divergence_counts[col] += 1
                    
        except Exception as e:
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            result_integration = f'[{timestamp}] - Erro na comparação da linha {idx}: {e} \n'
            save_imported_logs(client_id, result_integration)
            problematic_columns.append(col) 
    
    # Converte listas para strings separadas por vírgulas e listas vazias para strings vazias
    merged_df["divergent_columns_df"] = merged_df["divergent_columns_df"].apply(lambda x: ', '.join(x) if x else '')

    # Cria um DataFrame com os itens que NÃO divergiram
    # com isso sera possivel atualizar o status dos itens que estao como 2
    df_items_not_divergent = merged_df[~divergence_mask]
    # 1. Extrair os códigos
    codes_to_update = df_items_not_divergent['code'].unique().tolist()
    # Contagem de itens a serem atualizados
    num_to_update = Item.objects.filter(
        code__in=codes_to_update, 
        status_item=2, 
        client_id=client_id
    ).count() 
    
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
    delete_result = delete_imported_items(client_id, codes_to_update)
    if delete_result and delete_result.get('status') == 'error':
        return delete_result
    
    # Inserindo os itens novos na tabela de importacao
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando novos itens \n'   
    # Inicializar a coluna com listas vazias
    new_items_df["divergent_columns"] = [[] for _ in range(len(new_items_df))]     
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

    try:
        insert_result = insert_new_items(client_id, df_items_divergent, 1)
    except Exception as e:
        print(f"Erro ao inserir itens divergentes: {e}")
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Erro ao gravar os itens divergentes: {e} \n'
        save_imported_logs(client_id, result_integration)        
        return {'message': f"Erro ao inserir itens divergentes: {e}", 'status': 'error'}    
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - FIM \n'  
    save_imported_logs(client_id, result_integration)         

    return {'message': message, 'status': 'success'}

