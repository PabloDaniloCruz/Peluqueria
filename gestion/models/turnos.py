import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from .servicios import HorarioAtencion, EtapaServicio, Estacion


class DetalleTurno(models.Model):
    """
    Tabla intermedia M:N entre Turno y Servicio.
    Registra el precio REAL cobrado por cada servicio en ese turno (puede
    diferir del precio sugerido por promociones, ajustes, etc.).
    """

    turno = models.ForeignKey(
        "Turno", on_delete=models.CASCADE,
        verbose_name="turno"
    )
    servicio = models.ForeignKey(
        "Servicio", on_delete=models.CASCADE,
        verbose_name="servicio"
    )
    precio_real = models.DecimalField(
        "precio real", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    profesional = models.ForeignKey(
        "Profesional", on_delete=models.PROTECT,
        verbose_name="profesional"
    )
    hora_inicio = models.DateTimeField("hora de inicio", null=True, blank=True)
    hora_fin = models.DateTimeField("hora de fin", null=True, blank=True)

    class Meta:
        verbose_name = "Detalle del Turno"
        verbose_name_plural = "Detalles de los Turnos"
        constraints = [
            models.UniqueConstraint(
                fields=["turno", "servicio"],
                name="uq_detalle_turno"
            )
        ]

    def __str__(self):
        return f"{self.turno} — {self.servicio} (${self.precio_real})"


class DetalleEtapa(models.Model):
    """
    Asignación de estación por etapa de servicio dentro de un DetalleTurno.
    Reemplaza DetalleTurno.estacion como source of truth para la ocupación
    de estaciones en el algoritmo de disponibilidad.
    """

    detalle = models.ForeignKey(
        DetalleTurno, on_delete=models.CASCADE,
        related_name='etapas_asignadas', verbose_name="detalle del turno"
    )
    etapa_servicio = models.ForeignKey(
        EtapaServicio, on_delete=models.PROTECT,
        verbose_name="etapa del servicio"
    )
    estacion = models.ForeignKey(
        Estacion, on_delete=models.PROTECT,
        verbose_name="estación asignada",
        null=True, blank=True
    )
    hora_inicio = models.DateTimeField("hora de inicio", null=True, blank=True)
    hora_fin = models.DateTimeField("hora de fin", null=True, blank=True)

    class Meta:
        verbose_name = "Detalle de Etapa"
        verbose_name_plural = "Detalles de Etapas"
        constraints = [
            models.UniqueConstraint(
                fields=["detalle", "etapa_servicio"],
                name="uq_detalle_etapa"
            )
        ]
        indexes = [
            models.Index(fields=["estacion"]),
        ]

    def __str__(self):
        estacion_nombre = self.estacion.nombre if self.estacion else "Sin estación"
        return f"{self.detalle} — {self.etapa_servicio.nombre} en {estacion_nombre}"


class Turno(models.Model):
    """
    Agendamiento de un turno. Requiere la triple coincidencia:
    Profesional + Estación + Fecha/Hora.
    Puede incluir uno o más servicios vinculados vía DetalleTurno.
    """

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("en_curso", "En Curso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
        ("por_reprogramar", "Por Reprogramar"),
    ]


    cliente = models.ForeignKey(
        "Cliente", on_delete=models.CASCADE,
        related_name="turnos",
        verbose_name="cliente"
    )
    fecha_hora = models.DateTimeField("fecha y hora")
    hora_fin_estimada = models.DateTimeField("hora de fin estimada", blank=True, null=True)
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    observaciones = models.TextField("observaciones", blank=True)
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    token = models.UUIDField(
        "token de autogestión", default=uuid.uuid4,
        unique=True, editable=False
    )

    servicios = models.ManyToManyField(
        "Servicio",
        through=DetalleTurno,
        through_fields=("turno", "servicio"),
        related_name="turnos",
        verbose_name="servicios"
    )

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"Turno #{self.id} — {self.cliente} | {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"

    def clean(self):
        super().clean()
        if not self.fecha_hora or not self.hora_fin_estimada:
            return

        # Validación de Horario de Atención
        dia_semana = self.fecha_hora.weekday()
        horario = HorarioAtencion.objects.filter(dia_semana=dia_semana).first()
        
        if not horario or not horario.abierto:
            raise ValidationError("La peluquería está cerrada en ese día de la semana.")
            
        hora_inicio = self.fecha_hora.time()
        hora_fin = self.hora_fin_estimada.time()
        
        if hora_inicio < horario.hora_apertura or hora_fin > horario.hora_cierre:
            raise ValidationError(f"El turno debe estar dentro del horario de atención: {horario.hora_apertura} a {horario.hora_cierre}.")

    @property
    def total_servicios(self):
        """Suma de precios reales de todos los servicios del turno."""
        return sum(d.precio_real for d in self.detalleturno_set.all())
