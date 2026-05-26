from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, time as time_type
from decimal import Decimal

from ..models import Cliente, Profesional, Servicio, Estacion, HorarioAtencion, Turno, EtapaServicio

class TestDashboardRecepcion(TestCase):
    def setUp(self):
        self.client = Client()
        # Crear usuario para login
        self.user = User.objects.create_user(username='staff', password='password')
        self.client.login(username='staff', password='password')

        # Configurar Horarios de Atención comerciales
        for i in range(7):
            HorarioAtencion.objects.create(
                dia_semana=i,
                hora_apertura=time_type(9, 0),
                hora_cierre=time_type(19, 0),
                abierto=True
            )

        # Crear Servicios, Profesional y Estaciones
        self.servicio = Servicio.objects.create(
            nombre="Corte de Pelo",
            precio_sugerido=Decimal("1500.00"),
            orden_sugerido=1
        )
        EtapaServicio.objects.create(
            servicio=self.servicio, orden=1, nombre="Corte",
            duracion=30, tipo_estacion="estacion", requiere_profesional=True
        )
        self.profesional = Profesional.objects.create(
            nombre="Carlos",
            apellido="Gomez",
            porcentaje_comision=40
        )
        self.profesional.habilidades.add(self.servicio)
        self.estacion = Estacion.objects.create(
            nombre="Puesto 1",
            tipo="estacion",
            activa=True
        )
        self.cliente = Cliente.objects.create(
            nombre="Juan",
            apellido="Perez",
            telefono="3871234567"
        )

        # Crear Turnos para HOY pero a futuro, así el auto-inicio no los toca
        ahora = timezone.now()
        # 1. Turno Pendiente — a 30 minutos en el futuro
        self.turno_pendiente = Turno.objects.create(
            cliente=self.cliente,
            profesional=self.profesional,
            estacion=self.estacion,
            fecha_hora=ahora + timedelta(minutes=30),
            hora_fin_estimada=ahora + timedelta(minutes=60),
            estado="pendiente"
        )
        # En vez de .add(), creamos DetalleTurno para pasar precio_real
        from ..models import DetalleTurno
        DetalleTurno.objects.create(
            turno=self.turno_pendiente,
            servicio=self.servicio,
            precio_real=self.servicio.precio_sugerido
        )

        # 2. Turno Cancelado — a 90 minutos en el futuro (distinto para no solapar)
        self.turno_cancelado = Turno.objects.create(
            cliente=self.cliente,
            profesional=self.profesional,
            estacion=self.estacion,
            fecha_hora=ahora + timedelta(minutes=90),
            hora_fin_estimada=ahora + timedelta(minutes=120),
            estado="cancelado"
        )
        DetalleTurno.objects.create(
            turno=self.turno_cancelado,
            servicio=self.servicio,
            precio_real=self.servicio.precio_sugerido
        )

    def test_dashboard_shows_canceled_appointments(self):
        """Valida que el dashboard de recepción incluya los turnos cancelados por defecto."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Debe incluir ambos turnos en el contexto
        turnos_en_contexto = list(response.context['turnos'])
        self.assertIn(self.turno_pendiente, turnos_en_contexto)
        self.assertIn(self.turno_cancelado, turnos_en_contexto)
        
        # El contador debe registrar el cancelado
        contadores = response.context['contadores']
        self.assertEqual(contadores['total'], 2)
        self.assertEqual(contadores['pendiente'], 1)
        self.assertEqual(contadores['cancelado'], 1)

    def test_dashboard_filter_by_canceled_status(self):
        """Valida que se puedan filtrar los turnos cancelados en el dashboard."""
        response = self.client.get('/', {'estado': 'cancelado'})
        self.assertEqual(response.status_code, 200)
        
        turnos_en_contexto = list(response.context['turnos'])
        self.assertNotIn(self.turno_pendiente, turnos_en_contexto)
        self.assertIn(self.turno_cancelado, turnos_en_contexto)

    def test_dashboard_filter_by_pending_status(self):
        """Valida que al filtrar por pendiente no se muestren los cancelados."""
        response = self.client.get('/', {'estado': 'pendiente'})
        self.assertEqual(response.status_code, 200)
        
        turnos_en_contexto = list(response.context['turnos'])
        self.assertIn(self.turno_pendiente, turnos_en_contexto)
        self.assertNotIn(self.turno_cancelado, turnos_en_contexto)
