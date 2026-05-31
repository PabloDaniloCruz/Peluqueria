"""
Management command para cargar datos de prueba ficticios.

Uso:
    python manage.py cargar_datos_prueba
    python manage.py cargar_datos_prueba --forzar  # borra datos existentes primero

Genera clientes, profesionales, servicios con etapas, estaciones, horarios,
productos, turnos (pasados y futuros), ventas, fichas técnicas y consumos.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from random import choice, randint

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from gestion.models import (
    Cliente,
    Profesional,
    Servicio,
    EtapaServicio,
    Estacion,
    HorarioAtencion,
    Producto,
    Turno,
    DetalleTurno,
    DetalleEtapa,
    Venta,
    ComisionDetalle,
    DetalleVentaProducto,
    FichaTecnica,
    ConsumoInsumo,
    HabilidadProfesional,
)


# ──────────────────────────────────────────────
#  DATOS FICTICIOS
# ──────────────────────────────────────────────

SERVICIOS = [
    {
        "nombre": "Corte de Cabello (Mujer)",
        "precio": Decimal("4500.00"),
        "orden": 10,
        "etapas": [
            ("Corte", 25, "estacion", True),
        ],
    },
    {
        "nombre": "Corte de Cabello (Varón)",
        "precio": Decimal("3500.00"),
        "orden": 5,
        "etapas": [
            ("Corte", 20, "estacion", True),
        ],
    },
    {
        "nombre": "Lavado + Brushing",
        "precio": Decimal("5500.00"),
        "orden": 20,
        "etapas": [
            ("Lavado", 10, "lavacabeza", True),
            ("Brushing", 35, "estacion", True),
        ],
    },
    {
        "nombre": "Tintura (Raíz)",
        "precio": Decimal("8000.00"),
        "orden": 30,
        "etapas": [
            ("Aplicación de tintura", 20, "estacion", True),
            ("Tiempo de exposición", 25, "estacion", False),
            ("Lavado", 10, "lavacabeza", True),
            ("Brushing final", 15, "estacion", True),
        ],
    },
    {
        "nombre": "Mechas",
        "precio": Decimal("12000.00"),
        "orden": 40,
        "etapas": [
            ("Preparación y aplicación", 30, "estacion", True),
            ("Tiempo de acción", 25, "estacion", False),
            ("Lavado", 10, "lavacabeza", True),
            ("Brushing", 20, "estacion", True),
        ],
    },
    {
        "nombre": "Alisado",
        "precio": Decimal("15000.00"),
        "orden": 50,
        "etapas": [
            ("Lavado", 10, "lavacabeza", True),
            ("Aplicación de alisado", 30, "estacion", True),
            ("Planchado", 60, "estacion", True),
            ("Lavado final", 10, "lavacabeza", True),
            ("Secado", 20, "estacion", True),
        ],
    },
    {
        "nombre": "Baño de Crema",
        "precio": Decimal("3500.00"),
        "orden": 25,
        "etapas": [
            ("Lavado", 10, "lavacabeza", True),
            ("Aplicación de crema", 5, "estacion", True),
            ("Tiempo de acción", 15, "estacion", False),
            ("Enjuague", 5, "lavacabeza", True),
        ],
    },
    {
        "nombre": "Peinado",
        "precio": Decimal("3000.00"),
        "orden": 15,
        "etapas": [
            ("Peinado", 20, "estacion", True),
        ],
    },
    {
        "nombre": "Manicuría Completa",
        "precio": Decimal("4500.00"),
        "orden": 60,
        "etapas": [
            ("Limpieza y limado", 15, "manicura", True),
            ("Cutículas", 10, "manicura", True),
            ("Esmaltado", 15, "manicura", True),
        ],
    },
    {
        "nombre": "Corte + Brushing",
        "precio": Decimal("7000.00"),
        "orden": 12,
        "etapas": [
            ("Lavado", 10, "lavacabeza", True),
            ("Corte", 20, "estacion", True),
            ("Brushing", 20, "estacion", True),
        ],
    },
]

ESTACIONES = [
    ("Silla 1", "estacion"),
    ("Silla 2", "estacion"),
    ("Silla 3", "estacion"),
    ("Silla 4", "estacion"),
    ("Lavacabezas 1", "lavacabeza"),
    ("Lavacabezas 2", "lavacabeza"),
    ("Manicura 1", "manicura"),
]

HORARIOS = [
    (0, time(9, 0), time(20, 0), True),   # Lunes
    (1, time(9, 0), time(20, 0), True),   # Martes
    (2, time(9, 0), time(20, 0), True),   # Miércoles
    (3, time(9, 0), time(20, 0), True),   # Jueves
    (4, time(9, 0), time(20, 0), True),   # Viernes
    (5, time(9, 0), time(14, 0), True),   # Sábado
    (6, time(0, 0), time(0, 0), False),   # Domingo - cerrado
]

PROFESIONALES = [
    {
        "dni": "25123456",
        "nombre": "Ana",
        "apellido": "López",
        "telefono": "3875550101",
        "email": "ana.lopez@studiostesta.com",
        "comision": 40,
        "servicios": [
            "Corte de Cabello (Mujer)", "Corte de Cabello (Varón)",
            "Lavado + Brushing", "Tintura (Raíz)", "Mechas",
            "Baño de Crema", "Peinado", "Corte + Brushing",
        ],
    },
    {
        "dni": "27123457",
        "nombre": "Carlos",
        "apellido": "Martínez",
        "telefono": "3875550102",
        "email": "carlos.martinez@studiostesta.com",
        "comision": 35,
        "servicios": [
            "Corte de Cabello (Mujer)", "Corte de Cabello (Varón)",
            "Lavado + Brushing", "Peinado", "Corte + Brushing",
            "Baño de Crema",
        ],
    },
    {
        "dni": "30123458",
        "nombre": "Laura",
        "apellido": "García",
        "telefono": "3875550103",
        "email": "laura.garcia@studiostesta.com",
        "comision": 50,
        "servicios": [
            "Tintura (Raíz)", "Mechas", "Alisado",
            "Lavado + Brushing", "Baño de Crema", "Corte + Brushing",
            "Corte de Cabello (Mujer)",
        ],
    },
    {
        "dni": "32123459",
        "nombre": "Pedro",
        "apellido": "Rodríguez",
        "telefono": "3875550104",
        "email": "pedro.rodriguez@studiostesta.com",
        "comision": 35,
        "servicios": [
            "Corte de Cabello (Varón)", "Peinado",
        ],
    },
    {
        "dni": "28123460",
        "nombre": "María",
        "apellido": "Fernández",
        "telefono": "3875550105",
        "email": "maria.fernandez@studiostesta.com",
        "comision": 35,
        "servicios": [
            "Manicuría Completa",
        ],
    },
]

CLIENTES = [
    {"dni": "20123450", "nombre": "Sofía", "apellido": "Giménez", "telefono": "3875551001", "email": "sofia.gimenez@email.com"},
    {"dni": "21123451", "nombre": "Martina", "apellido": "Pérez", "telefono": "3875551002", "email": "martina.perez@email.com"},
    {"dni": "22123452", "nombre": "Joaquín", "apellido": "Díaz", "telefono": "3875551003", "email": "joaquin.diaz@email.com"},
    {"dni": "23123453", "nombre": "Valentina", "apellido": "Torres", "telefono": "3875551004", "email": "vale.torres@email.com"},
    {"dni": "24123454", "nombre": "Luciano", "apellido": "Acosta", "telefono": "3875551005", "email": "luciano.acosta@email.com"},
    {"dni": "25123455", "nombre": "Camila", "apellido": "Medina", "telefono": "3875551006", "email": "camila.medina@email.com"},
    {"dni": "26123456", "nombre": "Fernando", "apellido": "Ruiz", "telefono": "3875551007", "email": "fer.ruiz@email.com"},
    {"dni": "27123457", "nombre": "Lucía", "apellido": "Moreno", "telefono": "3875551008", "email": "lucia.moreno@email.com"},
    {"dni": "28123458", "nombre": "Agustín", "apellido": "Sosa", "telefono": "3875551009", "email": "agus.sosa@email.com"},
    {"dni": "29123459", "nombre": "Florencia", "apellido": "Vega", "telefono": "3875551010", "email": "flor.vega@email.com"},
    {"dni": "30123460", "nombre": "Matías", "apellido": "Castillo", "telefono": "3875551011", "email": "mati.castillo@email.com"},
    {"dni": "31123461", "nombre": "Julieta", "apellido": "Ríos", "telefono": "3875551012", "email": "juli.rios@email.com"},
]

PRODUCTOS_VENTA = [
    ("Champú Profesional Restaurador", "Champú para cabello dañado 300ml", Decimal("3200.00"), 15, 5, "mililitros"),
    ("Acondicionador Profesional", "Acondicionador nutritivo 300ml", Decimal("3500.00"), 12, 5, "mililitros"),
    ("Mascarilla Capilar Keratina", "Mascarilla reparadora 200g", Decimal("4800.00"), 8, 3, "gramos"),
    ("Cera para Peinar", "Cera modeladora 100g", Decimal("2500.00"), 10, 5, "gramos"),
    ("Laca Fijadora", "Laca extrafuerte 400ml", Decimal("2800.00"), 10, 4, "mililitros"),
    ("Aceite de Argan", "Aceite nutritivo 50ml", Decimal("5500.00"), 5, 2, "mililitros"),
    ("Protector Térmico", "Spray protector de calor 200ml", Decimal("3800.00"), 7, 3, "mililitros"),
    ("Esmalte Semi-permanente", "Esmalte color nude 15ml", Decimal("2200.00"), 20, 10, "mililitros"),
]

INSUMOS = [
    ("Coloración Tono 5.0", "Tinte castaño claro 60ml", None, 10, 3, "mililitros"),
    ("Coloración Tono 7.3", "Tinte rubio dorado 60ml", None, 8, 3, "mililitros"),
    ("Coloración Tono 9.1", "Tinte rubio ceniza 60ml", None, 6, 3, "mililitros"),
    ("Oxigenante 20 Vol", "Agua oxigenada 20 volúmenes 500ml", None, 15, 5, "mililitros"),
    ("Oxigenante 30 Vol", "Agua oxigenada 30 volúmenes 500ml", None, 12, 5, "mililitros"),
    ("Polvo Decolorante", "Polvo decolorante 500g", None, 5, 2, "gramos"),
    ("Guantes de Latex", "Guantes descartables caja 100u", None, 10, 5, "unidades"),
    ("Papel de Aluminio", "Rollos para mechas 50m", None, 4, 2, "unidades"),
]


class Command(BaseCommand):
    help = "Carga datos ficticios para testing de la peluquería"

    def add_arguments(self, parser):
        parser.add_argument(
            "--forzar", "-f",
            action="store_true",
            help="Borra todos los datos existentes antes de cargar",
        )

    def handle(self, *args, **options):
        if options["forzar"]:
            self._limpiar_base()
            self.stdout.write(self.style.WARNING("Base de datos limpiada."))

        if self._hay_datos():
            self.stdout.write(
                self.style.WARNING(
                    "Ya existen datos en la base. Usá --forzar para recargar desde cero."
                )
            )
            return

        self._crear_estaciones()
        self._crear_horarios()
        self._crear_servicios()
        self._crear_productos()
        profesionales = self._crear_profesionales()
        clientes = self._crear_clientes()
        servicios = {s.nombre: s for s in Servicio.objects.all()}
        profesionales_dict = {p.apellido: p for p in Profesional.objects.all()}

        self._crear_turnos_pasados(clientes, profesionales, servicios)
        self._crear_turnos_futuros(clientes, profesionales, servicios)
        self._crear_fichas_tecnicas(clientes)

        self.stdout.write(self.style.SUCCESS("\nOK — Datos de prueba cargados exitosamente."))
        self._resumen()

    # ── Helpers ──────────────────────────────

    def _hay_datos(self):
        return (
            Servicio.objects.exists()
            or Cliente.objects.exists()
            or Profesional.objects.exists()
        )

    def _limpiar_base(self):
        # Orden: tablas dependientes primero
        ComisionDetalle.objects.all().delete()
        DetalleVentaProducto.objects.all().delete()
        Venta.objects.all().delete()
        ConsumoInsumo.objects.all().delete()
        DetalleEtapa.objects.all().delete()
        DetalleTurno.objects.all().delete()
        Turno.objects.all().delete()
        FichaTecnica.objects.all().delete()
        HabilidadProfesional.objects.all().delete()
        Profesional.objects.all().delete()
        Cliente.objects.all().delete()
        EtapaServicio.objects.all().delete()
        Servicio.objects.all().delete()
        Estacion.objects.all().delete()
        HorarioAtencion.objects.all().delete()
        Producto.objects.all().delete()

    def _crear_estaciones(self):
        for nombre, tipo in ESTACIONES:
            Estacion.objects.create(nombre=nombre, tipo=tipo)
        self.stdout.write(f"  • {Estacion.objects.count()} estaciones creadas")

    def _crear_horarios(self):
        for dia, apertura, cierre, abierto in HORARIOS:
            HorarioAtencion.objects.create(
                dia_semana=dia,
                hora_apertura=apertura,
                hora_cierre=cierre,
                abierto=abierto,
            )
        self.stdout.write(f"  • {HorarioAtencion.objects.count()} horarios creados")

    def _crear_servicios(self):
        for s in SERVICIOS:
            serv = Servicio.objects.create(
                nombre=s["nombre"],
                precio_sugerido=s["precio"],
                orden_sugerido=s["orden"],
            )
            for i, (nombre_etapa, duracion, tipo_estacion, requiere_prof) in enumerate(
                s["etapas"], start=1
            ):
                EtapaServicio.objects.create(
                    servicio=serv,
                    orden=i,
                    nombre=nombre_etapa,
                    duracion=duracion,
                    tipo_estacion=tipo_estacion,
                    requiere_profesional=requiere_prof,
                )
        self.stdout.write(f"  • {Servicio.objects.count()} servicios creados")
        self.stdout.write(f"  • {EtapaServicio.objects.count()} etapas creadas")

    def _crear_productos(self):
        for nombre, desc, precio, stock, stock_min, unidad in PRODUCTOS_VENTA:
            Producto.objects.create(
                nombre=nombre,
                descripcion=desc,
                es_para_venta=True,
                es_insumo=False,
                unidad_medida=unidad,
                precio=precio,
                stock_actual=stock,
                stock_minimo=stock_min,
            )
        for nombre, desc, precio, stock, stock_min, unidad in INSUMOS:
            Producto.objects.create(
                nombre=nombre,
                descripcion=desc,
                es_para_venta=False,
                es_insumo=True,
                unidad_medida=unidad,
                precio=precio,
                stock_actual=stock,
                stock_minimo=stock_min,
            )
        self.stdout.write(f"  • {Producto.objects.count()} productos creados")

    def _crear_profesionales(self):
        creados = []
        for p in PROFESIONALES:
            prof = Profesional.objects.create(
                dni=p["dni"],
                nombre=p["nombre"],
                apellido=p["apellido"],
                telefono=p["telefono"],
                email=p["email"],
                porcentaje_comision=p["comision"],
            )
            for nombre_servicio in p["servicios"]:
                try:
                    servicio = Servicio.objects.get(nombre=nombre_servicio)
                    HabilidadProfesional.objects.create(
                        profesional=prof, servicio=servicio
                    )
                except Servicio.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ Servicio '{nombre_servicio}' no encontrado para {prof}"
                        )
                    )
            creados.append(prof)
        self.stdout.write(f"  • {len(creados)} profesionales creados")
        return creados

    def _crear_clientes(self):
        creados = []
        for c in CLIENTES:
            cliente = Cliente.objects.create(**c)
            creados.append(cliente)
        self.stdout.write(f"  • {len(creados)} clientes creados")
        return creados

    # ── Turnos ───────────────────────────────

    def _servicios_para_profesional(self, profesional):
        """Devuelve los servicios que un profesional puede realizar."""
        return Servicio.objects.filter(
            profesionales=profesional
        )

    def _elegir_profesional_para_servicio(self, profesionales, nombre_servicio):
        """Elige un profesional que pueda realizar el servicio dado."""
        for prof in profesionales:
            if Servicio.objects.filter(
                profesionales=prof,
                nombre=nombre_servicio,
            ).exists():
                return prof
        return choice(profesionales)

    def _crear_turno(
        self, cliente, profesional, servicio_nombre, fecha_hora, estado,
        crear_venta=False, metodo_pago=None
    ):
        """Crea un Turno con su DetalleTurno, DetalleEtapa y opcionalmente Venta."""
        serv = Servicio.objects.get(nombre=servicio_nombre)
        duracion_total = serv.duracion_estimada
        hora_fin = fecha_hora + timedelta(minutes=duracion_total)

        turno = Turno.objects.create(
            cliente=cliente,
            fecha_hora=fecha_hora,
            hora_fin_estimada=hora_fin,
            estado=estado,
        )

        detalle = DetalleTurno.objects.create(
            turno=turno,
            servicio=serv,
            precio_real=serv.precio_sugerido,
            profesional=profesional,
            hora_inicio=fecha_hora,
            hora_fin=hora_fin,
        )

        # Asignar estaciones a cada etapa
        estaciones_libres = list(Estacion.objects.filter(activa=True))
        for etapa in serv.etapas.all():
            estacion = None
            if etapa.tipo_estacion != "ninguna":
                # Buscar estación del tipo adecuado
                posibles = [e for e in estaciones_libres if e.tipo == etapa.tipo_estacion]
                if posibles:
                    estacion = choice(posibles)
            DetalleEtapa.objects.create(
                detalle=detalle,
                etapa_servicio=etapa,
                estacion=estacion,
            )

        if crear_venta and estado == "completado":
            self._crear_venta(turno, detalle, profesional, metodo_pago or "efectivo")

        return turno

    def _crear_venta(self, turno, detalle, profesional, metodo_pago):
        """Crea una Venta para un turno completado.
        La ComisionDetalle se crea automáticamente vía señal post_save.
        """
        total = detalle.precio_real
        comision = total * Decimal(profesional.porcentaje_comision) / Decimal(100)

        venta = Venta.objects.create(
            turno=turno,
            total=total,
            metodo_pago=metodo_pago,
            comision=comision,
        )

        # A veces agregar un producto a la venta
        if choice([True, False]):
            productos_venta = list(Producto.objects.filter(es_para_venta=True, stock_actual__gt=0))
            if productos_venta:
                prod = choice(productos_venta)
                cant = randint(1, 2)
                DetalleVentaProducto.objects.create(
                    venta=venta,
                    producto=prod,
                    cantidad=cant,
                    precio_unitario=prod.precio,
                )
                # Descontar stock
                prod.stock_actual -= cant
                prod.save()

        return venta

    def _crear_turnos_pasados(self, clientes, profesionales, servicios):
        """Crea turnos en fechas pasadas con estado 'completado' y sus ventas."""
        hoy = timezone.localdate()
        metodos = ["efectivo", "tarjeta_debito", "tarjeta_credito", "mercadopago", "transferencia"]

        turnos_creados = 0
        # Turnos en las últimas 2 semanas
        for dia_offset in range(14, 0, -1):
            fecha = hoy - timedelta(days=dia_offset)
            if fecha.weekday() == 6:  # domingo
                continue

            # 2 a 4 turnos por día
            for _ in range(randint(2, 4)):
                cliente = choice(clientes)
                profesional = choice(profesionales)
                servs_prof = list(self._servicios_para_profesional(profesional))
                if not servs_prof:
                    continue
                serv = choice(servs_prof)

                hora_base = time(randint(9, 17), choice([0, 15, 30, 45]))
                fecha_hora = timezone.make_aware(
                    datetime.combine(fecha, hora_base),
                )

                self._crear_turno(
                    cliente=cliente,
                    profesional=profesional,
                    servicio_nombre=serv.nombre,
                    fecha_hora=fecha_hora,
                    estado="completado",
                    crear_venta=True,
                    metodo_pago=choice(metodos),
                )
                turnos_creados += 1

        self.stdout.write(f"  • {turnos_creados} turnos pasados (completados) creados")

    def _crear_turnos_futuros(self, clientes, profesionales, servicios):
        """Crea turnos en fechas futuras con estado 'pendiente'."""
        hoy = timezone.localdate()
        turnos_creados = 0

        for dia_offset in range(1, 8):  # próxima semana
            fecha = hoy + timedelta(days=dia_offset)
            if fecha.weekday() == 6:  # domingo
                continue

            for _ in range(randint(1, 4)):
                cliente = choice(clientes)
                profesional = choice(profesionales)
                servs_prof = list(self._servicios_para_profesional(profesional))
                if not servs_prof:
                    continue
                serv = choice(servs_prof)

                hora_base = time(randint(9, 17), choice([0, 15, 30, 45]))
                fecha_hora = timezone.make_aware(
                    datetime.combine(fecha, hora_base),
                )

                # A veces un turno cancelado
                estado = choice(["pendiente", "pendiente", "pendiente", "cancelado"])

                self._crear_turno(
                    cliente=cliente,
                    profesional=profesional,
                    servicio_nombre=serv.nombre,
                    fecha_hora=fecha_hora,
                    estado=estado,
                )
                turnos_creados += 1

        self.stdout.write(f"  • {turnos_creados} turnos futuros creados")

    def _crear_fichas_tecnicas(self, clientes):
        """Crea algunas fichas técnicas de ejemplo."""
        formulas = [
            {
                "desc": "Tintura castaño oscuro",
                "formula": "Igora Royal 5-0 (30g) + Oxigenante 20 Vol (30g)\nTiempo de exposición: 35 min",
            },
            {
                "desc": "Mechas rubias",
                "formula": "Polvo decolorante (20g) + Oxigenante 30 Vol (30g)\nTiempo de acción: 25 min",
            },
            {
                "desc": "Baño de crema nutritivo",
                "formula": "Mascarilla Keratina (40g) + Aceite de Argan (5ml)\nTiempo de acción: 15 min con calor",
            },
        ]

        for formula in formulas:
            cliente = choice(clientes)
            FichaTecnica.objects.create(
                cliente=cliente,
                descripcion=formula["desc"],
                formula_quimica=formula["formula"],
            )

        self.stdout.write(f"  • {FichaTecnica.objects.count()} fichas técnicas creadas")

    def _resumen(self):
        """Muestra un resumen de los datos cargados."""
        models = [
            ("Servicios", Servicio),
            ("Etapas de Servicio", EtapaServicio),
            ("Estaciones", Estacion),
            ("Horarios de Atención", HorarioAtencion),
            ("Profesionales", Profesional),
            ("Clientes", Cliente),
            ("Turnos", Turno),
            ("Detalles de Turno", DetalleTurno),
            ("Detalles de Etapa", DetalleEtapa),
            ("Ventas", Venta),
            ("Comisiones", ComisionDetalle),
            ("Detalles Venta Producto", DetalleVentaProducto),
            ("Productos", Producto),
            ("Fichas Técnicas", FichaTecnica),
        ]

        self.stdout.write("\n--- Resumen ---")
        self.stdout.write("-" * 40)
        for nombre, modelo in models:
            self.stdout.write(f"  {nombre}: {modelo.objects.count()}")
