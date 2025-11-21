from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def money(value):
    """Format a numeric value as currency with thousands separator and 2 decimals.
    Examples:
      21970 -> "$21,970.00"
      Decimal('2.5') -> "$2.50"
    """
    try:
        if value is None:
            return ''
        # If it's a Decimal or string, convert to float safely
        if isinstance(value, Decimal):
            v = float(value)
        else:
            v = float(str(value))
        return f"${v:,.2f}"
    except Exception:
        try:
            return f"${float(value):,.2f}"
        except Exception:
            return str(value)


@register.filter
def trim_number(value):
    """Trim trailing zeros for Decimal numbers and use comma as decimal separator.
    Examples:
      Decimal('2.000') -> '2'
      Decimal('2.500') -> '2.5' (then comma '2,5' if needed)
    Returns string.
    """
    try:
        if value is None:
            return ''
        if isinstance(value, Decimal):
            s = format(value, 'f')
        else:
            s = str(value)
        # Remove trailing zeros and trailing dot
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        # Use comma as decimal separator for Spanish style
        if '.' in s:
            s = s.replace('.', ',')
        return s
    except Exception:
        return str(value)
