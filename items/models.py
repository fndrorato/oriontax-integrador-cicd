from django.db import models
from django.contrib.auth.models import User
from clients.models import Client, Store
from impostos.models import Cfop, IcmsCst, CBENEF, PisCofinsCst, NaturezaReceita, Protege, IcmsAliquota, IcmsAliquotaReduzida  # Supondo que os outros modelos estejam em app2
from django.core.exceptions import ValidationError

class Item(models.Model):
    client = models.ForeignKey(Client, on_delete=models.RESTRICT)
    code = models.PositiveIntegerField()
    barcode = models.CharField(max_length=255, null=True, blank=True, default='')
    description = models.CharField(max_length=255)
    ncm = models.CharField(max_length=8)
    cest = models.CharField(max_length=7, null=True, blank=True, default='')
    cfop = models.ForeignKey(Cfop, on_delete=models.RESTRICT)
    icms_cst = models.ForeignKey(IcmsCst, on_delete=models.RESTRICT)
    icms_aliquota = models.ForeignKey(IcmsAliquota, on_delete=models.RESTRICT)
    icms_aliquota_reduzida = models.CharField(max_length=3)
    protege = models.ForeignKey(Protege, on_delete=models.RESTRICT, null=True, blank=True)
    cbenef = models.ForeignKey(CBENEF, on_delete=models.RESTRICT, null=True, blank=True)
    piscofins_cst = models.ForeignKey(PisCofinsCst, related_name='piscofins_cst_items', on_delete=models.RESTRICT)
    pis_aliquota = models.FloatField()
    cofins_aliquota = models.FloatField()
    naturezareceita = models.ForeignKey(NaturezaReceita, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_pending_sync = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_created = models.ForeignKey(User, related_name='items_created', on_delete=models.SET_NULL, null=True, blank=True)
    user_updated = models.ForeignKey(User, related_name='items_updated', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['client', 'code'], name='unique_client_code')
        ]

    def __str__(self):
        return self.description