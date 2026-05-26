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
    @property
    def duracion_estimada(self):
        """Calcula la duración sumando los tiempos de todas las etapas."""
        return sum(etapa.duracion for etapa in self.etapas.all())
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


class EtapaServicio(models.Model):
    """Fases de un servicio para evaluación asimétrica en el algoritmo RCPSP."""
    
    TIPO_ESTACION_CHOICES = [
        ('estacion', 'Estación de Trabajo (Silla)'),
        ('lavacabeza', 'Lavacabezas'),
        ('ninguna', 'Ninguna / Sala de Espera'),
    ]

    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='etapas', verbose_name="Servicio")
    orden = models.PositiveIntegerField("orden de ejecución", help_text="Ej: 1 (Primero), 2 (Segundo)")
    nombre = models.CharField("nombre de la etapa", max_length=100, help_text="Ej: Aplicación, Exposición, Lavado")
    
    duracion = models.PositiveIntegerField(
        "duración (minutos)", 
        help_text="Debe ser múltiplo de 5 para encajar en el motor de slots."
    )
    
    tipo_estacion = models.CharField("estación requerida", max_length=20, choices=TIPO_ESTACION_CHOICES)
    requiere_profesional = models.BooleanField(
        "¿Requiere al profesional?", 
        default=True,
        help_text="Desmarcar si es un tiempo de espera (ej: esperando que actúe la tintura) donde el profesional se libera."
    )

    class Meta:
        verbose_name = "Etapa de Servicio"
        verbose_name_plural = "Etapas de Servicio"
        ordering = ['orden']
        unique_together = ['servicio', 'orden']

    def __str__(self):
        return f"{self.servicio.nombre} - Paso {self.orden}: {self.nombre}"


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
    dia_semana = models.IntegerField("día de la semana", choices=DIA_CHOICES)
    hora_apertura = models.TimeField("hora de apertura")
    hora_cierre = models.TimeField("hora de cierre")
    abierto = models.BooleanField("abierto", default=True)

    class Meta:
        verbose_name = "Horario de Atención"
        verbose_name_plural = "Horarios de Atención"
        ordering = ["dia_semana", "hora_apertura"]

    def __str__(self):
        estado = "Abierto" if self.abierto else "Cerrado"
        return f"{self.get_dia_semana_display()} — {estado} ({self.hora_apertura} a {self.hora_cierre})"


class CierreExcepcional(models.Model):
    """Días o rangos de horas donde el local estará cerrado (feriados, vacaciones, etc)."""
    fecha = models.DateField("fecha")
    descripcion = models.CharField("motivo/descripción", max_length=200, blank=True)
    es_dia_completo = models.BooleanField("todo el día", default=True)
    hora_inicio = models.TimeField("hora inicio", null=True, blank=True)
    hora_fin = models.TimeField("hora fin", null=True, blank=True)

    class Meta:
        verbose_name = "Cierre Excepcional"
        verbose_name_plural = "Cierres Excepcionales"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} — {self.descripcion or 'Cerrado'}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.apps import apps
        import datetime

        # Evitamos import circular usando apps.get_model
        Turno = apps.get_model('gestion', 'Turno')
        
        # Base de búsqueda: turnos pendientes en esa fecha
        qs = Turno.objects.filter(
            fecha_hora__date=self.fecha,
            estado='pendiente'
        )
        
        # Si no es día completo, refinamos por el rango de horas
        if not self.es_dia_completo and self.hora_inicio and self.hora_fin:
            dt_inicio = datetime.datetime.combine(self.fecha, self.hora_inicio)
            dt_fin = datetime.datetime.combine(self.fecha, self.hora_fin)
            
            # Solapamiento: turno.inicio < cierre.fin AND turno.fin > cierre.inicio
            qs = qs.filter(
                fecha_hora__lt=dt_fin,
                hora_fin_estimada__gt=dt_inicio
            )
        
        count = qs.count()
        if count > 0:
            raise ValidationError(
                f"¡Conflicto detectado! Hay {count} turnos pendientes en este horario. "
                "Para confirmar este cierre, usá la opción 'Forzar Cierre' desde el panel de configuración."
            )


