# 💇‍♂️ Studio Salta — Sistema de Gestión Integral para Peluquerías

Plataforma profesional para la gestión de turnos, inventario y administración de salones de belleza.
Diseñado para optimizar la ocupación del salón mediante un motor de agenda continua basado en **bitmasks** con búsqueda radial de disponibilidad, autogestión del cliente vía Magic Links, y notificación directa por WhatsApp.

**Producción**: [https://danilo2004.pythonanywhere.com](https://danilo2004.pythonanywhere.com)

---

## 🚀 Inicio Rápido (Desarrollo Local)

```bash
# 1. Clonar el repositorio
git clone https://github.com/PabloDaniloCruz/Peluqueria.git
cd Peluqueria

# 2. Crear y activar entorno virtual
python -m venv env
env\Scripts\activate        # Windows
# source env/bin/activate   # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar base de datos
python manage.py migrate

# 5. Crear usuario administrador
python manage.py createsuperuser

# 6. Ejecutar servidor de desarrollo
python manage.py runserver
```

La aplicación queda disponible en `http://127.0.0.1:8000/`.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3.10+ · Django 5.2 |
| **Frontend** | Vanilla JavaScript (ES6+) · Bootstrap 5.3 · Bootstrap Icons 1.11 · Chart.js (reportes) |
| **Base de Datos** | SQLite (desarrollo) · PostgreSQL compatible (producción) |
| **Optimización** | `django-compressor` para minificación y compresión de CSS/JS estáticos |
| **Zona Horaria** | `America/Argentina/Buenos_Aires` con `USE_TZ = True` |
| **Deploy** | PythonAnywhere (cuenta gratuita) |

### Dependencias

```
Django==5.2.1
django_compressor==4.5.1
django-appconf==1.0.6
asgiref==3.8.1
sqlparse==0.5.3
rcssmin==1.1.2
rjsmin==1.2.2
tzdata==2025.1
```

---

## ✨ Características Principales

### 📅 Sistema de Reservas Multi-Servicio

El corazón de la aplicación es un **wizard de reserva de 3 pasos** compartido entre el flujo público (clientes) y el flujo interno (recepción):

| Paso | Descripción |
|------|-------------|
| **1. Datos y Servicios** | El cliente completa sus datos de contacto y selecciona uno o más servicios del catálogo. Se muestra precio y duración estimada en tiempo real. |
| **2. Profesionales** | Para cada servicio, se puede elegir un profesional específico o dejarlo en "Cualquier profesional" para maximizar opciones de horario. |
| **3. Horarios Disponibles** | El motor de disponibilidad calcula las secuencias contiguas válidas y las presenta ordenadas por proximidad al horario preferido. La mejor opción se destaca con ⭐. |

#### Motor de Disponibilidad (`api_disponibilidad.py`)

El algoritmo de disponibilidad implementa una **arquitectura basada en bitmasks** donde cada bit representa un slot de 5 minutos. Las verificaciones de colisión son operaciones O(1) por comparación bitwise:

- **Algoritmo RCPSP con Evaluación Asimétrica**: Los servicios se dividen en etapas. Cada etapa define su propia duración, tipo de estación requerida, y si retiene o no al profesional (permitiendo intercalar clientes en tiempos muertos, ej: exposición de tintura).
- **Bitmasks de ocupación**: Se construyen bitmasks separados por profesional, por estación y por cliente. Cada bit encendido = slot ocupado.
- **Agenda continua**: Los servicios se encadenan uno tras otro.
- **Backtracking recursivo**: Para cada slot de inicio, se genera recursivamente todas las asignaciones válidas de profesional × estación evaluando etapa por etapa.
- **Búsqueda radial**: Si el cliente indica un horario preferido, se busca en una ventana de ±3 horas ordenada por proximidad, y luego el resto del día como último recurso.
- **Sistema de scoring**: Con preferencia horaria → `10000 - (distancia_minutos)` + bonus de calidad. Sin preferencia → bonus por hora temprana. Bonus de continuidad: +20 si el mismo profesional atiende el servicio siguiente, -5 si cambia.
- **Triple validación de recursos**: Cada slot candidato valida que el profesional, la estación física y el cliente estén libres simultáneamente.
- **Respeto del horario comercial**: Consulta los `HorarioAtencion` configurados y los `CierreExcepcional` (máscara de cierre por día completo o rango parcial).
- **Filtrado temporal**: Si la fecha es hoy, descarta automáticamente todos los slots que ya pasaron.
- **Alternativas automáticas**: Si se pidió un profesional específico, también genera opciones con todos los profesionales habilitados, deduplicando combinaciones ya vistas.
- **Límite de resultados**: Máximo 8 opciones principales + 8 alternativas.

**Constantes clave:**
```python
SLOT_MINUTES = 5   # Granularidad de 5 minutos
MAX_OPCIONES = 8   # Máximo de resultados por categoría
```

---

### 🔗 Magic Links — Autogestión del Cliente

Cada reserva genera un **token UUID único** (`Reserva.token`) que permite al cliente gestionar sus turnos **sin necesidad de registrarse ni iniciar sesión**:

| Funcionalidad | URL |
|---------------|-----|
| **Ver estado de la reserva** | `/reservas/publica/gestion/<token>/` |
| **Cancelar turnos** | `/reservas/publica/gestion/<token>/cancelar/` |
| **Reprogramar turnos** | Redirige al wizard público con datos pre-cargados vía `?repro_id=X&token=Y` |

El enlace de autogestión se incluye automáticamente en:
- El mensaje de WhatsApp que envía la recepción al confirmar.
- La pantalla de confirmación pública.
- El mensaje de cancelación por WhatsApp.

---

### 📱 Integración WhatsApp Click-to-Chat

La integración con WhatsApp se implementa mediante URLs `wa.me` (sin APIs externas ni costos):

| Contexto | Comportamiento |
|----------|---------------|
| **Reserva interna** | Al confirmar, aparece un botón "Enviar Comprobante por WhatsApp" que abre WhatsApp Web/App con el mensaje pre-armado incluyendo servicios, horarios y link de autogestión dirigido al teléfono del cliente. |
| **Reserva pública** | La pantalla de confirmación ofrece "Guardar Turno en mi WhatsApp" para que el cliente se envíe el comprobante al chat del salón. |
| **Cancelación desde dashboard** | Modal con dos opciones: "Cancelar sin notificar" o "Cancelar y notificar WhatsApp" que redirige a WhatsApp con mensaje de cancelación + link para reagendar. |
| **Cierres excepcionales** | Al forzar un cierre con turnos afectados, se generan links individuales de WhatsApp para avisar a cada cliente con mensaje personalizado de reprogramación. |
| **Listados** | Los listados de clientes y profesionales incluyen botón de WhatsApp directo. |

El teléfono del salón se configura en `core/settings.py`:
```python
SALON_WHATSAPP = '5493876310898'
```

---

### 📊 Dashboard de Recepción

El dashboard principal ofrece dos modos de visualización:

- **Vista Diaria**: Muestra todos los turnos del día con tarjetas de estado color-coded.
- **Vista Semanal**: Grilla de lunes a domingo con turnos agrupados por día y navegación por semana.

#### Auto-inicio de Turnos

Al cargar el dashboard, los turnos **pendientes** cuya hora ya pasó se inician automáticamente (estado → `en_curso`), notificando al operador cuántos se auto-iniciaron.

#### Filtros Disponibles

| Filtro | Descripción |
|--------|-------------|
| `estado` | pendiente · en_curso · completado · cancelado · por_reprogramar |
| `profesional` | Filtrar por profesional asignado |
| `servicio` | Filtrar por servicio reservado |
| `estacion` | Filtrar por estación física |
| `reserva` | Filtrar por número de reserva |
| `q` | Búsqueda por nombre, apellido o teléfono del cliente |
| `sin_facturar` | Mostrar solo turnos activos sin facturar |

#### Contadores de Estado

El dashboard muestra contadores en tiempo real: total de turnos del día, pendientes, en curso, completados y cancelados.

#### Alertas de Stock

Se muestran alertas de inventario clasificadas en:
- **Crítico**: Stock en 0
- **Alerta**: Stock por debajo del mínimo configurado
- **Normal**: Stock suficiente

#### Acciones Rápidas por Turno

Cada tarjeta de turno ofrece botones de acción según su estado:
- **Iniciar** (pendiente → en_curso)
- **Facturar** (en_curso → completado + checkout)
- **Cancelar** (con opción de notificar por WhatsApp)
- **Reprogramar** (pre-carga el wizard con los datos del turno)

---

### 💰 Módulo de Facturación y Checkout

Al facturar un turno (`/turno/<id>/facturar/`):

1. Se muestra el **total sugerido** basado en los precios reales de los servicios (`DetalleTurno.precio_real`).
2. El operador puede ajustar el monto final y elegir el **método de pago**:
   - Efectivo
   - Tarjeta de Débito
   - Tarjeta de Crédito
   - Transferencia Bancaria
   - Mercado Pago
3. Se pueden agregar **productos vendidos** al cliente (descuenta stock automáticamente con validación).
4. Se pueden registrar **insumos consumidos** durante el servicio (descuenta stock automáticamente con validación).
5. Se calcula la **comisión del profesional** según su `porcentaje_comision` (default 35%). La comisión se congela en `Venta.comision` para preservar el dato histórico.
6. Se utiliza **bloqueo pesimista** (`select_for_update`) para evitar doble facturación concurrente.

#### Venta Libre (Mostrador)

La vista `/ventas/nueva/` permite registrar ventas de productos sin asociar a un turno (venta de mostrador). El `Venta.turno` queda en `null` y no se calcula comisión.

---

### 📈 Reportes de Facturación

El módulo de reportes (`/reportes/facturacion/`) ofrece:

| KPI | Descripción |
|-----|-------------|
| Ingresos totales | Suma de todas las ventas en el período |
| Comisiones totales | Suma de comisiones generadas |
| Ticket promedio | Promedio por venta |
| Cantidad de turnos facturados | Total de cierres en el período |

**Visualizaciones con Chart.js:**
- Gráfico de **tendencia mensual** de ingresos (línea)
- Distribución por **método de pago** (torta)
- Ranking de **profesionales por facturación** (barras)
- Ranking de **servicios más solicitados** (barras)

**Filtros:** hoy, esta semana, este mes, este año, rango personalizado, y por profesional.

---

### 👥 Gestión de Clientes

| Funcionalidad | Ruta |
|---------------|------|
| Listado con búsqueda y filtro activos/inactivos | `/clientes/` |
| Crear nuevo cliente | `/clientes/nuevo/` |
| Editar cliente | `/clientes/<id>/editar/` |
| Eliminar (soft-delete) | `/clientes/<id>/eliminar/` |
| Reactivar | `/clientes/<id>/reactivar/` |
| Perfil completo | `/clientes/<id>/` |

El **perfil del cliente** incluye:
- Datos de contacto con botón WhatsApp directo
- Historial completo de turnos
- Fichas técnicas asociadas (fórmulas químicas, tratamientos)

La búsqueda funciona por nombre, apellido, teléfono y email.

---

### ✂️ Gestión de Profesionales

| Funcionalidad | Ruta |
|---------------|------|
| Listado con pestañas activos/inactivos | `/profesionales/` |
| Crear nuevo profesional | `/profesionales/nuevo/` |
| Editar (incluye habilidades y comisión) | `/profesionales/<id>/editar/` |
| Eliminar (soft-delete) | `/profesionales/<id>/eliminar/` |
| Reactivar | `/profesionales/<id>/reactivar/` |

Cada profesional tiene:
- **Habilidades** (M2M con Servicio vía `HabilidadProfesional`): Define qué servicios puede realizar.
- **Porcentaje de comisión**: Se aplica automáticamente al facturar (default 35%, configurable 0-100%).
- **Cuenta de usuario** (opcional): Se puede crear un `User` de Django asociado (`is_staff=True`) con credenciales propias para acceder al sistema.

---

### 🛎️ Gestión de Servicios (Multietapa)

| Funcionalidad | Ruta |
|---------------|------|
| Listado reordenable (drag & drop) | `/servicios/` |
| Crear nuevo servicio | `/servicios/nuevo/` |
| Editar servicio (y sus etapas) | `/servicios/<id>/editar/` |
| Eliminar (soft-delete) | `/servicios/<id>/eliminar/` |
| Reactivar | `/servicios/<id>/reactivar/` |
| Reordenar (AJAX con `bulk_update`) | `/servicios/reordenar/` |

**Novedad: Arquitectura Multietapa (RCPSP)**
Cada servicio se compone de **Etapas de Servicio**. Cada etapa define:
- **Duración**: En bloques de 5 minutos.
- **Tipo de Estación**: Estación de trabajo (silla), Lavacabezas o Ninguna (sala de espera).
- **Requiere Profesional**: Permite liberar al profesional durante tiempos de exposición (ej: actuando la tintura), para que atienda a otro cliente en paralelo.

La duración estimada del servicio se calcula dinámicamente como la suma de sus etapas.

---

### 💺 Gestión de Estaciones Físicas

Las estaciones representan los puestos físicos del salón. El motor de disponibilidad las utiliza para evitar la **colisión de espacio**: dos turnos simultáneos no pueden usar la misma estación.

**Tipos de estación:**
- `estacion` — Estación de Trabajo (silla de corte)
- `lavacabeza` — Lava-Cabezas

| Funcionalidad | Ruta |
|---------------|------|
| Listado | `/estaciones/` |
| Crear/Editar | `/estaciones/nueva/` · `/estaciones/<id>/editar/` |
| Eliminar (soft-delete) | `/estaciones/<id>/eliminar/` |
| Reactivar | `/estaciones/<id>/reactivar/` |

---

### 📦 Inventario y Productos

El sistema de inventario maneja dos tipos de productos con un único modelo:

| Tipo | Flag | Uso |
|------|------|-----|
| **Producto para venta** | `es_para_venta = True` | Productos retail vendidos al cliente en el checkout o en venta libre. |
| **Insumo** | `es_insumo = True` | Materiales consumidos durante el servicio (tinturas, shampoo, etc.). Se registran en el checkout. |

Un producto puede ser ambos simultáneamente. Soporta tres **unidades de medida**: unidades, gramos, mililitros.

#### Funcionalidades de Inventario

| Funcionalidad | Ruta |
|---------------|------|
| Listado con alertas de stock bajo | `/productos/` |
| Crear/Editar producto | `/productos/nuevo/` · `/productos/<id>/editar/` |
| Eliminar (soft-delete) | `/productos/<id>/eliminar/` |
| Reactivar | `/productos/<id>/reactivar/` |
| Ajuste rápido de stock (+/-) | `/productos/<id>/stock/<accion>/` |
| Ajuste masivo de precios (%) | `/productos/ajuste_masivo/` |

**Alerta de stock bajo**: Se muestra cuando `stock_actual <= stock_minimo`. El dashboard clasifica las alertas en crítico (stock=0), alerta (stock bajo) y normal.

---

### ⚙️ Configuración del Salón

#### Horarios de Atención (`HorarioAtencion`)

Configuración de horarios por día de la semana (Lunes=0 a Domingo=6). Soporta **múltiples turnos por día** (ej: mañana 9-13 y tarde 16-20).

| Funcionalidad | Ruta |
|---------------|------|
| Panel de configuración | `/configuracion/` |
| Crear/Editar horario | `/configuracion/horarios/nuevo/` · `/configuracion/horarios/<id>/editar/` |
| Eliminar horario | `/configuracion/horarios/<id>/eliminar/` |

#### Cierres Excepcionales (`CierreExcepcional`)

Permite registrar feriados o cierres no programados. Soporta **día completo** o **rango horario parcial** (`hora_inicio` / `hora_fin`).

| Funcionalidad | Ruta |
|---------------|------|
| Crear/Editar cierre | `/configuracion/cierres/nuevo/` · `/configuracion/cierres/<id>/editar/` |
| Eliminar cierre | `/configuracion/cierres/<id>/eliminar/` |

**Flujo de cierre con conflictos:**
1. Al registrar un cierre en una fecha con turnos pendientes, el modelo `CierreExcepcional.clean()` **detecta automáticamente los turnos afectados** y lanza un `ValidationError`.
2. La vista muestra la lista de clientes afectados con botones individuales de WhatsApp con mensaje pre-armado de reprogramación.
3. El operador puede **forzar el cierre**, lo que pasa todos los turnos afectados a estado `por_reprogramar`.

---

### 📋 Fichas Técnicas

Registro profesional de fórmulas químicas para tratamientos de coloración, asociados a un cliente y opcionalmente a un turno:

- Descripción del tratamiento
- Fórmula química (proporciones, marcas, colores, tiempos de acción)
- Observaciones

Accesibles desde el perfil del cliente y creables desde un turno específico (`/turno/<id>/ficha/nueva/`).

---

## 🔐 Control de Acceso

El sistema implementa tres niveles de acceso:

| Rol | Acceso |
|-----|--------|
| **Público** (sin login) | Wizard de reserva pública, APIs de disponibilidad pública, portal de autogestión vía Magic Link (token UUID) |
| **Staff** (login requerido) | Dashboard, reserva interna, gestión de clientes, cancelación/inicio/facturación de turnos, ventas de mostrador, búsqueda de clientes |
| **Admin** (superusuario) | Todo lo anterior + ABM de profesionales, servicios, estaciones, productos, configuración de horarios/cierres, reportes de facturación |

---

## 🔒 Patrones Arquitectónicos

| Patrón | Implementación |
|--------|---------------|
| **Bitmask-based Scheduling** | Cada slot de 5 min = 1 bit. Las colisiones se verifican en O(1) con operaciones bitwise AND. |
| **Soft Deletes** | Todas las entidades principales usan `activo = BooleanField(default=True)` en lugar de borrado físico. |
| **Bloqueo Pesimista** | `select_for_update()` sobre Turno, Cliente, Profesional y Estación durante la creación de reservas. IDs ordenados de menor a mayor para prevenir deadlocks. |
| **Transacciones Atómicas** | Todo flujo de reserva y facturación envuelto en `transaction.atomic()`. |
| **Double-Checked Locking** | El control de saturación (máx. 2 turnos) se valida preventivamente en la API de disponibilidad y luego definitivamente dentro de la transacción atómica de confirmación. |
| **Magic Links (UUID)** | `Reserva.token` (UUID4 auto-generado) habilita autogestión sin autenticación. |
| **Comisiones Congeladas** | La comisión se calcula al facturar y se guarda en `Venta.comision`, protegiendo el dato histórico ante cambios futuros del porcentaje del profesional. |
| **Localización de Zona Horaria** | `timezone.localtime()` en todas las vistas que generan texto orientado al cliente (mensajes de WhatsApp, confirmaciones). |
| **Inventario Dual** | Un único modelo `Producto` con flags `es_para_venta` / `es_insumo` cubre productos retail e insumos profesionales. |
| **Auto-inicio** | El dashboard transiciona automáticamente turnos pendientes atrasados a `en_curso`. |

---

## 📁 Estructura del Proyecto

```
studio-salta/
├── core/                          # Configuración Django
│   ├── settings.py                # Settings (TZ, SALON_WHATSAPP, compressor, etc.)
│   ├── urls.py                    # URL raíz (incluye gestion.urls)
│   └── wsgi.py                    # Entry point WSGI (PythonAnywhere)
│
├── gestion/                       # App principal
│   ├── models/                    # Modelos de datos
│   │   ├── clientes.py            # Cliente
│   │   ├── configuracion.py       # → importado desde servicios.py (HorarioAtencion, CierreExcepcional)
│   │   ├── fichas.py              # FichaTecnica
│   │   ├── inventario.py          # Producto, ConsumoInsumo
│   │   ├── profesionales.py       # Profesional, HabilidadProfesional
│   │   ├── servicios.py           # Servicio, Estacion, HorarioAtencion, CierreExcepcional
│   │   ├── turnos.py              # Turno, Reserva, DetalleTurno
│   │   └── ventas.py              # Venta, DetalleVentaProducto
│   │
│   ├── views/                     # Vistas organizadas por dominio
│   │   ├── api.py                 # APIs legacy (horarios, búsqueda clientes)
│   │   ├── clientes.py            # CRUD clientes + perfil
│   │   ├── configuracion.py       # Horarios + cierres excepcionales
│   │   ├── dashboard.py           # Dashboard recepción (diario/semanal + auto-inicio)
│   │   ├── estaciones.py          # CRUD estaciones
│   │   ├── fichas.py              # Fichas técnicas
│   │   ├── productos.py           # CRUD inventario + ajuste masivo
│   │   ├── profesionales.py       # CRUD profesionales + creación de usuarios
│   │   ├── reportes.py            # Reportes de facturación + KPIs + Chart.js
│   │   ├── reservas.py            # Wizard de reservas (público + interno) + Magic Links
│   │   ├── servicios.py           # CRUD servicios + reordenamiento drag & drop
│   │   ├── turnos.py              # Acciones sobre turnos (cancelar, iniciar, facturar)
│   │   └── ventas.py              # Venta libre (mostrador)
│   │
│   ├── tests/                     # Tests unitarios
│   │   ├── test_concurrencia.py   # Concurrencia: booking simultáneo, stock race conditions
│   │   ├── test_dashboard.py      # Dashboard: filtros, estados, contadores
│   │   └── test_public_reserva.py # Reserva pública: wizard, saturación, Magic Links
│   │
│   ├── api_disponibilidad.py      # Motor de disponibilidad (bitmask-based, 416 líneas)
│   ├── forms.py                   # 9 formularios Django
│   ├── urls.py                    # 75 rutas de la app
│   ├── templatetags/
│   │   └── gestion_extras.py      # Filtros: wa_phone (limpieza tel → WhatsApp), dict_get
│   │
│   └── static/gestion/
│       ├── css/
│       │   ├── base.css            # Estilos base globales
│       │   └── wizard.css          # Estilos del wizard de reservas
│       └── js/
│           ├── wizard_reserva.js   # Lógica compartida del wizard (22KB)
│           ├── servicios.js        # Drag & drop reordenamiento de servicios
│           └── ventas.js           # Gestión de filas de productos/insumos en facturación
│
├── templates/
│   ├── base.html                   # Layout base (Bootstrap 5 + sidebar + offcanvas mobile)
│   ├── registration/
│   │   └── login.html              # Pantalla de login
│   └── gestion/
│       ├── dashboard.html          # Dashboard principal (17KB)
│       ├── reserva_publica_wizard.html  # Wizard público (3 pasos)
│       ├── reserva_interna.html    # Wizard interno (3 pasos + buscador clientes)
│       ├── reserva_publica.html    # Formulario legacy de reserva simple
│       ├── confirmacion_publica.html    # Confirmación con WhatsApp + Calendar
│       ├── gestion_publica.html    # Portal autogestión (Magic Link)
│       ├── cancelar_publica.html   # Cancelación desde autogestión
│       ├── facturar.html           # Checkout / facturación
│       ├── venta_libre.html        # Venta de mostrador
│       ├── clientes.html           # Listado de clientes
│       ├── nuevo_cliente.html      # Crear/editar cliente
│       ├── perfil_cliente.html     # Perfil con historial
│       ├── profesionales.html      # Listado de profesionales
│       ├── profesional_form.html   # Crear/editar profesional (con habilidades y usuario)
│       ├── servicios.html          # Listado con drag & drop
│       ├── servicio_form.html      # Crear/editar servicio
│       ├── productos.html          # Inventario con alertas de stock
│       ├── producto_form.html      # Crear/editar producto
│       ├── estaciones.html         # Listado de estaciones
│       ├── estacion_form.html      # Crear/editar estación
│       ├── estacion_confirm_delete.html  # Confirmación de eliminación
│       ├── nueva_ficha.html        # Ficha técnica
│       ├── partials/
│       │   ├── _turno_card_diaria.html  # Tarjeta de turno (vista día)
│       │   ├── _turno_card_semanal.html # Tarjeta de turno (vista semana)
│       │   ├── _modal_cancelacion.html  # Modal cancelar + notificar WhatsApp
│       │   ├── _fila_producto.html      # Fila de producto en facturación
│       │   └── _fila_insumo.html        # Fila de insumo en facturación
│       ├── configuracion/
│       │   ├── panel.html          # Panel horarios + cierres
│       │   ├── horario_form.html   # Form de horario
│       │   └── cierre_form.html    # Form de cierre con afectados + WhatsApp
│       └── reportes/
│           └── facturacion.html    # Dashboard de reportes (40KB, 4 gráficos Chart.js)
│
├── docs/
│   ├── DEPLOY_PRODUCCION.md       # Guía paso a paso para deploy en PythonAnywhere
│   ├── der_report.md              # Reporte DER con diagrama Mermaid y reglas de negocio
│   └── sistema_horarios.md        # Documentación del sistema de horarios y bitmasks
│
├── requirements.txt
└── manage.py
```

---

## 🧪 Tests

El proyecto incluye **3 módulos de tests** organizados en `gestion/tests/`:

### Tests de Concurrencia (`test_concurrencia.py`)
- Booking simultáneo del mismo profesional por dos threads → solo uno debe tener éxito.
- Validación de stock bajo concurrencia → no permite vender más de lo disponible con rollback.

### Tests de Dashboard (`test_dashboard.py`)
- Turnos cancelados se muestran correctamente.
- Filtro por estado `cancelado` funciona.
- Filtro por estado `pendiente` funciona.

### Tests de Reserva Pública (`test_public_reserva.py`)
- El wizard público carga sin autenticación.
- La API de disponibilidad pública retorna slots válidos.
- **Control de saturación**: bloquea cuando el cliente tiene ≥2 turnos futuros.
- Confirmación atómica crea Reserva + múltiples Turnos.
- Las observaciones se guardan tanto en Reserva como en Turno.
- Ciclo completo de autogestión: acceso al portal → cancelación → verificación de estado y anotación.

```bash
# Ejecutar todos los tests
python manage.py test

# Ejecutar un módulo específico
python manage.py test gestion.tests.test_concurrencia
```

---

## 📡 Endpoints de la API

### Públicos (sin autenticación)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/reservas/publica/` | GET | Wizard de reserva pública |
| `/api/disponibilidad-publica/` | POST | Disponibilidad multi-servicio (con control de saturación) |
| `/api/reservas/publica/confirmar/` | POST | Confirmación atómica de reserva |
| `/reservas/publica/confirmacion/<token>/` | GET | Página de éxito (WhatsApp + Calendar) |
| `/reservas/publica/gestion/<token>/` | GET | Portal de autogestión (Magic Link) |
| `/reservas/publica/gestion/<token>/cancelar/` | GET/POST | Cancelación por el cliente |

### Staff (login requerido)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/clientes/buscar/?q=...` | GET | Búsqueda de clientes (JSON, mín. 2 chars, máx. 10 resultados) |
| `/api/disponibilidad-combinada/` | POST | Disponibilidad multi-servicio interna |
| `/api/horarios/` | GET | Disponibilidad legacy (un solo servicio) |

### Admin (superusuario)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/servicios/reordenar/` | POST | Reordenamiento drag & drop (JSON, `bulk_update`) |

---

## 🌐 Deploy a Producción (PythonAnywhere)

La documentación completa de deploy se encuentra en [`docs/DEPLOY_PRODUCCION.md`](docs/DEPLOY_PRODUCCION.md).

### Resumen del flujo de actualización:

```bash
# En la consola de PythonAnywhere (con venv activado)
cd ~/Peluqueria
git pull origin main
python manage.py collectstatic --no-input
python manage.py migrate
# → Ir a Web tab → Reload
```

### Variables de entorno requeridas en producción:

| Variable | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | Clave secreta única generada |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `danilo2004.pythonanywhere.com` |

---

## 📐 Modelo de Datos (16 modelos)

```mermaid
erDiagram
    Cliente ||--o{ Turno : tiene
    Cliente ||--o{ FichaTecnica : tiene
    Cliente ||--o{ Venta : "venta libre"
    Profesional ||--o{ Turno : atiende
    Profesional }o--o{ Servicio : "habilidades (via HabilidadProfesional)"
    Profesional ||--o| User : "cuenta opcional"
    Estacion ||--o{ Turno : ocupa
    Reserva ||--o{ Turno : agrupa
    Turno ||--o{ DetalleTurno : incluye
    Servicio ||--o{ DetalleTurno : detalla
    Servicio ||--o{ EtapaServicio : contiene
    Turno ||--o| Venta : factura
    Turno ||--o{ ConsumoInsumo : consume
    Turno ||--o{ FichaTecnica : registra
    Venta ||--o{ DetalleVentaProducto : vende
    Producto ||--o{ DetalleVentaProducto : vendido
    Producto ||--o{ ConsumoInsumo : consumido

    Cliente {
        string nombre
        string apellido
        string telefono UK
        string email
        bool activo
        date fecha_registro
    }
    Reserva {
        uuid token UK
        datetime fecha_creacion
        string observaciones
    }
    Turno {
        datetime fecha_hora
        datetime hora_fin_estimada
        string estado
        int orden
        string observaciones
    }
    Profesional {
        string nombre
        string apellido
        string telefono
        int porcentaje_comision
        bool activo
        date fecha_contratacion
    }
    HabilidadProfesional {
        FK profesional
        FK servicio
    }
    Servicio {
        string nombre UK
        decimal precio_sugerido
        int orden_sugerido
        bool activo
    }
    EtapaServicio {
        int orden
        string nombre
        int duracion
        string tipo_estacion
        bool requiere_profesional
    }
    Estacion {
        string nombre UK
        string tipo
        bool activa
    }
    HorarioAtencion {
        int dia_semana
        time hora_apertura
        time hora_cierre
        bool abierto
    }
    CierreExcepcional {
        date fecha
        string descripcion
        bool es_dia_completo
        time hora_inicio
        time hora_fin
    }
    Producto {
        string nombre UK
        decimal precio
        decimal stock_actual
        decimal stock_minimo
        string unidad_medida
        bool es_para_venta
        bool es_insumo
        bool activo
    }
    Venta {
        decimal total
        string metodo_pago
        decimal comision
        datetime fecha_venta
    }
    FichaTecnica {
        string descripcion
        string formula_quimica
        string observaciones
        datetime fecha_creacion
    }
    DetalleTurno {
        FK turno
        FK servicio
        decimal precio_real
    }
    DetalleVentaProducto {
        FK venta
        FK producto
        int cantidad
        decimal precio_unitario
    }
    ConsumoInsumo {
        FK turno
        FK producto
        decimal cantidad_usada
    }
```

---

## 📚 Documentación Adicional

| Documento | Contenido |
|-----------|-----------|
| [`docs/DEPLOY_PRODUCCION.md`](docs/DEPLOY_PRODUCCION.md) | Guía paso a paso de deploy en PythonAnywhere (318 líneas) |
| [`docs/der_report.md`](docs/der_report.md) | Reporte DER completo con diagrama Mermaid y 5 reglas de negocio documentadas |
| [`docs/sistema_horarios.md`](docs/sistema_horarios.md) | Arquitectura del sistema de horarios y explicación del algoritmo bitmask |

---

© 2026 Studio Salta — Gestión Profesional de Peluquería.
