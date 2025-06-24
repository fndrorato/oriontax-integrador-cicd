from auditlog.registry import auditlog
from django.contrib.auth.models import User
from django.db import models


class FieldConfiguration(models.Model):
    field_name = models.CharField(max_length=100, unique=True)
    field_label = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.field_label or self.field_name

class FieldOption(models.Model):
    field = models.ForeignKey(FieldConfiguration, related_name='options', on_delete=models.CASCADE)
    value = models.CharField(max_length=50)
    label = models.CharField(max_length=100)

    class Meta:
        unique_together = ('field', 'value')

    def __str__(self):
        return f"{self.label} ({self.value})"

class MatrixSimulation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simulations')
    description = models.CharField(max_length=255, blank=True, null=True)

    # Core simulation fields
    cow_weighing_location = models.CharField(max_length=50)

    monthly_sales_volume_kg = models.DecimalField(max_digits=12, decimal_places=2)
    average_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    total_sales_per_month = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, default=0)
    
    cows_per_month_producer = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cows_per_month_slaughterhouse = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cows_per_week_producer = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cows_per_week_slaughterhouse = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    mean_weight_per_cow_producer_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, default=0)    
    mean_weight_per_cow_slaughterhouse_kg = models.DecimalField(max_digits=8, decimal_places=2)
    mean_weight_per_cow_producer_arroba = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    mean_weight_per_cow_slaughterhouse_arroba = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  

    yield_live_cow_pasture_producer_percent = models.DecimalField(max_digits=5, decimal_places=2)
    yield_butchered_cow_producer_percent = models.DecimalField(max_digits=5, decimal_places=2)
    yield_live_cow_pasture_slaughterhouse_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  
    yield_butchered_cow_slaughterhouse_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)    

    price_closed_per_arroba_producer = models.DecimalField(max_digits=10, decimal_places=2)
    price_closed_per_arroba_slaughterhouse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    
    price_net_per_arroba_producer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_net_per_arroba_slaughterhouse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
       
    price_per_kg_butchered_cow_producer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_per_kg_butchered_cow_slaughterhouse = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg_after_butchered_cow_producer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    price_per_kg_after_butchered_cow_slaughterhouse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)    

    slaughter_service_per_cow_producer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    slaughter_service_per_cow_slaughterhouse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True) 
    
    freight_producer_slaughterhouse_producer = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    freight_slaughterhouse_store_producer = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    freight_slaughterhouse_store_slaughterhouse = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    commission_buyer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percent_comission = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.0)
    is_estorno_icms = models.BooleanField(default=False)
    total_slaughter_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_value_producer = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_value_slaughterhouse = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    profit_gain_comparison = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description or f"Simulation #{self.id} for {self.user.username}"

class MeatCut(models.Model):
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Usuário que criou
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class UserMeatCut(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    meat_cut = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)    

class ButcheryMaster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    arroba_price_nf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ButcheryDetail(models.Model):
    CUT_CLASS_CHOICES = [
        ('1A', '1ª'),
        ('2A', '2ª'),
    ]

    butchery = models.ForeignKey(ButcheryMaster, on_delete=models.CASCADE, related_name='details')    
    user_meat_cut = models.ForeignKey(UserMeatCut, on_delete=models.CASCADE)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    weight = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    cut_class = models.CharField(max_length=2, choices=CUT_CLASS_CHOICES, default='1A')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    
auditlog.register(FieldConfiguration)