from django.db import models
from django.core.exceptions import ValidationError
from auditlog.registry import auditlog

def validate_cfop(value):
    if value < 1000 or value > 9999:
        raise ValidationError(
            '%(value)s não é um CFOP válido. Deve ser um número de 4 dígitos.',
            params={'value': value},
        )

def validate_operation(value):
    if value not in ['E', 'S']:
        raise ValidationError(
            '%(value)s não é uma operação válida. Deve ser "E" ou "S".',
            params={'value': value},
        )

# Create your models here.
class Cfop(models.Model):
    cfop = models.PositiveIntegerField(primary_key=True, unique=True, validators=[validate_cfop])
    description = models.CharField(max_length=255, null=True, blank=True, default="Descrição CFOP")
    operation = models.CharField(max_length=1, default="S", validators=[validate_operation])

    def __str__(self):
        return f"{self.cfop}"

    class Meta:
        verbose_name = "CFOP"
        verbose_name_plural = "CFOPs"
        
class IcmsCst(models.Model):
    code = models.CharField(max_length=4, primary_key=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.code    

class CBENEF(models.Model):
    code = models.CharField(max_length=8, primary_key=True)
    icms_cst = models.ForeignKey(IcmsCst, on_delete=models.CASCADE)
    description = models.CharField(max_length=255, null=True, blank=True)
    legislation = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.code    
    
class IcmsAliquota(models.Model):
    code = models.PositiveIntegerField(primary_key=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.code)           

class IcmsAliquotaReduzida(models.Model):
    code = models.DecimalField(
        primary_key=True,
        max_digits=5,
        decimal_places=2
    )
    description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.code)  
    
class Protege(models.Model):
    code = models.PositiveIntegerField(primary_key=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.code)       
  
class PisCofinsCst(models.Model):
    DATA_TYPE_COMPANY_CHOICES = [
        ('1', 'Simples Nacional'),
        ('2', 'Lucro Presumido'),        
        ('3', 'Lucro Real'),
    ]

    code = models.CharField(max_length=4, primary_key=True)
    type_company = models.CharField(max_length=1, choices=DATA_TYPE_COMPANY_CHOICES, default='3')
    description = models.CharField(max_length=255, null=True, blank=True)
    pis_aliquota = models.FloatField(default=0)
    cofins_aliquota = models.FloatField()
    pis_aliquota_company_2 = models.FloatField(default=0)
    cofins_aliquota_company_2 = models.FloatField(default=0)    

    def __str__(self):
        return f"{self.code} - {self.description}"      

class NaturezaReceita(models.Model):
    CATEGORY_CHOICES = [
        ('Substituição Tributária', 'Substituição Tributária'),
        ('Alíquota Zero', 'Alíquota Zero'),
        ('Monofásico', 'Monofásico'),
        ('Suspensão', 'Suspensão'),
    ]

    id = models.AutoField(primary_key=True)  # Campo autonumérico como chave primária
    code = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True, choices=CATEGORY_CHOICES)
    description = models.TextField()
    ncm = models.TextField(blank=True, null=True)
    piscofins_cst = models.ForeignKey(PisCofinsCst, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.code}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code', 'piscofins_cst'], name='unique_code_piscofins_cst')
        ]

class ReformaTributaria(models.Model):
    cst_ibs_cbs = models.CharField(max_length=10, help_text="Código de Situação Tributária do IBS e da CBS")
    description_cst_ibs_cbs = models.CharField(max_length=255, null=True, blank=True, help_text="Descrição do Código de Situação Tributária do IBS e da CBS")
    c_class_trib = models.CharField(max_length=20, null=True, blank=True, help_text="Classificação Tributária do IBS e da CBS, sendo os três primeiros dígitos idênticos ao CST-IBS/CBS")
    name_c_class_trib = models.CharField(max_length=100, null=True, blank=True, help_text="Nome da Classificação Tributária do IBS e da CBS")
    description_c_class_trib = models.TextField(null=True, blank=True, help_text="Descrição da Classificação Tributária do IBS e da CBS")
    text_ec = models.CharField(max_length=100, null=True, blank=True)
    text_lc = models.TextField(null=True, blank=True)
    tipo_aliquota = models.CharField(max_length=20, null=True, blank=True, help_text="Define o tipo de alíquota aplicável, conforme disposto na Lei Complementar")
    aliquota_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    aliquota_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_ibs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    p_red_aliq_cbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"{self.cst_ibs_cbs} - {self.c_class_trib}"

auditlog.register(Cfop)
auditlog.register(IcmsCst)
auditlog.register(CBENEF)
auditlog.register(IcmsAliquota)
auditlog.register(IcmsAliquotaReduzida)
auditlog.register(Protege)
auditlog.register(PisCofinsCst)
auditlog.register(NaturezaReceita)
