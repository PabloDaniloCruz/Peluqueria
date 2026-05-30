# Plan: Eliminar `Reserva` — Mover `profesional` y `estacion` a `DetalleTurno`

## Objetivo

Eliminar la tabla `Reserva` moviendo `profesional` y `estacion` a `DetalleTurno`.
Un solo `Turno` agrupa todos los servicios de una visita, y `DetalleTurno` registra
qué profesional y estación ejecutó cada servicio.

## Modelo final

```
Turno (una visita del cliente)
├── cliente
├── fecha_hora          ← inicio del primer servicio
├── hora_fin_estimada  ← fin del último servicio
├── estado
├── observaciones
├── token (UUID)       ← autogestión pública (reemplaza Reserva.token)
│
└── DetalleTurno (por servicio)
    ├── servicio
    ├── precio_real
    ├── profesional    ← NUEVO, requerido
    ├── estacion       ← NUEVO, requerido
    └── (opcional) hora_inicio, hora_fin  ← timing exacto dentro del Turno
```

---

## Fase 0 — Backward compatibility (opcional)

Antes de cambiar el modelo, crear properties en `Turno` para que el código actual
siga funcionando mientras se migra:

```python
class Turno(models.Model):
    @property
    def profesional(self):
        return self.detalleturno_set.first().profesional if self.detalleturno_set.exists() else None

    @property
    def estacion(self):
        return self.detalleturno_set.first().estacion if self.detalleturno_set.exists() else None
```

Esto permite que el resto del código no se rompa mientras se van actualizando
las referencias. **No implementar si se va a hacer el cambio completo de una sola vez.**

---

## Fase 1 — Modelo

### 1.1 Agregar campos a `DetalleTurno`

`gestion/models/turnos.py`:

```python
class DetalleTurno(models.Model):
    turno = models.ForeignKey("Turno", on_delete=models.CASCADE, ...)
    servicio = models.ForeignKey("Servicio", on_delete=models.CASCADE, ...)
    precio_real = models.DecimalField(...)

    # NUEVOS
    profesional = models.ForeignKey(
        "Profesional", on_delete=models.PROTECT,
        null=True,  # nullable solo para la migración
        verbose_name="profesional"
    )
    estacion = models.ForeignKey(
        "Estacion", on_delete=models.PROTECT,
        null=True,  # nullable solo para la migración
        verbose_name="estación"
    )
    # Timing exacto dentro del turno (opcional, útil para reportes)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
```

### 1.2 Agregar `token` a `Turno`

```python
import uuid

class Turno(models.Model):
    # ... campos existentes ...
    token = models.UUIDField(
        "token de autogestión", default=uuid.uuid4,
        unique=True, editable=False, null=True  # null=True solo para migración
    )
    # NOTA: profesional y estacion se MANTIENEN temporalmente,
    # se eliminan en Fase 6
```

### 1.3 Generar migración

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Fase 2 — Migración de datos

Crear una **migración de datos** (`python manage.py makemigrations gestion --empty`)
que:

### 2.1 Poblar `DetalleTurno.profesional` y `DetalleTurno.estacion`

```python
def poblar_detalle_turno(apps, schema_editor):
    DetalleTurno = apps.get_model('gestion', 'DetalleTurno')
    for dt in DetalleTurno.objects.select_related('turno').iterator():
        dt.profesional = dt.turno.profesional
        dt.estacion = dt.turno.estacion
        dt.save(update_fields=['profesional', 'estacion'])
```

### 2.2 Poblar `Turno.token`

```python
def poblar_tokens(apps, schema_editor):
    import uuid
    Turno = apps.get_model('gestion', 'Turno')
    for turno in Turno.objects.filter(token__isnull=True).iterator():
        turno.token = uuid.uuid4()
        turno.save(update_fields=['token'])
```

### 2.3 Migrar observaciones desde `Reserva` a `Turno`

Las observaciones globales de la reserva se pierden si no se copian.
Opcional: concatenar `Reserva.observaciones` a `Turno.observaciones` del primer
turno de cada reserva.

```python
def migrar_observaciones(apps, schema_editor):
    Turno = apps.get_model('gestion', 'Turno')
    for turno in Turno.objects.filter(reserva__isnull=False).select_related('reserva').iterator():
        if turno.reserva.observaciones and turno.orden == 0:
            obs = turno.observaciones or ''
            turno.observaciones = f"{obs}\n[Reserva: {turno.reserva.observaciones}]".strip()
            turno.save(update_fields=['observaciones'])
```

### 2.4 Hacer NOT NULL los campos nuevos (opcional, en migración separada)

Después de poblar, cambiar `null=True` por `null=False` en `DetalleTurno.profesional`
y `DetalleTurno.estacion`.

---

## Fase 3 — Algoritmo de disponibilidad

`gestion/api_disponibilidad.py` **no requiere cambios estructurales**.

El algoritmo ya devuelve un `bloque` por servicio con su propio `profesional_id`
y `estacion_id`. Estructuralmente los bloques representan DetalleTurno, no Turnos.

Solo renombrar conceptualmente: donde el comentario dice "un turno por servicio",
cambiar a "un DetalleTurno por servicio". El JSON de respuesta sigue siendo
exactamente el mismo.

---

## Fase 4 — Vistas (creación de turnos)

### 4.1 `reservar_turno_interno` y `confirmar_reserva_publica`

Actualmente crean N Turnos bajo 1 Reserva:

```python
reserva = Reserva.objects.create(cliente=cliente, observaciones=observaciones)
for bloque in opcion['bloques']:
    turno = Turno(cliente=cliente, ..., reserva=reserva)
    turno.save()
    DetalleTurno.objects.create(turno=turno, servicio=servicio, precio_real=...)
```

Nuevo: crear 1 Turno con N DetalleTurno:

```python
# Calcular rango total del turno
inicio = datetime.strptime(opcion['bloques'][0]['inicio'], '%H:%M').time()
fin = datetime.strptime(opcion['bloques'][-1]['fin'], '%H:%M').time()

fecha_hora = timezone.make_aware(datetime.combine(fecha, inicio))
hora_fin_estimada = timezone.make_aware(datetime.combine(fecha, fin))

turno = Turno(
    cliente=cliente,
    fecha_hora=fecha_hora,
    hora_fin_estimada=hora_fin_estimada,
    estado='pendiente',
    observaciones=observaciones,
)
turno.save()

for idx, bloque in enumerate(opcion['bloques']):
    servicio = Servicio.objects.get(id=bloque['servicio_id'])
    profesional = Profesional.objects.get(id=bloque['profesional_id'])
    estacion = Estacion.objects.get(id=bloque['estacion_id'])

    DetalleTurno.objects.create(
        turno=turno,
        servicio=servicio,
        profesional=profesional,
        estacion=estacion,
        precio_real=servicio.precio_sugerido,
        hora_inicio=datetime.strptime(bloque['inicio'], '%H:%M').time(),
        hora_fin=datetime.strptime(bloque['fin'], '%H:%M').time(),
    )
```

### 4.2 Simplificación de transacciones

Ya no se necesita `select_for_update()` sobre profesionales y estaciones
por separado (se valida en el algoritmo de disponibilidad, no en clean()).

Se puede simplificar:

```python
with transaction.atomic():
    # Solo bloquear el cliente
    cliente = Cliente.objects.select_for_update().get(id=cliente.id)

    # Control de saturación
    ...

    # Crear turno + detalles
    turno = Turno(...)
    turno.save()

    for bloque in opcion['bloques']:
        DetalleTurno.objects.create(...)
```

### 4.3 Búsqueda de disponibilidad

Actualizar la búsqueda para que use las tablas correctas.
No hay cambio estructural — los mismos parámetros de búsqueda.

### 4.4 `Turno.clean()` — simplificar validación

La validación de solapamiento (profesional, estación, cliente) era responsabilidad
de `clean()`. Con la nueva arquitectura, el algoritmo de disponibilidad es la
fuente de verdad. Simplificar clean() para solo validar horario de atención:

```python
def clean(self):
    super().clean()
    if not self.fecha_hora or not self.hora_fin_estimada:
        return

    # 1. Validación de Horario de Atención
    dia_semana = self.fecha_hora.weekday()
    horario = HorarioAtencion.objects.filter(dia_semana=dia_semana, abierto=True).first()
    if not horario:
        raise ValidationError("La peluquería está cerrada ese día.")

    hora_inicio = self.fecha_hora.time()
    hora_fin = self.hora_fin_estimada.time()
    if hora_inicio < horario.hora_apertura or hora_fin > horario.hora_cierre:
        raise ValidationError("El turno debe estar dentro del horario de atención.")
```

---

## Fase 5 — Portal público de autogestión

### 5.1 URLs

Cambiar rutas de `reserva.token` a `turno.token`:

```python
# urls.py — NUEVAS
path('turnos/publica/<uuid:token>/', views.gestion_turno_publico, name='gestion_turno_publico'),
path('turnos/publica/<uuid:token>/cancelar/', views.cancelar_turno_publico, name='cancelar_turno_publico'),
```

Eliminar:
```python
# urls.py — ELIMINAR
path('reservas/publica/confirmacion/<uuid:token>/', ...)
path('reservas/publica/gestion/<uuid:token>/', ...)
path('reservas/publica/gestion/<uuid:token>/cancelar/', ...)
```

### 5.2 Vistas de autogestión

Renombrar y adaptar:

| Vista actual | Nueva vista |
|---|---|
| `confirmacion_reserva_publica(request, token)` | → `confirmacion_turno_publico(request, turno_id)` (redirige al dashboard o muestra detalle) |
| `gestion_reserva_publica(request, token)` | → `gestion_turno_publico(request, token)` — busca por `Turno.token` |
| `cancelar_reserva_publica(request, token)` | → `cancelar_turno_publico(request, token)` — busca por `Turno.token` |

Ya no se necesita el `orden` ni agrupar turnos, porque un Turno = una visita.

### 5.3 Templates

Adaptar las referencias a `reserva.token` → `turno.token`:

- `gestion_publica.html`
- `cancelar_publica.html`
- `confirmacion_publica.html`
- `_modal_cancelacion.html`
- `_turno_card_semanal.html`
- `_turno_card_diaria.html` — eliminar "Bloque X de la reserva"
- `dashboard.html` — eliminar filtro por reserva, badge de reserva

### 5.4 WhatsApp redirect

`gestion/views/turnos.py` — `cancelar_turno`:

```python
# Antes
if turno.reserva:
    url_gestion = reverse('gestion_reserva_publica', args=[turno.reserva.token])

# Después
url_gestion = reverse('gestion_turno_publico', args=[turno.token])
```

---

## Fase 6 — Billing / Facturación

`gestion/views/turnos.py` — `facturar_turno`:

### 6.1 Comisión multi-profesional

Actualmente:
```python
porcentaje = turno.profesional.porcentaje_comision
comision_calculada = (total_real * porcentaje) / 100
```

Con múltiples profesionales, hay dos opciones:

**Opción A (recomendada):** Venta con comisiones por DetalleTurno.

Crear modelo `ComisionDetalle` o directamente calcular por DetalleTurno:

```python
comision_total = 0
for dt in turno.detalleturno_set.all():
    porcentaje = dt.profesional.porcentaje_comision
    comision_total += (dt.precio_real * porcentaje) / 100
```

**Opción B (simplificada):** Usar el profesional del primer DetalleTurno.
Solo si en la práctica todos los servicios tienen el mismo profesional.

### 6.2 `Turno.total_servicios` property

Sigue siendo la misma: `sum(d.precio_real for d in self.detalleturno_set.all())`.
No requiere cambios.

---

## Fase 7 — Dashboard

### 7.1 Filtro de profesional y estación

Actualmente filtran directo en `Turno`:

```python
qs.filter(profesional_id=profesional_filtro)
qs.filter(estacion_id=estacion_filtro)
```

Con profesional/estacion en `DetalleTurno`, cambiar a:

```python
if profesional_filtro:
    qs = qs.filter(detalleturno__profesional_id=profesional_filtro).distinct()
if estacion_filtro:
    qs = qs.filter(detalleturno__estacion_id=estacion_filtro).distinct()
```

### 7.2 Filtro por reserva

Eliminar:
```python
# reserva_filtro — ya no existe
qs.filter(reserva_id=reserva_filtro)
```

### 7.3 Select_related

Actualmente:
```python
.select_related('cliente', 'profesional', 'estacion', 'reserva')
```

Cambiar a:
```python
.select_related('cliente')
.prefetch_related('detalleturno_set__profesional', 'detalleturno_set__estacion')
```

---

## Fase 8 — Limpieza de modelo

Después de verificar que todo funciona:

### 8.1 Eliminar campos obsoletos de `Turno`

```python
class Turno(models.Model):
    # ELIMINAR
    # profesional = models.ForeignKey(...)
    # estacion = models.ForeignKey(...)
    # reserva = models.ForeignKey(...)
    # orden = models.PositiveSmallIntegerField(...)
```

### 8.2 Eliminar modelo `Reserva`

```python
# class Reserva(models.Model):  # ELIMINAR
```

### 8.3 Migración final

```bash
python manage.py makemigrations
python manage.py migrate
```

### 8.4 Archivos a eliminar

- Migración `0008_reserva_compuesta.py` (o mantener por historial, pero no afecta)
- `ReservaAlPasoForm` en `forms.py` si ya no se usa

---

## Fase 9 — Tests

Actualizar `gestion/tests/test_public_reserva.py`:

| Test | Cambio |
|---|---|
| `test_confirmar_reserva_publica_success` | Ya no verifica 2 turnos bajo 1 reserva. Verifica 1 Turno con 2 DetalleTurno. |
| `test_confirmar_reserva_publica_with_observaciones` | Verifica `turno.observaciones` (ya no `reserva.observaciones`) |
| `test_gestion_y_cancelacion_publica_success` | Usa `Turno.token` en lugar de `Reserva.token` |
| `test_api_disponibilidad_publica_success` | Sin cambios (la API no cambia) |
| `test_api_disponibilidad_publica_saturation` | Sin cambios (sigue contando Turnos) |

Agregar test nuevo:
```python
def test_turno_con_multiples_servicios_distintos_profesionales(self):
    """Valida que 2 servicios con distintos profesionales se agrupen en 1 Turno."""
```

---

## Resumen de pasos

| Paso | Archivos | ¿Riesgo? |
|---|---|---|
| **F1** Agregar campos modelo | `models/turnos.py` | Bajo |
| **F2** Migración de datos | migración + datos | Medio (data loss si falla) |
| **F3** Algoritmo | `api_disponibilidad.py` | Ninguno (solo docs) |
| **F4** Vistas crear turno | `views/reservas.py` | Medio (lógica de creación) |
| **F5** Portal público | `views/reservas.py`, `urls.py`, templates | Alto (cambio de rutas) |
| **F6** Facturación | `views/turnos.py`, `models/ventas.py` | Medio (comisiones) |
| **F7** Dashboard | `views/dashboard.py`, templates | Medio (filtros) |
| **F8** Limpieza | `models/turnos.py` | Bajo (post-verificación) |
| **F9** Tests | `tests/test_public_reserva.py` | Bajo |

**Orden recomendado:** F1 → F2 → F4 → F5 → F7 → F6 → F3 (doc) → F8 → F9

**Rollback:** mantener `Reserva` y campos viejos hasta F8. Si algo falla,
se puede revertir a F5 sin perder datos.

---

## Notas sobre el modelo `Venta`

Si se implementa F6 Opción A (comisiones por DetalleTurno), `Venta` actual:

```python
class Venta(models.Model):
    turno = models.ForeignKey(Turno, ...)
    total = models.DecimalField(...)
    comision = models.DecimalField(...)  # comisión única
```

Podría necesitar:
- `ComisionDetalle(models.Model): venta, detalle_turno, profesional, monto`
- O cambiar `Venta.comision` a `DecimalField` que sume todas las comisiones

Esto queda **fuera del scope** de este plan si se opta por F6 Opción B
(primer profesional como principal para comisión). Decidir en el momento
de implementar F6 según el caso de uso real.
