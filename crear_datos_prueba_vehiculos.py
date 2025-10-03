#!/usr/bin/env python
"""
Script para crear datos de prueba para el sistema de vehículos
"""

import os
import sys
import django
from datetime import date, timedelta

# Configurar Django
sys.path.append('/home/moy/virtualenvs/soma_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from apps.usuarios.models import Usuario
from apps.recursos_humanos.models import Empleado, Puesto
from apps.flota_vehicular.models import Vehiculo, AsignacionVehiculo
from apps.empresas.models import Empresa

def crear_datos_prueba():
    print("Creando datos de prueba para vehículos...")
    
    # 1. Crear empresa de prueba si no existe
    empresa, created = Empresa.objects.get_or_create(
        nombre="Empresa Demo",
        defaults={
            'direccion': 'Av. Demo #123, Col. Prueba, CDMX',
            'activa': True
        }
    )
    if created:
        print(f"✓ Empresa creada: {empresa.nombre}")
    
    # 2. Crear puesto si no existe
    puesto, created = Puesto.objects.get_or_create(
        nombre="Técnico",
        defaults={
            'descripcion': 'Técnico especializado',
            'salario_minimo': 15000.00,
            'salario_maximo': 25000.00,
            'activo': True
        }
    )
    if created:
        print(f"✓ Puesto creado: {puesto.nombre}")
    
    # 3. Crear usuario y empleado de prueba si no existe
    usuario, created = Usuario.objects.get_or_create(
        username="empleado_demo",
        defaults={
            'first_name': 'Juan',
            'last_name': 'Pérez González',
            'email': 'juan.perez@demo.com',
            'is_active': True
        }
    )
    if created:
        usuario.set_password('demo123')
        usuario.save()
        print(f"✓ Usuario creado: {usuario.username}")
    
    # Crear empleado si no existe
    empleado, created = Empleado.objects.get_or_create(
        usuario=usuario,
        defaults={
            'numero_empleado': '1001',
            'curp': 'PEGJ900101HDFRRN01',
            'rfc': 'PEGJ900101H01',
            'fecha_nacimiento': date(1990, 1, 1),
            'estado_civil': 'soltero',
            'sexo': 'M',
            'telefono_personal': '5551234567',
            'telefono_emergencia': '5557654321',
            'contacto_emergencia': 'María Pérez (Madre)',
            'direccion': 'Calle Demo #456, Col. Test',
            'puesto': puesto,
            'fecha_ingreso': date.today() - timedelta(days=365),
            'salario_actual': 20000.00,
            'activo': True
        }
    )
    if created:
        print(f"✓ Empleado creado: {empleado.numero_empleado} - {empleado.usuario.get_full_name()}")
    
    # 4. Crear vehículo de prueba si no existe
    vehiculo, created = Vehiculo.objects.get_or_create(
        placas="ABC-123-D",
        defaults={
            'marca': 'Toyota',
            'modelo': 'Corolla',
            'año': 2020,
            'color': 'Blanco',
            'numero_serie': 'TOY123456789',
            'tipo': 'sedan',
            'kilometraje_actual': 25000.50,
            'estado': 'disponible',
            'aseguradora': 'Seguros Demo',
            'contacto_aseguradora': '800-123-4567',
            'numero_seguro': 'POL-2023-001234',
            'observaciones': 'Vehículo en excelentes condiciones'
        }
    )
    if created:
        print(f"✓ Vehículo creado: {vehiculo.marca} {vehiculo.modelo} - {vehiculo.placas}")
    
    # 5. Crear segundo vehículo
    vehiculo2, created = Vehiculo.objects.get_or_create(
        placas="XYZ-789-E",
        defaults={
            'marca': 'Nissan',
            'modelo': 'Sentra',
            'año': 2019,
            'color': 'Azul',
            'numero_serie': 'NIS987654321',
            'tipo': 'sedan',
            'kilometraje_actual': 35000.25,
            'estado': 'disponible',
            'aseguradora': 'Seguros Demo',
            'contacto_aseguradora': '800-123-4567',
            'numero_seguro': 'POL-2023-001235',
            'observaciones': 'Vehículo con mantenimiento reciente'
        }
    )
    if created:
        print(f"✓ Vehículo 2 creado: {vehiculo2.marca} {vehiculo2.modelo} - {vehiculo2.placas}")
    
    # 6. Crear asignación de vehículo al empleado
    asignacion, created = AsignacionVehiculo.objects.get_or_create(
        vehiculo=vehiculo,
        empleado=empleado,
        defaults={
            'fecha_asignacion': date.today(),
            'estado': 'activa',
            'observaciones': 'Asignación de prueba para el empleado demo'
        }
    )
    if created:
        print(f"✓ Asignación creada: {vehiculo} → {empleado.usuario.get_full_name()}")
        # Actualizar estado del vehículo
        vehiculo.estado = 'asignado'
        vehiculo.save()
        print(f"✓ Estado del vehículo actualizado a: {vehiculo.estado}")
    
    print("\n¡Datos de prueba creados exitosamente!")
    print(f"Usuario: {usuario.username}")
    print(f"Contraseña: demo123")
    print(f"Empleado: {empleado.numero_empleado} - {empleado.usuario.get_full_name()}")
    print(f"Vehículo asignado: {vehiculo.marca} {vehiculo.modelo} ({vehiculo.placas})")
    
    print("\nPuedes ingresar al sistema con estas credenciales para probar la funcionalidad.")

if __name__ == "__main__":
    crear_datos_prueba()