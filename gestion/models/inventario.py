from django.db import models
from django.core.validators import MinValueValidator


class Producto(models.Model):
    """
    Inventario de productos para venta o uso interno.
    Permite gestionar el stock actual y establecer un stock mínimo.
    """

    UNIDAD_MEDIDA_CHOICES = [
        ("unidades", "Unidades"),
        ("gramos", "Gramos"),
        ("mililitros", "Mililitros"),
    ]

    nombre = models.CharField("nombre", max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    es_para_venta = models.BooleanField("¿Es para la venta al público?", default=True)
    es_insumo = models.BooleanField("¿Es insumo interno (ej. coloración)?", default=False)
    unidad_medida = models.CharField("unidad de medida", max_length=20, choices=UNIDAD_MEDIDA_CHOICES, default="unidades")
    
    precio = models.DecimalField(
        "precio", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True, null=True,
        help_text="Precio de venta al público (si aplica)"
    )
    stock_actual = models.DecimalField(
        "stock actual", max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    stock_minimo = models.DecimalField(
        "stock mínimo", max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} (Stock: {self.stock_actual} {self.get_unidad_medida_display()})"


class ConsumoInsumo(models.Model):
    """Registro de insumos utilizados durante un turno específico."""
    turno = models.ForeignKey("Turno", on_delete=models.CASCADE, related_name="insumos_usados")
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT, related_name="consumos")
    cantidad_usada = models.DecimalField("cantidad usada", max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)], help_text="En la unidad de medida del producto (ej. 45.50 gramos)")

    class Meta:
        verbose_name = "Consumo de Insumo"
        verbose_name_plural = "Consumos de Insumos"
        constraints = [
            models.UniqueConstraint(
                fields=["turno", "producto"],
                name="uq_consumo_turno_producto"
            )
        ]

    def __str__(self):
        return f"{self.cantidad_usada} {self.producto.get_unidad_medida_display()} de {self.producto.nombre} en Turno #{self.turno.id}"
