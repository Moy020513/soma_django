from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from apps.recursos_humanos.models import Empleado
from .models import Herramienta, AsignacionHerramienta, TransferenciaHerramienta
from apps.notificaciones.models import Notificacion
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from .forms import SolicitudTransferenciaHerramientaForm, RespuestaTransferenciaHerramientaForm
from django import forms

# Helper de notificaciones para administradores (fuera de la clase para evitar problemas de indentación)
def _notificar_admins(titulo: str, mensaje: str, url: str = '', exclude_ids=None):
    """Crea una notificación para todos los usuarios administradores (is_staff) excepto los excluidos.
    exclude_ids: iterable de IDs de usuarios a omitir.
    """
    User = get_user_model()
    qs = User.objects.filter(is_staff=True, is_active=True)
    if exclude_ids:
        qs = qs.exclude(id__in=list(exclude_ids))
    objetos = [Notificacion(
        usuario=u,
        titulo=titulo,
        mensaje=mensaje,
        tipo='info',
        url=url or ''
    ) for u in qs]
    if objetos:
        Notificacion.objects.bulk_create(objetos)


class HerramientasView(ListView):
    template_name = 'herramientas/index.html'
    context_object_name = 'items'

    def get_queryset(self):
        return Herramienta.objects.all().order_by('categoria', 'codigo')


@login_required
def mi_herramienta(request):
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está vinculado a un empleado.')
        return redirect('perfil_usuario')
    asignaciones = list(
        AsignacionHerramienta.objects.filter(
            empleado=empleado,
            fecha_devolucion__isnull=True
        ).select_related('herramienta').order_by('herramienta__categoria', 'herramienta__codigo')
    )
    if not asignaciones:
        messages.info(request, 'No tienes herramientas asignadas actualmente. Verifica que el administrador haya creado una Asignación de Herramienta (no basta solo con cambiar el estado a "asignada").')
        return redirect('perfil_usuario')
    if len(asignaciones) == 1:
        asignacion = asignaciones[0]
        return render(request, 'herramientas/mi_herramienta.html', {
            'titulo': 'Mi Herramienta',
            'herramienta': asignacion.herramienta,
            'asignacion': asignacion,
        })
    # Múltiples herramientas: mostrar listado
    return render(request, 'herramientas/mis_herramientas.html', {
        'titulo': 'Mis Herramientas',
        'asignaciones': asignaciones,
    })


@login_required
def mis_herramientas(request):
    """Vista para mostrar la lista de herramientas asignadas al usuario"""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está vinculado a un empleado.')
        return redirect('perfil_usuario')
    
    asignaciones = list(
        AsignacionHerramienta.objects.filter(
            empleado=empleado,
            fecha_devolucion__isnull=True
        ).select_related('herramienta').order_by('herramienta__categoria', 'herramienta__codigo')
    )
    
    if not asignaciones:
        messages.info(request, 'No tienes herramientas asignadas actualmente.')
        return redirect('perfil_usuario')
    
    return render(request, 'herramientas/mis_herramientas.html', {
        'titulo': 'Mis Herramientas',
        'asignaciones': asignaciones,
    })


@login_required
def detalle_herramienta(request, herramienta_id):
    """Vista para mostrar los detalles de una herramienta específica"""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está vinculado a un empleado.')
        return redirect('perfil_usuario')
    
    # Verificar que la herramienta esté asignada al usuario
    asignacion = get_object_or_404(
        AsignacionHerramienta,
        herramienta_id=herramienta_id,
        empleado=empleado,
        fecha_devolucion__isnull=True
    )
    
    return render(request, 'herramientas/detalle_herramienta.html', {
        'titulo': f'Herramienta - {asignacion.herramienta.nombre}',
        'herramienta': asignacion.herramienta,
        'asignacion': asignacion,
    })


@login_required
def solicitar_transferencia_herramienta(request):
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')
    asignaciones = list(AsignacionHerramienta.objects.filter(empleado=empleado, fecha_devolucion__isnull=True).select_related('herramienta'))
    if not asignaciones:
        messages.error(request, 'No tienes una herramienta asignada para transferir.')
        return redirect('perfil_usuario')

    # Si hay solo una herramienta, validar transferencia pendiente
    if len(asignaciones) == 1:
        transferencia_pendiente = TransferenciaHerramienta.objects.filter(empleado_origen=empleado, herramienta=asignaciones[0].herramienta, estado='solicitada').first()
        if transferencia_pendiente:
            return redirect('herramientas:transferencia_detalle', pk=transferencia_pendiente.pk)

    pre_h = request.GET.get('h')
    try:
        pre_h = int(pre_h) if pre_h else None
    except ValueError:
        pre_h = None
    
    # Detectar de dónde viene para el botón cancelar
    referrer = request.META.get('HTTP_REFERER', '')
    from_list = 'mis/' in referrer or 'mis_herramientas' in referrer
    if request.method == 'POST':
        form = SolicitudTransferenciaHerramientaForm(request.POST, empleado_actual=empleado, pre_herramienta_id=pre_h)
        if form.is_valid():
            with transaction.atomic():
                transf = form.save(commit=False)
                herramienta = form.get_herramienta(empleado)
                if not herramienta:
                    messages.error(request, 'No se pudo determinar la herramienta a transferir.')
                    return redirect('herramientas:solicitar_transferencia')
                # Verificar duplicada
                if TransferenciaHerramienta.objects.filter(empleado_origen=empleado, herramienta=herramienta, estado='solicitada').exists():
                    messages.warning(request, 'Ya existe una solicitud pendiente para esa herramienta.')
                    if from_list:
                        return redirect('herramientas:mis_herramientas')
                    else:
                        return redirect('herramientas:mi_herramienta')
                transf.herramienta = herramienta
                transf.empleado_origen = empleado
                transf.estado = 'solicitada'
                transf.save()
                # Notificación empleado destino
                Notificacion.objects.create(
                    usuario=transf.empleado_destino.usuario,
                    titulo='🔧 Solicitud de Transferencia de Herramienta',
                    mensaje=f'{empleado.usuario.get_full_name()} quiere transferirte la herramienta {herramienta.nombre} ({herramienta.codigo}).',
                    tipo='info',
                    # Enviar directo al formulario de respuesta
                    url=f"/herramientas/transferencias/{transf.pk}/responder/"
                )
                # Notificar administradores (excluyendo origen y destino para evitar duplicados)
                _notificar_admins(
                    titulo='🔧 Nueva Solicitud de Transferencia de Herramienta',
                    mensaje=f'Se solicitó transferir la herramienta {herramienta.nombre} ({herramienta.codigo}) de {empleado.usuario.get_full_name()} a {transf.empleado_destino.usuario.get_full_name()}.',
                    # Para admins es útil ver el detalle completo primero
                    url=f"/herramientas/transferencias/{transf.pk}/",
                    exclude_ids=[empleado.usuario_id, transf.empleado_destino.usuario_id]
                )
                messages.success(request, 'Solicitud de transferencia enviada.')
                return redirect('herramientas:transferencia_detalle', pk=transf.pk)
    else:
        form = SolicitudTransferenciaHerramientaForm(empleado_actual=empleado, pre_herramienta_id=pre_h)
    return render(request, 'herramientas/solicitar_transferencia.html', {
        'titulo': 'Solicitar Transferencia de Herramienta',
        'form': form,
        'herramientas': [a.herramienta for a in asignaciones],
        'from_list': from_list,
    })


@login_required
def transferencia_detalle(request, pk):
    transferencia = get_object_or_404(TransferenciaHerramienta.objects.select_related('herramienta', 'empleado_origen__usuario', 'empleado_destino__usuario'), pk=pk)
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado or (transferencia.empleado_origen != empleado and transferencia.empleado_destino != empleado):
        messages.error(request, 'No puedes ver esta transferencia.')
        return redirect('perfil_usuario')
    return render(request, 'herramientas/transferencia_detalle.html', {
        'titulo': 'Detalle de Transferencia de Herramienta',
        'transferencia': transferencia,
        'empleado': empleado,
        'es_origen': transferencia.empleado_origen == empleado,
        'es_destino': transferencia.empleado_destino == empleado,
    })


@login_required
def responder_transferencia_herramienta(request, pk):
    transferencia = get_object_or_404(TransferenciaHerramienta.objects.select_related('herramienta', 'empleado_origen__usuario', 'empleado_destino__usuario'), pk=pk)
    # Si la vista fue abierta desde una notificación, los administradores no deben poder responder
    if request.GET.get('from_notification') and request.user.is_superuser:
        return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')
    empleado = Empleado.objects.filter(usuario=request.user).first()
    es_destino = empleado and transferencia.empleado_destino == empleado
    es_origen = empleado and transferencia.empleado_origen == empleado
    if not empleado:
        messages.error(request, 'No puedes responder esta transferencia.')
        return redirect('perfil_usuario')
    # Restricciones por estado
    if transferencia.estado in ['solicitada', 'inspeccion'] and not es_destino:
        messages.error(request, 'Solo el empleado destino puede responder ahora.')
        return redirect('perfil_usuario')
    if transferencia.estado == 'inspeccion_enviada' and not es_origen:
        messages.error(request, 'Solo el solicitante puede decidir tras la inspección.')
        return redirect('perfil_usuario')
    if transferencia.estado not in ['solicitada', 'inspeccion', 'inspeccion_enviada']:
        messages.info(request, 'Esta transferencia ya fue procesada.')
        return redirect('herramientas:transferencia_detalle', pk=transferencia.pk)

    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        obs = request.POST.get('observaciones', '').strip() or None
        with transaction.atomic():
            if respuesta == 'aprobar' and transferencia.estado in ['solicitada', 'inspeccion'] and es_destino:
                asignacion_anterior = AsignacionHerramienta.objects.filter(herramienta=transferencia.herramienta, fecha_devolucion__isnull=True).first()
                if asignacion_anterior:
                    asignacion_anterior.fecha_devolucion = timezone.now().date()
                    asignacion_anterior.save()
                AsignacionHerramienta.objects.create(
                    herramienta=transferencia.herramienta,
                    empleado=transferencia.empleado_destino,
                    fecha_asignacion=timezone.now().date(),
                    observaciones=f'Transferida de {transferencia.empleado_origen}'
                )
                transferencia.estado = 'aprobada'
                transferencia.fecha_transferencia = timezone.now()
                Notificacion.objects.create(
                    usuario=transferencia.empleado_origen.usuario,
                    titulo='✅ Transferencia de Herramienta Aprobada',
                    mensaje=f'{empleado.usuario.get_full_name()} aceptó la transferencia de la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    tipo='success',
                    url=f"/herramientas/transferencias/{transferencia.pk}/"
                )
                _notificar_admins(
                    titulo='✅ Transferencia de Herramienta Aprobada',
                    mensaje=f'La herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}) fue transferida a {transferencia.empleado_destino.usuario.get_full_name()}.',
                    url=f"/herramientas/transferencias/{transferencia.pk}/",
                    exclude_ids=[empleado.usuario_id, transferencia.empleado_origen.usuario_id]
                )
                messages.success(request, 'Transferencia aprobada.')
            elif respuesta == 'rechazar' and es_destino and transferencia.estado in ['solicitada', 'inspeccion']:
                transferencia.estado = 'rechazada'
                Notificacion.objects.create(
                    usuario=transferencia.empleado_origen.usuario,
                    titulo='❌ Transferencia de Herramienta Rechazada',
                    mensaje=f'{empleado.usuario.get_full_name()} rechazó la transferencia de la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    tipo='danger',
                    url=f"/herramientas/transferencias/{transferencia.pk}/"
                )
                _notificar_admins(
                    titulo='❌ Transferencia de Herramienta Rechazada',
                    mensaje=f'El destino {empleado.usuario.get_full_name()} rechazó la transferencia de {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    url=f"/herramientas/transferencias/{transferencia.pk}/",
                    exclude_ids=[empleado.usuario_id, transferencia.empleado_origen.usuario_id]
                )
                messages.info(request, 'Transferencia rechazada.')
            elif respuesta == 'inspeccionar' and transferencia.estado == 'solicitada' and es_destino:
                transferencia.estado = 'inspeccion'
                transferencia.fecha_inspeccion = timezone.now()
                transferencia.observaciones_inspeccion = obs or ''
                Notificacion.objects.create(
                    usuario=transferencia.empleado_origen.usuario,
                    titulo='🔍 Inspección de Herramienta',
                    mensaje=f'{empleado.usuario.get_full_name()} inició inspección de la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    tipo='warning',
                    url=f"/herramientas/transferencias/{transferencia.pk}/"
                )
                _notificar_admins(
                    titulo='🔍 Inspección de Herramienta Iniciada',
                    mensaje=f'{empleado.usuario.get_full_name()} está inspeccionando la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    url=f"/herramientas/transferencias/{transferencia.pk}/",
                    exclude_ids=[empleado.usuario_id, transferencia.empleado_origen.usuario_id]
                )
                messages.info(request, 'Has pasado la transferencia a inspección.')
            elif respuesta == 'aprobar' and transferencia.estado == 'inspeccion_enviada' and es_origen:
                asignacion_anterior = AsignacionHerramienta.objects.filter(herramienta=transferencia.herramienta, fecha_devolucion__isnull=True).first()
                if asignacion_anterior:
                    asignacion_anterior.fecha_devolucion = timezone.now().date()
                    asignacion_anterior.save()
                AsignacionHerramienta.objects.create(
                    herramienta=transferencia.herramienta,
                    empleado=transferencia.empleado_destino,
                    fecha_asignacion=timezone.now().date(),
                    observaciones=f'Transferida tras inspección de {transferencia.empleado_origen}'
                )
                transferencia.estado = 'aprobada'
                transferencia.fecha_transferencia = timezone.now()
                Notificacion.objects.create(
                    usuario=transferencia.empleado_destino.usuario,
                    titulo='✅ Transferencia de Herramienta Aprobada',
                    mensaje=f'{empleado.usuario.get_full_name()} aprobó la transferencia tras inspección de {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    tipo='success',
                    url=f"/herramientas/transferencias/{transferencia.pk}/"
                )
                _notificar_admins(
                    titulo='✅ Transferencia de Herramienta Aprobada',
                    mensaje=f'Transferencia aprobada tras inspección: {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    url=f"/herramientas/transferencias/{transferencia.pk}/",
                    exclude_ids=[empleado.usuario_id, transferencia.empleado_destino.usuario_id]
                )
                messages.success(request, 'Transferencia aprobada tras inspección.')
            elif respuesta == 'rechazar' and transferencia.estado == 'inspeccion_enviada' and es_origen:
                transferencia.estado = 'cancelada'
                Notificacion.objects.create(
                    usuario=transferencia.empleado_destino.usuario,
                    titulo='🚫 Transferencia Cancelada',
                    mensaje=f'{empleado.usuario.get_full_name()} canceló la transferencia tras inspección de {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    tipo='danger',
                    url=f"/herramientas/transferencias/{transferencia.pk}/"
                )
                _notificar_admins(
                    titulo='🚫 Transferencia Cancelada',
                    mensaje=f'Transferencia cancelada tras inspección: {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
                    url=f"/herramientas/transferencias/{transferencia.pk}/",
                    exclude_ids=[empleado.usuario_id, transferencia.empleado_destino.usuario_id]
                )
                messages.info(request, 'Transferencia cancelada tras inspección.')
            # Campos comunes
            transferencia.fecha_respuesta = timezone.now()
            if obs:
                transferencia.observaciones_respuesta = obs
            transferencia.save()
        return redirect('herramientas:transferencia_detalle', pk=transferencia.pk)
    else:
        class _RespuestaForm(RespuestaTransferenciaHerramientaForm):
            opciones = []
            if transferencia.estado in ['solicitada', 'inspeccion'] and es_destino:
                opciones = [
                    ('aprobar', 'Aprobar transferencia'),
                    ('rechazar', 'Rechazar transferencia'),
                ] + ([('inspeccionar', 'Pasar a Inspección')] if transferencia.estado == 'solicitada' else [])
            elif transferencia.estado == 'inspeccion_enviada' and es_origen:
                opciones = [
                    ('aprobar', 'Aprobar (Transferir)'),
                    ('rechazar', 'Cancelar Transferencia'),
                ]
            respuesta = forms.ChoiceField(choices=opciones, widget=forms.RadioSelect, label='Acción')
        form = _RespuestaForm()
    return render(request, 'herramientas/responder_solicitud.html', {
        'titulo': 'Responder Transferencia de Herramienta',
        'transferencia': transferencia,
        'form': form,
        'es_origen': es_origen,
        'es_destino': es_destino,
    })


@login_required
def inspeccionar_herramienta(request, pk):
    transferencia = get_object_or_404(TransferenciaHerramienta, pk=pk)
    # Bloquear administración desde notificaciones
    if request.GET.get('from_notification') and request.user.is_superuser:
        return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado or transferencia.empleado_destino != empleado:
        messages.error(request, 'No puedes inspeccionar esta transferencia.')
        return redirect('perfil_usuario')
    # Si aún está solicitada, pasarla a inspección automáticamente
    if transferencia.estado == 'solicitada':
        transferencia.estado = 'inspeccion'
        transferencia.fecha_inspeccion = timezone.now()
        transferencia.save(update_fields=['estado', 'fecha_inspeccion'])
        # Notificar origen y administradores de inicio de inspección
        Notificacion.objects.create(
            usuario=transferencia.empleado_origen.usuario,
            titulo='🔍 Inspección de Herramienta',
            mensaje=f'{empleado.usuario.get_full_name()} inició inspección de la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
            tipo='warning',
            url=f"/herramientas/transferencias/{transferencia.pk}/"
        )
        _notificar_admins(
            titulo='🔍 Inspección de Herramienta Iniciada',
            mensaje=f'{empleado.usuario.get_full_name()} está inspeccionando la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}).',
            url=f"/herramientas/transferencias/{transferencia.pk}/",
            exclude_ids=[empleado.usuario_id, transferencia.empleado_origen.usuario_id]
        )
        messages.info(request, 'Has iniciado la inspección de la herramienta.')
    elif transferencia.estado != 'inspeccion':
        messages.info(request, 'La transferencia no está en estado de inspección.')
        return redirect('herramientas:transferencia_detalle', pk=transferencia.pk)
    if request.method == 'POST':
        obs = request.POST.get('observaciones', '').strip()
        # Reemplazar observaciones acumulativas por consolidación antes de enviar
        if obs:
            transferencia.observaciones_inspeccion += f"\n{obs}" if transferencia.observaciones_inspeccion else obs
        # Enviar inspección: cambiar estado y notificar
        transferencia.estado = 'inspeccion_enviada'
        transferencia.save(update_fields=['observaciones_inspeccion', 'estado'])
        # Notificación al origen
        Notificacion.objects.create(
            usuario=transferencia.empleado_origen.usuario,
            titulo='📤 Inspección de Herramienta Enviada',
            mensaje=f'{empleado.usuario.get_full_name()} envió la inspección de la herramienta {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}). Debes aprobar o cancelar la transferencia.',
            tipo='info',
            # Enviar directo al template de decisión (responder)
            url=f"/herramientas/transferencias/{transferencia.pk}/responder/"
        )
        _notificar_admins(
            titulo='📤 Inspección de Herramienta Enviada',
            mensaje=f'Se envió la inspección de {transferencia.herramienta.nombre} ({transferencia.herramienta.codigo}); pendiente decisión del solicitante.',
            url=f"/herramientas/transferencias/{transferencia.pk}/",
            exclude_ids=[empleado.usuario_id, transferencia.empleado_origen.usuario_id]
        )
        messages.success(request, 'Tu inspección ha sido enviada al solicitante. Si la aprueba, la herramienta será transferida automáticamente; si la cancela, se cerrará la solicitud.')
        return redirect('herramientas:transferencia_detalle', pk=transferencia.pk)
    return render(request, 'herramientas/inspeccionar_herramienta.html', {
        'titulo': 'Inspeccionar Herramienta',
        'transferencia': transferencia,
    })


@login_required
def mis_transferencias_herramientas(request):
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')
    origen = TransferenciaHerramienta.objects.filter(empleado_origen=empleado).select_related('herramienta', 'empleado_destino__usuario')
    destino = TransferenciaHerramienta.objects.filter(empleado_destino=empleado).select_related('herramienta', 'empleado_origen__usuario')
    return render(request, 'herramientas/mis_transferencias.html', {
        'titulo': 'Mis Transferencias de Herramientas',
        'transferencias_origen': origen,
        'transferencias_destino': destino,
    })