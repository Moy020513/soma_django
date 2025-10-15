from django.db import models
from django.core.validators import RegexValidator
from django.urls import reverse
from apps.usuarios.models import Usuario
import re


class Puesto(models.Model):
    """Modelo para representar puestos de trabajo"""
    
    nombre = models.CharField(max_length=100, verbose_name="Nombre del puesto")
    descripcion = models.TextField(verbose_name="Descripción del puesto")
    salario_minimo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Salario mínimo"
    )
    salario_maximo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Salario máximo"
    )
    requisitos = models.TextField(blank=True, verbose_name="Requisitos")
    activo = models.BooleanField(default=True, verbose_name="Puesto activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    superior = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='puestos_subordinados', verbose_name='Puesto supervisor'
    )
    
    class Meta:
        verbose_name = "Puesto"
        verbose_name_plural = "Puestos"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    @property
    def dias_faltan_para_vacaciones(self):
        """Devuelve los días que faltan para cumplir el año y poder pedir vacaciones."""
        from datetime import date
        if not self.fecha_ingreso:
            return None
        hoy = date.today()
        aniversario = date(self.fecha_ingreso.year + 1, self.fecha_ingreso.month, self.fecha_ingreso.day)
        faltan = (aniversario - hoy).days
        return faltan if faltan > 0 else 0
    def dias_vacaciones_disponibles(self):
        """Devuelve los días de vacaciones disponibles solo si el empleado ya cumplió el año correspondiente, según la tabla oficial de la LFT mexicana (2023+)."""
        from datetime import date
        if not self.fecha_ingreso:
            return 0
        hoy = date.today()
        # Calcular años completos de servicio
        anios = hoy.year - self.fecha_ingreso.year - ((hoy.month, hoy.day) < (self.fecha_ingreso.month, self.fecha_ingreso.day))
        if anios < 1:
            dias = 0
        elif anios == 1:
            dias = 12
        elif anios == 2:
            dias = 14
        elif anios == 3:
            dias = 16
        elif anios == 4:
            dias = 18
        elif anios == 5:
            dias = 20
        elif 6 <= anios <= 10:
            dias = 22
        elif 11 <= anios <= 15:
            dias = 24
        elif 16 <= anios <= 20:
            dias = 26
        elif 21 <= anios <= 25:
            dias = 28
        elif 26 <= anios <= 30:
            dias = 30
        else:
            dias = 30
        usados = self.dias_vacaciones()
        return max(0, dias - usados)
    """Modelo para representar empleados"""
    
    ESTADOS_CIVILES = [
        ('soltero', 'Soltero/a'),
        ('casado', 'Casado/a'),
        ('divorciado', 'Divorciado/a'),
        ('viudo', 'Viudo/a'),
        ('union_libre', 'Unión libre'),
    ]
    
    TIPOS_SANGRE = [
        ('O+', 'O+'), ('O-', 'O-'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]
    
    # Información personal
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='empleado')
    numero_empleado = models.CharField(max_length=20, unique=True, verbose_name="Número de empleado")
    curp = models.CharField(
        max_length=18,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9]{2}$', 'CURP inválida')],
        verbose_name="CURP"
    )
    rfc = models.CharField(
        max_length=13,
        validators=[RegexValidator(r'^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$', 'RFC inválido')],
        verbose_name="RFC",
        blank=True
    )
    nss = models.CharField(max_length=11, blank=True, verbose_name="Número de Seguro Social")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de nacimiento")
    estado_civil = models.CharField(max_length=15, choices=ESTADOS_CIVILES, verbose_name="Estado civil")
    tipo_sangre = models.CharField(max_length=3, choices=TIPOS_SANGRE, blank=True, verbose_name="Tipo de sangre")
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('I', 'Indefinido')], verbose_name="Sexo", default='I')
    
    # Información de contacto
    telefono_personal = models.CharField(max_length=15, verbose_name="Teléfono personal")
    telefono_emergencia = models.CharField(max_length=15, verbose_name="Teléfono de emergencia")
    contacto_emergencia = models.CharField(max_length=100, verbose_name="Contacto de emergencia")
    direccion = models.TextField(verbose_name="Dirección")
    
    # Información laboral
    puesto = models.ForeignKey(Puesto, on_delete=models.PROTECT, verbose_name="Puesto")
    jefe_directo = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Jefe directo")
    fecha_ingreso = models.DateField(verbose_name="Fecha de ingreso")
    fecha_baja = models.DateField(null=True, blank=True, verbose_name="Fecha de baja")
    motivo_baja = models.TextField(blank=True, verbose_name="Motivo de baja")
    salario_actual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Salario actual")
    
    # Documentos
    foto = models.ImageField(upload_to='empleados/fotos/', blank=True, null=True, verbose_name="Fotografía")
    
    # Estado
    activo = models.BooleanField(default=True, verbose_name="Empleado activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última actualización")
    
    class Meta:
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ['numero_empleado']
    
    def __str__(self):
        return f"{self.numero_empleado} - {self.usuario.get_full_name()}"
    
    def get_absolute_url(self):
        return reverse('recursos_humanos:empleado_detalle', kwargs={'pk': self.pk})
    
    @property
    def nombre_completo(self):
        return self.usuario.get_full_name()
    
    #
    
    @property
    def antiguedad(self):
        from datetime import date
        if self.fecha_ingreso:
            delta = date.today() - self.fecha_ingreso
            return delta.days // 365
        return 0

    def _generate_numero_empleado(self) -> str:
        """Genera un número de empleado autoincremental como cadena de 4 dígitos.
        Busca el mayor número puramente numérico existente y suma 1.
        """
        qs = Empleado.objects.values_list('numero_empleado', flat=True)
        max_num = 0
        for val in qs:
            if val and re.fullmatch(r"\d+", str(val)):
                try:
                    n = int(val)
                    if n > max_num:
                        max_num = n
                except ValueError:
                    continue
        return f"{max_num + 1:04d}"

    def save(self, *args, **kwargs):
        # Generar número de empleado si viene vacío
        if not self.numero_empleado:
            self.numero_empleado = self._generate_numero_empleado()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Crear periodo de estatus 'activo' si es nuevo y no existe ninguno
        if is_new and not self.periodos_estatus.exists():
            from .models import PeriodoEstatusEmpleado
            PeriodoEstatusEmpleado.objects.create(
                empleado=self,
                estatus='activo',
                fecha_inicio=self.fecha_ingreso,
                observaciones='Registro automático de alta.'
            )

    def historial_estatus(self):
        """Devuelve el historial completo de periodos de estatus."""
        return self.periodos_estatus.order_by('fecha_inicio')

    def dias_trabajados(self):
        """Suma los días en que el empleado estuvo en estatus 'Activo'."""
        from datetime import date
        total = 0
        for periodo in self.periodos_estatus.filter(estatus="activo"):
            fin = periodo.fecha_fin or date.today()
            total += (fin - periodo.fecha_inicio).days + 1
        return total

    def dias_vacaciones(self):
        """Suma los días en que el empleado estuvo en 'Vacaciones', sin contar domingos."""
        from datetime import date, timedelta
        total = 0
        for periodo in self.periodos_estatus.filter(estatus="vacaciones"):
            fin = periodo.fecha_fin or date.today()
            temp = periodo.fecha_inicio
            while temp <= fin:
                if temp.weekday() != 6:  # 6 = domingo
                    total += 1
                temp += timedelta(days=1)
        return total

    def antiguedad_laboral(self):
        """Calcula la antigüedad descontando periodos no activos."""
        from datetime import date
        if not self.fecha_ingreso:
            return 0
        hoy = date.today()
        total_dias = (hoy - self.fecha_ingreso).days + 1
        no_activos = 0
        for periodo in self.periodos_estatus.exclude(estatus="activo"):
            fin = periodo.fecha_fin or hoy
            no_activos += (fin - periodo.fecha_inicio).days + 1
        return max(0, total_dias - no_activos)



# --- Modelo para historial de estatus laboral ---
class PeriodoEstatusEmpleado(models.Model):
    """Registra los periodos de estatus laboral de cada empleado."""
    ESTATUS_CHOICES = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("vacaciones", "Vacaciones"),
        ("incapacidad", "Incapacidad"),
    ]
    empleado = models.ForeignKey("Empleado", on_delete=models.CASCADE, related_name="periodos_estatus")
    estatus = models.CharField(max_length=20, choices=ESTATUS_CHOICES, verbose_name="Estatus laboral")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio del estatus")
    fecha_fin = models.DateField(null=True, blank=True, verbose_name="Fecha de fin del estatus")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Periodo de estatus de empleado"
        verbose_name_plural = "Periodos de estatus de empleados"
        ordering = ["-fecha_inicio"]

    def __str__(self):
        fin = self.fecha_fin.strftime('%Y-%m-%d') if self.fecha_fin else "actual"
        return f"{self.empleado} - {self.estatus} ({self.fecha_inicio} a {fin})"


 