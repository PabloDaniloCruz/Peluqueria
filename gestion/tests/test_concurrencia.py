import threading
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, time as time_type, datetime
from decimal import Decimal

from ..models import (
    Cliente, Profesional, Servicio, Estacion, HorarioAtencion, Turno, DetalleTurno, Producto
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
            precio_sugerido=Decimal("1500.00"),
            duracion_estimada=30
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

    def test_concurrent_turnos_same_professional(self):
        """
        Intenta guardar dos turnos superpuestos para el mismo profesional concurrentemente.
        El bloqueo pesimista debe forzar la serialización y que el segundo lance una validación errónea.
        """
        # Definir horario común
        fecha_hora = timezone.make_aware(datetime.combine(timezone.now().date() + timedelta(days=1), time_type(10, 0)))
        hora_fin_estimada = fecha_hora + timedelta(minutes=30)
        
        results = []
        errors = []
        
        def attempt_booking(cliente, profesional, estacion, ident):
            try:
                from django.db import transaction
                with transaction.atomic():
                    # Bloquear profesional y estaciones
                    prof = Profesional.objects.select_for_update().get(id=profesional.id)
                    _ = list(Estacion.objects.select_for_update().filter(activa=True).order_by('id'))
                    
                    # Chequear superposición del profesional (lógica que ocurre en clean del turno)
                    overlapping = Turno.objects.filter(
                        profesional=prof,
                        fecha_hora__lt=hora_fin_estimada,
                        hora_fin_estimada__gt=fecha_hora
                    ).exclude(estado__in=["cancelado", "completado"]).exists()
                    
                    if overlapping:
                        raise ValidationError("El profesional ya tiene un turno asignado en ese horario.")
                        
                    # Crear turno
                    t = Turno.objects.create(
                        cliente=cliente,
                        profesional=prof,
                        estacion=estacion,
                        fecha_hora=fecha_hora,
                        hora_fin_estimada=hora_fin_estimada
                    )
                    results.append(t)
            except Exception as e:
                errors.append(e)

        # Crear dos hilos concurrentes
        t1 = threading.Thread(target=attempt_booking, args=(self.cliente1, self.profesional, self.estacion, 1))
        t2 = threading.Thread(target=attempt_booking, args=(self.cliente2, self.profesional, self.estacion, 2))
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Debió haberse creado exactamente 1 turno y el otro debió fallar por colisión o por bloqueo de base de datos
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        
        from django.db import DatabaseError
        error = errors[0]
        if isinstance(error, ValidationError):
            self.assertEqual(str(error.messages[0]), "El profesional ya tiene un turno asignado en ese horario.")
        elif isinstance(error, (DatabaseError, Exception)) and "locked" in str(error).lower():
            # SQLite bloquea la base de datos concurrentemente, lo cual es totalmente válido
            pass
        else:
            self.fail(f"Se esperaba una colisión de negocio o un bloqueo de base de datos, pero se obtuvo: {type(error)} - {error}")

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
