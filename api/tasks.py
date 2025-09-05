# api/tasks.py
import pandas as pd
from huey.contrib.djhuey import task
from django.utils import timezone
from clients.utils import validateSelect, save_imported_logs, update_client_data_get

@task()  # executa em background
def process_import_job(client_id, items_csv_path, df_json_csv_path, initial_log, json_raw_path):
    now = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
    save_imported_logs(client_id, initial_log + f"[{now}] - Iniciando processamento em background\n")

    try:
        items_df = pd.read_csv(items_csv_path, dtype=str).fillna('')
        if 'icms_aliquota_reduzida' in items_df.columns:
            items_df['icms_aliquota_reduzida'] = pd.to_numeric(
                items_df['icms_aliquota_reduzida'], errors='coerce'
            ).fillna(0).round(2)

        df_json_recebido = pd.read_csv(df_json_csv_path, dtype=str).fillna('')

        validateSelect(client_id, items_df, df_json_recebido, initial_log)
        update_client_data_get(client_id, '1')

        done = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        save_imported_logs(client_id, initial_log + f"[{done}] - Processamento finalizado com sucesso\n")

    except Exception as e:
        err = timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        save_imported_logs(client_id, initial_log + f"[{err}] - Erro no processamento: {e}\n")
