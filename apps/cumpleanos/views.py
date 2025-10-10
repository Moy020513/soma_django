from django.shortcuts import render
from datetime import date, timedelta
from apps.recursos_humanos.models import Empleado
from apps.empresas.models import Contacto, Empresa
from django.db.models import Q


def proximos_cumpleanos(request):
    empresas = Empresa.objects.all().order_by('nombre')
    hoy = date.today()
    dias_raw = request.GET.get('dias', '')
    filtro = request.GET.get('tipo', 'todos')
    try:
        dias_adelante = int(dias_raw) if dias_raw else 30
    except ValueError:
        dias_adelante = 30
    busqueda = request.GET.get('q', '').strip()
    empresa_busqueda = request.GET.get('empresa', '').strip()

    # Filtrar empleados próximos a cumplir años
    empleados = Empleado.objects.filter(fecha_nacimiento__isnull=False)
    contactos = Contacto.objects.filter(fecha_nacimiento__isnull=False)

    def cumple_pronto(fecha):
        if not fecha:
            return False
        proximo = fecha.replace(year=hoy.year)
        if proximo < hoy:
            proximo = proximo.replace(year=hoy.year + 1)
        return (proximo - hoy).days <= dias_adelante

    if filtro == 'empleados':
        empleados = [e for e in empleados if cumple_pronto(e.fecha_nacimiento)]
        contactos = []
    elif filtro == 'contactos':
        empleados = []
        contactos = [c for c in contactos if cumple_pronto(c.fecha_nacimiento)]
    elif filtro == 'todos':
        empleados = [e for e in empleados if cumple_pronto(e.fecha_nacimiento)]
        contactos = [c for c in contactos if cumple_pronto(c.fecha_nacimiento)]
    elif filtro == 'ver_todos':
        empleados = list(empleados)
        contactos = list(contactos)

    if busqueda:
        empleados = [e for e in empleados if busqueda.lower() in e.nombre_completo.lower()]
        contactos = [c for c in contactos if busqueda.lower() in c.nombre.lower() or busqueda.lower() in getattr(c, 'apellidos', '')]
    if empresa_busqueda:
        empleados = [e for e in empleados if hasattr(e, 'empresa') and empresa_busqueda.lower() in e.empresa.nombre.lower()]
        contactos = [c for c in contactos if c.empresa and empresa_busqueda.lower() in c.empresa.nombre.lower()]

    return render(request, 'cumpleanos/lista_cumpleanos.html', {
        'empleados': empleados,
        'contactos': contactos,
        'dias_adelante': dias_adelante,
        'busqueda': busqueda,
        'empresa_busqueda': empresa_busqueda,
        'empresas': empresas,
        'filtro': filtro,
    })
