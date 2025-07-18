# Generated by Django 5.0.6 on 2025-06-14 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cattles', '0003_rename_yield_butchered_cow_percent_matrixsimulation_yield_butchered_cow_producer_percent_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='matrixsimulation',
            old_name='price_per_arroba_producer',
            new_name='price_closed_per_arroba_producer',
        ),
        migrations.RenameField(
            model_name='matrixsimulation',
            old_name='price_per_arroba_slaughterhouse',
            new_name='price_closed_per_arroba_slaughterhouse',
        ),
        migrations.RenameField(
            model_name='matrixsimulation',
            old_name='price_per_kg_butchered_cow',
            new_name='price_net_per_arroba_producer',
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='freight_producer_slaughterhouse_producer',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='freight_slaughterhouse_store_producer',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='freight_slaughterhouse_store_slaughterhouse',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='price_net_per_arroba_slaughterhouse',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='price_per_kg_after_butchered_cow_producer',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='price_per_kg_after_butchered_cow_slaughterhouse',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='price_per_kg_butchered_cow_producer',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='matrixsimulation',
            name='price_per_kg_butchered_cow_slaughterhouse',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
