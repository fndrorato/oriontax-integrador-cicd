from django.db import models
from django.contrib.postgres.fields import JSONField 
from auditlog.registry import auditlog

class ERP(models.Model):
    DATA_METHOD_INTEGRATION_CHOICES = [
        ('1', 'API'),
        ('2', 'FTP'),
        ('3', 'SFTP'),
        ('4', 'Manual'),
    ]
        
    name = models.CharField(max_length=255)
    description = models.TextField()
    unnecessary_fields = models.JSONField(default=list, blank=True, null=True)
    method_integration = models.CharField(max_length=2, choices=DATA_METHOD_INTEGRATION_CHOICES, blank=True, null=True)
    periodicity = models.ForeignKey('ERPIntegrationSchedule', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name
    
class AccessDropbox(models.Model):
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    code = models.CharField(max_length=255, null=True, blank=True)
    access_token = models.CharField(max_length=255, null=True, blank=True)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)  # Data e hora de criação
    updated_at = models.DateTimeField(auto_now=True)      # Data e hora de última atualização    


class ERPIntegrationSchedule(models.Model):
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.description}"

auditlog.register(ERP)
auditlog.register(AccessDropbox)
