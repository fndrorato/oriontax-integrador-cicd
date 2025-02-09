# Generated by Django 5.0.6 on 2024-09-30 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0005_erp_unnecessary_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessDropbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.CharField(max_length=255)),
                ('client_secret', models.CharField(max_length=255)),
                ('code', models.CharField(blank=True, max_length=255, null=True)),
                ('access_token', models.CharField(blank=True, max_length=255, null=True)),
                ('refresh_token', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
