import pandas as pd
import openpyxl
from datetime import datetime
from items.models import ImportedItem
from .models import Client, LogIntegration
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

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
    
def insert_new_items(client_id, df, status_id):
    client_instance = Client.objects.get(id=client_id)  # Obtenha a instância do cliente correta

    # Converter as colunas para os tipos desejados
    df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float).astype(int)
    df['icms_aliquota_reduzida'] = pd.to_numeric(df['icms_aliquota_reduzida'], errors='coerce').fillna(0).astype(float).astype(int)
    df['pis_aliquota'] = pd.to_numeric(df['pis_aliquota'], errors='coerce').fillna(0.0).astype(float)
    df['cofins_aliquota'] = pd.to_numeric(df['cofins_aliquota'], errors='coerce').fillna(0.0).astype(float)
    df['protege'] = pd.to_numeric(df['protege'], errors='coerce').fillna(0).astype(int)

    # Crie uma lista de instâncias do modelo ImportedItem
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
            status_item=status_id  # Supondo que todos os novos itens sejam "Produto Novo"
        )
        for index, row in df.iterrows()
    ]

    # Inserir todos os itens de uma vez usando bulk_create
    try:
        ImportedItem.objects.bulk_create(new_items_list)
    except Exception as e:
        print(f'Erro ao inserir itens: {e}')
        return {'message': f'Erro ao inserir itens: {e}', 'status': 'error'} 

    return {'message': 'Itens inseridos com sucesso', 'status': 'success'}
  

def validateSysmo(client_id, items_df, df):
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
    result_integration = ''
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Dados Recebidos para o Sistema Sysmo \n'
    
    # Eliminar as colunas indesejadas
    df = df.drop(columns=['cd_sequencial', 'tx_estadoorigem', 'tx_estadodestino', 'nr_cst_cofins'])
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
        'nr_naturezareceita': 'naturezareceita'
    }) 
    print('3-Rename colunas')
    
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

    print('6-Encontrando os novos produtos... ')
    ################################
    # 1- Encontrar os novos produtos
    # Realizar a junção para encontrar os itens presentes em df mas não em items_df
    merged_df = df.merge(items_df[['code']], on='code', how='left', indicator=True)
    # Filtrar os itens que estão em df mas não em items_df
    new_items_df = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])
    
    print('7-Limpando os novos produtos ')
    ## limpando os dados
    new_items_df['barcode'] = new_items_df['barcode'].fillna('')  
    new_items_df['cest'] = new_items_df['cest'].fillna('') 
    new_items_df['cbenef'] = new_items_df['cbenef'].fillna('') 
     
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - executado função dos novos itens. Foram encontrados {len(new_items_df)} novos produtos \n'
    print('8-executado função dos novos itens. Foram encontrados:', len(new_items_df))
    ################################
    # 2- Encontrar os itens divergentes
    # Remover os itens encontrados em new_items_df do dataframe original df
    df = df[df['code'].isin(new_items_df['code']) == False]
    # Preenchendo com 0 a esquerda para o código do piscofins cst
    df['piscofins_cst'] = df['piscofins_cst'].astype(str).str.zfill(2)
    # Realizar a junção para verificar todos os itens e identificar divergências
    merged_df = df.merge(items_df, on='code', suffixes=('_df', '_items_df'))
    # Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)
    print('9-Verificar se as colunas renomeadas existem após a junção (MOVIDO PARA DEPOIS DA JUNÇÃO)')
    missing_columns = []
    for col in expected_columns:
        if f"{col}_df" not in merged_df.columns or f"{col}_items_df" not in merged_df.columns:
            missing_columns.append(col)
    print('10-verificando colunas ausentes')
    if missing_columns:
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        result_integration += f'[{timestamp}] - Colunas ausentes na importação do cliente: {missing_columns} \n'
        save_imported_logs(client_id, result_integration)
        raise ValueError(f"Colunas ausentes no DataFrame merged_df: {missing_columns}")

    print('11-comparando as colunas- gerando _df e _items_df')
    # Comparar as colunas
    # Lidar com valores nulos e tipos de dados diferentes
    for col in expected_columns:
        # Preencher valores nulos com strings vazias
        merged_df[f'{col}_df'] = merged_df[f'{col}_df'].fillna('').astype(str)
        merged_df[f'{col}_items_df'] = merged_df[f'{col}_items_df'].fillna('').astype(str)

    divergence_mask = pd.Series(False, index=merged_df.index)  # Inicializa a máscara como False
    problematic_columns = []
    divergence_counts = {col: 0 for col in expected_columns}

    for col in expected_columns:
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
    print('12-montando o message')
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
    print(result_integration) 
    #############################################
    ## 3 - GRAVANDO NA TABELA DE ITENS IMPORTADOS
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Deletando itens importados antigos \n'        
    delete_result = delete_imported_items(client_id)
    if delete_result and delete_result.get('status') == 'error':
        return delete_result
    
    # Inserindo os itens novos na tabela de importacao
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Gravando novos itens \n'   
    print(result_integration)          
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
    
    print(result_integration) 
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - FIM \n'  
    save_imported_logs(client_id, result_integration)         

    return {'message': message, 'status': 'success'}
