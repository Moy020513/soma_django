from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from django.utils import timezone
from django.db import transaction

from .models import TransferenciaVehicular, AsignacionVehiculo, Vehiculo
from .forms import (
    SolicitudTransferenciaForm,
    InspeccionTransferenciaForm,
    RespuestaTransferenciaForm,
    GasolinaRequestCreateForm,
    GasolinaComprobanteForm,
)
from .models import GasolinaRequest
from apps.recursos_humanos.models import Empleado
from apps.notificaciones.models import Notificacion
from apps.usuarios.models import Usuario
from django.urls import reverse
from django.db.models import Q


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
                # Notificar a administradores que se creó una nueva solicitud de transferencia
                try:
                    admins = Usuario.objects.filter(is_staff=True)
                    for admin in admins:
                        noti = Notificacion.objects.create(
                            usuario=admin,
                            titulo='📣 Nueva solicitud de transferencia',
                            mensaje=f'El usuario {empleado.usuario.get_full_name()} ha solicitado transferir el vehículo {asignacion.vehiculo} a {transferencia.empleado_destino.usuario.get_full_name()}.',
                            tipo='info',
                        )
                        # Poner la URL al detalle de la notificación para que el dropdown apunte al recurso concreto
                        try:
                            noti.url = reverse('notificaciones:detalle_usuario', args=[noti.id])
                            noti.save()
                        except Exception:
                            # Si falla construir la URL no bloqueamos la operación
                            pass
                except Exception:
                    # No bloquear la operación de transferencia ante fallo en notificaciones a admins
                    pass
                
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
                # Notificar a administradores sobre la transferencia aprobada
                try:
                    admins = Usuario.objects.filter(is_staff=True)
                    for admin in admins:
                        noti = Notificacion.objects.create(
                            usuario=admin,
                            titulo='🚚 Transferencia aprobada',
                            mensaje=f'La transferencia del vehículo {transferencia.vehiculo} de {transferencia.empleado_origen.usuario.get_full_name()} a {transferencia.empleado_destino.usuario.get_full_name()} ha sido aprobada.',
                            tipo='info',
                        )
                        try:
                            noti.url = reverse('notificaciones:detalle_usuario', args=[noti.id])
                            noti.save()
                        except Exception:
                            pass
                except Exception:
                    pass
                
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
                    titulo='🔍 Inspección de Transferencia Completada',
                    mensaje=f'{empleado.usuario.get_full_name()} ha completado la inspección del vehículo {transferencia.vehiculo}.\n\n✅ Revisa las observaciones y decide si aprobar o rechazar la transferencia.',
                    tipo='warning',
                    url=f'/flota/transferencias/{transferencia.pk}/responder/'
                )

                # Notificar a administradores sobre la inspección realizada
                try:
                    admins = Usuario.objects.filter(is_staff=True)
                    for admin in admins:
                        # Incluir las observaciones de inspección en el mensaje para que se muestren
                        inspeccion_msg = f'El empleado {empleado.usuario.get_full_name()} ha completado la inspección del vehículo {transferencia.vehiculo} para la transferencia hacia {transferencia.empleado_origen.usuario.get_full_name()}.'
                        if transferencia.observaciones_inspeccion:
                            inspeccion_msg += "\n\nObservaciones de la inspección:\n" + transferencia.observaciones_inspeccion
                        noti = Notificacion.objects.create(
                            usuario=admin,
                            titulo='🔔 Inspección de transferencia completada',
                            mensaje=inspeccion_msg,
                            tipo='info',
                        )
                        try:
                            noti.url = reverse('notificaciones:detalle_usuario', args=[noti.id])
                            noti.save()
                        except Exception:
                            pass
                except Exception:
                    # No bloquear la operación si falla el envío de notificaciones a admins
                    pass

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

    # Si viene de notificación, marcarla como leída (si es del usuario)
    if from_notification:
        try:
            notificacion = Notificacion.objects.get(id=from_notification, usuario=request.user, leida=False)
            notificacion.leida = True
            notificacion.save()
        except Notificacion.DoesNotExist:
            pass

    # Buscar la transferencia y manejar casos donde ya cambió de estado para evitar 404
    try:
        transferencia = TransferenciaVehicular.objects.select_related('vehiculo', 'empleado_destino__usuario').get(pk=pk)
    except TransferenciaVehicular.DoesNotExist:
        messages.error(request, 'La transferencia no existe o ya no está disponible.')
        return redirect('flota:mis_transferencias')

    # Verificar que quien responde es el empleado origen
    if transferencia.empleado_origen != empleado:
        messages.error(request, 'No tienes permisos para responder la inspección de esta transferencia.')
        return redirect('flota:mis_transferencias')

    # Si la transferencia ya no está en inspección, redirigir con mensaje explicativo
    if transferencia.estado != 'inspeccion':
        if transferencia.estado == 'aprobada':
            messages.info(request, 'Esta transferencia ya fue aprobada.')
            return redirect('flota:transferencia_detalle', pk=transferencia.pk)
        if transferencia.estado == 'rechazada':
            messages.info(request, 'La inspección ya fue respondida y la transferencia fue rechazada.')
            return redirect('flota:transferencia_detalle', pk=transferencia.pk)
        if transferencia.estado == 'solicitada':
            messages.info(request, 'La transferencia aún está en estado de solicitud.')
            return redirect('flota:transferencia_detalle', pk=transferencia.pk)
        if transferencia.estado == 'cancelada':
            messages.info(request, 'La transferencia fue cancelada.')
            return redirect('flota:mis_transferencias')
        # Caso por defecto
        messages.info(request, 'El estado de la transferencia no permite responder la inspección en este momento.')
        return redirect('flota:transferencia_detalle', pk=transferencia.pk)
    
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
                    # Notificar a administradores sobre la transferencia aprobada (desde inspección)
                    try:
                        admins = Usuario.objects.filter(is_staff=True)
                        for admin in admins:
                            noti = Notificacion.objects.create(
                                usuario=admin,
                                titulo='🚚 Transferencia aprobada',
                                mensaje=f'La transferencia del vehículo {transferencia.vehiculo} de {empleado.usuario.get_full_name()} a {transferencia.empleado_destino.usuario.get_full_name()} ha sido aprobada tras inspección.',
                                tipo='info',
                            )
                            try:
                                noti.url = reverse('notificaciones:detalle_usuario', args=[noti.id])
                                noti.save()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
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
                    # Notificar a administradores sobre el rechazo de la inspección
                    try:
                        admins = Usuario.objects.filter(is_staff=True)
                        for admin in admins:
                            admin_msg = f'El empleado {empleado.usuario.get_full_name()} ha rechazado la inspección del vehículo {transferencia.vehiculo}.'
                            if observaciones:
                                admin_msg += "\n\nObservaciones de la respuesta:\n" + observaciones
                            noti = Notificacion.objects.create(
                                usuario=admin,
                                titulo='🔔 Inspección Rechazada',
                                mensaje=admin_msg,
                                tipo='warning',
                            )
                            try:
                                noti.url = reverse('notificaciones:detalle_usuario', args=[noti.id])
                                noti.save()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
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


@login_required
def pedir_gasolina(request):
    """Permite al empleado subir comprobante de gasolina con precio; notifica a todos los admins."""
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')

    # Determinar vehículo asignado (interno primero, luego externo)
    asignacion = AsignacionVehiculo.objects.filter(empleado=empleado, estado='activa').select_related('vehiculo').first()
    vehiculo = None
    vehiculo_externo = None
    if asignacion:
        vehiculo = asignacion.vehiculo
    else:
        try:
            from .models import AsignacionVehiculoExterno
            asign_ext = AsignacionVehiculoExterno.objects.filter(empleado=empleado, estado='activa').select_related('vehiculo_externo').first()
            if asign_ext:
                vehiculo_externo = asign_ext.vehiculo_externo
        except Exception:
            vehiculo_externo = None

    if not vehiculo and not vehiculo_externo:
        messages.info(request, 'No tienes un vehículo asignado para solicitar gasolina.')
        return redirect('perfil_usuario')

    # Revisar la última solicitud del empleado para aplicar reglas de flujo
    from .models import GasolinaRequest
    ultima = GasolinaRequest.objects.filter(empleado=empleado).order_by('-fecha').first()
    # Además revisar si existe alguna solicitud con comprobante subido que aún no ha sido validada
    try:
        pendiente_validacion = GasolinaRequest.objects.filter(
            empleado=empleado
        ).filter(
            Q(comprobante__isnull=False) & Q(monto_comprobado__isnull=True) | Q(estado='parcial')
        ).exists()
    except Exception:
        pendiente_validacion = False
    if pendiente_validacion:
        messages.info(request, 'Tienes una solicitud con comprobante subido pendiente de validación por administración. Espera a que se confirme (completo o parcial).')
        return redirect('mi_vehiculo')
    if ultima:
        # Si hay una solicitud pendiente, bloquear nueva solicitud
        if ultima.estado == 'pendiente':
            messages.info(request, 'Ya tienes una solicitud pendiente. Espera a que sea revisada.')
            return redirect('mi_vehiculo')

        # Si la solicitud aún no tiene comprobante, pedir subir comprobante antes de crear otra solicitud.
        if not ultima.comprobante:
            messages.warning(request, f'Falta tu comprobante de tu solicitud de {ultima.precio} MXN. Sube el comprobante antes de crear otra solicitud.')
            return redirect('flota:subir_comprobante_gasolina', pk=ultima.pk)

        # Si ya subiste el comprobante pero aún no ha sido validado por admin (monto_comprobado es None),
        # bloquear nueva solicitud hasta la validación.
        try:
            if ultima.comprobante and (ultima.monto_comprobado is None):
                messages.info(request, 'Has subido el comprobante y está pendiente de validación por administración. Espera a que se confirme (completo o parcial).')
                return redirect('mi_vehiculo')
        except Exception:
            # Si hay algún problema con el campo previsto, no bloquear la creación (fallo seguro)
            pass

        # Si ya se comprobó parcialmente, indicar al usuario cuánto falta y dirigir a subir comprobante
        try:
            if ultima.monto_comprobado is not None and ultima.monto_comprobado < ultima.precio:
                restante = ultima.precio - ultima.monto_comprobado
                messages.info(request, f'Tienes un monto pendiente de comprobación por ${restante}. Sube el comprobante adicional para completar la solicitud.')
                return redirect('flota:subir_comprobante_gasolina', pk=ultima.pk)
        except Exception:
            # Si hay algún problema con el campo previsto, no bloquear la creación (fallo seguro)
            pass

    if request.method == 'POST':
        form = GasolinaRequestCreateForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.empleado = empleado
            req.vehiculo = vehiculo
            req.vehiculo_externo = vehiculo_externo
            # estado por defecto es 'pendiente'
            req.save()

            # Notificar a todos los administradores
            admins = Usuario.objects.filter(is_staff=True)
            for admin in admins:
                try:
                    url = reverse('admin:flota_vehicular_gasolinarequest_change', args=[req.pk])
                except Exception:
                    url = ''
                mensaje = f'El empleado {empleado.usuario.get_full_name()} ha solicitado gasolina para {vehiculo or vehiculo_externo} por {req.precio} MXN.'
                noti = Notificacion.objects.create(
                    usuario=admin,
                    titulo='📄 Nueva solicitud de gasolina',
                    mensaje=mensaje,
                    tipo='info',
                    url=''
                )
                try:
                    noti.url = reverse('notificaciones:admin_detalle', args=[noti.pk]) + f'?gasolina_id={req.pk}'
                    noti.save()
                except Exception:
                    pass

            messages.success(request, 'Solicitud enviada. Los administradores serán notificados.')
            return redirect('mi_vehiculo')
    else:
        form = GasolinaRequestCreateForm()

    context = {
        'form': form,
        'vehiculo': vehiculo or vehiculo_externo,
        'empleado': empleado,
        'titulo': 'Pedir gasolina',
    }
    return render(request, 'flota_vehicular/pedir_gasolina.html', context)


@login_required
def subir_comprobante_gasolina(request, pk):
    """Permite al empleado subir el comprobante solo después de que su solicitud haya sido revisada
    (estado 'revisado' o 'rechazado'). La opción sólo aparece/está disponible si la solicitud no tiene comprobante.
    """
    empleado = Empleado.objects.filter(usuario=request.user).first()
    if not empleado:
        messages.error(request, 'Tu usuario no está asociado a un empleado.')
        return redirect('perfil_usuario')

    req = get_object_or_404(GasolinaRequest, pk=pk)

    # Verificar permisos
    if req.empleado != empleado:
        messages.error(request, 'No tienes permisos para subir comprobante a esta solicitud.')
        return redirect('mi_vehiculo')

    # Sólo permitir si ya fue revisada (aceptada/rechazada) o si está en estado 'parcial'.
    if req.estado == 'pendiente':
        messages.info(request, 'La solicitud aún está pendiente de revisión por un administrador.')
        return redirect('mi_vehiculo')

    # Si ya fue completamente comprobada, no permitir más uploads
    if req.estado == 'comprobado':
        messages.info(request, 'La solicitud ya fue completamente comprobada. No es posible subir más comprobantes.')
        return redirect('mi_vehiculo')

    # Si ya hay un comprobante y la solicitud NO está en estado 'parcial', bloquear la subida (evitar sobrescribir accidentalmente)
    if req.comprobante and req.estado != 'parcial':
        messages.info(request, 'Esta solicitud ya tiene comprobante subido.')
        return redirect('mi_vehiculo')

    if request.method == 'POST':
        form = GasolinaComprobanteForm(request.POST, request.FILES, instance=req)
        if form.is_valid():
            form.save()
            # Marcar como leída la notificación si venimos desde una notificación
            from_notification = request.GET.get('from_notification')
            if from_notification:
                try:
                    noti = Notificacion.objects.get(id=from_notification, usuario=request.user, leida=False)
                    noti.leida = True
                    noti.save()
                except Notificacion.DoesNotExist:
                    pass

            # Respaldo: notificar a administradores si no lo hizo la señal (chequeo idempotente)
            try:
                import logging
                logger = logging.getLogger(__name__)
                from apps.usuarios.models import Usuario
                admins = Usuario.objects.filter(is_staff=True)
                for admin in admins:
                    titulo_admin = '📥 Comprobante de gasolina subido'
                    mensaje_admin = f'El empleado {req.empleado.usuario.get_full_name()} ha subido un comprobante de gasolina para {req.vehiculo or req.vehiculo_externo} por ${req.precio}.'
                    try:
                        if req.comprobante:
                            mensaje_admin += f' Comprobante: {req.comprobante.url}'
                    except Exception:
                        # No bloquear la creación de la notificación por error al acceder al URL
                        pass
                    try:
                        noti = Notificacion.objects.create(
                            usuario=admin,
                            titulo=titulo_admin,
                            mensaje=mensaje_admin,
                            tipo='info',
                            url=''
                        )
                        try:
                            noti.url = reverse('notificaciones:admin_detalle', args=[noti.pk]) + f'?gasolina_id={req.pk}'
                            noti.save()
                        except Exception as e:
                            logger.exception('Error construyendo URL de notificación admin: %s', e)
                    except Exception as e:
                        logger.exception('Error creando notificación para admin %s: %s', admin, e)
            except Exception as e:
                # Registrar fallo general para no silenciar errores
                import logging
                logging.getLogger(__name__).exception('Error en notificación admins tras subir comprobante: %s', e)
            except Exception:
                pass
            messages.success(request, 'Comprobante subido correctamente. Gracias.')
            return redirect('mi_vehiculo')
    else:
        form = GasolinaComprobanteForm(instance=req)

    # Si llegamos desde una notificación y es del usuario, marcarla como leída (GET request)
    from_notification = request.GET.get('from_notification')
    if from_notification and request.user.is_authenticated:
        try:
            noti = Notificacion.objects.get(id=from_notification, usuario=request.user, leida=False)
            noti.leida = True
            noti.save()
        except Notificacion.DoesNotExist:
            pass

    # Si venimos desde una notificación y la solicitud está parcialmente comprobada,
    # mostrar un flash con cuánto se comprobó y cuánto falta.
    if request.method == 'GET' and from_notification:
        try:
            if req.monto_comprobado is not None and req.monto_comprobado < req.precio:
                restante = req.precio - req.monto_comprobado
                messages.info(request, f'Comprobante parcial: se ha comprobado ${req.monto_comprobado}. Falta por comprobar ${restante}.')
        except Exception:
            pass

    context = {
        'form': form,
        'solicitud': req,
        'titulo': 'Subir comprobante de gasolina',
    }
    return render(request, 'flota_vehicular/subir_comprobante_gasolina.html', context)