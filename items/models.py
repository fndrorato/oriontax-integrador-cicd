from django.db import models
from django.contrib.auth.models import User
from clients.models import Client, Store
from impostos.models import (
    Cfop, 
    IcmsCst, 
    CBENEF, 
    PisCofinsCst, 
    NaturezaReceita, 
    Protege, 
    IcmsAliquota, 
    IcmsAliquotaReduzida,
    ReformaTributaria
)
from django.core.exceptions import ValidationError
from auditlog.registry import auditlog

class Item(models.Model):
    TYPE_PRODUCT_CHOICES = [
        ('', '----'),
        ('Revenda', 'Revenda'),
        ('Imobilizado', 'Imobilizado'),
        ('Insumos', 'Insumos'),
    ]
    
    STATUS_CHOICES = [
        (0, 'Produto Novo'),
        (1, 'Aguardando Sincronização'),        
        (2, 'Enviado - Aguard Validação'),
        (3, 'Validado'),
        (4, 'Inativo')
    ]    
        
    client = models.ForeignKey(Client, on_delete=models.RESTRICT)
    code = models.CharField(max_length=50, null=True, blank=True, default='0')
    sequencial = models.PositiveIntegerField(null=True, blank=True, default=0)
    barcode = models.CharField(max_length=255, null=True, blank=True, default='')
    description = models.CharField(max_length=255)
    ncm = models.CharField(max_length=8)
    cest = models.CharField(max_length=7, null=True, blank=True, default='')
    cfop = models.ForeignKey(Cfop, on_delete=models.RESTRICT)
    icms_cst = models.ForeignKey(IcmsCst, on_delete=models.RESTRICT)
    icms_aliquota = models.ForeignKey(IcmsAliquota, on_delete=models.RESTRICT)
    icms_aliquota_reduzida = models.CharField(max_length=5)
    percentual_redbcde = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.00)
    protege = models.ForeignKey(Protege, on_delete=models.RESTRICT, null=True, blank=True)
    cbenef = models.ForeignKey(CBENEF, on_delete=models.RESTRICT, null=True, blank=True)
    piscofins_cst = models.ForeignKey(PisCofinsCst, related_name='piscofins_cst_items', on_delete=models.RESTRICT)
    pis_aliquota = models.FloatField()
    cofins_aliquota = models.FloatField()
    naturezareceita = models.ForeignKey(NaturezaReceita, on_delete=models.SET_NULL, null=True, blank=True)
    # reforma_tributaria = models.ForeignKey(ReformaTributaria, on_delete=models.RESTRICT, null=True, blank=True)
    
    cst_ibs_cbs = models.CharField(max_length=10, blank=True, null=True, help_text="Código de Situação Tributária do IBS e da CBS")
    c_class_trib = models.CharField(max_length=20, null=True, blank=True, help_text="Classificação Tributária do IBS e da CBS, sendo os três primeiros dígitos idênticos ao CST-IBS/CBS")
    aliquota_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    aliquota_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)    
    
    type_product = models.CharField(max_length=20, choices=TYPE_PRODUCT_CHOICES, default='', blank=True)
    other_information = models.CharField(max_length=255, default='', null=True, blank=True)
    status_item = models.IntegerField(choices=STATUS_CHOICES, default=3)
    history = models.CharField(max_length=255, default='', null=True, blank=True)
    estado_origem = models.CharField(max_length=3, default='', null=True, blank=True)
    estado_destino = models.CharField(max_length=3, default='', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_pending_sync = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    sync_at = models.DateTimeField(null=True, blank=True)
    await_sync_at = models.DateTimeField(null=True, blank=True)
    sync_validate_at = models.DateTimeField(null=True, blank=True)
    user_created = models.ForeignKey(User, related_name='items_created', on_delete=models.SET_NULL, null=True, blank=True)
    user_updated = models.ForeignKey(User, related_name='items_updated', on_delete=models.SET_NULL, null=True, blank=True)
    
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['client', 'code'], name='unique_client_code')
        ]

    def __str__(self):
        return self.description
    
class ImportedItem(models.Model):  
    STATUS_CHOICES = [
        (0, 'Produto Novo'),
        (1, 'Problemas Encontrados'),
    ]       
           
    client = models.ForeignKey(Client, on_delete=models.RESTRICT)
    code = models.CharField(max_length=50, null=True, blank=True, default='0')
    sequencial = models.PositiveIntegerField(null=True, blank=True, default=0)    
    barcode = models.CharField(max_length=255, null=True, blank=True, default='')
    description = models.CharField(max_length=255)
    ncm = models.CharField(max_length=255)
    cest = models.CharField(max_length=255, null=True, blank=True, default='')
    cfop = models.PositiveIntegerField(null=True, blank=True, default=0)
    icms_cst = models.IntegerField(null=True, blank=True, default=0)
    icms_aliquota = models.IntegerField(null=True, blank=True, default=0)
    icms_aliquota_reduzida = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, default=0.00)
    percentual_redbcde = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.00)
    protege = models.IntegerField(null=True, blank=True, default=0)
    cbenef = models.CharField(max_length=255, null=True, blank=True, default='')
    piscofins_cst = models.IntegerField(null=True, blank=True, default=0)
    pis_aliquota = models.FloatField(null=True, blank=True, default=0)
    cofins_aliquota = models.FloatField(null=True, blank=True, default=0)
    naturezareceita = models.IntegerField(null=True, blank=True, default=0)
    status_item = models.IntegerField(choices=STATUS_CHOICES, default=1)

    cst_ibs_cbs = models.CharField(max_length=10, blank=True, null=True, help_text="Código de Situação Tributária do IBS e da CBS")
    c_class_trib = models.CharField(max_length=20, null=True, blank=True, help_text="Classificação Tributária do IBS e da CBS, sendo os três primeiros dígitos idênticos ao CST-IBS/CBS")
    aliquota_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    aliquota_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    is_pending = models.BooleanField(default=True)
    divergent_columns = models.CharField(max_length=255, null=True, blank=True, default='')
    estado_origem = models.CharField(max_length=3, default='', null=True, blank=True)
    estado_destino = models.CharField(max_length=3, default='', null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)    

    def __str__(self):
        return self.description

    # class Meta:
    #     unique_together = ('client', 'code')    
    
auditlog.register(Item, mapping_fields={'history':'Histórico', 'updated_at':'Última Atualização', 'created_at':'Criado Em', 'description':'Descrição', 'barcode':'Cód. Barras',  'code':'Codigo', 'other_information':'outras informações', 'type_product':'Tipo Produto'})
