from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.recursos_humanos.models import Empleado
import pytz
from datetime import timedelta, date
from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


class RegistroUbicacion(models.Model):
    """
    Modelo para registrar la ubicación de entrada y salida de empleados
    """
    TIPO_REGISTRO = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
    ]
    
    empleado = models.ForeignKey(
        Empleado, 
        on_delete=models.CASCADE, 
        related_name='registros_ubicacion',
        verbose_name="Empleado"
    )
    latitud = models.DecimalField(
        max_digits=12, 
        decimal_places=8,
        verbose_name="Latitud",
        help_text="Coordenada de latitud GPS"
    )
    longitud = models.DecimalField(
        max_digits=12, 
        decimal_places=8,
        verbose_name="Longitud", 
        help_text="Coordenada de longitud GPS"
    )
    precision = models.FloatField(
        null=True, 
        blank=True,
        verbose_name="Precisión",
        help_text="Precisión del GPS en metros"
    )
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_REGISTRO,
        verbose_name="Tipo de registro"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora"
    )
    # Fecha (día) extraída de `timestamp` para permitir constraints por día
    fecha = models.DateField(
        editable=False,
        verbose_name="Fecha"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    
    class Meta:
        verbose_name = "Registro de Ubicación"
        verbose_name_plural = "Registros de Ubicación"
        ordering = ['-timestamp']
        # Índices para mejorar performance
        indexes = [
            models.Index(fields=['empleado', 'tipo', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['fecha']),
        ]
        constraints = [
            # A nivel de base de datos, asegurar único por (empleado, tipo, fecha)
            models.UniqueConstraint(fields=['empleado', 'tipo', 'fecha'], name='unique_registro_per_day'),
        ]
    
    def __str__(self):
        return f"{self.empleado.nombre_completo} - {self.get_tipo_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def fecha_local(self):
        """Convierte el timestamp a zona horaria de México"""
        mexico_tz = pytz.timezone('America/Mexico_City')
        return self.timestamp.astimezone(mexico_tz)
    
    @property
    def coordenadas_str(self):
        """Retorna las coordenadas como string formateado"""
        return f"{self.latitud}, {self.longitud}"
    
    @classmethod
    def ya_registro_hoy(cls, empleado, tipo):
        """Verifica si el empleado ya registró entrada o salida hoy"""
        hoy = timezone.now().date()
        return cls.objects.filter(
            empleado=empleado,
            tipo=tipo,
            fecha=hoy
        ).exists()
    
    @classmethod
    def registros_del_dia(cls, fecha=None):
        """Obtiene todos los registros de un día específico"""
        if fecha is None:
            fecha = timezone.now().date()
        return cls.objects.filter(fecha=fecha)
    
    @classmethod
    def empleados_registrados_hoy(cls, tipo):
        """Obtiene empleados que ya registraron entrada o salida hoy"""
        hoy = timezone.now().date()
        empleados_ids = cls.objects.filter(
            tipo=tipo,
            fecha=hoy
        ).values_list('empleado_id', flat=True)
        return Empleado.objects.filter(id__in=empleados_ids, activo=True)
    
    @classmethod
    def empleados_faltantes_hoy(cls, tipo):
        """Obtiene empleados que NO han registrado entrada o salida hoy"""
        empleados_registrados = cls.empleados_registrados_hoy(tipo)
        return Empleado.objects.filter(activo=True).exclude(
            id__in=empleados_registrados.values_list('id', flat=True)
        )

    def save(self, *args, **kwargs):
        """Asegurarse de tener el campo `fecha` consistente con `timestamp` antes de guardar."""
        # Extraer la fecha desde el timestamp usando la hora local configurada
        # Esto evita que registros cerca de la medianoche queden asignados al día erróneo
        if self.timestamp:
            try:
                # Usa timezone.localtime para convertir a la zona horaria activa en settings
                self.fecha = timezone.localtime(self.timestamp).date()
            except Exception:
                # Fallback simple
                self.fecha = self.timestamp.date()
        else:
            self.fecha = timezone.localtime(timezone.now()).date()
        super().save(*args, **kwargs)


class SemanaLaboralEmpleado(models.Model):
    """
    Resumen semanal de horas trabajadas por empleado.
    Se crea/actualiza cada lunes con el total de horas trabajadas
    entre el lunes (inclusive) y el domingo (inclusive).
    """
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name='semanas_laborales',
        verbose_name='Empleado'
    )
    semana_inicio = models.DateField(verbose_name='Semana (inicio - Lunes)')
    horas_trabajadas = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal('0.00'),
        verbose_name='Horas trabajadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Semana laboral por empleado'
        verbose_name_plural = 'Semanas laborales por empleado'
        unique_together = ('empleado', 'semana_inicio')

    def __str__(self):
        return f"{self.empleado.nombre_completo} — Semana {self.semana_inicio.strftime('%d/%m/%Y')} — {self.horas_trabajadas} h"


def _get_monday_of_date(d):
    """Devuelve el lunes (fecha) de la semana a la que pertenece d."""
    return d - timedelta(days=d.weekday())


def compute_hours_for_week_and_employee(empleado, semana_inicio):
    """
    Calcula las horas trabajadas por `empleado` entre `semana_inicio` (lunes)
    y el siguiente domingo (inclusive). Se cuentan solo los días donde exista
    tanto registro de entrada como de salida; se ignoran días incompletos.
    Retorna Decimal(hours_with_two_decimals).
    """
    semana_inicio = semana_inicio
    total_seconds = 0
    for i in range(7):
        dia = semana_inicio + timedelta(days=i)
        entradas = RegistroUbicacion.objects.filter(empleado=empleado, fecha=dia, tipo='entrada').order_by('timestamp')
        salidas = RegistroUbicacion.objects.filter(empleado=empleado, fecha=dia, tipo='salida').order_by('-timestamp')
        if entradas.exists() and salidas.exists():
            entrada = entradas.first()
            salida = salidas.first()
            # Asegurarnos de que la salida sea posterior a la entrada
            if salida.timestamp > entrada.timestamp:
                delta = salida.timestamp - entrada.timestamp
                total_seconds += delta.total_seconds()
    hours = Decimal(total_seconds) / Decimal(3600)
    # Normalizar a 2 decimales
    return hours.quantize(Decimal('0.01'))


def compute_weekly_hours_for_all(week_start_date=None):
    """
    Calcula y persiste las semanas laborales para todos los empleados activos.
    Si `week_start_date` es None, se toma la semana anterior completa (el lunes
    anterior a la fecha actual menos 7 días), lo cual es útil para ejecutar
    el job cada lunes y generar la semana que terminó.
    Retorna cantidad de registros creados/actualizados.
    """
    today = timezone.localdate()
    if week_start_date is None:
        # semana anterior: obtener el lunes de la semana actual y restar 7 días
        current_monday = _get_monday_of_date(today)
        week_start_date = current_monday - timedelta(days=7)

    empleados = Empleado.objects.filter(activo=True)
    updated = 0
    for emp in empleados:
        horas = compute_hours_for_week_and_employee(emp, week_start_date)
        obj, created = SemanaLaboralEmpleado.objects.update_or_create(
            empleado=emp,
            semana_inicio=week_start_date,
            defaults={'horas_trabajadas': horas}
        )
        updated += 1
    return updated


def create_week_records_for_all(week_start_date=None):
    """
    Crea (si no existen) registros `SemanaLaboralEmpleado` para todos los empleados activos
    para la semana indicada. Si `week_start_date` es None, toma el lunes de la semana actual.
    Retorna la cantidad de registros creados.
    """
    today = timezone.localdate()
    if week_start_date is None:
        current_monday = _get_monday_of_date(today)
        week_start_date = current_monday

    empleados = Empleado.objects.filter(activo=True)
    created = 0
    for emp in empleados:
        obj, created_flag = SemanaLaboralEmpleado.objects.get_or_create(
            empleado=emp,
            semana_inicio=week_start_date,
            defaults={'horas_trabajadas': Decimal('0.00')}
        )
        if created_flag:
            created += 1
    return created


class SemanaLaboralDia(models.Model):
    """Detalle por día dentro de una semana laboral de un empleado.
    Contiene hora de entrada y salida (si están disponibles) y las horas calculadas.
    """
    semana = models.ForeignKey(
        'SemanaLaboralEmpleado',
        on_delete=models.CASCADE,
        related_name='dias',
        verbose_name='Semana laboral'
    )
    fecha = models.DateField(verbose_name='Fecha')
    entrada = models.DateTimeField(null=True, blank=True, verbose_name='Entrada')
    salida = models.DateTimeField(null=True, blank=True, verbose_name='Salida')
    horas = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), verbose_name='Horas')

    class Meta:
        verbose_name = 'Día laboral'
        verbose_name_plural = 'Días laborales'
        unique_together = ('semana', 'fecha')
        ordering = ['fecha']

    def __str__(self):
        return f"{self.semana.empleado.nombre_completo} — {self.fecha.strftime('%d/%m/%Y')} — {self.horas} h"

    def compute_horas(self):
        """Calcula las horas del día a partir de entrada y salida, si ambos existen."""
        if self.entrada and self.salida and self.salida > self.entrada:
            delta = self.salida - self.entrada
            horas = Decimal(delta.total_seconds()) / Decimal(3600)
            return horas.quantize(Decimal('0.01'))
        return Decimal('0.00')


@receiver(post_save, sender=SemanaLaboralDia)
def on_semanalaboraldia_saved(sender, instance, **kwargs):
    """Recalcula las horas del día y de la semana cuando se guarda un día."""
    # recalcular horas del día
    nuevas_horas = instance.compute_horas()
    if instance.horas != nuevas_horas:
        instance.horas = nuevas_horas
        # evitar recursión infinita al guardar
        SemanaLaboralDia.objects.filter(pk=instance.pk).update(horas=nuevas_horas)

    # recalcular total de la semana
    semana = instance.semana
    total = SemanaLaboralDia.objects.filter(semana=semana).aggregate(
        total=models.Sum('horas')
    )['total'] or Decimal('0.00')
    if semana.horas_trabajadas != total:
        SemanaLaboralEmpleado.objects.filter(pk=semana.pk).update(horas_trabajadas=total)


@receiver(post_save, sender=RegistroUbicacion)
def on_registro_ubicacion_saved(sender, instance, created, **kwargs):
    """Cuando un registro de ubicación se guarda, actualiza/crea la semana y el día correspondiente.
    Esto permite que las semanas se vayan llenando aunque solo exista la entrada.
    """
    try:
        registro = instance
        emp = registro.empleado
        semana_inicio = _get_monday_of_date(registro.fecha)
        semana_obj, _ = SemanaLaboralEmpleado.objects.get_or_create(
            empleado=emp,
            semana_inicio=semana_inicio,
            defaults={'horas_trabajadas': Decimal('0.00')}
        )
        dia_obj, _ = SemanaLaboralDia.objects.get_or_create(
            semana=semana_obj,
            fecha=registro.fecha,
            defaults={'entrada': None, 'salida': None, 'horas': Decimal('0.00')}
        )
        # asignar entrada o salida según el tipo del registro
        if registro.tipo == 'entrada':
            # si ya existe una entrada, respetamos la primera (asumimos unico por dia)
            if not dia_obj.entrada or dia_obj.entrada != registro.timestamp:
                dia_obj.entrada = registro.timestamp
        elif registro.tipo == 'salida':
            if not dia_obj.salida or dia_obj.salida != registro.timestamp:
                dia_obj.salida = registro.timestamp

        # guardar cambios en el día (esto disparará la señal de SemanaLaboralDia)
        dia_obj.save()
    except Exception:
        # no bloquear el flujo si algo sale mal; logs opcionales
        pass