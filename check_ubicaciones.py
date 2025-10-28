#!/usr/bin/env python
"""Script para verificar los registros de ubicación"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from apps.ubicaciones.models import RegistroUbicacion
from django.utils import timezone

print(f'Total de registros: {RegistroUbicacion.objects.count()}')
hoy = timezone.now().date()
registros_hoy = RegistroUbicacion.objects.filter(fecha=hoy)
print(f'Registros de hoy ({hoy}): {registros_hoy.count()}')

if registros_hoy.exists():
    print('\nPrimeros 5 registros de hoy:')
    for r in registros_hoy[:5]:
        print(f'  - {r.empleado.nombre_completo}: {r.tipo} a las {r.fecha_local.strftime("%H:%M:%S")}')
        print(f'    Coords: {r.latitud}, {r.longitud}')
        print(f'    Precisión: {r.precision}m')
else:
    print('\nNo hay registros para hoy.')
    
print('\nÚltimos 5 registros en total:')
for r in RegistroUbicacion.objects.all()[:5]:
    print(f'  - {r.empleado.nombre_completo}: {r.tipo} - {r.fecha_local.strftime("%d/%m/%Y %H:%M:%S")}')
    print(f'    Coords: {r.latitud}, {r.longitud}')
