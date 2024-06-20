from django.contrib.contenttypes.models import ContentType
from auditlog.models import LogEntry

def get_auditlog_history(model_name, object_id):
    """Retorna o histórico de auditoria para um modelo e objeto específico."""

    try:
        content_type = ContentType.objects.get(model=model_name.lower())  # Converta para minúsculas para evitar problemas de case
        return LogEntry.objects.filter(content_type=content_type, object_pk=str(object_id))
    except ContentType.DoesNotExist:
        return LogEntry.objects.none()  # Retorna um QuerySet vazio se o modelo não existir
