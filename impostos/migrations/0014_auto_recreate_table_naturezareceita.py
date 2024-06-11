# your_app_name/migrations/0002_auto_recreate_table.py

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('impostos', '0013_rename_aliquota_piscofinscst_cofins_aliquota_and_more'),  # Substitua por sua migração inicial ou a última migração bem-sucedida
    ]

    operations = [
        migrations.CreateModel(
            name='NaturezaReceita',
            fields=[
                ('id', models.AutoField(primary_key=True)),
                ('code', models.CharField(max_length=255)),
                ('category', models.CharField(
                    max_length=255,
                    blank=True,
                    null=True,
                    choices=[
                        ('Substituição Tributária', 'Substituição Tributária'),
                        ('Alíquota Zero', 'Alíquota Zero'),
                        ('Monofásico', 'Monofásico')
                    ]
                )),
                ('description', models.TextField()),
                ('ncm', models.TextField(blank=True, null=True)),
                ('piscofins_cst', models.ForeignKey(on_delete=models.CASCADE, to='impostos.piscofinscst')),
            ],
            options={
                'constraints': [
                    models.UniqueConstraint(fields=['code', 'piscofins_cst'], name='unique_code_piscofins_cst')
                ],
            },
        ),
    ]
