from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


class HabilidadProfesional(models.Model):
    """
    Tabla intermedia M:N entre Profesional y Servicio.
    Define qué servicios puede realizar cada profesional.
    """

    profesional = models.ForeignKey(
        "Profesional", on_delete=models.CASCADE,
        verbose_name="profesional"
    )
    servicio = models.ForeignKey(
        "Servicio", on_delete=models.CASCADE,
        verbose_name="servicio"
    )

    class Meta:
        verbose_name = "Habilidad del Profesional"
        verbose_name_plural = "Habilidades de los Profesionales"
        constraints = [
            models.UniqueConstraint(
                fields=["profesional", "servicio"],
                name="uq_habilidad_profesional"
            )
        ]

    def __str__(self):
        return f"{self.profesional} → {self.servicio}"


class Profesional(models.Model):
    """
    Perfil del profesional. Su comisión se define como porcentaje (35% o 50%)
    y se aplica sobre el total de servicios realizados.
    Las habilidades (servicios que puede realizar) se vinculan vía M2M
    a través de HabilidadProfesional.
    """

    nombre = models.CharField("nombre", max_length=100)
    apellido = models.CharField("apellido", max_length=100)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    porcentaje_comision = models.IntegerField(
        "porcentaje de comisión",
        default=35,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje de comisión para el profesional (0-100)"
    )
    activo = models.BooleanField("activo", default=True)
    fecha_contratacion = models.DateField("fecha de contratación", auto_now_add=True)
    
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='profesional', verbose_name='usuario del sistema'
    )

    habilidades = models.ManyToManyField(
        "Servicio",
        through=HabilidadProfesional,
        through_fields=("profesional", "servicio"),
        related_name="profesionales",
        verbose_name="habilidades"
    )

    class Meta:
        verbose_name = "Profesional"
        verbose_name_plural = "Profesionales"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
