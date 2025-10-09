#!/usr/bin/env python
"""Script para probar la vista del dashboard"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from apps.ubicaciones.views import DashboardUbicacionesView
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Crear request factory
factory = RequestFactory()

# Obtener un usuario admin (asumiendo que existe uno)
try:
    admin_user = User.objects.filter(is_staff=True, is_superuser=True).first()
    if not admin_user:
        print("No hay usuarios administradores en la base de datos")
        exit(1)
    
    print(f"Usuario admin encontrado: {admin_user.username}")
    
    # Test 1: Sin parámetros (debe usar fecha de hoy)
    print("\n=== Test 1: Sin parámetros ===")
    request = factory.get('/ubicaciones/list/')
    request.user = admin_user
    view = DashboardUbicacionesView()
    view.request = request
    context = view.get_context_data()
    
    print(f"Fecha de consulta: {context['fecha_consulta']}")
    print(f"Fecha de hoy: {timezone.now().date()}")
    print(f"¿Son iguales? {context['fecha_consulta'] == timezone.now().date()}")
    print(f"Total de registros entrada: {context['registros_entrada'].count()}")
    print(f"Total de registros salida: {context['registros_salida'].count()}")
    
    # Test 2: Con parámetro GET
    print("\n=== Test 2: Con parámetro GET (2025-10-08) ===")
    request = factory.get('/ubicaciones/list/?fecha=2025-10-08')
    request.user = admin_user
    view = DashboardUbicacionesView()
    view.request = request
    context = view.get_context_data()
    
    print(f"Fecha de consulta: {context['fecha_consulta']}")
    print(f"Total de registros entrada: {context['registros_entrada'].count()}")
    print(f"Total de registros salida: {context['registros_salida'].count()}")
    
    if context['registros_entrada'].exists():
        print("\nPrimeros registros de entrada:")
        for r in context['registros_entrada'][:3]:
            print(f"  - {r.empleado.nombre_completo}: {r.tipo} - {r.fecha_local}")
            print(f"    Lat: {r.latitud}, Lon: {r.longitud}")
    
    print("\n✓ Todos los tests completados exitosamente")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
