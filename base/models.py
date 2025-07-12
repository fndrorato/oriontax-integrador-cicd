from django.db import models


class States(models.Model):
    code = models.CharField(max_length=2, unique=True, verbose_name="State Code")
    name = models.CharField(max_length=100, verbose_name="State Name")
    aliquota_inter = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, verbose_name="Interstate Rate")
    pis_aliquota = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, verbose_name="Interstate Rate")
    cofins_aliquota = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, verbose_name="Interstate Rate")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"

class Costs(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Cost Name")
    active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    
    def __str__(self):
        return self.name
    