# Arquitectura de Gestión de Horarios y Disponibilidad

Este documento resume cómo funciona el sistema de horarios, turnos partidos y cierres excepcionales en Studio Salta.

## Resumen Ejecutivo
El sistema permite al administrador definir múltiples rangos de atención por día (ej. mañana y tarde) y bloquear fechas específicas (feriados/vacaciones) mediante una interfaz visual. Estos cambios alimentan un algoritmo de disponibilidad basado en **máscaras de bits** que garantiza que no se reserven turnos fuera del horario laboral.

## Componentes Técnicos

| Componente | Descripción |
| :--- | :--- |
| **Modelo `HorarioAtencion`** | Almacena los rangos de apertura. Permite múltiples registros por día (ej. Lunes 9-13 y Lunes 16-20). |
| **Modelo `CierreExcepcional`** | Almacena fechas bloqueadas. Puede ser día completo o un rango específico. |
| **API de Disponibilidad** | Procesa los modelos y genera una máscara de bits donde `1 = ocupado/cerrado` y `0 = disponible`. |
| **Panel de Configuración** | Interfaz administrativa para gestionar estos datos sin entrar al panel técnico de Django. |

## Lógica de Cálculo de Disponibilidad

El algoritmo en `gestion/api_disponibilidad.py` sigue este flujo para cada solicitud de reserva:

1.  **Carga de Horarios**: Busca todos los `HorarioAtencion` activos para el día de la semana solicitado.
2.  **Generación de Máscara Base**:
    *   Crea una máscara donde todos los slots (de 5 min) están marcados como **ocupados**.
    *   "Perfora" (marca como libre) los slots que coinciden con los rangos de `HorarioAtencion`.
3.  **Aplicación de Cierres**:
    *   Si existe un `CierreExcepcional` para la fecha, vuelve a marcar esos slots como **ocupados**.
4.  **Validación Final**: Si la máscara resultante indica que todo el día está ocupado, devuelve un error de "Local Cerrado".
5.  **Cruce con Turnos**: La máscara de horario se combina con la disponibilidad de los profesionales y estaciones de trabajo.

## Cómo administrar (Ruta de Administrador)

1.  Navegar a **⚙️ Configuración** en el sidebar.
2.  **Horarios**: Click en "+ Agregar Turno" para sumar rangos a un día. Se pueden borrar o editar los existentes.
3.  **Cierres**: Click en "+ Nuevo Cierre" para bloquear un feriado o un rango de horas (ej. "Cierre por desinfección").

## Consideraciones para Desarrolladores

- **Deduplicación**: Al mostrar los horarios agrupados en el panel, se utiliza el filtro personalizado `dict_get` definido en `gestion/templatetags/gestion_extras.py`.
- **Performance**: Las consultas a horarios y cierres están optimizadas, pero se recomienda no tener cientos de cierres activos para la misma fecha (poco probable en uso real).
- **Consistencia**: Al eliminar un horario, la API reflejará el cambio instantáneamente en las nuevas búsquedas de turnos.
