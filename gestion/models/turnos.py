from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from .servicios import HorarioAtencion


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


class Reserva(models.Model):
    """Agrupa múltiples turnos creados en una misma sesión de reserva."""

    cliente = models.ForeignKey(
        "Cliente", on_delete=models.CASCADE,
        related_name="reservas",
        verbose_name="cliente"
    )
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    observaciones = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Reserva #{self.id} — {self.cliente}"


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
    profesional = models.ForeignKey(
        "Profesional", on_delete=models.CASCADE,
        related_name="turnos",
        verbose_name="profesional"
    )
    estacion = models.ForeignKey(
        "Estacion", on_delete=models.CASCADE,
        related_name="turnos",
        verbose_name="estación"
    )
    fecha_hora = models.DateTimeField("fecha y hora")
    hora_fin_estimada = models.DateTimeField("hora de fin estimada", blank=True, null=True)
    estado = models.CharField(
        "estado", max_length=20, choices=ESTADO_CHOICES, default="pendiente"
    )
    observaciones = models.TextField("observaciones", blank=True)
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    reserva = models.ForeignKey(
        Reserva, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="turnos_reserva",
        verbose_name="reserva asociada"
    )
    orden = models.PositiveSmallIntegerField(
        "orden en la reserva", default=0,
        help_text="Posición del turno dentro de la secuencia de la reserva"
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

        # 1. Validación de Horario de Atención
        dia_semana = self.fecha_hora.weekday()
        horario = HorarioAtencion.objects.filter(dia_semana=dia_semana).first()
        
        if not horario or not horario.abierto:
            raise ValidationError("La peluquería está cerrada en ese día de la semana.")
            
        hora_inicio = self.fecha_hora.time()
        hora_fin = self.hora_fin_estimada.time()
        
        if hora_inicio < horario.hora_apertura or hora_fin > horario.hora_cierre:
            raise ValidationError(f"El turno debe estar dentro del horario de atención: {horario.hora_apertura} a {horario.hora_cierre}.")

        # 2. Validación de disponibilidad del Profesional
        overlapping_prof = Turno.objects.filter(
            profesional=self.profesional,
            fecha_hora__lt=self.hora_fin_estimada,
            hora_fin_estimada__gt=self.fecha_hora
        ).exclude(pk=self.pk).exclude(estado__in=["cancelado", "completado"])
        
        if overlapping_prof.exists():
            raise ValidationError("El profesional ya tiene un turno asignado en ese horario.")

        # 3. Validación de disponibilidad de la Estación
        if hasattr(self, 'estacion') and self.estacion_id:
            overlapping_est = Turno.objects.filter(
                estacion=self.estacion,
                fecha_hora__lt=self.hora_fin_estimada,
                hora_fin_estimada__gt=self.fecha_hora
            ).exclude(pk=self.pk).exclude(estado__in=["cancelado", "completado"])
            
            if overlapping_est.exists():
                raise ValidationError("La estación seleccionada ya está ocupada en ese horario.")

        # 4. Validación de disponibilidad del Cliente
        overlapping_cliente = Turno.objects.filter(
            cliente=self.cliente,
            fecha_hora__lt=self.hora_fin_estimada,
            hora_fin_estimada__gt=self.fecha_hora
        ).exclude(pk=self.pk).exclude(estado__in=["cancelado", "completado"])
        
        if overlapping_cliente.exists():
            raise ValidationError("El cliente ya tiene otro turno reservado en este mismo horario.")

    @property
    def total_servicios(self):
        """Suma de precios reales de todos los servicios del turno."""
        return sum(d.precio_real for d in self.detalleturno_set.all())
