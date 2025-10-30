from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, date, timedelta
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import IntegrityError

from .models import RegistroUbicacion
from .forms import RegistroUbicacionForm
from apps.recursos_humanos.models import Empleado


class EmpleadoRequiredMixin(LoginRequiredMixin):
    """Mixin para verificar que el usuario tenga un empleado asociado"""
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'empleado'):
            messages.error(request, 'No tienes un perfil de empleado asociado.')
            return redirect('admin:index')
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin para verificar que el usuario sea staff"""
    
    def test_func(self):
        return self.request.user.is_staff


class RegistrarUbicacionView(EmpleadoRequiredMixin, TemplateView):
    """Vista principal para que los empleados registren su ubicación"""
    template_name = 'ubicaciones/registrar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empleado = self.request.user.empleado
        hoy = timezone.now().date()
        
        # Verificar si ya registró entrada y salida hoy
        ya_registro_entrada = RegistroUbicacion.ya_registro_hoy(empleado, 'entrada')
        ya_registro_salida = RegistroUbicacion.ya_registro_hoy(empleado, 'salida')
        
        # Obtener registros de hoy (usando el campo `fecha` para consistencia)
        registros_hoy = RegistroUbicacion.objects.filter(
            empleado=empleado,
            fecha=hoy
        ).order_by('timestamp')
        
        # Obtener registros recientes (últimos 5)
        registros_recientes = RegistroUbicacion.objects.filter(
            empleado=empleado
        ).order_by('-timestamp')[:5]
        
        context.update({
            'empleado': empleado,
            'ya_registro_entrada': ya_registro_entrada,
            'ya_registro_salida': ya_registro_salida,
            'registros_hoy': registros_hoy,
            'registros_recientes': registros_recientes,
            'form': RegistroUbicacionForm(empleado=empleado),
        })
        # Calcular el momento en que vuelve a ser posible registrar (inicio del siguiente día
        # usando la zona horaria activa/configurada en settings)
        # timezone.localtime(timezone.now()) respeta TIME_ZONE y el timezone activo.
        local_now = timezone.localtime(timezone.now())
        next_day_start = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        if ya_registro_entrada:
            # timestamp en milisegundos para uso en JS
            context['next_allowed_entrada_ts'] = int(next_day_start.timestamp() * 1000)
            context['next_allowed_entrada_display'] = next_day_start.strftime('%Y-%m-%d %H:%M:%S %Z')
        else:
            context['next_allowed_entrada_ts'] = None
            context['next_allowed_entrada_display'] = None

        if ya_registro_salida:
            context['next_allowed_salida_ts'] = int(next_day_start.timestamp() * 1000)
            context['next_allowed_salida_display'] = next_day_start.strftime('%Y-%m-%d %H:%M:%S %Z')
        else:
            context['next_allowed_salida_ts'] = None
            context['next_allowed_salida_display'] = None

        return context


@method_decorator(csrf_exempt, name='dispatch')
class RegistrarUbicacionAPIView(EmpleadoRequiredMixin, View):
    """API endpoint para registrar ubicación desde JavaScript"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Manejar tanto JSON como FormData
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # FormData desde el frontend
                data = {
                    'tipo': request.POST.get('tipo'),
                    'latitud': request.POST.get('latitud'),
                    'longitud': request.POST.get('longitud'),
                    'precision': request.POST.get('precision'),
                }
            
            empleado = request.user.empleado
            
            # Validar datos requeridos
            required_fields = ['latitud', 'longitud', 'tipo']
            for field in required_fields:
                if field not in data or not data[field]:
                    return JsonResponse({
                        'success': False,
                        'message': f'Campo requerido: {field}'
                    }, status=400)
            
            # Verificar que no exista registro del mismo tipo hoy
            if RegistroUbicacion.ya_registro_hoy(empleado, data['tipo']):
                return JsonResponse({
                    'success': False,
                    'message': f'Ya registraste {data["tipo"]} para hoy. Solo se permite un registro por día.'
                })

            # Si se intenta registrar una 'salida' sin haber registrado 'entrada' hoy, bloquear
            if data['tipo'] == 'salida' and not RegistroUbicacion.ya_registro_hoy(empleado, 'entrada'):
                return JsonResponse({
                    'success': False,
                    'message': 'No puedes registrar salida antes de haber registrado la entrada hoy.'
                }, status=400)
            
            # Crear el registro
            precision_value = data.get('precision')
            if precision_value:
                try:
                    precision_value = float(precision_value)
                except (ValueError, TypeError):
                    precision_value = None
            
            registro = RegistroUbicacion.objects.create(
                empleado=empleado,
                latitud=float(data['latitud']),
                longitud=float(data['longitud']),
                precision=precision_value,
                tipo=data['tipo']
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Registro de {data["tipo"]} exitoso',
                'registro_id': registro.id,
                'timestamp': registro.fecha_local.strftime('%d/%m/%Y %H:%M:%S')
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Datos JSON inválidos'
            }, status=400)
        except IntegrityError:
            return JsonResponse({
                'success': False,
                'message': 'Ya existe un registro del mismo tipo para hoy'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error interno: {str(e)}'
            }, status=500)


class DashboardUbicacionesView(AdminRequiredMixin, TemplateView):
    """Dashboard para administradores - vista de todas las ubicaciones"""
    template_name = 'ubicaciones/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener fecha del parámetro URL o del parámetro GET o usar hoy
        fecha_param = kwargs.get('fecha') or self.request.GET.get('fecha')
        if fecha_param:
            try:
                fecha_consulta = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                fecha_consulta = timezone.now().date()
        else:
            fecha_consulta = timezone.now().date()
        
        # Obtener registros del día específico
        registros_entrada = RegistroUbicacion.registros_del_dia(fecha_consulta).filter(tipo='entrada')
        registros_salida = RegistroUbicacion.registros_del_dia(fecha_consulta).filter(tipo='salida')
        
        # Estadísticas basadas en la fecha consultada
        empleados_con_entrada = registros_entrada.values('empleado').distinct().count()
        empleados_con_salida = registros_salida.values('empleado').distinct().count()
        
        # Obtener empleados activos
        empleados_activos = Empleado.objects.filter(activo=True)
        total_empleados_activos = empleados_activos.count()
        
        # Obtener IDs de empleados con entrada y salida
        empleados_ids_entrada = registros_entrada.values_list('empleado_id', flat=True).distinct()
        empleados_ids_salida = registros_salida.values_list('empleado_id', flat=True).distinct()
        
        # Empleados faltantes
        empleados_sin_entrada = empleados_activos.exclude(id__in=empleados_ids_entrada)
        empleados_sin_salida = empleados_activos.exclude(id__in=empleados_ids_salida)
        
        context.update({
            'fecha_consulta': fecha_consulta,
            'registros_entrada': registros_entrada,
            'registros_salida': registros_salida,
            'empleados_con_entrada': empleados_con_entrada,
            'empleados_con_salida': empleados_con_salida,
            'empleados_sin_entrada': empleados_sin_entrada,
            'empleados_sin_salida': empleados_sin_salida,
            'total_empleados_activos': total_empleados_activos,
            'total_registros': registros_entrada.count() + registros_salida.count(),
        })
        return context


@method_decorator(csrf_exempt, name='dispatch')
class LimpiarUbicacionesAPIView(AdminRequiredMixin, View):
    """API para limpiar todas las ubicaciones (solo administradores)"""
    
    def post(self, request, *args, **kwargs):
        try:
            total_eliminados = RegistroUbicacion.objects.count()
            RegistroUbicacion.objects.all().delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Se eliminaron {total_eliminados} registros de ubicación',
                'total_eliminados': total_eliminados
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al eliminar registros: {str(e)}'
            }, status=500)


class MapaUbicacionView(AdminRequiredMixin, TemplateView):
    """Vista de mapa individual para un registro específico"""
    template_name = 'ubicaciones/mapa_detalle.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        registro_id = kwargs.get('registro_id')
        registro = get_object_or_404(RegistroUbicacion, id=registro_id)
        
        context.update({
            'registro': registro,
        })
        return context
    

class EmpleadosSinEntradaView(AdminRequiredMixin, TemplateView):
    template_name = 'ubicaciones/lista_sin_entrada.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha_param = kwargs.get('fecha') or self.request.GET.get('fecha')
        if fecha_param:
            try:
                fecha_consulta = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                fecha_consulta = timezone.now().date()
        else:
            fecha_consulta = timezone.now().date()
        empleados_activos = Empleado.objects.filter(activo=True)
        registros_entrada = RegistroUbicacion.registros_del_dia(fecha_consulta).filter(tipo='entrada')
        empleados_ids_entrada = registros_entrada.values_list('empleado_id', flat=True).distinct()
        empleados_sin_entrada = empleados_activos.exclude(id__in=empleados_ids_entrada)
        context.update({
            'empleados_sin_entrada': empleados_sin_entrada,
            'fecha_consulta': fecha_consulta,
        })
        return context

class EmpleadosSinSalidaView(AdminRequiredMixin, TemplateView):
    template_name = 'ubicaciones/lista_sin_salida.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha_param = kwargs.get('fecha') or self.request.GET.get('fecha')
        if fecha_param:
            try:
                fecha_consulta = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                fecha_consulta = timezone.now().date()
        else:
            fecha_consulta = timezone.now().date()
        empleados_activos = Empleado.objects.filter(activo=True)
        registros_salida = RegistroUbicacion.registros_del_dia(fecha_consulta).filter(tipo='salida')
        empleados_ids_salida = registros_salida.values_list('empleado_id', flat=True).distinct()
        empleados_sin_salida = empleados_activos.exclude(id__in=empleados_ids_salida)
        context.update({
            'empleados_sin_salida': empleados_sin_salida,
            'fecha_consulta': fecha_consulta,
        })
        return context