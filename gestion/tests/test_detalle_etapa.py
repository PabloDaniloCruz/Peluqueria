from django.test import TestCase, Client
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta, time as time_type, datetime
from decimal import Decimal

from ..models import (
    Cliente, Profesional, Servicio, Estacion, HorarioAtencion,
    Turno, DetalleTurno, DetalleEtapa, EtapaServicio
)


class TestDetalleEtapaModel(TestCase):
    """Pruebas del modelo DetalleEtapa (Phase 4.1)."""

    def setUp(self):
        for i in range(7):
            HorarioAtencion.objects.create(
                dia_semana=i,
                hora_apertura=time_type(8, 0),
                hora_cierre=time_type(20, 0),
                abierto=True
            )

        self.servicio = Servicio.objects.create(
            nombre="Tintura",
            precio_sugerido=Decimal("3000.00")
        )
        self.etapa1 = EtapaServicio.objects.create(
            servicio=self.servicio, orden=1, nombre="Aplicación",
            duracion=20, tipo_estacion="estacion", requiere_profesional=True
        )
        self.etapa2 = EtapaServicio.objects.create(
            servicio=self.servicio, orden=2, nombre="Exposición",
            duracion=15, tipo_estacion="ninguna", requiere_profesional=False
        )
        self.etapa3 = EtapaServicio.objects.create(
            servicio=self.servicio, orden=3, nombre="Lavado",
            duracion=10, tipo_estacion="lavacabeza", requiere_profesional=True
        )

        self.cliente = Cliente.objects.create(
            nombre="Test", apellido="User", telefono="3870000000"
        )
        self.profesional = Profesional.objects.create(
            nombre="Test", apellido="Prof", porcentaje_comision=50
        )
        self.profesional.habilidades.add(self.servicio)
        self.estacion = Estacion.objects.create(
            nombre="Silla 1", tipo="estacion", activa=True
        )

        self.turno = Turno.objects.create(
            cliente=self.cliente,
            fecha_hora=timezone.make_aware(
                datetime.combine(
                    timezone.localdate() + timedelta(days=1),
                    time_type(10, 0)
                )
            ),
            hora_fin_estimada=timezone.make_aware(
                datetime.combine(
                    timezone.localdate() + timedelta(days=1),
                    time_type(10, 45)
                )
            ),
            estado="pendiente"
        )
        self.detalle = DetalleTurno.objects.create(
            turno=self.turno,
            servicio=self.servicio,
            profesional=self.profesional,
            precio_real=Decimal("3000.00"),
            hora_inicio=time_type(10, 0),
            hora_fin=time_type(10, 45),
        )

    def test_create_detalle_etapa_con_estacion(self):
        """Crea DetalleEtapa con estación asignada."""
        de = DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa1,
            estacion=self.estacion,
            hora_inicio=time_type(10, 0),
            hora_fin=time_type(10, 20),
        )
        self.assertEqual(de.etapa_servicio, self.etapa1)
        self.assertEqual(de.estacion, self.estacion)
        self.assertEqual(de.detalle, self.detalle)
        self.assertIn(self.servicio.nombre, str(de))

    def test_create_detalle_etapa_sin_estacion(self):
        """Crea DetalleEtapa con estacion=None (tipo_estacion='ninguna')."""
        de = DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa2,
            estacion=None,
            hora_inicio=time_type(10, 20),
            hora_fin=time_type(10, 35),
        )
        self.assertIsNone(de.estacion)
        self.assertIn("Sin estación", str(de))

    def test_unique_constraint_detalle_etapa(self):
        """Valida UniqueConstraint(detalle, etapa_servicio)."""
        DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa1,
            estacion=self.estacion,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleEtapa.objects.create(
                    detalle=self.detalle,
                    etapa_servicio=self.etapa1,
                    estacion=self.estacion,
                )

    def test_related_name_etapas_asignadas(self):
        """Valida el related_name 'etapas_asignadas' desde DetalleTurno."""
        DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa1,
            estacion=self.estacion,
        )
        DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa3,
            estacion=None,
        )
        self.assertEqual(self.detalle.etapas_asignadas.count(), 2)

    def test_cascade_delete_detalle(self):
        """Eliminar DetalleTurno debe eliminar sus DetalleEtapa (CASCADE)."""
        DetalleEtapa.objects.create(
            detalle=self.detalle,
            etapa_servicio=self.etapa1,
            estacion=self.estacion,
        )
        detalle_id = self.detalle.id
        self.detalle.delete()
        self.assertEqual(DetalleEtapa.objects.filter(detalle_id=detalle_id).count(), 0)


class TestDetalleEtapaReservaFlows(TestCase):
    """Prueba que los flujos de reserva creen DetalleEtapa (Phase 4.3)."""

    def setUp(self):
        self.client = Client()
        for i in range(7):
            HorarioAtencion.objects.create(
                dia_semana=i,
                hora_apertura=time_type(9, 0),
                hora_cierre=time_type(19, 0),
                abierto=True
            )

        self.servicio = Servicio.objects.create(
            nombre="Corte Premium",
            precio_sugerido=Decimal("2000.00"),
            orden_sugerido=1
        )
        self.etapa_corte = EtapaServicio.objects.create(
            servicio=self.servicio, orden=1, nombre="Corte",
            duracion=30, tipo_estacion="estacion", requiere_profesional=True
        )

        self.estilista = Profesional.objects.create(
            nombre="Danilo", apellido="Cruz", porcentaje_comision=40
        )
        self.estilista.habilidades.add(self.servicio)

        self.estacion1 = Estacion.objects.create(
            nombre="Puesto 1", tipo="estacion", activa=True
        )

    def _bloque_corte(self, inicio="11:00", fin="11:30"):
        return {
            "servicio_id": self.servicio.id,
            "servicio_nombre": "Corte Premium",
            "profesional_id": self.estilista.id,
            "profesional_nombre": "Danilo Cruz",
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

    def test_reserva_publica_crea_detalle_etapa(self):
        """La reserva pública crea DetalleEtapa por cada etapa del servicio."""
        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        opcion_elegida = {
            "duracion_total": 30,
            "inicio": "11:00",
            "fin": "11:30",
            "bloques": [self._bloque_corte("11:00", "11:30")],
        }
        payload = {
            "nombre": "Sofia",
            "apellido": "Lopez",
            "dni": "40123456",
            "telefono": "3874443322",
            "fecha": fecha_test,
            "opcion": opcion_elegida,
        }
        response = self.client.post(
            '/api/reservas/publica/confirmar/',
            data=__import__('json').dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        # Verificar que se creó DetalleEtapa
        cliente = Cliente.objects.get(dni="40123456")
        turno = Turno.objects.filter(cliente=cliente).first()
        detalle = turno.detalleturno_set.first()
        etapas = detalle.etapas_asignadas.all()
        self.assertEqual(etapas.count(), 1)
        self.assertEqual(etapas[0].etapa_servicio, self.etapa_corte)
        self.assertEqual(etapas[0].estacion_id, self.estacion1.id)

    def test_reserva_multi_servicio_crea_detalle_etapa(self):
        """Reserva multi-servicio crea DetalleEtapa para cada servicio."""
        servicio2 = Servicio.objects.create(
            nombre="Lavado Nutritivo",
            precio_sugerido=Decimal("800.00"),
            orden_sugerido=2
        )
        etapa_lavado = EtapaServicio.objects.create(
            servicio=servicio2, orden=1, nombre="Lavado",
            duracion=15, tipo_estacion="estacion", requiere_profesional=True
        )
        self.estilista.habilidades.add(servicio2)

        fecha_test = (timezone.now() + timedelta(days=2)).date().isoformat()
        bloque_lavado = {
            "servicio_id": servicio2.id,
            "servicio_nombre": "Lavado Nutritivo",
            "profesional_id": self.estilista.id,
            "profesional_nombre": "Danilo Cruz",
            "inicio": "11:30",
            "fin": "11:45",
            "duracion": 15,
            "estaciones_asignadas": [
                {
                    "etapa_servicio_id": etapa_lavado.id,
                    "nombre": "Lavado",
                    "estacion_id": self.estacion1.id,
                    "hora_inicio": "11:30",
                    "hora_fin": "11:45",
                }
            ],
        }
        opcion_elegida = {
            "duracion_total": 45,
            "inicio": "11:00",
            "fin": "11:45",
            "bloques": [
                self._bloque_corte("11:00", "11:30"),
                bloque_lavado,
            ],
        }
        payload = {
            "nombre": "Multi",
            "apellido": "Servicio",
            "dni": "50123456",
            "telefono": "3875556677",
            "fecha": fecha_test,
            "opcion": opcion_elegida,
        }
        response = self.client.post(
            '/api/reservas/publica/confirmar/',
            data=__import__('json').dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        cliente = Cliente.objects.get(dni="50123456")
        turno = Turno.objects.filter(cliente=cliente).first()
        self.assertEqual(turno.detalleturno_set.count(), 2)
        for dt in turno.detalleturno_set.all():
            self.assertEqual(dt.etapas_asignadas.count(), 1)
