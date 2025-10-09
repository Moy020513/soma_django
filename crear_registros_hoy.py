#!/usr/bin/env python
"""Script para crear registros de ubicación de prueba para hoy"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from apps.ubicaciones.models import RegistroUbicacion
from apps.recursos_humanos.models import Empleado
from django.utils import timezone
from decimal import Decimal

# Obtener empleados activos
empleados = Empleado.objects.filter(activo=True)[:5]

if not empleados:
    print("No hay empleados activos en la base de datos")
    exit(1)

print(f"Creando registros para {len(empleados)} empleados...")

# Coordenadas de ejemplo (Ciudad de México - diferentes puntos)
coordenadas_ejemplo = [
    (Decimal('19.432608'), Decimal('-99.133209')),  # Centro
    (Decimal('19.426097'), Decimal('-99.167634')),  # Condesa
    (Decimal('19.411775'), Decimal('-99.163391')),  # Del Valle
    (Decimal('19.403134'), Decimal('-99.171120')),  # Narvarte
    (Decimal('19.390519'), Decimal('-99.286090')),  # Santa Fe
]

creados = 0
for i, empleado in enumerate(empleados):
    lat, lon = coordenadas_ejemplo[i % len(coordenadas_ejemplo)]
    
    # Verificar si ya tiene entrada hoy
    if not RegistroUbicacion.ya_registro_hoy(empleado, 'entrada'):
        entrada = RegistroUbicacion.objects.create(
            empleado=empleado,
            latitud=lat,
            longitud=lon,
            precision=15.5,
            tipo='entrada',
            timestamp=timezone.now().replace(hour=8, minute=30 + i*5)
        )
        print(f"✓ Entrada creada para {empleado.nombre_completo}")
        creados += 1
    else:
        print(f"- {empleado.nombre_completo} ya tiene entrada hoy")
    
    # Crear salida para algunos empleados
    if i < 3 and not RegistroUbicacion.ya_registro_hoy(empleado, 'salida'):
        salida = RegistroUbicacion.objects.create(
            empleado=empleado,
            latitud=lat + Decimal('0.0001'),
            longitud=lon + Decimal('0.0001'),
            precision=12.3,
            tipo='salida',
            timestamp=timezone.now().replace(hour=17, minute=45 + i*5)
        )
        print(f"✓ Salida creada para {empleado.nombre_completo}")
        creados += 1

print(f"\n✓ Se crearon {creados} registros de prueba para hoy")
print(f"Total de registros hoy: {RegistroUbicacion.registros_del_dia().count()}")
