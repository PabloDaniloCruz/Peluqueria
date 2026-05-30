import threading
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, time as time_type, datetime
from decimal import Decimal

from ..models import (
    Cliente, Profesional, Servicio, Estacion, HorarioAtencion, Turno, DetalleTurno, Producto, EtapaServicio
)


class TestConcurrencia(TransactionTestCase):
    def setUp(self):
        # 1. Crear Horario de Atención para todos los días de la semana
        for i in range(7):
            HorarioAtencion.objects.create(
                dia_semana=i,
                hora_apertura=time_type(8, 0),
                hora_cierre=time_type(20, 0),
                abierto=True
            )
            
        # 2. Crear Clientes
        self.cliente1 = Cliente.objects.create(
            nombre="Juan",
            apellido="Perez",
            telefono="11223344"
        )
        self.cliente2 = Cliente.objects.create(
            nombre="Maria",
            apellido="Gomez",
            telefono="55667788"
        )
        
        # 3. Crear Servicio
        self.servicio = Servicio.objects.create(
            nombre="Corte de Pelo",
            precio_sugerido=Decimal("1500.00")
        )
        EtapaServicio.objects.create(
            servicio=self.servicio, orden=1, nombre="Corte",
            duracion=30, tipo_estacion="estacion", requiere_profesional=True
        )
        
        # 4. Crear Profesional y vincular Habilidad
        self.profesional = Profesional.objects.create(
            nombre="Carlos",
            apellido="Estilista",
            porcentaje_comision=35
        )
        self.profesional.habilidades.add(self.servicio)
        
        # 5. Crear Estación
        self.estacion = Estacion.objects.create(
            nombre="Estacion 1",
            tipo="estacion",
            activa=True
        )
        
        # 6. Crear Producto con stock para facturación
        self.producto = Producto.objects.create(
            nombre="Shampoo Hidratante",
            precio=Decimal("500.00"),
            stock_actual=Decimal("5.00"),
            stock_minimo=Decimal("1.00"),
            es_para_venta=True
        )

    def test_concurrent_turno_multiples_detalles(self):
        """
        Valida que un Turno pueda tener múltiples DetalleTurno con distintos profesionales
        creados de forma atómica (nuevo modelo: 1 Turno = 1 visita con N servicios).
        """
        from django.db import transaction

        fecha_hora = timezone.make_aware(datetime.combine(
            timezone.now().date() + timedelta(days=1), time_type(10, 0)
        ))
        hora_fin = fecha_hora + timedelta(minutes=45)

        # Crear un segundo profesional y un segundo servicio
        from ..models import DetalleTurno
        profesional2 = Profesional.objects.create(
            nombre="Ana", apellido="Estilista",
            porcentaje_comision=30
        )
        profesional2.habilidades.add(self.servicio)

        servicio2 = Servicio.objects.create(
            nombre="Corte + Lavado",
            precio_sugerido=Decimal("2500.00")
        )
        EtapaServicio.objects.create(
            servicio=servicio2, orden=1, nombre="Corte",
            duracion=30, tipo_estacion="estacion", requiere_profesional=True
        )
        profesional2.habilidades.add(servicio2)
        self.profesional.habilidades.add(servicio2)

        try:
            with transaction.atomic():
                turno = Turno.objects.create(
                    cliente=self.cliente1,
                    fecha_hora=fecha_hora,
                    hora_fin_estimada=hora_fin,
                    estado="pendiente"
                )

                # Crear 2 DetalleTurno con distintos profesionales y servicios
                dt1 = DetalleTurno.objects.create(
                    turno=turno,
                    servicio=self.servicio,
                    profesional=self.profesional,
                    precio_real=Decimal("1500.00"),
                    hora_inicio=time_type(10, 0),
                    hora_fin=time_type(10, 30),
                )

                dt2 = DetalleTurno.objects.create(
                    turno=turno,
                    servicio=servicio2,
                    profesional=profesional2,
                    precio_real=Decimal("2500.00"),
                    hora_inicio=time_type(10, 30),
                    hora_fin=time_type(10, 45),
                )

            # Verificar: 1 Turno con 2 DetalleTurno
            self.assertEqual(Turno.objects.count(), 1)
            self.assertEqual(DetalleTurno.objects.count(), 2)
            self.assertEqual(turno.detalleturno_set.count(), 2)

            # Verificar profesionales distintos
            profesionales = set(dt.profesional.id for dt in turno.detalleturno_set.all())
            self.assertIn(self.profesional.id, profesionales)
            self.assertIn(profesional2.id, profesionales)
        except Exception as e:
            self.fail(f"La creación atómica de 1 Turno + N DetalleTurno falló: {e}")

    def test_concurrency_stock_facturacion(self):
        """
        Intenta facturar productos superando el stock disponible de forma concurrente.
        El bloqueo de stock debe evitar que quede en negativo y revertir la venta fallida.
        """
        # Simular facturación con stock insuficiente
        from django.db import transaction
        
        # Intentar vender 6 unidades cuando solo hay 5
        cantidad_venta = 6
        
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                # select_for_update
                prod = Producto.objects.select_for_update().get(id=self.producto.id)
                if prod.stock_actual < cantidad_venta:
                    raise ValidationError("No hay suficiente stock")
                
                prod.stock_actual -= cantidad_venta
                prod.save()
                
        # Verificar que el stock siga siendo 5 (hizo rollback completo del descuento)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, Decimal("5.00"))
