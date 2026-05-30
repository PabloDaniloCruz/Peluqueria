from django.db.models.signals import post_save
from django.dispatch import receiver

from .models.ventas import Venta, ComisionDetalle


@receiver(post_save, sender=Venta)
def auto_crear_comisiones(sender, instance, created, **kwargs):
    """Crea ComisionDetalle automáticamente al crear una Venta con turno.

    Sirve como safety net para code paths que no sean facturar_turno
    (admin, API, etc.). La vista facturar_turno también crea las comisiones
    explícitamente.
    """
    if not created:
        return

    if instance.turno is None:
        return

    # Backfill cliente desde el turno si no se asignó (safety net para Fix 3)
    if instance.cliente is None and instance.turno.cliente is not None:
        Venta.objects.filter(pk=instance.pk).update(cliente=instance.turno.cliente)
        instance.cliente = instance.turno.cliente

    # Crear ComisionDetalle por cada DetalleTurno
    for dt in instance.turno.detalleturno_set.select_related('profesional').all():
        monto = dt.precio_real * dt.profesional.porcentaje_comision / 100
        ComisionDetalle.objects.create(
            venta=instance,
            detalle_turno=dt,
            profesional=dt.profesional,
            monto=monto,
        )
