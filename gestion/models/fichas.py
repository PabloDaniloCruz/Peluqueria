from django.db import models


class FichaTecnica(models.Model):
    """
    Repositorio de fórmulas químicas para tratamientos de coloración.
    Relacionada al Cliente para mantener el historial de fórmulas aplicadas.
    """

    cliente = models.ForeignKey(
        "Cliente", on_delete=models.CASCADE,
        related_name="fichas_tecnicas",
        verbose_name="cliente"
    )
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    turno = models.ForeignKey(
        "Turno", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fichas_tecnicas",
        verbose_name="turno asociado",
        help_text="Turno en el que se generó esta ficha"
    )
    descripcion = models.TextField(
        "descripción",
        blank=True, null=True,
        help_text="Nombre o descripción del tratamiento/fórmula"
    )
    formula_quimica = models.TextField(
        "fórmula química",
        blank=True, null=True,
        help_text="Proporciones, marcas, colores, tiempos de acción, etc."
    )
    observaciones = models.TextField("observaciones", blank=True)

    class Meta:
        verbose_name = "Ficha Técnica"
        verbose_name_plural = "Fichas Técnicas"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return (
            f"Ficha #{self.id} — {self.cliente} "
            f"({self.fecha_creacion.strftime('%d/%m/%Y')})"
        )
