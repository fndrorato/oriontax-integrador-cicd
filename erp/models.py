from django.db import models
from django.contrib.postgres.fields import JSONField 
from auditlog.registry import auditlog

class ERP(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    unnecessary_fields = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return self.name

auditlog.register(ERP)
