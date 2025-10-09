#!/usr/bin/env python
"""Script para verificar el filtro unlocalize en templates"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soma.settings')
django.setup()

from django.template import Template, Context
from decimal import Decimal

# Test del filtro unlocalize
template_code = """
{% load l10n %}
Sin unlocalize: {{ lat }}, {{ lng }}
Con unlocalize: {{ lat|unlocalize }}, {{ lng|unlocalize }}
"""

template = Template(template_code)
context = Context({
    'lat': Decimal('20.43440000'),
    'lng': Decimal('-100.02020000')
})

resultado = template.render(context)
print("=" * 50)
print("Test del filtro unlocalize")
print("=" * 50)
print(resultado)
print("=" * 50)

# Verificar que el formato sea correcto
if '20.43440000' in resultado and '-100.02020000' in resultado:
    print("✅ El filtro unlocalize funciona correctamente")
    print("✅ Las coordenadas usan puntos decimales")
else:
    print("❌ Error: El filtro unlocalize no está funcionando")
