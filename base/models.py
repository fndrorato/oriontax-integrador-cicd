from django.db import models


class States(models.Model):
    code = models.CharField(max_length=2, unique=True, verbose_name="State Code")
    name = models.CharField(max_length=100, verbose_name="State Name")
    aliquota_inter = models.DecimalField(default=0.0, max_digits=5, decimal_places=2, verbose_name="Interstate Rate")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
