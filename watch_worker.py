# watch_worker.py
import os, time, shutil, logging
import sys
import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ---- Django setup ----
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")  # <<< AJUSTE para seu projeto
import django
django.setup()
import json
from api.serializers import ItemImportedModelSerializer
from clients.utils import validateSelect, save_imported_logs, update_client_data_get
from datetime import datetime
from django.conf import settings
from django.db.models import F
from items.models import Item



BASE = settings.API_JOBS_DIR
INBOX = settings.API_JOBS_INBOX
PROC  = settings.API_JOBS_PROCESSING
DONE  = settings.API_JOBS_DONE
ERR   = settings.API_JOBS_ERROR
for d in (INBOX, PROC, DONE, ERR): os.makedirs(d, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def wait_file_stable(path, checks=3, interval=0.5):
    """Espera o arquivo não crescer por N checks consecutivos."""
    last = -1
    stable = 0
    for _ in range(120):  # ~60s
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            return False
        if size == last:
            stable += 1
            if stable >= checks:
                return True
        else:
            stable = 0
            last = size
        time.sleep(interval)
    return False

def process_job(file_base):
    json_path    = os.path.join(INBOX, f"{file_base}.json")
    items_path   = os.path.join(INBOX, f"{file_base}_items.csv")
    payload_path = os.path.join(INBOX, f"{file_base}_payload.csv")

    # aguarda estabilidade
    for p in (json_path, items_path, payload_path):
        if not wait_file_stable(p):
            raise RuntimeError(f"Arquivo não estabilizou: {p}")

    # move trio para uma pasta de processing (lock simples)
    proc_dir = os.path.join(PROC, file_base)
    os.makedirs(proc_dir, exist_ok=True)
    j2 = shutil.move(json_path,    os.path.join(proc_dir, os.path.basename(json_path)))
    i2 = shutil.move(items_path,   os.path.join(proc_dir, os.path.basename(items_path)))
    p2 = shutil.move(payload_path, os.path.join(proc_dir, os.path.basename(payload_path)))

    # extrai client_id do prefixo do file_base: {clientid}_{timestamp}
    client_id = int(file_base.split("_", 1)[0])
    start_msg = f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] - Job {file_base} iniciou no watcher\n"
    save_imported_logs(client_id, start_msg)

    try:
        with open(j2, "r", encoding="utf-8") as f:
            data_json = json.load(f)        
        # Mapeia os campos do JSON recebido para os campos esperados pelo serializer
        def rename_fields(data):
            return {
                'code': data.get('codigo'),
                'barcode': data.get('codigo_barras'),
                'description': data.get('descricao'),
                'ncm': data.get('ncm'),
                'cest': data.get('cest'),
                'cfop': data.get('cfop'),
                'icms_cst': data.get('icms_cst'),
                'icms_aliquota': data.get('icms_aliquota'),
                'icms_aliquota_reduzida': data.get('icms_aliquota_reduzida'),
                'cbenef': data.get('cbenef'),
                'protege': data.get('protege'),
                'piscofins_cst': data.get('pis_cst'),
                'pis_aliquota': data.get('pis_aliquota'),
                'cofins_aliquota': data.get('cofins_aliquota'),
                'naturezareceita': data.get('natureza_receita'),
                'percentual_redbcde': data.get('percentual_redbcde'),
                'cst_ibs_cbs': data.get('cst_ibs_cbs', ''),
                'c_class_trib': data.get('c_class_trib', ''),
                'aliquota_ibs': data.get('aliquota_ibs', ''),
                'aliquota_cbs': data.get('aliquota_cbs', ''),
                'p_red_aliq_ibs': data.get('p_red_aliq_ibs', ''),
                'p_red_aliq_cbs': data.get('p_red_aliq_cbs', ''),
            }

        # Renomeia os campos em todos os itens da lista
        renamed_data = [rename_fields(item) for item in data_json]        
        
        # Serializa os dados recebidos
        serializer = ItemImportedModelSerializer(data=renamed_data, many=True)
          
        # Transforma os dados validados em um dataframe
        if serializer.is_valid():
            df_json_recebido = pd.DataFrame(serializer.validated_data)          
            
            df_json_recebido['sequencial'] = 0
            df_json_recebido['estado_origem'] = ''
            df_json_recebido['estado_destino'] = ''            
            
            # Pega todos os itens relacionados a esse cliente
            items_queryset = Item.objects.filter(client=client_id).values(
                'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst', 
                'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef', 
                'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'type_product',
                'cst_ibs_cbs', 'c_class_trib', 'aliquota_ibs', 'aliquota_cbs', 
                'p_red_aliq_ibs', 'p_red_aliq_cbs',                   
                naturezareceita_code=F('naturezareceita__code')
            )        
            if items_queryset:
                items_df = pd.DataFrame(list(items_queryset.values()))  
                items_df = items_df.astype({'icms_aliquota_reduzida': 'float'})

                # Opcional: se quiser preencher com zeros inicialmente
                items_df['icms_aliquota_reduzida'] = items_df['icms_aliquota_reduzida'].fillna(0).round(2)                           
            else: 
                # Lista das colunas desejadas
                colunas_desejadas = [
                    'code', 'barcode', 'description', 'ncm', 'cest', 'cfop', 'icms_cst',
                    'icms_aliquota', 'icms_aliquota_reduzida', 'protege', 'cbenef',
                    'piscofins_cst', 'pis_aliquota', 'cofins_aliquota', 'naturezareceita_code',
                    'id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 
                    'is_pending_sync', 'history', 'other_information', 'type_product',
                    'cst_ibs_cbs', 'c_class_trib', 'aliquota_ibs', 'aliquota_cbs', 
                    'p_red_aliq_ibs', 'p_red_aliq_cbs'                    
                ]

                # Criar um DataFrame vazio com as colunas desejadas
                items_df = pd.DataFrame(columns=colunas_desejadas)
                            
            items_df.drop(columns=['id', 'client_id', 'user_updated_id', 'user_created_id', 'created_at', 'is_pending_sync', 'history', 'other_information'], inplace=True)            

            validateSelect(client_id, items_df, df_json_recebido, start_msg)

            update_client_data_get(client_id, "1")
            dest = os.path.join(DONE, file_base)
            if os.path.exists(dest): shutil.rmtree(dest)
            shutil.move(proc_dir, dest)
            save_imported_logs(client_id, start_msg + f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] - Concluído com sucesso\n")
            logging.info("Job %s finalizado.", file_base)            
        else:
            save_imported_logs(client_id, start_msg + f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] - Erro: {serializer.errors}\n")
            logging.exception("Job %s falhou: %s", file_base, e)            
            logging.error(f"Dados JSON inválidos: {serializer.errors}")
            raise ValueError(f"Dados JSON inválidos: {serializer.errors}")

    except Exception as e:
        dest = os.path.join(ERR, file_base)
        if os.path.exists(dest): shutil.rmtree(dest)
        shutil.move(proc_dir, dest)
        save_imported_logs(client_id, start_msg + f"[{time.strftime('%d/%m/%Y %H:%M:%S')}] - Erro: {e}\n")
        logging.exception("Job %s falhou: %s", file_base, e)

class InboxHandler(FileSystemEventHandler):
    def _maybe_process(self, fullpath):
        # fullpath: caminho do arquivo que gerou o evento
        name = os.path.basename(fullpath)
        # Dispare SOMENTE quando o payload final existir (gatilho)
        if not name.endswith("_payload.csv"):
            return
        file_base = name[:-len("_payload.csv")]
        needed = [f"{file_base}.json", f"{file_base}_items.csv"]
        if all(os.path.exists(os.path.join(INBOX, n)) for n in needed):
            try:
                logging.info("Gatilho detectado para %s", file_base)
                process_job(file_base)
            except Exception:
                logging.exception("Falha ao processar %s", file_base)

    # quando o arquivo é CRIADO (ex.: se você gerasse direto sem .tmp)
    def on_created(self, event):
        if event.is_directory:
            return
        logging.debug("on_created: %s", event.src_path)
        self._maybe_process(event.src_path)

    # quando o arquivo é RENOMEADO/MOVIDO (ex.: .tmp -> final)
    def on_moved(self, event):
        if event.is_directory:
            return
        logging.debug("on_moved: %s -> %s", event.src_path, event.dest_path)
        # o rename final interessa (dest_path)
        self._maybe_process(event.dest_path)

    # opcional: algumas plataformas disparam modified em writes/renames
    def on_modified(self, event):
        if event.is_directory:
            return
        logging.debug("on_modified: %s", event.src_path)
        self._maybe_process(event.src_path)

def periodic_sweep():
    """
    Varredura de segurança: a cada X segundos procura trios completos esquecidos em INBOX.
    Evita perder jobs se o evento não foi disparado por algum motivo.
    """
    try:
        filenames = set(os.listdir(INBOX))
        # pegue apenas bases que tenham *_payload.csv
        bases = [fn[:-len("_payload.csv")] for fn in filenames if fn.endswith("_payload.csv")]
        for base in bases:
            if (f"{base}.json" in filenames) and (f"{base}_items.csv" in filenames):
                logging.info("Periodic sweep encontrou trio completo: %s", base)
                try:
                    print(f"Periodic sweep processando {base}...")
                    process_job(base)
                except Exception:
                    logging.exception("Falha no periodic sweep para %s", base)
    except Exception:
        logging.exception("Erro no periodic_sweep")

def main():
    print('main() iniciado')
    obs = Observer()
    handler = InboxHandler()
    # use str(INBOX) caso INBOX seja Path
    obs.schedule(handler, str(INBOX), recursive=False)
    obs.start()
    print("Watcher ativo em", INBOX)
    logging.info("Watcher ativo em %s", INBOX)
    try:
        while True:
            # roda a varredura a cada 10s (ajuste se quiser)
            periodic_sweep()
            time.sleep(10)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()

if __name__ == "__main__":
    main()
