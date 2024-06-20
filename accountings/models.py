from django.db import models
from auditlog.registry import auditlog
from clients.models import Cities

class Accounting(models.Model):
    name = models.CharField(max_length=255)
    city = models.ForeignKey(Cities, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    contact = models.CharField(max_length=255)

    def __str__(self):
        return self.name

auditlog.register(Accounting)