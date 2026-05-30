# Plan de Rediseño — Studio Salta

> Basado en el sistema de diseño definido en `DESIGN.md`
> Generado: 2026-05-29

## Resumen Ejecutivo

Aplicar el diseño definido en `DESIGN.md` a todo el proyecto. Es un cambio grande (~36-38 archivos, ~2500-3500 líneas) que reemplaza la capa visual de Bootstrap 5.3 por una paleta Charcoal + Gold, tipografía Noto Serif + Inter, y componentes completamente rediseñados.

## Stack Actual

| Aspecto | Detalle |
|---------|---------|
| Framework | Django 5.2 |
| Frontend | Bootstrap 5.3 CDN + Bootstrap Icons + django-compressor |
| CSS custom | `base.css` (32 líneas) + `wizard.css` (142 líneas) |
| Templates | 33 archivos (1 base + 28 admin + 4 públicos) |
| JS dinámico | `wizard_reserva.js` (~554 líneas, genera clases Bootstrap inline) |
| Testing | Django TestCase (4 archivos de test) |

## Archivos Afectados

| Categoría | Cantidad | Detalle |
|-----------|----------|---------|
| Templates Django | 33 | `base.html`, 22 en `templates/gestion/`, 5 partials, 1 login, etc. |
| CSS actual | 2 | `base.css`, `wizard.css` → reemplazar por design system |
| CSS nuevo | 1-3 | `design-system.css` con custom properties + componentes |
| JS | 1 | `wizard_reserva.js` — clases Bootstrap inline a refactorizar |
| Settings | 1 | Posible actualización en `core/settings.py` |
| **Total estimado** | **~36-38 archivos** | |

## Líneas de Cambio Estimadas

| Componente | Líneas |
|------------|--------|
| CSS del design system | ~500-800 |
| Templates (clases Bootstrap → design system) | ~1500-2000 |
| JS (wizard_reserva.js) | ~30-50 |
| **Total** | **~2500-3500 líneas** |

## Riesgos

### 🔴 Alto
- **Big Bang Visual**: Cambiar `--bs-primary` de azul (`#0d6efd`) a charcoal (`#1A1A1A`) rompe TODOS los componentes de golpe (botones, badges, alerts, navbars, modals). No hay forma de hacerlo gradual.
- **Sidebar**: Pasa de col-md-2 Bootstrap a sidebar fija de 280px con diseño distinto. Requiere replantear navegación mobile.

### 🟡 Medio
- **Responsive**: La navegación mobile actual (navbar dark → offcanvas) necesita rediseñarse con la nueva sidebar fija.
- **JS Wizard**: `wizard_reserva.js` genera HTML con clases Bootstrap en 5-6 lugares. Cualquier cambio de clases en templates debe replicarse ahí.
- **Páginas Públicas**: 4 templates con gradientes inline propios que necesitan atención especial para integrarse al nuevo sistema.
- **Inputs**: Bootstrap `form-control` tiene borde completo. El nuevo diseño pide bottom-border-only con gold focus. Requiere overrides masivos.

### 🟢 Bajo
- **Template Logic**: No se toca — `{% url %}`, `{% if %}`, `{% for %}`, filtros Django, CSRF tokens, query params se mantienen intactos.
- **Forms**: Todos los forms se renderizan campo por campo (no `form.as_p`), lo que permite control granular.

## Estrategia Recomendada

### Enfoque: Híbrido (Bootstrap + Design System)

**NO eliminar Bootstrap**. Mantenerlo para su parte **estructural**:
- Grid system (`.row`, `.col-*`)
- Modales y Offcanvas
- Dropdowns
- Componentes JS (tooltips, collapse, tabs)

**Reemplazar su capa visual** vía CSS custom properties:
```css
:root {
  --color-deep-charcoal: #1A1A1A;
  --color-soft-gold: #D4AF37;
  --color-clean-white: #FFFFFF;
  --color-warm-gray: #F9F9F7;

  /* Bootstrap overrides */
  --bs-primary: var(--color-deep-charcoal);
  --bs-primary-rgb: 26, 26, 26;
  /* ... */
}
```

Más clases custom para lo que Bootstrap no cubre:
- `.glass-panel` — glassmorphism
- `.surface-level-1/2` — tonal layering
- `.accent-bar` — barra vertical en appointment cards
- `.status-chip` — pills desaturados
- `.input-minimalist` — inputs bottom-border-only
- `.card-appointment` — cards con 32px border-radius

## Estrategia de Entrega: 3 PRs Encadenados

### PR 1 — Foundation (~800-1000 líneas)
**Riesgo: 🔴 Alto**

Archivos: ~20
Qué incluye:
- `design-system.css` con custom properties + Bootstrap overrides
- Google Fonts (Noto Serif + Inter) en `base.html`
- Sidebar fija de 280px + layout fluid
- Tipografía base (headings Noto Serif, body Inter)
- Reset de colores Bootstrap para que todo el sitio use la nueva paleta

Este PR rompe visualmente TODO. Es el "big bang" controlado — se acepta que todo se ve diferente.

### PR 2 — Componentes Core (~1000-1200 líneas)
**Riesgo: 🟡 Medio**

Archivos: ~25
Qué incluye:
- Appointment cards con accent bar + 32px border-radius
- Status pills desaturados
- Botones (primary charcoal, secondary gold border)
- Inputs minimalistas (bottom-border-only)
- Wizard stepper rediseñado
- Modales con glassmorphism

### PR 3 — Polish + Públicas (~500-800 líneas)
**Riesgo: 🟢 Bajo**

Archivos: ~10
Qué incluye:
- Páginas públicas (gestión, confirmación, cancelación) — las que tienen gradientes inline
- Timeline grid horizontal scrolling
- Indicador "current time" en gold
- Glassmorphism en sticky headers
- Micro-animaciones y transiciones
- Refactor de `wizard_reserva.js`

## Próximos Pasos (cuando retomes)

1. `/sdd-new "Rediseño visual completo"` — arranca la propuesta formal del cambio
2. Elegir: modo **interactivo** (validar fase por fase) o **automático** (todo corrido)
3. Elegir estrategia de entrega: **auto-chain** (3 PRs automáticos) o **ask-on-risk** (preguntar antes de cada PR grande)

## Referencias

- `doc_disenio/DESIGN.md` — Sistema de diseño completo
- `templates/base.html` — Template base actual
- `gestion/static/gestion/css/base.css` — CSS actual
- `gestion/static/gestion/css/wizard.css` — CSS del wizard
