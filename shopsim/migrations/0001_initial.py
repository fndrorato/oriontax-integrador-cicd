# Generated by Django 5.0.6 on 2025-06-19 15:29

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SupplierProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Supplier Profile Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('tax_value', models.DecimalField(decimal_places=2, default=0.0, max_digits=5, verbose_name='Tax Value')),
            ],
            options={
                'verbose_name': 'Supplier Profile',
                'verbose_name_plural': 'Supplier Profiles',
            },
        ),
        migrations.CreateModel(
            name='PriceQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_icms_7', models.BooleanField(verbose_name='Is product taxed at 7% ICMS?')),
                ('product_pis_cofins', models.BooleanField(verbose_name='Is product taxed for PIS/COFINS?')),
                ('description', models.CharField(max_length=255)),
                ('product_price_01', models.DecimalField(decimal_places=2, max_digits=10)),
                ('product_price_02', models.DecimalField(decimal_places=2, max_digits=10)),
                ('freight_01', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('freight_02', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('additional_costs_01', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('additional_costs_02', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('interstate_tax_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('icms_credit', models.DecimalField(decimal_places=2, max_digits=10)),
                ('pis_cofins_credit', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('best_option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='best_option', to='base.states', verbose_name='Best Option State')),
                ('state_option_01', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='state_option_01', to='base.states', verbose_name='State Option 01')),
                ('state_option_02', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='state_option_02', to='base.states', verbose_name='State Option 02')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_quotes', to=settings.AUTH_USER_MODEL)),
                ('supplier_profile_01', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shopsim.supplierprofile', verbose_name='Supplier Profile')),
                ('supplier_profile_02', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='supplier_profile_02', to='shopsim.supplierprofile', verbose_name='Supplier Profile 02')),
            ],
        ),
    ]
