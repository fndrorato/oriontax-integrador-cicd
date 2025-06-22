from django.db import models
from django.contrib.auth.models import User
from django.db import models
from shopsim.models import SupplierProfile


class UsersCosts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='users_costs')
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.description}'

class CostsMaster(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='costs_master')
    sales_per_month = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.sales_per_month}'

class CostsDetail(models.Model):
    costs_master = models.ForeignKey(CostsMaster, on_delete=models.CASCADE, related_name='costs_detail')
    user_costs = models.ForeignKey(UsersCosts, on_delete=models.CASCADE, related_name='user_costs_detail')
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.costs_master.user.username} - {self.user_costs.description} - {self.value}'

class ItemClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icms_value  = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    pis_value = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cofins_value = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Pricing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pricings_user')
    description = models.CharField(max_length=255, blank=True, null=True)
    item_class = models.ForeignKey(ItemClass, on_delete=models.CASCADE, related_name='pricings')
    item_icms_excluded = models.BooleanField(default=False)
    items_pis_cofins_excluded = models.BooleanField(default=False)
    supplier = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='pricings')
    total_cost_at_moment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    markup = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    card_tax = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.item_class.name} - {self.supplier.name} - {self.sale_price}'
