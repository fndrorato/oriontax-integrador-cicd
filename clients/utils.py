import pandas as pd
import openpyxl
import logging
import uuid
from datetime import datetime
from django.db import transaction
from items.models import ImportedItem, Item
from .models import Client, LogIntegration
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from decimal import Decimal
from notifications.models import Notification


logger = logging.getLogger(__name__)  # Obtenha um logger
User = get_user_model()

def create_notification(user, message, **kwargs):
    """
    Cria uma nova notificação com tratamento de erros
    
    Args:
        user: User instance or user ID
        message: Texto da mensagem (obrigatório)
        
    Kwargs:
        title: Título da notificação
        notification_type: Tipo da notificação (default: 'info')
        action_url: URL para ação
        reference: Referência interna
        icon: Classe do ícone
        
    Returns:
        Notification object
        
    Raises:
        ValueError: Se parâmetros inválidos forem fornecidos
    """
    # Validação básica
    if not message:
        raise ValueError("A mensagem da notificação é obrigatória")
    
    # Resolve o usuário
    if isinstance(user, int):
        try:
            user = User.objects.get(id=user)
        except User.DoesNotExist:
            raise ValueError("Usuário não encontrado")
    elif not isinstance(user, User):
        raise ValueError("O parâmetro 'user' deve ser uma instância de User ou um ID")
    
    # Valida o tipo de notificação
    valid_types = dict(Notification.NotificationType.choices).keys()
    notification_type = kwargs.get('notification_type', 'info')
    if notification_type not in valid_types:
        raise ValueError(f"Tipo de notificação inválido. Opções válidas: {', '.join(valid_types)}")
    
    # Cria a notificação
    try:
        return Notification.objects.create(
            user=user,
            message=message,
            title=kwargs.get('title'),
            notification_type=notification_type,
            action_url=kwargs.get('action_url'),
            reference=kwargs.get('reference'),
            icon=kwargs.get('icon', 'fa fa-bell')
        )
    except Exception as e:
        raise ValueError(f"Erro ao criar notificação: {str(e)}")

def update_client_data_send(client_id=None, method_integration=None):
    if client_id:
        try:
            current_time = timezone.now()
            client = Client.objects.get(id=client_id)
            client.last_date_send = current_time
            client.method_integration = method_integration
            client.save()
            print(f"Úlima data de envio atualizado com sucesso para o cliente {client.name}.")
        except Client.DoesNotExist:
            print(f"Cliente com ID {client_id} não encontrado.")
    else:
        print(f'Nenhum ID de cliente fornecido para atualização.')

def update_client_data_get(client_id=None, method_integration=None):
    if client_id:
        try:
            current_time = timezone.now()
            client = Client.objects.get(id=client_id)
            client.last_date_get = current_time
            client.method_integration = method_integration
            client.save()
            print(f"Úlima data de recebimento atualizado com sucesso para o cliente {client.name}.")
        except Client.DoesNotExist:
            print(f"Cliente com ID {client_id} não encontrado.")
    else:
        print(f'Nenhum ID de cliente fornecido para atualização.')

def generate_and_update_client_tokens(client_id=None):
    if client_id:
        try:
            client = Client.objects.get(id=client_id)
            client.token = uuid.uuid4()
            client.save()
            print(f"Token gerado e atualizado com sucesso para o cliente {client.name}.")
        except Client.DoesNotExist:
            print(f"Cliente com ID {client_id} não encontrado.")
    else:
        clients_without_token = Client.objects.filter(token__isnull=True)

        for client in clients_without_token:
            client.token = uuid.uuid4()
            client.save()

        print(f"{clients_without_token.count()} tokens gerados e atualizados com sucesso.")

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
    
def delete_imported_items(client_id, codes_to_delete):
    
    try:
        client_instance = Client.objects.get(id=client_id)

        # Deletar apenas os códigos presentes em codes_to_update
        ImportedItem.objects.filter(
            client=client_instance,
            code__in=codes_to_delete
        ).delete()

        print(f"Itens com códigos específicos do cliente ID {client_id} foram deletados com sucesso.")

    except Client.DoesNotExist as e:
        return {'message': f'Erro ao deletar itens: {e}', 'status': 'error'}

# def insert_new_items(client_id, df, status_id, batch_size=5000):
#     client_instance = Client.objects.get(id=client_id)
#     current_time = timezone.now()

#     for i in range(0, len(df), batch_size):
#         try:
#             with transaction.atomic():
#                 batch = df.iloc[i: i + batch_size]
#                 new_items_list = [
#                     ImportedItem(
#                         client=client_instance,
#                         code=row['code'],
#                         barcode=row['barcode'],
#                         description=row['description'],
#                         ncm=row['ncm'],
#                         cest=row['cest'],
#                         cfop=row['cfop'],
#                         icms_cst=row['icms_cst'],
#                         icms_aliquota=row['icms_aliquota'],
#                         icms_aliquota_reduzida=row['icms_aliquota_reduzida'],
#                         protege=row['protege'],
#                         cbenef=row['cbenef'],
#                         piscofins_cst=row['piscofins_cst'],
#                         pis_aliquota=row['pis_aliquota'],
#                         cofins_aliquota=row['cofins_aliquota'],
#                         naturezareceita=row['naturezareceita'],
#                         sequencial=row['sequencial'],
#                         estado_origem=row['estado_origem'],
#                         estado_destino=row['estado_destino'],
#                         divergent_columns=row['divergent_columns'],
#                         created_at=current_time,
#                         status_item=status_id
#                     )
#                     for _, row in batch.iterrows()
#                 ]   

#                 ImportedItem.objects.bulk_create(new_items_list)

#                 if status_id == 1:
#                     # Atualizar itens no modelo Item
#                     imported_items_dict = { (item.code, item.client_id): item for item in new_items_list }
#                     items_to_update = Item.objects.filter(
#                         client_id=client_id,
#                         code__in=[item.code for item in new_items_list]
#                     )
#                     for item in items_to_update:
#                         imported_item = imported_items_dict.get((item.code, item.client_id))
#                         if imported_item:
#                             if not item.sequencial:
#                                 item.sequencial = imported_item.sequencial
#                             if not item.estado_origem:
#                                 item.estado_origem = imported_item.estado_origem
#                             if not item.estado_destino:
#                                 item.estado_destino = imported_item.estado_destino                            
#                     Item.objects.bulk_update(items_to_update, ['sequencial', 'estado_origem', 'estado_destino'])

#                 print(f'Lote {i // batch_size + 1} de {len(df) // batch_size + 1} inserido e atualizado com sucesso')

#         except ValueError as ve:
#             logger.error(f"Erro ao converter valor para float: {ve}")
#             return {'message': f"Erro ao converter valor para float. Verifique os logs para mais detalhes.", 'status': 'error'}

#         except Exception as e:
#             logger.error(f"Erro ao inserir/atualizar lote (iniciando em índice {i}): {e}")
#             return {'message': f"Erro ao inserir/atualizar lote de itens. Verifique os logs para mais detalhes.", 'status': 'error'}

#     return {'message': 'Todos os itens foram inseridos e atualizados com sucesso', 'status': 'success'}


def insert_new_items(client_id, df, status_id, batch_size=5000):
    client_instance = Client.objects.get(id=client_id)
    current_time = timezone.now()

    for i in range(0, len(df), batch_size):
        try:
            with transaction.atomic():
                batch = df.iloc[i:i + batch_size]

                # Chaves únicas a considerar
                incoming_keys = set((row['code'], client_id) for _, row in batch.iterrows())

                # Buscar registros existentes
                existing_items = ImportedItem.objects.filter(
                    client_id=client_id,
                    code__in=[code for code, _ in incoming_keys]
                )
                existing_keys = set((item.code, item.client_id) for item in existing_items)

                items_to_create = []
                items_to_update = []

                for _, row in batch.iterrows():
                    key = (row['code'], client_id)
                    
                    if str(row['code']) == '784881':
                        print(row.to_dict())

                    item_data = {
                        'client': client_instance,
                        'code': row['code'],
                        'barcode': row['barcode'],
                        'description': row['description'],
                        'ncm': row['ncm'],
                        'cest': row['cest'],
                        'cfop': row['cfop'],
                        'icms_cst': row['icms_cst'],
                        'icms_aliquota': row['icms_aliquota'],
                        'icms_aliquota_reduzida': row['icms_aliquota_reduzida'],
                        'protege': row['protege'],
                        'cbenef': row['cbenef'],
                        'piscofins_cst': row['piscofins_cst'],
                        'pis_aliquota': row['pis_aliquota'],
                        'cofins_aliquota': row['cofins_aliquota'],
                        'naturezareceita': row['naturezareceita'],
                        'sequencial': row['sequencial'],
                        'estado_origem': row['estado_origem'],
                        'estado_destino': row['estado_destino'],
                        'divergent_columns': row['divergent_columns'],
                        'created_at': current_time,
                        'status_item': status_id
                    }

                    if key in existing_keys:
                        # Atualizar registro existente
                        item = next(e for e in existing_items if e.code == row['code'])
                        for field, value in item_data.items():
                            setattr(item, field, value)
                        items_to_update.append(item)
                    else:
                        items_to_create.append(ImportedItem(**item_data))

                if items_to_create:
                    ImportedItem.objects.bulk_create(items_to_create)

                if items_to_update:
                    ImportedItem.objects.bulk_update(
                        items_to_update,
                        fields=list(item_data.keys())
                    )

                # Atualizar campos do modelo Item se status_id == 1
                if status_id == 1:
                    all_processed_items = items_to_create + items_to_update
                    imported_items_dict = {
                        (item.code, item.client_id): item for item in all_processed_items
                    }

                    items_to_update_in_item_model = Item.objects.filter(
                        client_id=client_id,
                        code__in=[item.code for item in all_processed_items]
                    )

                    for item in items_to_update_in_item_model:
                        imported_item = imported_items_dict.get((item.code, item.client_id))
                        if imported_item:
                            if not item.sequencial:
                                item.sequencial = imported_item.sequencial
                            if not item.estado_origem:
                                item.estado_origem = imported_item.estado_origem
                            if not item.estado_destino:
                                item.estado_destino = imported_item.estado_destino

                    Item.objects.bulk_update(
                        items_to_update_in_item_model,
                        ['sequencial', 'estado_origem', 'estado_destino']
                    )

                print(f'Lote {i // batch_size + 1} de {len(df) // batch_size + 1} processado: '
                      f'{len(items_to_create)} criados, {len(items_to_update)} atualizados')

        except ValueError as ve:
            logger.error(f"Erro ao converter valor para float: {ve}")
            return {'message': f"Erro ao converter valor para float. Verifique os logs para mais detalhes.", 'status': 'error'}

        except Exception as e:
            logger.error(f"Erro ao inserir/atualizar lote (iniciando em índice {i}): {e}")
            return {'message': f"Erro ao inserir/atualizar lote de itens. Verifique os logs para mais detalhes.", 'status': 'error'}

    return {'message': 'Todos os itens foram inseridos e atualizados com sucesso', 'status': 'success'}

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
    items_df['naturezareceita'] = items_df['naturezareceita'].astype(int)
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
            
            # Imprime o resultado para a linha atual
            # print(f"Code: {code}")
            # for result in comparison_results:
            #     print(f"  Column: {result['column']}, DF Value: {result['df_value']}, Items DF Value: {result['items_df_value']}, Divergence: {result['divergence']}")
            # print(f"  Divergent Columns: {merged_df.at[idx, 'divergent_columns_df']}")
        
                    
        except Exception as e:
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            result_integration = f'[{timestamp}] - Erro na comparação da linha {idx}: {e} \n'
            save_imported_logs(client_id, result_integration)
            problematic_columns.append(col) 
    # for col in filtered_columns:
    #     try:
    #         if col in ['icms_aliquota', 'icms_aliquota_reduzida']:
    #             icms_cst_df_value = merged_df['icms_cst_df'].astype(int)  # Converter para inteiro
    #             icms_cst_items_df_value = merged_df['icms_cst_items_df'].astype(int)  # Converter para inteiro

    #             if (icms_cst_df_value == icms_cst_items_df_value).all():
    #                 print('icms_cst iguais')
    #                 if icms_cst_df_value.isin([40, 41, 60]).all():
    #                     continue
    #                 else:
    #                     print('nao esta na lista 40,41,60')

    #         col_mask = merged_df[f'{col}_df'] != merged_df[f'{col}_items_df']
    #         divergence_counts[col] = col_mask.sum()  # Conta as divergências na coluna
    #         divergence_mask |= col_mask       
    #         # Adiciona o nome da coluna nas linhas onde há divergência
    #         for idx in merged_df.index[col_mask]:
    #             merged_df.at[idx, "divergent_columns_df"].append(col)            
    #     except Exception as e:
    #         # print(f"Erro na comparação da coluna '{col}': {e}")
    #         timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    #         result_integration += f'[{timestamp}] - Erro na comparação da coluna \'{col}\': {e} \n'
    #         save_imported_logs(client_id, result_integration)
    #         problematic_columns.append(col)

    # Converte listas para strings separadas por vírgulas e listas vazias para strings vazias
    merged_df["divergent_columns_df"] = merged_df["divergent_columns_df"].apply(lambda x: ', '.join(x) if x else '')

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
    # codigos_para_atulizar = Item.objects.filter(
    #     code__in=codes_to_update, 
    #     status_item=2, 
    #     client_id=client_id
    # ).values('code', 'description').order_by('description')  
    # print(codigos_para_atulizar) 
    # return 
    
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
    delete_result = delete_imported_items(client_id, codes_to_update)
    if delete_result and delete_result.get('status') == 'error':
        return delete_result
    
    print('14-inserindo os novos itens')
    print(message)
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
        Column: piscofins_cst, DF Value: 1.0, Items DF Value: 01, Divergence: True
        Column: cfop, DF Value: 5102.0, Items DF Value: 5102, Divergence: True
        Column: icms_cst, DF Value: 20.0, Items DF Value: 20, Divergence: True        
    """
    print('1-Entrou no validate')
    if initial_log is None:
        result_integration = ''
    else: 
        result_integration = initial_log
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')    
    result_integration += f'[{timestamp}] - Iniciando a validação\n'
    client_instance = Client.objects.get(id=client_id)
    unnecessary_fields = client_instance.erp.unnecessary_fields
    # Excluindo os items que estão marcados como INSUMOS OU IMOBILIZADOS
    filtered_df = items_df[items_df['type_product'] != 'Revenda']
    df_filtered = df[~df['code'].isin(filtered_df['code'])]
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
    
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    result_integration += f'[{timestamp}] - Dados Recebidos \n'
    
    unique_values = df['protege'].unique()
    df['protege'] = df['protege'].fillna(0)
    unique_values = df['protege'].unique()
    
    df['protege'] = df['protege'].apply(lambda x: int(x))
    unique_values = df['protege'].unique()
    
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
    
    df['naturezareceita'] = df['naturezareceita'].fillna(0)
    # ANTES PASSAVA TUDO COMO INT - AGORA TESTE PARA VALIDAR SE FUNCIONA COM FLOAT
    df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float).astype(int)
    # df['icms_aliquota'] = pd.to_numeric(df['icms_aliquota'], errors='coerce').fillna(0).astype(float)
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

    print('7-Encontrando os novos produtos... ')   
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
        merged_df[f'{col}_items_df'] = merged_df[f'{col}_items_df'].fillna('').astype(str).infer_objects(copy=False)

    divergence_mask = pd.Series(False, index=merged_df.index)  # Inicializa a máscara como False
    problematic_columns = []
    divergence_counts = {col: 0 for col in expected_columns}

    columns_not_compare = ['sequencial', 'estado_origem', 'estado_destino']
    # Mesclando as duas listas
    columns_not_compare = columns_not_compare + unnecessary_fields
  
    # Filtrar as colunas esperadas para remover as colunas que não devem ser comparadas
    filtered_columns = [col for col in expected_columns if col not in columns_not_compare]    
    # Criar uma nova coluna vazia para armazenar as colunas divergentes
    merged_df["divergent_columns_df"] = [[] for _ in range(len(merged_df))] 
    
    # remove o .0 de naturezareceita_df, ou seja, o que vem do cliente    
    merged_df['naturezareceita_df'] = merged_df['naturezareceita_df'].replace(r'\.0$', '', regex=True)
    # Filtra os valores que têm apenas 1 dígito e são diferentes de 0
    merged_df['naturezareceita_df'] = merged_df['naturezareceita_df'].apply(
        lambda x: str(int(x)).zfill(3) if len(str(int(x))) == 1 and int(x) != 0 else str(int(x))
    )
    
    # Filtrar os dados
    print('merged df')
    print(merged_df[merged_df['code'] == '784881'])
    test_df = merged_df[merged_df['code'] == '784881'][['code', 'naturezareceita_df', 'naturezareceita_items_df']]

    # Verificar se há pelo menos uma linha antes de acessar
    if not test_df.empty:
        # Pegar os valores da primeira linha
        valor_df = test_df.iloc[0]['naturezareceita_df']
        valor_items_df = test_df.iloc[0]['naturezareceita_items_df']
        
        # Comparação direta
        if valor_df == valor_items_df:
            print('São iguais')
        else:
            print('São diferentes')
    else:
        print('Nenhum resultado encontrado para code = 2674')
    
    print(test_df.head())
    # raise SystemExit
    
    
    # Itera sobre as linhas do DataFrame
    for idx, row in merged_df.iterrows():
        try:
            # Recupera o código para imprimir
            code = row.get('code', 'N/A')
            
            # Lista para armazenar os resultados da comparação
            comparison_results = []
            
            # Comparar todas as colunas, exceto 'icms_aliquota' e 'icms_aliquota_reduzida' se a flag for True
            for col in filtered_columns:
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
    print('XX-items NAO divergentes')
    df_items_not_divergent = merged_df[~divergence_mask]
    # 1. Extrair os códigos
    print('DF NOT DIVERGENT')
    print(df_items_not_divergent[df_items_not_divergent['code'] == '784881'])
    codes_to_update = df_items_not_divergent['code'].unique().tolist()
    # Contagem de itens a serem atualizados
    num_to_update = Item.objects.filter(
        code__in=codes_to_update, 
        status_item=2, 
        client_id=client_id
    ).count()

    if '784881' in codes_to_update:
        print("Código 784881 está presente em codes_to_update")
    else:
        print("Código 784881 **NÃO** está presente em codes_to_update")


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
    delete_result = delete_imported_items(client_id, codes_to_update)
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

    print(message)
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

    # Converter a coluna 'cfop' para numérico, lidando com erros de conversão
    df_items_divergent['cfop'] = pd.to_numeric(df_items_divergent['cfop'], errors='coerce')

    # Arredondar os valores numéricos
    df_items_divergent['cfop'] = df_items_divergent['cfop'].round()

    # Converter a coluna 'cfop' para Int64, permitindo valores nulos
    df_items_divergent['cfop'] = df_items_divergent['cfop'].astype('Int64')

    # Exibir os valores únicos convertidos
    df_items_divergent['piscofins_cst'] = df_items_divergent['piscofins_cst'].astype(float).astype('Int64')
    df_items_divergent['icms_cst'] = df_items_divergent['icms_cst'].astype(float).astype('Int64')
    
    # Tratando os valores vazios da natureza da receita
    # Substitui valores vazios ('') por None no campo 'naturezareceita'
    df_items_divergent['naturezareceita'] = df_items_divergent['naturezareceita'].replace('', None)
    # # Remover possíveis strings e converter corretamente
    # df_items_divergent['naturezareceita'] = (
    #     pd.to_numeric(df_items_divergent['naturezareceita'], errors='coerce')
    #     .astype('Int64')  # Mantém valores como inteiros sem erro em NaN
    # )        
    print('15-inserindo os itens com divergencia')  
    print(df_items_divergent[df_items_divergent['code'] == '784881'])

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


