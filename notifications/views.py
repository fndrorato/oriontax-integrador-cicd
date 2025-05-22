# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # ou use @csrf_protect se usar token no JS
from django.shortcuts import get_object_or_404
from .models import Notification
from django.utils import timezone


@login_required
def notificacoes_json(request):
    notificacoes = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:3]
    
    data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'created_at': n.created_at.strftime('%d/%m/%Y %H:%M'),
            'type': n.notification_type,
        }
        for n in notificacoes
    ]

    return JsonResponse({
        'total': notificacoes.count(),
        'notificacoes': data
    })

@csrf_exempt
@require_POST
@login_required
def marcar_notificacao_como_lida(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.mark_as_read()
    return JsonResponse({'status': 'ok'})

@require_POST
@login_required
@csrf_exempt
def marcar_todas_como_lidas(request):
    request.user.notifications.filter(is_read=False).update(is_read=True, read_at=timezone.now())
    return JsonResponse({'status': 'ok'})
