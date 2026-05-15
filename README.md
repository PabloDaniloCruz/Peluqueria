# 💇‍♂️ Studio Salta | Sistema de Gestión Integral

Plataforma profesional para la gestión de turnos, inventario y administración de peluquerías. Diseñado para optimizar la ocupación del salón mediante un motor de agenda continua y búsqueda radial de disponibilidad.

## 🚀 Inicio Rápido

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configurar base de datos**:
   ```bash
   python manage.py migrate
   ```
3. **Crear administrador**:
   ```bash
   python manage.py createsuperuser
   ```
4. **Ejecutar servidor local**:
   ```bash
   python manage.py runserver
   ```

## ✨ Características Principales

| Módulo | Funcionalidad Clave |
|--------|---------------------|
| **Agenda Inteligente** | Wizard de reserva interna con algoritmo radial que prioriza el horario preferido del cliente y evita solapamientos. |
| **Dashboard Pro** | Vista diaria y semanal con filtros granulares por profesional, servicio, estación y estado de facturación. |
| **Administración** | Gestión completa de Profesionales (con comisiones), Servicios reordenables y Estaciones físicas (lava-cabezas). |
| **Inventario** | Control de stock con alertas de reposición y herramienta de ajuste masivo de precios. |
| **Checkout** | Módulo de facturación integrada que descuenta stock automáticamente y procesa ventas de mostrador. |

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.x + Django 5.x
- **Frontend**: Vanilla JavaScript (ES6+), Modern CSS (Glassmorphism & Dark Mode), Bootstrap 5.
- **Assets**: `django-compressor` para optimización de estáticos.
- **Base de Datos**: SQLite (Desarrollo) / PostgreSQL compatible (Producción).

## 📋 Requisitos de Negocio Implementados

- [x] **Agenda Continua**: Los turnos se bloquean en cascada según la duración real de cada servicio.
- [x] **Control de Recursos**: Gestión de estaciones físicas para evitar colisiones de espacio.
- [x] **Comisiones Dinámicas**: Cálculo automático de ganancias por profesional.
- [x] **Horarios Dinámicos**: Sincronización en tiempo real con la configuración de apertura/cierre del salón.

---
© 2026 Studio Salta - Gestión Profesional de Peluquería.
