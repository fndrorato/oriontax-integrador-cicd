# Generated by Django 5.0.6 on 2024-07-04 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0011_store_password_route_store_port_route_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='connection_route',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Rota da Conexão'),
        ),
        migrations.AddField(
            model_name='client',
            name='password_route',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Senha do usuário'),
        ),
        migrations.AddField(
            model_name='client',
            name='port_route',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Porta'),
        ),
        migrations.AddField(
            model_name='client',
            name='user_route',
            field=models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Usuário para conectar'),
        ),
    ]