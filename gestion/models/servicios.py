from django.db import models
from django.core.validators import MinValueValidator


class Servicio(models.Model):
    """Servicio ofrecido: nombre, precio sugerido y duración estimada en minutos."""

    nombre = models.CharField("nombre", max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    precio_sugerido = models.DecimalField(
        "precio sugerido", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    duracion_estimada = models.PositiveIntegerField(
        "duración estimada (minutos)",
        help_text="Duración estimada del servicio en minutos"
    )
    orden_sugerido = models.PositiveSmallIntegerField(
        "orden sugerido", default=0,
        help_text="Orden predefinido de la peluquería para secuencias de servicios (menor = primero)"
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["orden_sugerido", "nombre"]

    def __str__(self):
        return self.nombre


class Estacion(models.Model):
    """Recurso físico: estación de trabajo o lava-cabezas."""

    TIPO_CHOICES = [
        ("estacion", "Estación de Trabajo"),
        ("lavacabeza", "Lava-Cabezas"),
    ]

    nombre = models.CharField("nombre", max_length=50, unique=True)
    tipo = models.CharField("tipo", max_length=20, choices=TIPO_CHOICES)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "Estación"
        verbose_name_plural = "Estaciones"
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class HorarioAtencion(models.Model):
    """Horarios generales de la peluquería."""
    DIA_CHOICES = [
        (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
        (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo"),
    ]
    dia_semana = models.IntegerField("día de la semana", choices=DIA_CHOICES, unique=True)
    hora_apertura = models.TimeField("hora de apertura")
    hora_cierre = models.TimeField("hora de cierre")
    abierto = models.BooleanField("abierto", default=True)

    class Meta:
        verbose_name = "Horario de Atención"
        verbose_name_plural = "Horarios de Atención"
        ordering = ["dia_semana"]

    def __str__(self):
        estado = "Abierto" if self.abierto else "Cerrado"
        return f"{self.get_dia_semana_display()} — {estado} ({self.hora_apertura} a {self.hora_cierre})"
