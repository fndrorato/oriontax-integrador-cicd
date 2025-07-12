from base.models import States
from django.contrib.auth.models import User
from django.db import models


class SupplierProfile(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Supplier Profile Name")
    description = models.TextField(blank=True, verbose_name="Description")
    tax_value = models.DecimalField(max_digits=5, decimal_places=2, default=0.0, verbose_name="Tax Value")
    only_shop_simulation = models.BooleanField(default=True, verbose_name="Only Shop Simulation")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Supplier Profile"
        verbose_name_plural = "Supplier Profiles"

class PriceQuote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_quotes')
    simulation_description = models.CharField(max_length=100, verbose_name="Simulation Description")
    tax_icms_sale = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    product_icms_7 = models.BooleanField(verbose_name="Is product taxed at 7% ICMS?", null=True, blank=True)
    product_pis_cofins = models.BooleanField(verbose_name="Is product taxed for PIS/COFINS?")
    product_description = models.CharField(max_length=255)
    state_option_01 = models.ForeignKey(States, on_delete=models.CASCADE, related_name='state_option_01', verbose_name="State Option 01")
    state_option_02 = models.ForeignKey(States, on_delete=models.CASCADE, related_name='state_option_02', verbose_name="State Option 02")
    
    supplier_profile_01 = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, verbose_name="Supplier Profile")
    supplier_profile_02 = models.ForeignKey(SupplierProfile, on_delete=models.CASCADE, related_name='supplier_profile_02', verbose_name="Supplier Profile 02")
    
    product_price_01 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    product_price_02 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    freight_01 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    freight_02 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    additional_costs_01 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    additional_costs_02 = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    interstate_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # e.g., 10.00 for 10%
    icms_credit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    pis_cofins_credit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    best_option = models.ForeignKey(States, on_delete=models.CASCADE, related_name='best_option', verbose_name="Best Option State")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description
				