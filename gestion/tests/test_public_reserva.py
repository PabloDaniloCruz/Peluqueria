import json
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta, time as time_type, datetime
from decimal import Decimal

from ..models import (
    Cliente, Profesional, Servicio, Estacion, HorarioAtencion, Turno, DetalleTurno, Reserva
)

class TestReservaPublicaWizard(TestCase):
    def setUp(self):
        # 1. Crear cliente http client
        self.client = Client()
        
        # 2. Configurar Horarios de Atención comerciales
        for i in range(7):
            HorarioAtencion.objects.create(
                dia_semana=i,
                hora_apertura=time_type(9, 0),
                hora_cierre=time_type(19, 0),
                abierto=True
            )
            
        # 3. Crear Servicios
        self.servicio_corte = Servicio.objects.create(
            nombre="Corte Premium",
            precio_sugerido=Decimal("2000.00"),
            duracion_estimada=30,
            orden_sugerido=1
        )
        self.servicio_lavado = Servicio.objects.create(
            nombre="Lavado Nutritivo",
            precio_sugerido=Decimal("800.00"),
            duracion_estimada=15,
            orden_sugerido=2
        )
        
        # 4. Crear Profesional y vincular habilidades
        self.estilista = Profesional.objects.create(
            nombre="Danilo",
            apellido="Cruz",
            porcentaje_comision=40
        )
        self.estilista.habilidades.add(self.servicio_corte)
        self.estilista.habilidades.add(self.servicio_lavado)
        
        # 5. Crear Estaciones de Trabajo
        self.estacion1 = Estacion.objects.create(
            nombre="Puesto 1",
            tipo="estacion",
            activa=True
        )

    def test_get_reserva_publica_wizard_view(self):
        """Valida que la vista del wizard público cargue correctamente y sin requerir login."""
        response = self.client.get('/reservas/publica/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gestion/reserva_publica_wizard.html")
        self.assertContains(response, "Studio Salta")

    def test_api_disponibilidad_publica_success(self):
        """Valida que el endpoint de disponibilidad retorne slots válidos."""
        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        payload = {
            "fecha": fecha_test,
            "hora_preferida": "10:00",
            "telefono": "3871234567",
            "servicios": [
                {"servicio_id": self.servicio_corte.id, "profesional_id": self.estilista.id},
                {"servicio_id": self.servicio_lavado.id, "profesional_id": None}
            ]
        }
        
        response = self.client.post(
            '/api/disponibilidad-publica/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('opciones', data)
        self.assertGreater(len(data['opciones']), 0)

    def test_api_disponibilidad_publica_saturation(self):
        """Valida que el control preventivo de saturación bloquee la consulta si ya tiene 2 turnos."""
        # Registrar un cliente existente con el teléfono de prueba
        telefono_test = "3879998887"
        cliente = Cliente.objects.create(
            nombre="Pablo",
            apellido="Gomez",
            telefono=telefono_test
        )
        
        # Crear 2 turnos futuros para este cliente
        manana = timezone.now() + timedelta(days=1)
        Turno.objects.create(
            cliente=cliente, profesional=self.estilista, estacion=self.estacion1,
            fecha_hora=manana, hora_fin_estimada=manana + timedelta(minutes=30)
        )
        pasado_manana = timezone.now() + timedelta(days=2)
        Turno.objects.create(
            cliente=cliente, profesional=self.estilista, estacion=self.estacion1,
            fecha_hora=pasado_manana, hora_fin_estimada=pasado_manana + timedelta(minutes=30)
        )
        
        # Consultar disponibilidad
        payload = {
            "fecha": pasado_manana.date().isoformat(),
            "telefono": telefono_test,
            "servicios": [{"servicio_id": self.servicio_corte.id, "profesional_id": None}]
        }
        
        response = self.client.post(
            '/api/disponibilidad-publica/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn("Ya tenés 2 turnos reservados a futuro", data['error'])

    def test_confirmar_reserva_publica_success(self):
        """Valida que se confirmen los múltiples turnos correctamente de manera atómica."""
        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        
        # Simulamos una opción válida devuelta por el buscador
        opcion_elegida = {
            "duracion_total": 45,
            "inicio": "11:00",
            "fin": "11:45",
            "bloques": [
                {
                    "servicio_id": self.servicio_corte.id,
                    "servicio_nombre": "Corte Premium",
                    "profesional_id": self.estilista.id,
                    "profesional_nombre": "Danilo Cruz",
                    "estacion_id": self.estacion1.id,
                    "estacion_nombre": "Puesto 1",
                    "inicio": "11:00",
                    "fin": "11:30",
                    "duracion": 30
                },
                {
                    "servicio_id": self.servicio_lavado.id,
                    "servicio_nombre": "Lavado Nutritivo",
                    "profesional_id": self.estilista.id,
                    "profesional_nombre": "Danilo Cruz",
                    "estacion_id": self.estacion1.id,
                    "estacion_nombre": "Puesto 1",
                    "inicio": "11:30",
                    "fin": "11:45",
                    "duracion": 15
                }
            ]
        }
        
        payload = {
            "nombre": "Sofia",
            "apellido": "Lopez",
            "telefono": "3874443322",
            "fecha": fecha_test,
            "opcion": opcion_elegida
        }
        
        # Ejecutar confirmación
        response = self.client.post(
            '/api/reservas/publica/confirmar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('redirect', data)
        
        # Verificar en base de datos
        cliente = Cliente.objects.get(telefono="3874443322")
        self.assertEqual(cliente.nombre, "Sofia")
        
        # Deben haberse creado 2 turnos vinculados a una única Reserva
        turnos = Turno.objects.filter(cliente=cliente)
        self.assertEqual(turnos.count(), 2)
        self.assertIsNotNone(turnos[0].reserva)
        self.assertEqual(turnos[0].reserva, turnos[1].reserva)

    def test_confirmar_reserva_publica_with_observaciones(self):
        """Valida que la reserva pública guarde las observaciones tanto en Reserva como en Turno."""
        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        
        opcion_elegida = {
            "duracion_total": 30,
            "inicio": "12:00",
            "fin": "12:30",
            "bloques": [
                {
                    "servicio_id": self.servicio_corte.id,
                    "servicio_nombre": "Corte Premium",
                    "profesional_id": self.estilista.id,
                    "profesional_nombre": "Danilo Cruz",
                    "estacion_id": self.estacion1.id,
                    "estacion_nombre": "Puesto 1",
                    "inicio": "12:00",
                    "fin": "12:30",
                    "duracion": 30
                }
            ]
        }
        
        payload = {
            "nombre": "Ana",
            "apellido": "Martínez",
            "telefono": "3879998877",
            "fecha": fecha_test,
            "observaciones": "Alergia a productos fuertes y prefiere café",
            "opcion": opcion_elegida
        }
        
        response = self.client.post(
            '/api/reservas/publica/confirmar/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verificar en base de datos
        cliente = Cliente.objects.get(telefono="3879998877")
        turnos = Turno.objects.filter(cliente=cliente)
        self.assertEqual(turnos.count(), 1)
        
        turno = turnos.first()
        self.assertEqual(turno.observaciones, "Alergia a productos fuertes y prefiere café")
        self.assertIsNotNone(turno.reserva)
        self.assertEqual(turno.reserva.observaciones, "Alergia a productos fuertes y prefiere café")

    def test_gestion_y_cancelacion_publica_success(self):
        """Valida el portal de gestión y la cancelación lógica segura por token."""
        # 1. Crear una reserva con token y turnos
        cliente = Cliente.objects.create(nombre="Pedro", apellido="Sánchez", telefono="3871112233")
        reserva = Reserva.objects.create(cliente=cliente)
        
        manana = timezone.now() + timedelta(days=1)
        turno = Turno.objects.create(
            cliente=cliente, profesional=self.estilista, estacion=self.estacion1,
            fecha_hora=manana, hora_fin_estimada=manana + timedelta(minutes=30),
            reserva=reserva
        )
        
        # 2. Acceder al portal de gestión
        response = self.client.get(f'/reservas/publica/gestion/{reserva.token}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gestion/gestion_publica.html")
        self.assertContains(response, "Pedro Sánchez")
        
        # 3. Acceder a la confirmación de cancelación
        response = self.client.get(f'/reservas/publica/gestion/{reserva.token}/cancelar/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gestion/cancelar_publica.html")
        
        # 4. Confirmar la cancelación (POST)
        response = self.client.post(f'/reservas/publica/gestion/{reserva.token}/cancelar/')
        self.assertEqual(response.status_code, 302) # Redirecciona de vuelta al portal
        
        # 5. Verificar que el estado cambió a cancelado
        turno.refresh_from_db()
        self.assertEqual(turno.estado, "cancelado")
        self.assertIn("Cancelado por el cliente", turno.observaciones)
