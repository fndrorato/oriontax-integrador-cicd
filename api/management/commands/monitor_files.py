import os
import sys
import time
import zipfile
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sales.models import SalesCab, SalesDet, FileProcessingLog
from api.models import FileMonitorStatus  
from django.utils import timezone

# Define o diretório de uploads de forma absoluta
UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads/zips/"))

class ZipFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Verifica se o arquivo é um arquivo ZIP
        if event.is_directory or not event.src_path.endswith('.zip'):
            return
        
        print(f"Arquivo ZIP detectado: {event.src_path}")
        self.process_zip_file(event.src_path)
        
    def save_log_file_processing(self, file_name, message, success):
        log_entry = FileProcessingLog(
            csv_file_name=file_name,
            log=message,
            resultado=success
        )
        log_entry.save()        

    def process_zip_file(self, zip_path):
        # Extrai o arquivo ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(UPLOADS_DIR)
            print(f"Arquivo ZIP extraído: {zip_path}")

        # Lê os arquivos CSV extraídos
        for extracted_file in os.listdir(UPLOADS_DIR):
            if extracted_file.endswith('.csv'):
                csv_path = os.path.join(UPLOADS_DIR, extracted_file)
                
                # Processa o arquivo CSV e verifica o resultado
                if self.process_csv_file(csv_path, extracted_file):
                    # Se o processamento foi bem-sucedido, exclui o arquivo CSV
                    os.remove(csv_path)
                    print(f"Arquivo CSV deletado: {csv_path}")

        # Se o processamento de pelo menos um CSV foi bem-sucedido, exclui o ZIP
        os.remove(zip_path)
        print(f"Arquivo ZIP deletado: {zip_path}")

    def process_csv_file(self, csv_path, csv_file):
        # Verifica se o arquivo CSV existe
        if not os.path.isfile(csv_path):
            print(f"O arquivo {csv_path} não foi encontrado.")
            return
        
        # Lê o arquivo CSV usando pandas
        try:
            df = pd.read_csv(csv_path)
            print(f"Arquivo CSV lido com sucesso: {csv_path}")
            # Convertendo as colunas para string
            df['nNF'] = df['nNF'].astype(str)
            df['serie'] = df['serie'].astype(str)
            df['CNPJ'] = df['CNPJ'].astype(str)   
            
            ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            log = f'[{ts}] - Iniciando o processamento do arquivo: {csv_file} \n'
            
            # Seleciona as colunas que correspondem ao modelo SalesCab
            df_cab = df[['CNPJ', 'xNome', 'xFant', 'nNF', 'serie', 'tpNF', 'cUF', 'cNF', 'natOp', 'mod', 'cMunFG', 'tpAmb', 'dhEmi', 'IE', 'CRT']]

            # Remove duplicatas para evitar registros repetidos
            df_cab = df_cab.drop_duplicates()
            
            # Obtenha as combinações únicas de CNPJ, nNF, serie e tpNF do DataFrame
            unique_keys = df_cab[['CNPJ', 'nNF', 'serie', 'tpNF']].drop_duplicates()

            # Converta os valores únicos para uma lista de tuplas
            unique_keys_tuples = list(unique_keys.itertuples(index=False, name=None))

            # Consulte o banco para verificar quais combinações já existem
            existing_sales = SalesCab.objects.filter(
                CNPJ__in=[key[0] for key in unique_keys_tuples],
                nNF__in=[key[1] for key in unique_keys_tuples],
                serie__in=[key[2] for key in unique_keys_tuples],
                tpNF__in=[key[3] for key in unique_keys_tuples]
            ).values_list('CNPJ', 'nNF', 'serie', 'tpNF')  

            # Converte para DataFrame para facilitar a comparação
            existing_sales_set = set(existing_sales)        
            
            # Filtre o DataFrame para remover as combinações que já existem 
            df_cab = df_cab[~df_cab[['CNPJ', 'nNF', 'serie', 'tpNF']].apply(tuple, axis=1).isin(existing_sales_set)]
            
            # Converte o campo `dhEmi` para o formato datetime, se necessário
            df_cab['dhEmi'] = pd.to_datetime(df_cab['dhEmi'], errors='coerce')
            
            # Cria uma lista de instâncias de SalesCab para o bulk_create
            sales_cab_instances = [
                SalesCab(
                    CNPJ=row['CNPJ'],
                    xNome=row['xNome'],
                    xFant=row['xFant'],
                    nNF=row['nNF'],
                    serie=row['serie'],
                    tpNF=row['tpNF'],
                    cUF=row['cUF'],
                    cNF=row['cNF'],
                    natOp=row['natOp'],
                    mod=row['mod'],
                    cMunFG=row['cMunFG'],
                    tpAmb=row['tpAmb'],
                    dhEmi=row['dhEmi'] or timezone.now(),  # Use a data atual caso dhEmi esteja nulo
                    IE=row['IE'],
                    CRT=row['CRT'],
                )
                for _, row in df_cab.iterrows()
            ]

            # Salva os dados em massa no banco de dados, ignorando conflitos de chave única       
            try:
                # Insere os registros de SalesDet no banco
                SalesCab.objects.bulk_create(sales_cab_instances) 
                ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                log += f'[{ts}] - Dados registrados com sucesso no SalesCab. Total de registros: {len(df_cab)}  \n'
            except Exception as e:
                print("Erro ao inserir registros no banco SalesCab:", e)
                ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                log += f'[{ts}] - Erro ao inserir registros no banco SalesCab: {e}  \n'
                self.save_log_file_processing(csv_file, log, False)
                return False    
            
            # Recupera os registros recém-inseridos
            sales_cab_records = SalesCab.objects.filter(
                CNPJ__in=df_cab['CNPJ'].unique(),
                nNF__in=df_cab['nNF'].unique(),
                serie__in=df_cab['serie'].unique(),
                tpNF__in=df_cab['tpNF'].unique()
            )   
            
            # Verifica se o total de registros é igual a 0
            if sales_cab_records.count() == 0:
                ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                log += f'[{ts}] - Nenhum registro encontrado em SalesCab para os dados fornecidos.\n'
                self.save_log_file_processing(csv_file, log, False)
                print("Nenhum registro encontrado. O programa será encerrado.")
                return False            
            
            # Converte os registros do QuerySet em um DataFrame de mapeamento
            sales_cab_map = pd.DataFrame(list(sales_cab_records.values('id', 'CNPJ', 'nNF', 'serie', 'tpNF')))
            
            df_det = df[
                ['CNPJ', 'nNF', 'serie', 'tpNF', 'prod_cProd', 'prod_cEAN', 'prod_xProd', 'prod_NCM', 'prod_CEST', 'prod_cBenef',
                'prod_CFOP', 'prod_uCom', 'prod_qCom', 'prod_vUnCom', 'prod_vProd', 'prod_cEANTrib', 'prod_uTrib', 'prod_qTrib',
                'prod_vUnTrib', 'prod_indTot', 'prod_NumItem', 'ICMS_orig', 'ICMS_CST', 'PIS_CST', 'PIS_vBC', 'PIS_pPIS', 'PIS_vPIS',
                'COFINS_CST', 'COFINS_vBC', 'COFINS_pCOFINS', 'COFINS_vCOFINS', 'ICMS_modBC', 'ICMS_vBC', 'ICMS_pICMS', 'ICMS_vICMS',
                'ICMS_pRedBC']
            ]      
            
            # Supondo que df_det seja o DataFrame de detalhes
            df_det = df_det.merge(
                sales_cab_map,
                on=['CNPJ', 'nNF', 'serie', 'tpNF'],
                how='left'
            )

            # Renomeie a coluna 'id' para 'sales_cab_id' (ou o campo do FK)
            df_det = df_det.rename(columns={'id': 'sales_cab_id'})
            
            df_det = df_det.dropna(subset=['sales_cab_id'])
            
            # Substitui os valores NaN por 0 (ou outro valor padrão, se preferir)
            df_det["ICMS_modBC"] = df_det["ICMS_modBC"].fillna(0).astype(float)
            df_det["ICMS_pRedBC"] = df_det["ICMS_pRedBC"].fillna(0).astype(float)
            df_det["ICMS_vICMS"] = df_det["ICMS_vICMS"].fillna(0).astype(float)
            df_det["ICMS_pICMS"] = df_det["ICMS_vICMS"].fillna(0).astype(float)
            df_det["ICMS_vBC"] = df_det["ICMS_vBC"].fillna(0).astype(float)
            
            df_det["prod_cBenef"] = df_det["prod_cBenef"].fillna('')
            
            
            df_det["PIS_CST"] = df_det["PIS_CST"].fillna(0).astype(int)
            df_det["PIS_vBC"] = df_det["PIS_vBC"].fillna(0).astype(float)
            df_det["PIS_pPIS"] = df_det["PIS_pPIS"].fillna(0).astype(float)
            df_det["PIS_vPIS"] = df_det["PIS_vPIS"].fillna(0).astype(float)
            
            df_det["COFINS_CST"] = df_det["COFINS_CST"].fillna(0).astype(int)
            df_det["COFINS_vBC"] = df_det["COFINS_vBC"].fillna(0).astype(float)
            df_det["COFINS_pCOFINS"] = df_det["COFINS_pCOFINS"].fillna(0).astype(float)
            df_det["COFINS_vCOFINS"] = df_det["COFINS_vCOFINS"].fillna(0).astype(float)        
                    

            # # Filtra o DataFrame para encontrar registros onde PIS_CST é NaN
            # filtered_df = df_det[df_det['PIS_CST'].isna()]

            # # Verifica se há algum registro filtrado e imprime todos os campos do primeiro registro
            # if not filtered_df.empty:
            #     first_record = filtered_df.iloc[0]  # Acessa o primeiro registro
            #     print("Registro com PIS_CST NaN:")
            #     print(first_record)
            # else:
            #     print("Nenhum registro encontrado com PIS_CST NaN.")

            # Cria uma lista de instâncias de SalesDet para o bulk_create
            sales_det_instances = [
                SalesDet(
                    sales_cab_id=row['sales_cab_id'],  # usa o ID de SalesCab como FK
                    prod_NumItem=row['prod_NumItem'],
                    cProd=row['prod_cProd'],
                    cEAN=row['prod_cEAN'],
                    xProd=row['prod_xProd'],
                    NCM=row['prod_NCM'],
                    CEST=row['prod_CEST'],
                    CFOP=row['prod_CFOP'],
                    uCom=row['prod_uCom'],
                    qCom=row['prod_qCom'],
                    vUnCom=row['prod_vUnCom'],
                    vProd=row['prod_vProd'],
                    cEANTrib=row['prod_cEANTrib'],
                    uTrib=row['prod_uTrib'],
                    qTrib=row['prod_qTrib'],
                    vUnTrib=row['prod_vUnTrib'],
                    indTot=row['prod_indTot'],
                    ICMS_orig=row['ICMS_orig'],
                    ICMS_CST=row['ICMS_CST'],
                    ICMS_modBC=row['ICMS_modBC'],
                    ICMS_vBC=row['ICMS_vBC'],
                    ICMS_pICMS=row['ICMS_pICMS'],
                    ICMS_vICMS=row['ICMS_vICMS'],
                    PIS_CST=row['PIS_CST'],
                    PIS_vBC=row['PIS_vBC'],
                    PIS_pPIS=row['PIS_pPIS'],
                    PIS_vPIS=row['PIS_vPIS'],
                    COFINS_CST=row['COFINS_CST'],
                    COFINS_vBC=row['COFINS_vBC'],
                    COFINS_pCOFINS=row['COFINS_pCOFINS'],
                    COFINS_vCOFINS=row['COFINS_vCOFINS'],
                    prod_cBenef=row['prod_cBenef'],
                    ICMS_pRedBC=row['ICMS_pRedBC'],
                )
                for _, row in df_det.iterrows()
            ]
            
            # for i, instance in enumerate(sales_det_instances):
            #     try:
            #         instance.save()
            #     except Exception as e:
            #         print(f"Erro ao salvar a instância na linha {i+1}: {e}")
            #         print("Dados da instância com erro:", instance.__dict__)
            #         break
            

            try:
                # Insere os registros de SalesDet no banco
                SalesDet.objects.bulk_create(sales_det_instances)
                ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                log += f'[{ts}] - Dados registrados com sucesso no SalesDet. Total de registros: {len(df_det)}  \n'                
            except Exception as e:
                print("Erro ao inserir registros no banco SalesDet:", e)
                ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                log += f'[{ts}] - Erro ao inserir registros no banco SalesDet: {e}  \n'
                self.save_log_file_processing(csv_file, log, False)
                return False
            
        except Exception as e:
            print(f"Erro ao ler o arquivo CSV: {e}")
            return False

        log += f'[{ts}] - Registros do arquivo {csv_file} gravados com sucesso  \n'
        self.save_log_file_processing(csv_file, log, True) 
        
        return True       


class Command(BaseCommand):
    help = 'Monitora a pasta de uploads para novos arquivos ZIP'

    def handle(self, *args, **kwargs):
        print("Iniciando monitoramento de arquivos...")
        
        # Atualiza o status para "em execução"
        FileMonitorStatus.objects.update_or_create(
            pk=1,
            defaults={'is_running': True, 'last_checked': timezone.now()}
        )    
        
        event_handler = ZipFileHandler()
        observer = Observer()
        observer.schedule(event_handler, UPLOADS_DIR, recursive=False)
        observer.start()
        
        try:
            while True:
                # Atualiza o status periodicamente
                FileMonitorStatus.objects.update(
                    is_running=True,
                    last_checked=timezone.now()
                )            
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            # Define o status como "não está em execução" ao encerrar
            FileMonitorStatus.objects.update(is_running=False)
            print("Monitoramento encerrado.")
        
        observer.join()
