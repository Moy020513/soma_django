from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


def _to_decimal(value):
    try:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter(is_safe=True)
def moneda(value):
    """Format a number as currency using Spanish-style separators:
    - thousands: dot
    - decimal: comma
    - two decimal places
    Example: 1375 -> $\u00A01.375,00
    """
    d = _to_decimal(value)
    if d is None:
        return ''
    # Always show two decimals for money
    s = f"{d:,.2f}"
    # s uses English separators: 1,375.00 -> convert to 1.375,00
    s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"$\u00A0{s}"


@register.filter(is_safe=True)
def num_trim(value):
    """Format numeric values trimming unnecessary trailing zeros.
    Uses comma as decimal separator when needed.
    Examples:
      2.000 -> '2'
      2.500 -> '2,5'
      1375.00 -> '1.375'
    """
    d = _to_decimal(value)
    if d is None:
        return ''
    # Convert normalized string
    s = format(d.normalize(), 'f')
    # s uses '.' as decimal; replace with comma and handle thousands
    if '.' in s:
        intpart, frac = s.split('.')
        # remove trailing zeros from frac
        frac = frac.rstrip('0')
        if frac:
            # add thousands separator to intpart
            intpart_with = _thousands(intpart)
            return f"{intpart_with},{frac}"
        else:
            return _thousands(intpart)
    else:
        return _thousands(s)


def _thousands(intpart_str):
    # Insert dots as thousands separators for integer part
    s = intpart_str
    neg = s.startswith('-')
    if neg:
        s = s[1:]
    parts = []
    while s:
        parts.append(s[-3:])
        s = s[:-3]
    res = '.'.join(reversed(parts))
    if neg:
        res = '-' + res
    return res
