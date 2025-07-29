# models.py
from django.db import models
from django.contrib.auth.models import User
from auditlog.registry import auditlog

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    supervisor = models.ForeignKey(User, related_name='analysts', null=True, blank=True, on_delete=models.SET_NULL)
    manager = models.ForeignKey(User, related_name='supervisors', null=True, blank=True, on_delete=models.SET_NULL)
    tax_management_permission = models.BooleanField(default=False)
    cattle_permission = models.BooleanField(default=False)
    shop_simulation_permission = models.BooleanField(default=False)
    pricing_permission = models.BooleanField(default=False)
    

    def __str__(self):
        return self.user.username
    
auditlog.register(Profile)