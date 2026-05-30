import json
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta, time as time_type, datetime
from decimal import Decimal

from ..models import (
    Cliente, Profesional, Servicio, Estacion, HorarioAtencion, Turno, DetalleTurno, EtapaServicio
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
            orden_sugerido=1
        )
        self.etapa_corte = EtapaServicio.objects.create(
            servicio=self.servicio_corte, orden=1, nombre="Corte", 
            duracion=30, tipo_estacion="estacion", requiere_profesional=True
        )

        self.servicio_lavado = Servicio.objects.create(
            nombre="Lavado Nutritivo",
            precio_sugerido=Decimal("800.00"),
            orden_sugerido=2
        )
        self.etapa_lavado = EtapaServicio.objects.create(
            servicio=self.servicio_lavado, orden=1, nombre="Lavado", 
            duracion=15, tipo_estacion="estacion", requiere_profesional=True
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

    def _bloque_corte(self, inicio="11:00", fin="11:30"):
        """Helper para crear bloque de corte con estaciones_asignadas."""
        return {
            "servicio_id": self.servicio_corte.id,
            "servicio_nombre": "Corte Premium",
            "profesional_id": self.estilista.id,
            "profesional_nombre": "Danilo Cruz",
            "estacion_id": self.estacion1.id,
            "inicio": inicio,
            "fin": fin,
            "duracion": 30,
            "estaciones_asignadas": [
                {
                    "etapa_servicio_id": self.etapa_corte.id,
                    "nombre": "Corte",
                    "estacion_id": self.estacion1.id,
                    "hora_inicio": inicio,
                    "hora_fin": fin,
                }
            ],
        }

    def _bloque_lavado(self, inicio="11:30", fin="11:45"):
        """Helper para crear bloque de lavado con estaciones_asignadas."""
        return {
            "servicio_id": self.servicio_lavado.id,
            "servicio_nombre": "Lavado Nutritivo",
            "profesional_id": self.estilista.id,
            "profesional_nombre": "Danilo Cruz",
            "estacion_id": self.estacion1.id,
            "inicio": inicio,
            "fin": fin,
            "duracion": 15,
            "estaciones_asignadas": [
                {
                    "etapa_servicio_id": self.etapa_lavado.id,
                    "nombre": "Lavado",
                    "estacion_id": self.estacion1.id,
                    "hora_inicio": inicio,
                    "hora_fin": fin,
                }
            ],
        }

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
            "dni": "12345678",
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
        # Registrar un cliente existente con el DNI de prueba
        dni_test = "87654321"
        telefono_test = "3879998887"
        cliente = Cliente.objects.create(
            dni=dni_test,
            nombre="Pablo",
            apellido="Gomez",
            telefono=telefono_test
        )
        
        # Crear 2 turnos futuros para este cliente
        manana = timezone.now() + timedelta(days=1)
        turno1 = Turno.objects.create(
            cliente=cliente, fecha_hora=manana, hora_fin_estimada=manana + timedelta(minutes=30)
        )
        DetalleTurno.objects.create(
            turno=turno1, servicio=self.servicio_corte,
            profesional=self.estilista,
            precio_real=Decimal("2000.00"),
            hora_inicio=manana.time(), hora_fin=(manana + timedelta(minutes=30)).time()
        )
        pasado_manana = timezone.now() + timedelta(days=2)
        turno2 = Turno.objects.create(
            cliente=cliente, fecha_hora=pasado_manana, hora_fin_estimada=pasado_manana + timedelta(minutes=30)
        )
        DetalleTurno.objects.create(
            turno=turno2, servicio=self.servicio_corte,
            profesional=self.estilista,
            precio_real=Decimal("2000.00"),
            hora_inicio=pasado_manana.time(), hora_fin=(pasado_manana + timedelta(minutes=30)).time()
        )
        
        # Consultar disponibilidad
        payload = {
            "fecha": pasado_manana.date().isoformat(),
            "dni": dni_test,
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
                self._bloque_corte("11:00", "11:30"),
                self._bloque_lavado("11:30", "11:45"),
            ]
        }
        
        payload = {
            "nombre": "Sofia",
            "apellido": "Lopez",
            "dni": "40123456",
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
        cliente = Cliente.objects.get(dni="40123456")
        self.assertEqual(cliente.nombre, "Sofia")
        
        # Debe haberse creado 1 Turno con 2 DetalleTurno
        turnos = Turno.objects.filter(cliente=cliente)
        self.assertEqual(turnos.count(), 1)
        turno = turnos.first()
        self.assertEqual(turno.detalleturno_set.count(), 2)
        self.assertIsNotNone(turno.token)
        # Verificar DetalleTurno con profesional y DetalleEtapa con estacion
        detalles = turno.detalleturno_set.all()
        self.assertEqual(detalles[0].profesional, self.estilista)
        etapas = detalles[0].etapas_asignadas.all()
        self.assertGreater(len(etapas), 0)
        # La primera etapa debe tener la estación asignada
        self.assertEqual(etapas[0].estacion_id, self.estacion1.id)

    def test_confirmar_reserva_publica_with_observaciones(self):
        """Valida que la reserva pública guarde las observaciones tanto en Reserva como en Turno."""
        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        
        opcion_elegida = {
            "duracion_total": 30,
            "inicio": "12:00",
            "fin": "12:30",
            "bloques": [
                self._bloque_corte("12:00", "12:30"),
            ]
        }
        
        payload = {
            "nombre": "Ana",
            "apellido": "Martínez",
            "dni": "40987654",
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
        cliente = Cliente.objects.get(dni="40987654")
        turnos = Turno.objects.filter(cliente=cliente)
        self.assertEqual(turnos.count(), 1)
        
        turno = turnos.first()
        self.assertIsNotNone(turno.token)
        self.assertEqual(turno.observaciones, "Alergia a productos fuertes y prefiere café")
        # Verificar que se creó 1 DetalleTurno
        self.assertEqual(turno.detalleturno_set.count(), 1)
        detalle = turno.detalleturno_set.first()
        self.assertEqual(detalle.profesional, self.estilista)

    def test_gestion_y_cancelacion_publica_success(self):
        """Valida el portal de gestión y cancelación por token de Turno."""
        # 1. Crear turno con token
        cliente = Cliente.objects.create(dni="41111222", nombre="Pedro", apellido="Sánchez", telefono="3871112233")
        turno = Turno.objects.create(
            cliente=cliente, fecha_hora=timezone.now() + timedelta(days=1),
            hora_fin_estimada=timezone.now() + timedelta(days=1, minutes=30)
        )
        DetalleTurno.objects.create(
            turno=turno, servicio=self.servicio_corte,
            profesional=self.estilista,
            precio_real=Decimal("2000.00")
        )
        
        # 2. Acceder al portal de gestión
        response = self.client.get(f'/turnos/publica/gestion/{turno.token}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gestion/gestion_publica.html")
        self.assertContains(response, "Pedro Sánchez")
        
        # 3. Acceder a cancelación
        response = self.client.get(f'/turnos/publica/gestion/{turno.token}/cancelar/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gestion/cancelar_publica.html")
        
        # 4. Confirmar cancelación
        response = self.client.post(f'/turnos/publica/gestion/{turno.token}/cancelar/')
        self.assertEqual(response.status_code, 302)
        
        # 5. Verificar cancelado
        turno.refresh_from_db()
        self.assertEqual(turno.estado, "cancelado")
        self.assertIn("Cancelado por el cliente", turno.observaciones)

    def test_turno_con_multiples_servicios_distintos_profesionales(self):
        """Valida que 2 servicios con distintos profesionales se agrupen en 1 Turno."""
        # Crear segundo profesional
        estilista2 = Profesional.objects.create(
            nombre="Carlos", apellido="López", porcentaje_comision=30
        )
        estilista2.habilidades.add(self.servicio_lavado)

        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        bloque_lavado_estilista2 = {
            "servicio_id": self.servicio_lavado.id,
            "servicio_nombre": "Lavado Nutritivo",
            "profesional_id": estilista2.id,
            "profesional_nombre": "Carlos López",
            "estacion_id": self.estacion1.id,
            "inicio": "11:30",
            "fin": "11:45",
            "duracion": 15,
            "estaciones_asignadas": [
                {
                    "etapa_servicio_id": self.etapa_lavado.id,
                    "nombre": "Lavado",
                    "estacion_id": self.estacion1.id,
                    "hora_inicio": "11:30",
                    "hora_fin": "11:45",
                }
            ],
        }
        opcion_elegida = {
            "duracion_total": 45, "inicio": "11:00", "fin": "11:45",
            "bloques": [
                self._bloque_corte("11:00", "11:30"),
                bloque_lavado_estilista2,
            ]
        }
        payload = {
            "nombre": "Multi", "apellido": "Profesional", "dni": "50123456",
            "telefono": "3875556677", "fecha": fecha_test, "opcion": opcion_elegida
        }
        response = self.client.post(
            '/api/reservas/publica/confirmar/',
            data=json.dumps(payload), content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        cliente = Cliente.objects.get(dni="50123456")
        turnos = Turno.objects.filter(cliente=cliente)
        self.assertEqual(turnos.count(), 1)
        turno = turnos.first()
        self.assertEqual(turno.detalleturno_set.count(), 2)
        profesionales = set(dt.profesional.id for dt in turno.detalleturno_set.all())
        self.assertIn(self.estilista.id, profesionales)
        self.assertIn(estilista2.id, profesionales)

    def test_token_autogestion_turno(self):
        """Verifica que cada Turno tiene un token UUID único."""
        from uuid import UUID
        cliente = Cliente.objects.create(dni="60123456", nombre="Token", apellido="Test", telefono="3876667788")
        turno1 = Turno.objects.create(cliente=cliente, fecha_hora=timezone.now() + timedelta(days=1))
        turno2 = Turno.objects.create(cliente=cliente, fecha_hora=timezone.now() + timedelta(days=2))

        self.assertIsNotNone(turno1.token)
        self.assertIsNotNone(turno2.token)
        self.assertNotEqual(turno1.token, turno2.token)
        # Verificar que son UUIDs válidos
        UUID(str(turno1.token), version=4)
        UUID(str(turno2.token), version=4)
