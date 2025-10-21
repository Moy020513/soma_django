from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone
from django.db import transaction

from .models import TransferenciaVehicular, AsignacionVehiculo, Vehiculo
from .forms import SolicitudTransferenciaForm, InspeccionTransferenciaForm, RespuestaTransferenciaForm
from apps.recursos_humanos.models import Empleado
from apps.notificaciones.models import Notificacion


@login_required
def solicitar_transferencia(request):
    """Vista para solicitar la transferencia de un vehículo"""
    
    # Verificar que el usuario tenga un empleado asociado
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('mi_vehiculo')
    
    # Verificar que tenga un vehículo asignado
    asignacion = AsignacionVehiculo.objects.filter(
        empleado=empleado, 
        estado='activa'
    ).select_related('vehiculo').first()
    
    if not asignacion:
        messages.error(request, 'No tienes un vehículo asignado actualmente.')
        return redirect('perfil_usuario')
    
    # Verificar transferencias pendientes del vehículo actual
    transferencia_pendiente = TransferenciaVehicular.objects.filter(
        empleado_origen=empleado,
        vehiculo=asignacion.vehiculo,
        estado__in=['solicitada', 'inspeccion']
    ).first()
    
    # Cancelar transferencias huérfanas (de vehículos que ya no tiene asignados)
    transferencias_huerfanas = TransferenciaVehicular.objects.filter(
        empleado_origen=empleado,
        estado__in=['solicitada', 'inspeccion']
    ).exclude(vehiculo=asignacion.vehiculo)
    
    if transferencias_huerfanas.exists():
        transferencias_huerfanas.update(
            estado='cancelada',
            fecha_respuesta=timezone.now(),
            observaciones_inspeccion='Cancelada automáticamente: el vehículo fue reasignado a otro empleado.'
        )
        
        # Notificar a los empleados destino de las transferencias canceladas
        for transferencia in transferencias_huerfanas:
            Notificacion.objects.create(
                usuario=transferencia.empleado_destino.usuario,
                titulo='⚠️ Transferencia Cancelada',
                mensaje=f'La transferencia del vehículo {transferencia.vehiculo} ha sido cancelada porque fue reasignado.',
                tipo='warning',
                url=f'/flota/transferencias/'
            )
    
    if transferencia_pendiente:
        return redirect('flota:transferencia_detalle', pk=transferencia_pendiente.pk)
    
    if request.method == 'POST':
        form = SolicitudTransferenciaForm(request.POST, empleado_actual=empleado)
        if form.is_valid():
            with transaction.atomic():
                transferencia = form.save(commit=False)
                transferencia.vehiculo = asignacion.vehiculo
                transferencia.empleado_origen = empleado
                transferencia.estado = 'solicitada'
                print(f"[DEBUG] Estado a guardar: '{transferencia.estado}' (longitud: {len(transferencia.estado)})")
                print(f"[DEBUG] Empleado origen: {transferencia.empleado_origen}")
                print(f"[DEBUG] Empleado destino: {transferencia.empleado_destino}")
                transferencia.save()
                
                # Crear notificación para el empleado destino
                Notificacion.objects.create(
                    usuario=transferencia.empleado_destino.usuario,
                    titulo=f'🚗 Solicitud de Transferencia de Vehículo',
                    mensaje=f'{empleado.usuario.get_full_name()} te ha enviado una solicitud para transferirte el vehículo {asignacion.vehiculo}.\n\n✅ Haz clic en "Responder Solicitud" para aceptar o rechazar la transferencia.',
                    tipo='info',
                    url=f'/flota/transferencias/{transferencia.pk}/responder-solicitud/'
                )
                
                messages.success(request, f'Solicitud de transferencia enviada a {transferencia.empleado_destino.usuario.get_full_name()}')
                return redirect('flota:transferencia_detalle', pk=transferencia.pk)
    else:
        form = SolicitudTransferenciaForm(empleado_actual=empleado)
    
    context = {
        'form': form,
        'vehiculo': asignacion.vehiculo,
        'empleado': empleado,
        'titulo': 'Solicitar Transferencia de Vehículo',
    }
    return render(request, 'flota_vehicular/solicitar_transferencia.html', context)


@login_required
def transferencia_detalle(request, pk):
    """Vista para ver los detalles de una transferencia"""
    
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('home')
    
    transferencia = get_object_or_404(
        TransferenciaVehicular.objects.select_related(
            'vehiculo', 'empleado_origen__usuario', 'empleado_destino__usuario'
        ),
        pk=pk
    )
    
    # Verificar que el usuario esté involucrado en la transferencia
    if transferencia.empleado_origen != empleado and transferencia.empleado_destino != empleado:
        raise Http404("No tienes permisos para ver esta transferencia.")
    
    context = {
        'transferencia': transferencia,
        'empleado': empleado,
        'es_origen': transferencia.empleado_origen == empleado,
        'es_destino': transferencia.empleado_destino == empleado,
        'titulo': 'Detalle de Transferencia',
    }
    return render(request, 'flota_vehicular/transferencia_detalle.html', context)


@login_required
def responder_solicitud(request, pk):
    """Vista para que el empleado destino responda directamente a la solicitud"""
    # Comprobar si viene de notificación y bloquear admins inmediatamente
    from_notification = request.GET.get('from_notification')
    if from_notification and request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')

    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('home')
    if from_notification:
        try:
            notificacion = Notificacion.objects.get(
                id=from_notification,
                usuario=request.user,
                leida=False
            )
            notificacion.leida = True
            notificacion.save()
        except Notificacion.DoesNotExist:
            pass  # La notificación ya fue leída o no existe
    
    # Buscar la transferencia con mejor manejo de errores
    try:
        transferencia = TransferenciaVehicular.objects.select_related(
            'vehiculo', 'empleado_origen__usuario'
        ).get(pk=pk)
        
        # Verificar que la transferencia es para este empleado
        if transferencia.empleado_destino != empleado:
            messages.error(request, 'Esta solicitud de transferencia no está dirigida a ti.')
            return redirect('flota:mis_transferencias')
        
        # Verificar que está en estado correcto
        if transferencia.estado != 'solicitada':
            if transferencia.estado == 'aprobada':
                messages.info(request, 'Esta transferencia ya fue aprobada.')
            elif transferencia.estado == 'rechazada':
                messages.info(request, 'Esta transferencia ya fue rechazada.')
            elif transferencia.estado == 'cancelada':
                messages.info(request, 'Esta transferencia fue cancelada.')
            elif transferencia.estado == 'inspeccion':
                messages.info(request, 'Esta transferencia está en proceso de inspección.')
            return redirect('flota:mis_transferencias')
            
    except TransferenciaVehicular.DoesNotExist:
        messages.error(request, 'La solicitud de transferencia no existe o ya no está disponible.')
        return redirect('flota:mis_transferencias')
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        observaciones = request.POST.get('observaciones', '')
        
        if accion == 'aceptar':
            with transaction.atomic():
                # Crear nueva asignación para el empleado destino
                nueva_asignacion = AsignacionVehiculo.objects.create(
                    empleado=empleado,
                    vehiculo=transferencia.vehiculo,
                    fecha_asignacion=timezone.now(),
                    estado='activa'
                )
                
                # Finalizar asignación anterior
                asignacion_anterior = AsignacionVehiculo.objects.filter(
                    empleado=transferencia.empleado_origen,
                    vehiculo=transferencia.vehiculo,
                    estado='activa'
                ).first()
                
                if asignacion_anterior:
                    asignacion_anterior.fecha_finalizacion = timezone.now()
                    asignacion_anterior.estado = 'finalizada'
                    asignacion_anterior.save()
                
                # Actualizar transferencia
                transferencia.estado = 'aprobada'
                transferencia.fecha_respuesta = timezone.now()
                if observaciones:
                    transferencia.observaciones_inspeccion = observaciones
                transferencia.save()
                
                # Crear notificación para el empleado origen
                Notificacion.objects.create(
                    usuario=transferencia.empleado_origen.usuario,
                    titulo='✅ Transferencia Aceptada',
                    mensaje=f'{empleado.usuario.get_full_name()} ha aceptado la transferencia del vehículo {transferencia.vehiculo}',
                    tipo='success',
                    url=f'/flota/transferencias/{transferencia.pk}/'
                )
                
                messages.success(request, 'Transferencia aceptada. El vehículo ha sido asignado a ti.')
                return redirect('mi_vehiculo')
        
        elif accion == 'rechazar':
            transferencia.estado = 'rechazada'
            transferencia.fecha_respuesta = timezone.now()
            if observaciones:
                transferencia.observaciones_inspeccion = observaciones
            transferencia.save()
            
            # Crear notificación para el empleado origen
            Notificacion.objects.create(
                usuario=transferencia.empleado_origen.usuario,
                titulo='❌ Transferencia Rechazada',
                mensaje=f'{empleado.usuario.get_full_name()} ha rechazado la transferencia del vehículo {transferencia.vehiculo}',
                tipo='danger',
                url=f'/flota/transferencias/{transferencia.pk}/'
            )
            
            messages.info(request, 'Transferencia rechazada.')
            return redirect('flota:transferencia_detalle', pk=transferencia.pk)
    
    context = {
        'transferencia': transferencia,
        'empleado': empleado,
        'titulo': 'Responder Solicitud de Transferencia',
    }
    return render(request, 'flota_vehicular/responder_solicitud.html', context)


@login_required
def inspeccionar_vehiculo(request, pk):
    """Vista para que el empleado destino inspeccione el vehículo"""
    
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('home')
    
    # Comprobar si viene de notificación y bloquear admins inmediatamente
    from_notification = request.GET.get('from_notification')
    if from_notification and request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')

    transferencia = get_object_or_404(
        TransferenciaVehicular.objects.select_related('vehiculo', 'empleado_origen__usuario'),
        pk=pk,
        empleado_destino=empleado,
        estado='solicitada'
    )
    
    if request.method == 'POST':
        form = InspeccionTransferenciaForm(request.POST, instance=transferencia)
        if form.is_valid():
            with transaction.atomic():
                transferencia = form.save(commit=False)
                # Cambiar estado a 'inspeccion'
                transferencia.estado = 'inspeccion'
                transferencia.fecha_inspeccion = timezone.now()
                transferencia.save()
                
                # Crear notificación para el empleado origen
                Notificacion.objects.create(
                    usuario=transferencia.empleado_origen.usuario,
                    titulo=f'🔍 Inspección de Transferencia Completada',
                    mensaje=f'{empleado.usuario.get_full_name()} ha completado la inspección del vehículo {transferencia.vehiculo}.\n\n✅ Revisa las observaciones y decide si aprobar o rechazar la transferencia.',
                    tipo='warning',
                    url=f'/flota/transferencias/{transferencia.pk}/responder/'
                )
                
                messages.success(request, 'Inspección registrada. El propietario actual revisará tus observaciones.')
                return redirect('flota:transferencia_detalle', pk=transferencia.pk)
    else:
        form = InspeccionTransferenciaForm(instance=transferencia)
    
    context = {
        'form': form,
        'transferencia': transferencia,
        'empleado': empleado,
        'titulo': 'Inspeccionar Vehículo',
    }
    return render(request, 'flota_vehicular/inspeccionar_vehiculo.html', context)


@login_required
def responder_inspeccion(request, pk):
    """Vista para que el empleado origen responda a la inspección"""
    
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('home')
    
    # Comprobar si viene de notificación y bloquear admins inmediatamente
    from_notification = request.GET.get('from_notification')
    if from_notification and request.user.is_superuser:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('Los administradores no pueden responder notificaciones.')

    transferencia = get_object_or_404(
        TransferenciaVehicular.objects.select_related('vehiculo', 'empleado_destino__usuario'),
        pk=pk,
        empleado_origen=empleado,
        estado='inspeccion'
    )
    
    if request.method == 'POST':
        form = RespuestaTransferenciaForm(request.POST)
        if form.is_valid():
            respuesta = form.cleaned_data['respuesta']
            observaciones = form.cleaned_data['observaciones']
            
            with transaction.atomic():
                if respuesta == 'aprobar':
                    # Aprobar la transferencia
                    transferencia.estado = 'aprobada'
                    transferencia.fecha_transferencia = timezone.now()
                    
                    # Finalizar la asignación actual
                    asignacion_actual = AsignacionVehiculo.objects.get(
                        vehiculo=transferencia.vehiculo,
                        empleado=empleado,
                        estado='activa'
                    )
                    asignacion_actual.estado = 'finalizada'
                    asignacion_actual.fecha_finalizacion = timezone.now().date()
                    asignacion_actual.save()
                    
                    # Crear nueva asignación para el empleado destino
                    AsignacionVehiculo.objects.create(
                        vehiculo=transferencia.vehiculo,
                        empleado=transferencia.empleado_destino,
                        fecha_asignacion=timezone.now().date(),
                        estado='activa',
                        observaciones=f'Transferido de {empleado.usuario.get_full_name()}'
                    )
                    
                    # Actualizar kilometraje del vehículo
                    if transferencia.kilometraje_transferencia:
                        transferencia.vehiculo.kilometraje_actual = transferencia.kilometraje_transferencia
                        transferencia.vehiculo.save()
                    
                    # Crear notificación de aprobación
                    Notificacion.objects.create(
                        usuario=transferencia.empleado_destino.usuario,
                        titulo=f'✅ Transferencia Aprobada',
                        mensaje=f'¡Felicidades! {empleado.usuario.get_full_name()} ha aprobado la transferencia. El vehículo {transferencia.vehiculo} ahora es tuyo.',
                        tipo='success'
                    )
                    
                    messages.success(request, f'Transferencia aprobada. El vehículo ahora pertenece a {transferencia.empleado_destino.usuario.get_full_name()}.')
                    
                else:
                    # Rechazar la transferencia
                    transferencia.estado = 'rechazada'
                    
                    # Crear notificación de rechazo
                    Notificacion.objects.create(
                        usuario=transferencia.empleado_destino.usuario,
                        titulo=f'❌ Transferencia Rechazada',
                        mensaje=f'{empleado.usuario.get_full_name()} ha rechazado la transferencia del vehículo {transferencia.vehiculo}.',
                        tipo='danger'
                    )
                    
                    messages.info(request, 'Transferencia rechazada.')
                
                # Guardar observaciones adicionales si las hay
                if observaciones:
                    transferencia.observaciones_solicitud += f'\n\nRespuesta: {observaciones}'
                
                transferencia.save()
                
                return redirect('flota:transferencia_detalle', pk=transferencia.pk)
    else:
        form = RespuestaTransferenciaForm()
    
    context = {
        'form': form,
        'transferencia': transferencia,
        'empleado': empleado,
        'titulo': 'Responder a Inspección',
    }
    return render(request, 'flota_vehicular/responder_inspeccion.html', context)


@login_required
def mis_transferencias(request):
    """Vista para listar las transferencias del usuario"""
    
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('home')
    
    # Transferencias como origen (vehículos que está transfiriendo)
    transferencias_origen = TransferenciaVehicular.objects.filter(
        empleado_origen=empleado
    ).select_related('vehiculo', 'empleado_destino__usuario').order_by('-fecha_solicitud')
    
    # Transferencias como destino (vehículos que le están transfiriendo)
    transferencias_destino = TransferenciaVehicular.objects.filter(
        empleado_destino=empleado
    ).select_related('vehiculo', 'empleado_origen__usuario').order_by('-fecha_solicitud')
    
    context = {
        'transferencias_origen': transferencias_origen,
        'transferencias_destino': transferencias_destino,
        'empleado': empleado,
        'titulo': 'Mis Transferencias',
    }
    return render(request, 'flota_vehicular/mis_transferencias.html', context)