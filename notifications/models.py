# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'info', _('Informação')
        WARNING = 'warning', _('Aviso')
        DANGER = 'danger', _('Urgente')
        SUCCESS = 'success', _('Sucesso')
        SYSTEM = 'system', _('Sistema')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Usuário')
    )
    
    title = models.CharField(
        _('Título'),
        max_length=100,
        blank=True,
        null=True
    )
    
    message = models.TextField(
        _('Mensagem'),
        max_length=500
    )
    
    notification_type = models.CharField(
        _('Tipo'),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    
    # URL para redirecionamento quando clicar na notificação
    action_url = models.URLField(
        _('URL de ação'),
        max_length=500,
        blank=True,
        null=True
    )
    
    # Referência a algum objeto no sistema (ex: 'order:123')
    reference = models.CharField(
        _('Referência'),
        max_length=100,
        blank=True,
        null=True
    )
    
    is_read = models.BooleanField(
        _('Lida?'),
        default=False
    )
    
    created_at = models.DateTimeField(
        _('Criado em'),
        default=timezone.now,
        editable=False
    )
    
    read_at = models.DateTimeField(
        _('Lida em'),
        blank=True,
        null=True
    )
    
    # Ícone para exibição (usando classes de font-awesome ou similar)
    icon = models.CharField(
        _('Ícone'),
        max_length=50,
        default='fa fa-bell'
    )

    class Meta:
        verbose_name = _('Notificação')
        verbose_name_plural = _('Notificações')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}..."

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def get_absolute_url(self):
        if self.action_url:
            return self.action_url
        return reverse('notifications:view', args=[str(self.id)])

    @property
    def is_recent(self):
        return (timezone.now() - self.created_at).days < 1