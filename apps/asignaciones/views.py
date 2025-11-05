from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
import json
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from django.contrib.staticfiles import finders

from .models import Asignacion, ActividadAsignada


class MisAsignacionesView(LoginRequiredMixin, ListView):
    template_name = 'asignaciones/mis_asignaciones.html'
    context_object_name = 'asignaciones'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.recursos_humanos.models import Empleado
        context['empleado'] = Empleado.objects.filter(usuario=self.request.user).first()
        return context

    def get_queryset(self):
        user = self.request.user
        from apps.recursos_humanos.models import Empleado
        from django.db.models import Q
        empleado = Empleado.objects.filter(usuario=user).first()
        if empleado:
            # Incluir asignaciones donde el usuario es empleado O supervisor
            qs = (Asignacion.objects
                  .filter(Q(empleados=empleado) | Q(supervisor=empleado))
                  .select_related('empresa', 'supervisor')
                  .prefetch_related('empleados')
                  .distinct()  # Evitar duplicados si es empleado Y supervisor de la misma asignación
                  .order_by('-fecha', '-fecha_creacion'))
            
            fecha = self.request.GET.get('fecha')
            if fecha:
                try:
                    from datetime import date
                    y, m, d = map(int, fecha.split('-'))
                    qs = qs.filter(fecha=date(y, m, d))
                except Exception:
                    pass
            return qs
        return Asignacion.objects.none()


class EsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser)


class AsignacionCreateView(LoginRequiredMixin, EsAdminMixin, CreateView):
    model = Asignacion
    fields = ['fecha', 'empresa', 'supervisor', 'detalles']
    success_url = reverse_lazy('asignaciones:listar_admin')
    template_name = 'asignaciones/form.html'


class AsignacionUpdateView(LoginRequiredMixin, EsAdminMixin, UpdateView):
    model = Asignacion
    fields = ['fecha', 'empresa', 'supervisor', 'detalles']
    success_url = reverse_lazy('asignaciones:listar_admin')
    template_name = 'asignaciones/form.html'


class AsignacionListAdminView(LoginRequiredMixin, EsAdminMixin, ListView):
    model = Asignacion
    template_name = 'asignaciones/lista_admin.html'
    context_object_name = 'asignaciones'
    paginate_by = 20
    ordering = ['-fecha']


class AsignacionDetailView(LoginRequiredMixin, DetailView):
    model = Asignacion
    template_name = 'asignaciones/detalle.html'
    context_object_name = 'asignacion'


class AsignacionesTodasView(LoginRequiredMixin, ListView):
    """Listado de todas las asignaciones visibles para cualquier usuario autenticado.
    - Usuarios estándar: ven todas las asignaciones, ordenadas por fecha desc.
    - Admins: igual, con paginación.
    Futuro: se pueden añadir filtros por fecha/empleado.
    """
    model = Asignacion
    template_name = 'asignaciones/todas.html'
    context_object_name = 'asignaciones'
    paginate_by = 20

    def get_queryset(self):
            qs = (Asignacion.objects
                  .select_related('empresa', 'supervisor')
                  .order_by('-fecha', '-fecha_creacion'))
            # Filtros opcionales por querystring
            empleado_id = self.request.GET.get('empleado')
            fecha = self.request.GET.get('fecha')
            if empleado_id:
                qs = qs.filter(empleados__id=empleado_id)
            if fecha:
                # Formato esperado YYYY-MM-DD
                try:
                    from datetime import date
                    y, m, d = map(int, fecha.split('-'))
                    qs = qs.filter(fecha=date(y, m, d))
                except Exception:
                    pass
            return qs


@csrf_exempt
@require_POST
@login_required
def marcar_actividad_completada(request, actividad_id):
    """
    Vista AJAX para marcar una actividad como completada por el supervisor.
    """
    try:
        # Obtener empleado del usuario actual
        from apps.recursos_humanos.models import Empleado
        empleado = get_object_or_404(Empleado, usuario=request.user)
        
        # Obtener la actividad asignada
        actividad = get_object_or_404(ActividadAsignada, id=actividad_id)
        
        # Verificar que el usuario es el supervisor de la asignación
        if actividad.asignacion.supervisor != empleado:
            return JsonResponse({
                'success': False,
                'error': 'No tienes permisos para completar esta actividad'
            }, status=403)
        
        # Obtener el estado del request
        data = json.loads(request.body)
        completada = data.get('completada', False)
        
        # Actualizar la actividad
        actividad.completada = completada
        if completada:
            actividad.fecha_completada = timezone.now()
            actividad.completada_por = empleado
        else:
            actividad.fecha_completada = None
            actividad.completada_por = None
        actividad.save()
        
        # Enviar notificación al admin si la actividad se marca como completada
        if completada:
            print(f"Enviando notificación para actividad completada: {actividad.nombre}")
            enviar_notificacion_admin_actividad_completada(actividad, empleado)
        else:
            print(f"Actividad marcada como pendiente: {actividad.nombre}")
        
        return JsonResponse({
            'success': True,
            'completada': actividad.completada,
            'fecha_completada': actividad.fecha_completada.isoformat() if actividad.fecha_completada else None,
            'porcentaje_asignacion': actividad.asignacion.porcentaje_completado
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def enviar_notificacion_admin_actividad_completada(actividad, supervisor):
    """
    Envía notificación al admin cuando se completa una actividad.
    """
    print(f"=== INICIANDO ENVÍO DE NOTIFICACIÓN ===")
    print(f"Actividad: {actividad.nombre}")
    print(f"Supervisor: {supervisor.nombre_completo}")
    
    try:
        from apps.notificaciones.models import Notificacion
        from apps.usuarios.models import Usuario
        
        # Obtener todos los usuarios admin (usando el modelo personalizado Usuario)
        admins = Usuario.objects.filter(is_staff=True, is_active=True)
        print(f"Admins encontrados: {admins.count()}")
        
        # Obtener información detallada de la asignación
        asignacion = actividad.asignacion
        todas_actividades = asignacion.actividades.all()
        actividades_completadas = todas_actividades.filter(completada=True)
        actividades_pendientes = todas_actividades.filter(completada=False)
        porcentaje_total = asignacion.porcentaje_completado
        
        titulo = f"✅ Actividad completada por {supervisor.nombre_completo}"
        
        # Crear mensaje estructurado con iconos
        lineas = []
        lineas.append(f"🎯 ACTIVIDAD: {actividad.nombre} ({actividad.porcentaje}%)")
        lineas.append("=" * 45)
        lineas.append(f"📊 PROGRESO: {porcentaje_total}% ({actividades_completadas.count()}/{todas_actividades.count()} completadas)")
        lineas.append("")
        lineas.append(f"👤 Supervisor: {supervisor.nombre_completo}")
        lineas.append(f"🏢 Empresa: {asignacion.empresa.nombre}")
        lineas.append(f"📅 Fecha: {asignacion.fecha.strftime('%d/%m/%Y')}")

        # Actividades completadas (máximo 3)
        if actividades_completadas.exists():
            lineas.append("")
            lineas.append("✅ COMPLETADAS:")
            for act in actividades_completadas[:3]:
                dias_texto = f"{act.tiempo_estimado_dias} día{'s' if act.tiempo_estimado_dias != 1 else ''}"
                lineas.append(f"   ✓ {act.nombre} ({act.porcentaje}% - {dias_texto})")
            if actividades_completadas.count() > 3:
                lineas.append(f"   ➕ ... y {actividades_completadas.count() - 3} mas")
        
        # Actividades pendientes (máximo 3)
        if actividades_pendientes.exists():
            lineas.append("")
            lineas.append("⏳ PENDIENTES:")
            for act in actividades_pendientes[:3]:
                dias_texto = f"{act.tiempo_estimado_dias} día{'s' if act.tiempo_estimado_dias != 1 else ''}"
                lineas.append(f"   ⭕ {act.nombre} ({act.porcentaje}% - {dias_texto})")
            if actividades_pendientes.count() > 3:
                lineas.append(f"   ➕ ... y {actividades_pendientes.count() - 3} mas")
        else:
            lineas.append("")
            lineas.append("🎉 ¡ASIGNACION COMPLETADA AL 100%!")
        
        # Empleados (máximo 2)
        empleados = asignacion.empleados.all()
        if empleados.count() > 0:
            lineas.append("")
            lineas.append("EQUIPO:")
            for emp in empleados[:2]:
                lineas.append(f"  - {emp.nombre_completo}")
            if empleados.count() > 2:
                lineas.append(f"  - ... y {empleados.count() - 2} mas")
        
        mensaje = "\n".join(lineas)
        
        # Crear notificación para cada admin
        notificaciones_creadas = 0
        for admin in admins:
            notificacion = Notificacion.objects.create(
                usuario=admin,
                titulo=titulo,
                mensaje=mensaje,
                tipo='success'
            )
            notificaciones_creadas += 1
            print(f"✅ Notificación #{notificacion.id} creada para {admin.username}")
            
        print(f"🎉 Total notificaciones enviadas: {notificaciones_creadas}")
        return True
            
    except Exception as e:
        print(f"❌ Error enviando notificación: {e}")
        import traceback
        traceback.print_exc()
        return False


class SupervisorAsignacionDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada de una asignación para el supervisor,
    que permite marcar actividades como completadas.
    """
    model = Asignacion
    template_name = 'asignaciones/supervisor_detalle.html'
    context_object_name = 'asignacion'
    
    def get_queryset(self):
        # Solo permitir ver asignaciones donde el usuario es supervisor
        from apps.recursos_humanos.models import Empleado
        empleado = Empleado.objects.filter(usuario=self.request.user).first()
        if empleado:
            return Asignacion.objects.filter(supervisor=empleado)
        return Asignacion.objects.none()


@staff_member_required
def exportar_asignaciones_hoy_pdf(request):
    """
    Exporta todas las asignaciones de hoy a PDF en formato tabla con logo SOMA
    """
    from django.conf import settings
    import os
    
    hoy = date.today()
    asignaciones = Asignacion.objects.filter(fecha=hoy).select_related(
        'empresa', 'supervisor'
    ).prefetch_related('empleados', 'actividades')
    
    # Crear response PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="asignaciones_{hoy.strftime("%Y%m%d")}.pdf"'
    
    try:
        # Crear documento PDF
        doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=15,
            spaceBefore=5,
            textColor=colors.HexColor('#1e3a8a'),  # Azul marino igual que el header
            alignment=1,  # Centro
            fontName='Helvetica-Bold'
        )
        
        # Header con logo de SOMA y posible membrete
        # Mostrar el título con la segunda línea en color naranja
        titulo_principal = Paragraph("Servicios Industriales SOMA<br/><font color='#F97316'>Asignaciones de Hoy</font>", title_style)

        # Preparar metadata del PDF (título que aparece en la pestaña)
        pdf_title = f"Asignaciones {hoy.strftime('%d/%m/%Y')}"

        def _on_first_page(canvas, doc_obj):
            try:
                canvas.setTitle(pdf_title)
                canvas.setAuthor('Servicios Industriales SOMA')
            except Exception:
                pass

        # Intentar localizar un banner/membrete completo primero (imagen a lo ancho)
        banner_path = None
        banner_candidates = [
            'images/membrete_header.png',
            'images/membrete.png',
            'img/membrete.png',
            'images/header.png'
        ]
        for cand in banner_candidates:
            p = finders.find(cand)
            if p:
                banner_path = p
                break

        if banner_path and os.path.exists(banner_path):
            try:
                banner = Image(banner_path, width=7.6*inch, height=1*inch)
                story.append(banner)
                story.append(Spacer(1, 6))
            except Exception as e:
                print(f"No se pudo cargar banner desde {banner_path}: {e}")

        # Buscar el logo en ubicaciones estáticas conocidas (más robusto usando finders)
        logo_soma = None
        logo_candidates = [
            'images/logo.png', 'images/logo_soma.png', 'img/logo.png', 'img/logo_soma.png'
        ]
        for cand in logo_candidates:
            ruta = finders.find(cand)
            if ruta and os.path.exists(ruta):
                try:
                    logo_soma = Image(ruta, width=1.2*inch, height=0.9*inch)
                    break
                except Exception as e:
                    print(f"Error cargando logo desde {ruta}: {e}")
                    continue

        # Header: logo (izquierda) + título (centrado) + celda vacía simétrica para centrar perfectamente
        if logo_soma:
            header_table = Table([[logo_soma, titulo_principal, '']], colWidths=[1.2*inch, 5.2*inch, 1.2*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(header_table)
        else:
            header_table = Table([[titulo_principal]], colWidths=[7.6*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(header_table)

        story.append(Paragraph(f"Fecha: {hoy.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        if asignaciones.exists():
            # Crear tabla principal de asignaciones
            table_data = [
                ['Empresa', 'Supervisor', 'Empleados', 'Detalles']
            ]
            
            for asignacion in asignaciones:
                # Preparar datos de la fila
                empresa = asignacion.empresa.nombre
                supervisor = asignacion.supervisor.nombre_completo if asignacion.supervisor else 'Sin asignar'
                
                # Mostrar todos los empleados con cantidad total
                todos_empleados = asignacion.empleados.all()
                total_empleados = todos_empleados.count()
                
                if total_empleados == 0:
                    empleados = "Sin empleados asignados"
                elif total_empleados == 1:
                    empleados = f"(1) {todos_empleados[0].nombre_completo}"
                else:
                    empleados_lista = [e.nombre_completo for e in todos_empleados]
                    empleados = f"({total_empleados}) " + '\n'.join(empleados_lista)
                
                detalles = (asignacion.detalles[:150] + '...') if len(asignacion.detalles) > 150 else asignacion.detalles
                
                table_data.append([
                    empresa,
                    supervisor, 
                    empleados,
                    detalles
                ])
            
            # Crear y estilizar la tabla
            main_table = Table(table_data, colWidths=[1.8*inch, 1.5*inch, 1.8*inch, 2.4*inch])
            main_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#001a63")),  # Azul marino
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

                # Contenido (más compacto)
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),

                # Bordes y colores alternos (ligeramente más finos)
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            story.append(main_table)
            
        else:
            story.append(Paragraph("No hay asignaciones programadas para hoy.", styles['Normal']))
        
        # Footer simple
        story.append(Spacer(1, 30))
        footer_text = f"Reporte generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por Servicios Industriales SOMA"
        story.append(Paragraph(footer_text, styles['Normal']))

        # Generar el PDF (aplicar metadata en la primera página)
        doc.build(story, onFirstPage=_on_first_page)

        return response
        
    except Exception as e:
        from django.http import HttpResponseServerError
        return HttpResponseServerError(f"Error generando PDF: {str(e)}")
