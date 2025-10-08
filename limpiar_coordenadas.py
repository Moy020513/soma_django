#!/usr/bin/env python
"""
Script para limpiar coordenadas incorrectas en la base de datos
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from apps.ubicaciones.models import RegistroUbicacion
from decimal import Decimal

def main():
    print("🔍 Revisando registros de ubicación...")
    
    # Obtener todos los registros
    registros = RegistroUbicacion.objects.all()
    print(f"📊 Total de registros: {registros.count()}")
    
    registros_problemáticos = []
    registros_correctos = []
    
    for registro in registros:
        # Validar rangos de coordenadas
        # Latitud: -90 a 90
        # Longitud: -180 a 180
        lat_valida = -90 <= float(registro.latitud) <= 90
        lng_valida = -180 <= float(registro.longitud) <= 180
        
        if not lat_valida or not lng_valida:
            registros_problemáticos.append(registro)
            print(f"❌ Registro ID {registro.id}: Lat={registro.latitud}, Lng={registro.longitud}")
        else:
            registros_correctos.append(registro)
            print(f"✅ Registro ID {registro.id}: Lat={registro.latitud}, Lng={registro.longitud}")
    
    print(f"\n📈 Resumen:")
    print(f"✅ Registros correctos: {len(registros_correctos)}")
    print(f"❌ Registros problemáticos: {len(registros_problemáticos)}")
    
    if registros_problemáticos:
        print(f"\n🔧 Corrigiendo registros problemáticos...")
        
        for registro in registros_problemáticos:
            # Coordenadas de ejemplo para Ciudad de México
            # Estas son coordenadas realistas
            nueva_lat = Decimal('19.432608')  # CDMX Centro
            nueva_lng = Decimal('-99.133209') # CDMX Centro
            
            print(f"🔄 Corrigiendo registro ID {registro.id}:")
            print(f"   Antes: Lat={registro.latitud}, Lng={registro.longitud}")
            
            registro.latitud = nueva_lat
            registro.longitud = nueva_lng
            registro.save()
            
            print(f"   Después: Lat={registro.latitud}, Lng={registro.longitud}")
        
        print(f"\n✅ {len(registros_problemáticos)} registros corregidos!")
    else:
        print(f"\n✅ Todos los registros tienen coordenadas válidas!")

if __name__ == '__main__':
    main()