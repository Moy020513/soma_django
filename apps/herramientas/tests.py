from django.test import TestCase
from django.utils import timezone
from apps.recursos_humanos.models import Empleado
from django.contrib.auth import get_user_model
from .models import Herramienta, AsignacionHerramienta, TransferenciaHerramienta

User = get_user_model()

class HerramientaCodigoTest(TestCase):
    def test_codigo_incremental_por_categoria(self):
        h1 = Herramienta.objects.create(nombre='Taladro', categoria='CON')
        self.assertEqual(h1.codigo, 'CON001')
        h2 = Herramienta.objects.create(nombre='Cincel', categoria='CON')
        self.assertEqual(h2.codigo, 'CON002')
        h3 = Herramienta.objects.create(nombre='Escoba', categoria='LIM')
        self.assertEqual(h3.codigo, 'LIM001')

class TransferenciaHerramientaTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='u1', password='pass')
        self.user2 = User.objects.create_user(username='u2', password='pass')
        self.emp1 = Empleado.objects.create(usuario=self.user1, nombre='Emp1', apellidos='Test', activo=True)
        self.emp2 = Empleado.objects.create(usuario=self.user2, nombre='Emp2', apellidos='Test', activo=True)
        self.h = Herramienta.objects.create(nombre='Martillo', categoria='CON')
        self.asig = AsignacionHerramienta.objects.create(herramienta=self.h, empleado=self.emp1, fecha_asignacion=timezone.now().date())

    def test_transferencia_aprobada(self):
        transf = TransferenciaHerramienta.objects.create(herramienta=self.h, empleado_origen=self.emp1, empleado_destino=self.emp2, observaciones_solicitud='Prueba')
        # Simular aprobación: cerrar asignación actual y crear nueva
        self.asig.fecha_devolucion = timezone.now().date()
        self.asig.save()
        AsignacionHerramienta.objects.create(herramienta=self.h, empleado=self.emp2, fecha_asignacion=timezone.now().date())
        transf.estado = 'aprobada'
        transf.save()
        self.assertEqual(AsignacionHerramienta.objects.filter(herramienta=self.h, fecha_devolucion__isnull=True).first().empleado, self.emp2)
