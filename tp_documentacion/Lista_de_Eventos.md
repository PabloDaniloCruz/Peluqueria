# Lista de Eventos — Studio Salta

Este documento presenta la **Lista de Eventos (LE)** del sistema de información de Studio Salta, organizada por diálogos con cada Entidad Externa (EE). Cada evento se redacta como una oración donde el **sujeto** es la EE que genera el estímulo, el **verbo** expresa la acción y el **predicado** explicita el flujo de datos que impacta sobre el sistema.

Se incluye el **Diccionario de Datos (DD)** de los flujos de datos mencionados en la LE, de modo que pueda balancearse directamente contra el Diagrama de Contextos (DC).

---

## Entidades Externas Identificadas

| Código | Entidad Externa | Descripción |
|--------|----------------|-------------|
| **EE1** | Cliente (Público) | Persona que accede al portal público sin autenticación para reservar, consultar o gestionar sus turnos vía Magic Link. |
| **EE2** | Recepcionista (Staff) | Personal del salón con acceso autenticado al dashboard, gestión de turnos, clientes, ventas y facturación. |
| **EE3** | Administrador | Superusuario con acceso total: ABM de profesionales, servicios, estaciones, productos, configuración y reportes. |
| **EE4** | Reloj del Sistema | Entidad temporal que desencadena procesos automáticos por cumplimiento de condición horaria. |

---

## Lista de Eventos

### Diálogo 1: Cliente (Público) → Sistema

| N° | Evento | Flujo de Datos de Entrada | Flujo de Datos de Salida |
|----|--------|--------------------------|--------------------------|
| 1.1 | El **Cliente** solicita reservar turno/s ingresando sus datos y seleccionando servicios | `datos_reserva_publica` | `opciones_disponibilidad` |
| 1.2 | El **Cliente** selecciona profesionales para cada servicio solicitado | `seleccion_profesionales` | `opciones_disponibilidad` |
| 1.3 | El **Cliente** confirma la reserva eligiendo un horario disponible | `confirmacion_reserva_publica` | `comprobante_reserva` |
| 1.4 | El **Cliente** consulta el estado de su reserva a través del Magic Link | `token_reserva` | `detalle_reserva_publica` |
| 1.5 | El **Cliente** cancela uno o más turnos de su reserva desde el portal de autogestión | `cancelacion_publica` | `confirmacion_cancelacion` |
| 1.6 | El **Cliente** solicita reprogramar un turno desde el portal de autogestión | `solicitud_reprogramacion_publica` | `wizard_reprogramacion` |

---

### Diálogo 2: Recepcionista (Staff) → Sistema

| N° | Evento | Flujo de Datos de Entrada | Flujo de Datos de Salida |
|----|--------|--------------------------|--------------------------|
| 2.1 | La **Recepcionista** registra un nuevo cliente | `datos_cliente` | `confirmacion_alta_cliente` |
| 2.2 | La **Recepcionista** modifica los datos de un cliente existente | `datos_cliente_modificados` | `confirmacion_modificacion_cliente` |
| 2.3 | La **Recepcionista** deshabilita un cliente | `id_cliente` | `confirmacion_baja_cliente` |
| 2.4 | La **Recepcionista** reactiva un cliente previamente dado de baja | `id_cliente` | `confirmacion_reactivacion_cliente` |
| 2.5 | La **Recepcionista** agenda un turno interno (presencial o telefónico) | `datos_reserva_interna` | `opciones_disponibilidad` |
| 2.6 | La **Recepcionista** confirma la asignación del turno interno eligiendo un horario | `confirmacion_reserva_interna` | `comprobante_reserva` |
| 2.7 | La **Recepcionista** inicia un turno al llegar el cliente | `id_turno` | `confirmacion_inicio_turno` |
| 2.8 | La **Recepcionista** cancela un turno desde el dashboard | `cancelacion_turno_interna` | `confirmacion_cancelacion` |
| 2.9 | La **Recepcionista** factura un turno completado (checkout) | `datos_facturacion` | `comprobante_venta` |
| 2.10 | La **Recepcionista** registra una venta libre de mostrador (sin turno) | `datos_venta_libre` | `comprobante_venta` |
| 2.11 | La **Recepcionista** registra una ficha técnica de coloración para un cliente | `datos_ficha_tecnica` | `confirmacion_ficha` |
| 2.12 | La **Recepcionista** consulta el perfil integral de un cliente | `criterio_busqueda_cliente` | `perfil_cliente` |
| 2.13 | La **Recepcionista** consulta el dashboard de turnos del día o la semana | `filtros_dashboard` | `vista_dashboard` |

---

### Diálogo 3: Administrador → Sistema

| N° | Evento | Flujo de Datos de Entrada | Flujo de Datos de Salida |
|----|--------|--------------------------|--------------------------|
| 3.1 | El **Administrador** registra un nuevo profesional | `datos_profesional` | `confirmacion_alta_profesional` |
| 3.2 | El **Administrador** modifica los datos de un profesional (incluye habilidades y comisión) | `datos_profesional_modificados` | `confirmacion_modificacion_profesional` |
| 3.3 | El **Administrador** deshabilita un profesional | `id_profesional` | `confirmacion_baja_profesional` |
| 3.4 | El **Administrador** reactiva un profesional | `id_profesional` | `confirmacion_reactivacion_profesional` |
| 3.5 | El **Administrador** registra un nuevo servicio con sus etapas | `datos_servicio` | `confirmacion_alta_servicio` |
| 3.6 | El **Administrador** modifica un servicio existente y sus etapas | `datos_servicio_modificados` | `confirmacion_modificacion_servicio` |
| 3.7 | El **Administrador** deshabilita un servicio | `id_servicio` | `confirmacion_baja_servicio` |
| 3.8 | El **Administrador** reactiva un servicio | `id_servicio` | `confirmacion_reactivacion_servicio` |
| 3.9 | El **Administrador** reordena los servicios del catálogo | `orden_servicios` | `confirmacion_reorden` |
| 3.10 | El **Administrador** registra una nueva estación física | `datos_estacion` | `confirmacion_alta_estacion` |
| 3.11 | El **Administrador** modifica una estación existente | `datos_estacion_modificados` | `confirmacion_modificacion_estacion` |
| 3.12 | El **Administrador** deshabilita una estación | `id_estacion` | `confirmacion_baja_estacion` |
| 3.13 | El **Administrador** reactiva una estación | `id_estacion` | `confirmacion_reactivacion_estacion` |
| 3.14 | El **Administrador** registra un nuevo producto/insumo en el inventario | `datos_producto` | `confirmacion_alta_producto` |
| 3.15 | El **Administrador** modifica un producto/insumo existente | `datos_producto_modificados` | `confirmacion_modificacion_producto` |
| 3.16 | El **Administrador** deshabilita un producto/insumo | `id_producto` | `confirmacion_baja_producto` |
| 3.17 | El **Administrador** reactiva un producto/insumo | `id_producto` | `confirmacion_reactivacion_producto` |
| 3.18 | El **Administrador** ajusta el stock de un producto manualmente | `ajuste_stock` | `confirmacion_ajuste_stock` |
| 3.19 | El **Administrador** aplica un ajuste masivo de precios a los productos | `ajuste_masivo_precios` | `confirmacion_ajuste_precios` |
| 3.20 | El **Administrador** configura los horarios de atención del salón | `datos_horario` | `confirmacion_horario` |
| 3.21 | El **Administrador** registra un cierre excepcional (feriado/vacaciones) | `datos_cierre` | `confirmacion_cierre` |
| 3.22 | El **Administrador** fuerza un cierre con turnos afectados | `forzar_cierre` | `listado_turnos_afectados` |
| 3.23 | El **Administrador** consulta los reportes de facturación | `filtros_reporte` | `reporte_facturacion` |

---

### Diálogo 4: Reloj del Sistema → Sistema

| N° | Evento | Estímulo | Flujo de Datos de Salida |
|----|--------|----------|--------------------------|
| 4.1 | El **Reloj del Sistema** detecta que la hora actual superó la hora de inicio de turnos pendientes | `hora_actual` | `notificacion_auto_inicio` |

---

## Diccionario de Datos de la Lista de Eventos

### Flujos de Entrada

---

#### `datos_reserva_publica`

Información ingresada por el cliente público al iniciar el wizard de reserva (Paso 1).

```
datos_reserva_publica = nombre_cliente + apellido_cliente + telefono_cliente
                        + email_cliente + {id_servicio_seleccionado}
                        + [observaciones] + [horario_preferido]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre_cliente` | Alfanumérico (100) | Sí | Nombre del cliente |
| `apellido_cliente` | Alfanumérico (100) | Sí | Apellido del cliente |
| `telefono_cliente` | Alfanumérico (20) | No | Teléfono de contacto |
| `email_cliente` | Email | No | Correo electrónico |
| `id_servicio_seleccionado` | Entero {1,N} | Sí | ID de cada servicio seleccionado (mínimo 1) |
| `observaciones` | Texto libre | No | Observaciones o indicaciones adicionales |
| `horario_preferido` | Hora (HH:MM) | No | Horario preferido para la búsqueda radial |

---

#### `seleccion_profesionales`

Preferencias de profesional para cada servicio seleccionado (Paso 2 del wizard).

```
seleccion_profesionales = {id_servicio + id_profesional_elegido}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_servicio` | Entero | Sí | ID del servicio |
| `id_profesional_elegido` | Entero \| NULL | Sí | ID del profesional elegido. NULL = "Cualquier profesional" |

---

#### `confirmacion_reserva_publica`

Datos enviados al confirmar la reserva pública (Paso 3 del wizard).

```
confirmacion_reserva_publica = id_opcion_horaria_elegida
                               + nombre_cliente + apellido_cliente
                               + telefono_cliente + [email_cliente]
                               + [observaciones]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_opcion_horaria_elegida` | Entero | Sí | Identificador de la opción de horario seleccionada de las alternativas calculadas |
| `nombre_cliente` | Alfanumérico (100) | Sí | Nombre del cliente (puede ser nuevo o existente) |
| `apellido_cliente` | Alfanumérico (100) | Sí | Apellido del cliente |
| `telefono_cliente` | Alfanumérico (20) | No | Teléfono de contacto |
| `email_cliente` | Email | No | Correo electrónico |
| `observaciones` | Texto libre | No | Observaciones generales de la reserva |

---

#### `token_reserva`

Token UUID para acceder al portal de autogestión.

```
token_reserva = uuid_token
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `uuid_token` | UUID v4 | Sí | Token único de la reserva (generado automáticamente al crear la reserva) |

---

#### `cancelacion_publica`

Datos de la cancelación de un turno desde el portal de autogestión.

```
cancelacion_publica = uuid_token + [motivo_cancelacion]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `uuid_token` | UUID v4 | Sí | Token de la reserva |
| `motivo_cancelacion` | Texto libre | No | Motivo de cancelación indicado por el cliente |

---

#### `solicitud_reprogramacion_publica`

Datos para iniciar una reprogramación desde autogestión.

```
solicitud_reprogramacion_publica = uuid_token + id_turno_a_reprogramar
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `uuid_token` | UUID v4 | Sí | Token de la reserva original |
| `id_turno_a_reprogramar` | Entero | Sí | ID del turno que se desea reprogramar |

---

#### `datos_cliente`

Información para dar de alta un cliente nuevo.

```
datos_cliente = nombre + apellido + [telefono] + [email]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre` | Alfanumérico (100) | Sí | Nombre del cliente |
| `apellido` | Alfanumérico (100) | Sí | Apellido del cliente |
| `telefono` | Alfanumérico (20) | No | Teléfono de contacto |
| `email` | Email | No | Correo electrónico |

---

#### `datos_cliente_modificados`

Datos actualizados de un cliente existente.

```
datos_cliente_modificados = id_cliente + [nombre] + [apellido] + [telefono] + [email]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_cliente` | Entero | Sí | Identificador del cliente a modificar |
| `nombre` | Alfanumérico (100) | No | Nombre actualizado |
| `apellido` | Alfanumérico (100) | No | Apellido actualizado |
| `telefono` | Alfanumérico (20) | No | Teléfono actualizado |
| `email` | Email | No | Email actualizado |

---

#### `datos_reserva_interna`

Información ingresada por la recepcionista para agendar un turno interno.

```
datos_reserva_interna = id_cliente + {id_servicio_seleccionado}
                        + {id_profesional_elegido} + fecha_deseada
                        + [horario_preferido] + [observaciones]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_cliente` | Entero | Sí | Cliente seleccionado (por búsqueda) |
| `id_servicio_seleccionado` | Entero {1,N} | Sí | Servicios elegidos |
| `id_profesional_elegido` | Entero \| NULL {1,N} | Sí | Profesional por servicio (NULL = cualquiera) |
| `fecha_deseada` | Fecha (AAAA-MM-DD) | Sí | Fecha del turno |
| `horario_preferido` | Hora (HH:MM) | No | Horario preferido |
| `observaciones` | Texto libre | No | Observaciones del turno |

---

#### `confirmacion_reserva_interna`

Confirmación de la opción de horario elegida por la recepcionista.

```
confirmacion_reserva_interna = id_opcion_horaria_elegida + id_cliente + [observaciones]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_opcion_horaria_elegida` | Entero | Sí | Opción de disponibilidad elegida |
| `id_cliente` | Entero | Sí | Cliente asociado |
| `observaciones` | Texto libre | No | Observaciones adicionales |

---

#### `cancelacion_turno_interna`

Datos para la cancelación de un turno desde el dashboard.

```
cancelacion_turno_interna = id_turno + notificar_whatsapp
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_turno` | Entero | Sí | Turno a cancelar |
| `notificar_whatsapp` | Booleano | Sí | Si se debe generar enlace de WhatsApp para notificar al cliente |

---

#### `datos_facturacion`

Datos del checkout al facturar un turno.

```
datos_facturacion = id_turno + monto_total + metodo_pago
                    + [{id_producto_vendido + cantidad + precio_unitario}]
                    + [{id_insumo_consumido + cantidad_usada}]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_turno` | Entero | Sí | Turno a facturar |
| `monto_total` | Decimal (10,2) | Sí | Monto total facturado (puede diferir del sugerido) |
| `metodo_pago` | Enumerado | Sí | `efectivo` \| `tarjeta_debito` \| `tarjeta_credito` \| `transferencia` \| `mercadopago` |
| `id_producto_vendido` | Entero {0,N} | No | Producto retail vendido durante el checkout |
| `cantidad` | Entero ≥ 1 | Cond. | Cantidad del producto vendido (obligatorio si hay producto) |
| `precio_unitario` | Decimal (10,2) | Cond. | Precio unitario del producto |
| `id_insumo_consumido` | Entero {0,N} | No | Insumo profesional consumido durante el servicio |
| `cantidad_usada` | Decimal (10,2) | Cond. | Cantidad de insumo consumida (obligatorio si hay insumo) |

---

#### `datos_venta_libre`

Datos para registrar una venta de mostrador sin turno asociado.

```
datos_venta_libre = [id_cliente] + monto_total + metodo_pago
                    + {id_producto + cantidad + precio_unitario}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_cliente` | Entero | No | Cliente (opcional para venta de mostrador) |
| `monto_total` | Decimal (10,2) | Sí | Total de la venta |
| `metodo_pago` | Enumerado | Sí | Método de pago seleccionado |
| `id_producto` | Entero {1,N} | Sí | Producto vendido (mínimo 1) |
| `cantidad` | Entero ≥ 1 | Sí | Unidades vendidas |
| `precio_unitario` | Decimal (10,2) | Sí | Precio unitario del producto |

---

#### `datos_ficha_tecnica`

Información de la ficha técnica de coloración.

```
datos_ficha_tecnica = id_cliente + [id_turno] + [descripcion]
                      + [formula_quimica] + [observaciones]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_cliente` | Entero | Sí | Cliente al que pertenece la ficha |
| `id_turno` | Entero | No | Turno donde se aplicó el tratamiento |
| `descripcion` | Texto libre | No | Descripción del tratamiento |
| `formula_quimica` | Texto libre | No | Proporciones, marcas, colores, tiempos de acción |
| `observaciones` | Texto libre | No | Observaciones adicionales |

---

#### `criterio_busqueda_cliente`

Criterio de búsqueda para localizar un cliente.

```
criterio_busqueda_cliente = texto_busqueda
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `texto_busqueda` | Alfanumérico | Sí | Búsqueda por nombre, apellido, teléfono o email (mínimo 2 caracteres) |

---

#### `filtros_dashboard`

Criterios de filtrado para la vista del dashboard.

```
filtros_dashboard = [modo_vista] + [estado] + [id_profesional]
                    + [id_servicio] + [id_estacion] + [nro_reserva]
                    + [texto_busqueda] + [sin_facturar] + [fecha]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `modo_vista` | Enumerado | No | `diaria` \| `semanal` (default: diaria) |
| `estado` | Enumerado | No | `pendiente` \| `en_curso` \| `completado` \| `cancelado` \| `por_reprogramar` |
| `id_profesional` | Entero | No | Filtrar por profesional |
| `id_servicio` | Entero | No | Filtrar por servicio |
| `id_estacion` | Entero | No | Filtrar por estación |
| `nro_reserva` | Entero | No | Filtrar por número de reserva |
| `texto_busqueda` | Alfanumérico | No | Nombre, apellido o teléfono del cliente |
| `sin_facturar` | Booleano | No | Mostrar solo turnos activos sin facturar |
| `fecha` | Fecha | No | Fecha de referencia (default: hoy) |

---

#### `datos_profesional`

Información para dar de alta un profesional.

```
datos_profesional = nombre + apellido + [telefono] + [email]
                    + [porcentaje_comision] + {id_servicio_habilidad}
                    + [crear_usuario + username + password]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre` | Alfanumérico (100) | Sí | Nombre del profesional |
| `apellido` | Alfanumérico (100) | Sí | Apellido del profesional |
| `telefono` | Alfanumérico (20) | No | Teléfono de contacto |
| `email` | Email | No | Correo electrónico |
| `porcentaje_comision` | Entero [0-100] | No | Porcentaje de comisión (default: 35%) |
| `id_servicio_habilidad` | Entero {0,N} | No | Servicios que el profesional puede realizar |
| `crear_usuario` | Booleano | No | Si se debe crear una cuenta de acceso al sistema |
| `username` | Alfanumérico | Cond. | Nombre de usuario (obligatorio si `crear_usuario = true`) |
| `password` | Alfanumérico | Cond. | Contraseña (obligatorio si `crear_usuario = true`) |

---

#### `datos_profesional_modificados`

Datos actualizados de un profesional existente.

```
datos_profesional_modificados = id_profesional + [nombre] + [apellido]
                                + [telefono] + [email] + [porcentaje_comision]
                                + {id_servicio_habilidad}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_profesional` | Entero | Sí | ID del profesional a modificar |
| _(demás campos)_ | — | No | Mismos campos que `datos_profesional` (los que se envíen se actualizan) |

---

#### `datos_servicio`

Información para dar de alta un servicio con sus etapas.

```
datos_servicio = nombre_servicio + [descripcion] + precio_sugerido
                 + {datos_etapa}
```

```
datos_etapa = orden + nombre_etapa + duracion_minutos
              + tipo_estacion + requiere_profesional
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre_servicio` | Alfanumérico (100) | Sí | Nombre único del servicio |
| `descripcion` | Texto libre | No | Descripción del servicio |
| `precio_sugerido` | Decimal (10,2) ≥ 0 | Sí | Precio sugerido de referencia |
| `orden` | Entero ≥ 1 | Sí | Orden de ejecución de la etapa |
| `nombre_etapa` | Alfanumérico (100) | Sí | Nombre de la etapa (ej: Aplicación, Exposición, Lavado) |
| `duracion_minutos` | Entero (múltiplo de 5) | Sí | Duración en minutos de la etapa |
| `tipo_estacion` | Enumerado | Sí | `estacion` \| `lavacabeza` \| `ninguna` |
| `requiere_profesional` | Booleano | Sí | Si el profesional debe estar presente durante la etapa |

---

#### `datos_servicio_modificados`

Datos actualizados de un servicio y sus etapas.

```
datos_servicio_modificados = id_servicio + [nombre_servicio] + [descripcion]
                             + [precio_sugerido] + {datos_etapa}
```

---

#### `orden_servicios`

Nuevo orden de visualización de los servicios del catálogo.

```
orden_servicios = {id_servicio + posicion}
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_servicio` | Entero | Sí | ID del servicio |
| `posicion` | Entero ≥ 0 | Sí | Nueva posición en el catálogo |

---

#### `datos_estacion`

Información para dar de alta una estación física.

```
datos_estacion = nombre_estacion + tipo_estacion
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre_estacion` | Alfanumérico (50) | Sí | Nombre único de la estación |
| `tipo_estacion` | Enumerado | Sí | `estacion` (Silla) \| `lavacabeza` (Lava-Cabezas) |

---

#### `datos_estacion_modificados`

Datos actualizados de una estación existente.

```
datos_estacion_modificados = id_estacion + [nombre_estacion] + [tipo_estacion]
```

---

#### `datos_producto`

Información para dar de alta un producto/insumo.

```
datos_producto = nombre_producto + [descripcion] + es_para_venta
                 + es_insumo + unidad_medida + [precio]
                 + stock_actual + stock_minimo
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `nombre_producto` | Alfanumérico (100) | Sí | Nombre único del producto |
| `descripcion` | Texto libre | No | Descripción del producto |
| `es_para_venta` | Booleano | Sí | Indica si es un producto de venta al público |
| `es_insumo` | Booleano | Sí | Indica si es un insumo de uso profesional |
| `unidad_medida` | Enumerado | Sí | `unidades` \| `gramos` \| `mililitros` |
| `precio` | Decimal (10,2) ≥ 0 | No | Precio de venta al público (si aplica) |
| `stock_actual` | Decimal (10,2) ≥ 0 | Sí | Cantidad actual en stock |
| `stock_minimo` | Decimal (10,2) ≥ 0 | Sí | Umbral de alerta de stock bajo |

---

#### `datos_producto_modificados`

Datos actualizados de un producto/insumo existente.

```
datos_producto_modificados = id_producto + [nombre_producto] + [descripcion]
                             + [es_para_venta] + [es_insumo] + [unidad_medida]
                             + [precio] + [stock_actual] + [stock_minimo]
```

---

#### `ajuste_stock`

Ajuste rápido de stock de un producto.

```
ajuste_stock = id_producto + accion
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_producto` | Entero | Sí | Producto a ajustar |
| `accion` | Enumerado | Sí | `incrementar` \| `decrementar` |

---

#### `ajuste_masivo_precios`

Porcentaje de ajuste aplicado masivamente al catálogo de productos.

```
ajuste_masivo_precios = porcentaje_ajuste
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `porcentaje_ajuste` | Decimal | Sí | Porcentaje de ajuste (positivo = aumento, negativo = descuento) |

---

#### `datos_horario`

Configuración de horario de atención.

```
datos_horario = dia_semana + hora_apertura + hora_cierre + abierto
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `dia_semana` | Entero [0-6] | Sí | Día de la semana (0=Lunes, 6=Domingo) |
| `hora_apertura` | Hora (HH:MM) | Sí | Hora de apertura del turno |
| `hora_cierre` | Hora (HH:MM) | Sí | Hora de cierre del turno |
| `abierto` | Booleano | Sí | Si el salón atiende ese día/turno |

---

#### `datos_cierre`

Registro de un cierre excepcional.

```
datos_cierre = fecha_cierre + [descripcion] + es_dia_completo
               + [hora_inicio] + [hora_fin]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `fecha_cierre` | Fecha (AAAA-MM-DD) | Sí | Fecha del cierre |
| `descripcion` | Alfanumérico (200) | No | Motivo del cierre (ej: "Feriado Nacional") |
| `es_dia_completo` | Booleano | Sí | Si el cierre abarca todo el día |
| `hora_inicio` | Hora (HH:MM) | Cond. | Hora de inicio del cierre parcial (obligatorio si `es_dia_completo = false`) |
| `hora_fin` | Hora (HH:MM) | Cond. | Hora de fin del cierre parcial (obligatorio si `es_dia_completo = false`) |

---

#### `forzar_cierre`

Confirmación de cierre forzado con turnos conflictivos.

```
forzar_cierre = id_cierre_excepcional + confirmar_forzado
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `id_cierre_excepcional` | Entero | Sí | ID del cierre a forzar |
| `confirmar_forzado` | Booleano (true) | Sí | Confirmación explícita del forzado |

---

#### `filtros_reporte`

Criterios de filtrado para reportes de facturación.

```
filtros_reporte = [rango_temporal] + [fecha_desde] + [fecha_hasta]
                  + [id_profesional]
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `rango_temporal` | Enumerado | No | `hoy` \| `esta_semana` \| `este_mes` \| `este_anio` \| `personalizado` |
| `fecha_desde` | Fecha | Cond. | Inicio del rango (obligatorio si `rango_temporal = personalizado`) |
| `fecha_hasta` | Fecha | Cond. | Fin del rango (obligatorio si `rango_temporal = personalizado`) |
| `id_profesional` | Entero | No | Filtrar por profesional |

---

#### `id_turno`, `id_cliente`, `id_profesional`, `id_servicio`, `id_estacion`, `id_producto`

Identificadores simples para operaciones de deshabilitar, reactivar, iniciar o consultar.

```
id_<entidad> = identificador_numerico_unico
```

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|:-----------:|-------------|
| `identificador_numerico_unico` | Entero > 0 | Sí | Clave primaria de la entidad en el sistema |

---

### Flujos de Salida

---

#### `opciones_disponibilidad`

Resultado del motor de disponibilidad con las opciones de horario calculadas.

```
opciones_disponibilidad = {opcion_horaria} + [alternativas]
```

```
opcion_horaria = id_opcion + hora_inicio + hora_fin_estimada + score
                 + {servicio + profesional_asignado + estacion_asignada
                    + hora_inicio_servicio + hora_fin_servicio}
                 + es_mejor_opcion
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_opcion` | Entero | Identificador de la opción |
| `hora_inicio` | Hora (HH:MM) | Hora de inicio de la secuencia completa |
| `hora_fin_estimada` | Hora (HH:MM) | Hora de fin estimada de todos los servicios |
| `score` | Entero | Puntaje de calidad (mayor = mejor) |
| `servicio` | Texto | Nombre del servicio |
| `profesional_asignado` | Texto | Nombre del profesional asignado |
| `estacion_asignada` | Texto | Nombre de la estación asignada |
| `hora_inicio_servicio` | Hora | Hora de inicio del servicio individual |
| `hora_fin_servicio` | Hora | Hora de fin del servicio individual |
| `es_mejor_opcion` | Booleano | Indica si es la opción con mejor puntaje (⭐) |
| `alternativas` | Lista {0,8} | Opciones con otros profesionales (si se pidió uno específico) |

---

#### `comprobante_reserva`

Confirmación exitosa de una reserva con datos del Magic Link.

```
comprobante_reserva = nro_reserva + token_magic_link + fecha_creacion
                      + nombre_cliente + {detalle_turno_confirmado}
                      + enlace_whatsapp + enlace_autogestión
```

```
detalle_turno_confirmado = nro_turno + servicio + profesional
                           + fecha_hora + hora_fin_estimada + estacion
```

---

#### `detalle_reserva_publica`

Información de la reserva consultada por el cliente desde el portal de autogestión.

```
detalle_reserva_publica = nro_reserva + nombre_cliente + fecha_creacion
                          + {detalle_turno_publico} + [observaciones]
```

```
detalle_turno_publico = nro_turno + servicio + profesional + fecha_hora
                        + hora_fin_estimada + estado
```

---

#### `confirmacion_cancelacion`

Confirmación de cancelación de un turno.

```
confirmacion_cancelacion = nro_turno + estado_anterior + estado_nuevo
                           + [enlace_whatsapp_notificacion]
                           + [enlace_reprogramacion]
```

---

#### `comprobante_venta`

Comprobante generado al facturar un turno o registrar una venta libre.

```
comprobante_venta = nro_venta + fecha_venta + total_facturado
                    + metodo_pago + comision_profesional
                    + {detalle_servicio_facturado}
                    + [{detalle_producto_vendido}]
                    + [{detalle_insumo_consumido}]
                    + [enlace_whatsapp_comprobante]
```

---

#### `perfil_cliente`

Perfil integral del cliente con historial.

```
perfil_cliente = datos_personales + {historial_turnos} + {fichas_tecnicas}
                 + enlace_whatsapp_directo
```

```
datos_personales = nombre + apellido + telefono + email + fecha_registro + activo
```

---

#### `vista_dashboard`

Datos presentados en el dashboard de recepción.

```
vista_dashboard = modo_vista + fecha_referencia + contadores_estado
                  + {tarjeta_turno} + [alertas_stock]
```

```
contadores_estado = total_turnos + pendientes + en_curso + completados + cancelados
```

```
tarjeta_turno = nro_turno + cliente + profesional + servicios + estacion
                + hora_inicio + hora_fin + estado + [acciones_disponibles]
```

```
alertas_stock = {nombre_producto + stock_actual + stock_minimo + nivel_alerta}
```

---

#### `reporte_facturacion`

Datos del reporte de facturación con KPIs y gráficos.

```
reporte_facturacion = periodo_consultado + ingresos_totales + comisiones_totales
                      + ticket_promedio + cantidad_turnos_facturados
                      + grafico_tendencia_mensual + grafico_metodo_pago
                      + grafico_ranking_profesionales + grafico_ranking_servicios
```

---

#### `listado_turnos_afectados`

Lista de turnos en conflicto al forzar un cierre excepcional.

```
listado_turnos_afectados = cantidad_afectados
                           + {nro_turno + cliente + telefono + servicios
                              + hora_turno + enlace_whatsapp_reprogramacion}
```

---

#### `notificacion_auto_inicio`

Notificación generada por el auto-inicio de turnos atrasados.

```
notificacion_auto_inicio = cantidad_turnos_auto_iniciados
                           + {nro_turno + cliente + hora_original}
```

---

#### Flujos de confirmación simples

Los flujos con prefijo `confirmacion_` que no se detallan arriba siguen la estructura genérica:

```
confirmacion_<operacion> = resultado + [mensaje_exito | mensaje_error]
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `resultado` | Booleano | `true` si la operación fue exitosa |
| `mensaje_exito` | Texto | Mensaje descriptivo del éxito de la operación |
| `mensaje_error` | Texto | Mensaje descriptivo del error (si falló) |

---

## Resumen Cuantitativo

| Métrica | Cantidad |
|---------|----------|
| Entidades Externas | 4 |
| Total de Eventos | 36 |
| Eventos del Cliente (EE1) | 6 |
| Eventos de la Recepcionista (EE2) | 13 |
| Eventos del Administrador (EE3) | 23 |
| Eventos del Reloj del Sistema (EE4) | 1 |
| Flujos de Datos de Entrada (DD) | 30 |
| Flujos de Datos de Salida (DD) | 12 |

---

> **Nota**: Los nombres de los flujos de datos de esta Lista de Eventos están diseñados para coincidir con los que se utilicen en el Diagrama de Contextos (DC), facilitando el balanceo cruzado entre ambas herramientas.
