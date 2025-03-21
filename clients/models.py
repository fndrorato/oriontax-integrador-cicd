import uuid
from django.db import models
from django.contrib.auth.models import User
from erp.models import ERP
from auditlog.registry import auditlog

class Cities(models.Model):
    nome = models.CharField(max_length=255)
    id_estado = models.IntegerField()
    ibge = models.CharField(max_length=8)
    nome_estado = models.CharField(max_length=64)
    uf_estado = models.CharField(max_length=2)

    def __str__(self):
        return self.nome

class Client(models.Model):
    DATA_SENT_CHOICES = [
        ('5', '5'),
        ('10', '10'),
        ('15', '15'),
        ('20', '20'),
        ('25', '25'),
        ('30', '30'),
    ]

    DATA_STATUS_CHOICES = [
        ('1', 'Ativo'),
        ('2', 'Inativo'),        
        ('3', 'Suspenso'),
    ]
    
    DATA_METHOD_INTEGRATION_CHOICES = [
        ('1', 'API'),
        ('2', 'FTP'),
        ('3', 'SFTP'),
        ('4', 'Manual'),
    ]       

    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, blank=True, null=True, default='', verbose_name="CNPJ")
    token = models.UUIDField(default=uuid.uuid4, unique=True, blank=True, null=True)
    num_stores = models.IntegerField()
    date_contract = models.DateField()
    date_send = models.DateField(blank=True, null=True)
    economic_benefit = models.BooleanField(verbose_name="Benefício Econômico")
    erp = models.ForeignKey(ERP, on_delete=models.RESTRICT)
    accounting = models.ForeignKey('accountings.Accounting', on_delete=models.RESTRICT, verbose_name="Contabilidade")
    commercial_responsible = models.CharField(max_length=255, verbose_name="Responsável Comercial")
    owner = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    contact = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    client_status = models.CharField(max_length=2, choices=DATA_STATUS_CHOICES, blank=True, null=True, default=1)
    day_sent = models.CharField(max_length=2, choices=DATA_SENT_CHOICES, blank=True, null=True)    
    first_load_date = models.DateField(blank=True, null=True, verbose_name="Data Primeira Carga")
    connection_route = models.CharField(max_length=255, verbose_name="Rota da Conexão", blank=True, null=True, default=None)
    port_route = models.CharField(max_length=255, verbose_name="Porta", blank=True, null=True, default=None)
    user_route = models.CharField(max_length=255, verbose_name="Usuário para conectar", blank=True, null=True, default=None)
    password_route = models.CharField(max_length=255, verbose_name="Senha do usuário", blank=True, null=True, default=None)    
    database_route = models.CharField(max_length=255, verbose_name="Senha do usuário", blank=True, null=True, default=None) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_created = models.ForeignKey(User, related_name='clients_created', on_delete=models.SET_NULL, null=True, blank=True)
    user_updated = models.ForeignKey(User, related_name='clients_updated', on_delete=models.SET_NULL, null=True, blank=True)    
    last_date_get = models.DateTimeField(blank=True, null=True, verbose_name="Último Recebimento")
    last_date_send = models.DateTimeField(blank=True, null=True, verbose_name="Último Envio")
    method_integration = models.CharField(max_length=2, choices=DATA_METHOD_INTEGRATION_CHOICES, blank=True, null=True)

    def __str__(self):
        return self.name  
    
class Store(models.Model):
    client = models.ForeignKey(Client, related_name='stores', on_delete=models.CASCADE)    
    corporate_name = models.CharField(max_length=255, verbose_name="Razão Social")
    cnpj = models.CharField(max_length=18, unique=True, verbose_name="CNPJ")
    city = models.ForeignKey(Cities, on_delete=models.CASCADE)
    connection_route = models.CharField(max_length=255, verbose_name="Rota da Conexão")
    port_route = models.CharField(max_length=255, verbose_name="Porta", blank=True, null=True, default=None)
    user_route = models.CharField(max_length=255, verbose_name="Usuário para conectar", blank=True, null=True, default=None)
    password_route = models.CharField(max_length=255, verbose_name="Senha do usuário", blank=True, null=True, default=None)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user_created = models.ForeignKey(User, related_name='stores_created', on_delete=models.SET_NULL, null=True, blank=True)
    user_updated = models.ForeignKey(User, related_name='stores_updated', on_delete=models.SET_NULL, null=True, blank=True)    
    

    def __str__(self):
        return self.corporate_name   
    
class LogIntegration(models.Model):
    DATA_OPTION_CHOICES = [
        ('1', 'Dados Recebidos'),
        ('2', 'Dados Enviados'),
    ]

    DATA_METHOD_INTEGRATION_CHOICES = [
        ('1', 'API'),
        ('2', 'FTP'),
        ('3', 'SFTP'),
        ('4', 'Manual'),
    ]    
    
    client = models.ForeignKey(Client, on_delete=models.RESTRICT)
    result_integration = models.TextField()
    data_option = models.CharField(max_length=2, choices=DATA_OPTION_CHOICES, blank=True, null=True)
    method_integration = models.CharField(max_length=2, choices=DATA_METHOD_INTEGRATION_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

auditlog.register(Client)
auditlog.register(Store)