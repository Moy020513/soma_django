from django.contrib.admin.models import LogEntry

def recent_admin_actions(request):
    """Retorna las últimas 10 acciones del admin para usuarios staff.
    Se usa en el header (modal de Acciones recientes).
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or not user.is_staff:
        return {}
    entries = (LogEntry.objects.select_related('user', 'content_type')
               .order_by('-action_time')[:10])
    return {
        'recent_admin_actions': entries
    }
