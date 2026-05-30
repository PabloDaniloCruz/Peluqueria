from django.db import models


class Cliente(models.Model):
    """Datos personales e histórico de fidelidad del cliente."""

    dni = models.CharField(
        "DNI", max_length=15, unique=True, blank=True, null=True,
        help_text="Documento Nacional de Identidad (opcional para extranjeros)"
    )
    nombre = models.CharField("nombre", max_length=100)
    apellido = models.CharField("apellido", max_length=100)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    fecha_registro = models.DateTimeField("fecha de registro", auto_now_add=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["apellido", "nombre"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"
