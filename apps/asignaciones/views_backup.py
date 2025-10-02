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
from django.template.loader import get_template
import json
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus.flowables import PageBreak

from .models import Asignacion, ActividadAsignada

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
            fontSize=16,
            spaceAfter=10,
            textColor=colors.HexColor('#007bff'),
            alignment=1  # Centro
        )
        
        # Header con logo y título
        header_data = []
        
        # Intentar cargar logo
        logo_path = os.path.join(settings.STATIC_ROOT or settings.STATICFILES_DIRS[0], 'images', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = ImageReader(logo_path)
                header_data = [
                    [logo, Paragraph("SISTEMA SOMA<br/>Asignaciones de Hoy", title_style)]
                ]
            except:
                header_data = [
                    ["", Paragraph("SISTEMA SOMA<br/>Asignaciones de Hoy", title_style)]
                ]
        else:
            header_data = [
                ["", Paragraph("SISTEMA SOMA<br/>Asignaciones de Hoy", title_style)]
            ]
        
        if header_data[0][0]:  # Si hay logo
            header_table = Table(header_data, colWidths=[1.5*inch, 5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
        else:
            header_table = Table([["", Paragraph("SISTEMA SOMA<br/>Asignaciones de Hoy", title_style)]], colWidths=[0.5*inch, 6*inch])
        
        story.append(header_table)
        story.append(Paragraph(f"Fecha: {hoy.strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        if asignaciones.exists():
            # Crear tabla principal de asignaciones
            table_data = [
                ['Empresa', 'Supervisor', 'Empleados', 'Actividades', 'Progreso', 'Detalles']
            ]
            
            for asignacion in asignaciones:
                # Preparar datos de la fila
                empresa = asignacion.empresa.nombre
                supervisor = asignacion.supervisor.nombre_completo if asignacion.supervisor else 'Sin asignar'
                empleados = ', '.join([e.nombre_completo for e in asignacion.empleados.all()[:2]])  # Máximo 2 empleados
                if asignacion.empleados.count() > 2:
                    empleados += f' (+{asignacion.empleados.count()-2} más)'
                
                # Lista de actividades
                actividades_lista = []
                for actividad in asignacion.actividades.all():
                    estado = "✓" if actividad.completada else "○"
                    actividades_lista.append(f"{estado} {actividad.nombre}")
                
                actividades_text = '\n'.join(actividades_lista[:4])  # Máximo 4 actividades
                if asignacion.actividades.count() > 4:
                    actividades_text += f'\n(+{asignacion.actividades.count()-4} más)'
                
                progreso = f"{asignacion.porcentaje_completado}%"
                detalles = (asignacion.detalles[:100] + '...') if len(asignacion.detalles) > 100 else asignacion.detalles
                
                table_data.append([
                    empresa,
                    supervisor, 
                    empleados,
                    actividades_text,
                    progreso,
                    detalles
                ])
            
            # Crear y estilizar la tabla
            main_table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1.2*inch, 1.5*inch, 0.6*inch, 1.5*inch])
            main_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Contenido
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Progreso centrado
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                
                # Bordes y colores alternos
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            story.append(main_table)
            
        else:
            story.append(Paragraph("No hay asignaciones programadas para hoy.", styles['Normal']))
        
        # Footer simple
        story.append(Spacer(1, 30))
        footer_text = f"Reporte generado el {timezone.now().strftime('%d/%m/%Y %H:%M')} por {request.user.get_full_name() or request.user.username}"
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Generar el PDF
        doc.build(story)
        
        return response
        
    except Exception as e:
        from django.http import HttpResponseServerError
        return HttpResponseServerError(f"Error generando PDF: {str(e)}")