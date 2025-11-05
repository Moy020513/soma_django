from django import template
import re
from django.utils.safestring import mark_safe

register = template.Library()

# Mapeo simple de frases comunes en mensajes del admin/objetos a español.
REPLACEMENTS = [
    (re.compile(r"was added successfully", re.I), "se agregó correctamente"),
    (re.compile(r"was changed successfully", re.I), "se cambió correctamente"),
    (re.compile(r"was deleted successfully", re.I), "se eliminó correctamente"),
    (re.compile(r"added successfully", re.I), "agregado correctamente"),
    (re.compile(r"changed successfully", re.I), "cambiado correctamente"),
    (re.compile(r"deleted successfully", re.I), "eliminado correctamente"),
    (re.compile(r"error", re.I), "error"),
    (re.compile(r"The (.+) was added successfully\."), r"Se agregó correctamente \1."),
    (re.compile(r"The (.+) was changed successfully\."), r"Se modificó correctamente \1."),
]

@register.filter(is_safe=True)
def es_alert(value):
    """Traduce frases comunes de alertas al español (fallback simple).

    No sustituye la internacionalización completa; está pensado para mensajes
    administrativos frecuentes como "X was added successfully".
    """
    if not isinstance(value, str):
        try:
            value = str(value)
        except Exception:
            return value

    out = value
    for pattern, repl in REPLACEMENTS:
        out = pattern.sub(repl, out)

    return mark_safe(out)
