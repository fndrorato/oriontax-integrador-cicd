from django.db import models
from auditlog.registry import auditlog

class ERP(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

auditlog.register(ERP)
