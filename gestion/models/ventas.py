from django.db import models
from django.core.validators import MinValueValidator

from .turnos import Turno


class Venta(models.Model):
    """
    Facturación final del turno (relación 1:1).
    Almacena el total facturado, método de pago y la comisión YA CALCULADA
    para el profesional (evita recalcular en consultas posteriores).
    """

    METODO_PAGO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("tarjeta_debito", "Tarjeta de Débito"),
        ("tarjeta_credito", "Tarjeta de Crédito"),
        ("transferencia", "Transferencia Bancaria"),
        ("mercadopago", "Mercado Pago"),
    ]

    turno = models.OneToOneField(
        Turno, on_delete=models.CASCADE,
        related_name="venta",
        verbose_name="turno",
        null=True, blank=True
    )
    cliente = models.ForeignKey(
        "Cliente", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ventas",
        verbose_name="cliente (si es venta libre)"
    )
    total = models.DecimalField(
        "total", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    metodo_pago = models.CharField(
        "método de pago", max_length=20, choices=METODO_PAGO_CHOICES
    )
    comision = models.DecimalField(
        "comisión", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Comisión ya calculada: total × (profesional.porcentaje_comision / 100)"
    )
    fecha_venta = models.DateTimeField("fecha de venta", auto_now_add=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha_venta"]

    def __str__(self):
        return f"Venta #{self.id} — ${self.total} ({self.get_metodo_pago_display()})"


class DetalleVentaProducto(models.Model):
    """Registro de productos vendidos en una Venta."""
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles_productos")
    producto = models.ForeignKey("Producto", on_delete=models.RESTRICT, related_name="ventas")
    cantidad = models.PositiveIntegerField("cantidad", default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField("precio unitario", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de Venta de Producto"
        verbose_name_plural = "Detalles de Venta de Productos"

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
