---
name: Modern Salon Management
colors:
  surface: '#fbf9f9'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e3e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#444748'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a1c1b'
  on-tertiary-container: '#838483'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474746'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#e2e3e1'
  tertiary-fixed-dim: '#c6c7c5'
  on-tertiary-fixed: '#1a1c1b'
  on-tertiary-fixed-variant: '#454746'
  background: '#fbf9f9'
  on-background: '#1b1c1c'
  surface-variant: '#e3e2e2'
typography:
  display-lg:
    fontFamily: Noto Serif
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Noto Serif
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-md:
    fontFamily: Noto Serif
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.4'
  headline-sm:
    fontFamily: Noto Serif
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  headline-lg-mobile:
    fontFamily: Noto Serif
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.3'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding: 32px
  gutter: 24px
  sidebar-width: 280px
  timeline-row-height: 80px
---

## Brand & Style
The design system is engineered for high-end beauty and wellness environments where the interface must reflect the same level of curation and professionalism as the service provided. The brand personality is **Elite, Serene, and Efficient**. 

We employ a **Minimalist** design style with a focus on generous whitespace and high-quality typography. The aesthetic avoids "clinical" coldness by introducing warmth through soft gold accents and organic rounded corners. The goal is to evoke a sense of calm organization for salon owners and stylists, transforming complex scheduling data into a visually soothing experience.

## Colors
The palette is rooted in high-contrast sophistication. 
- **Deep Charcoal (#1A1A1A):** Used for primary text and core structural elements to provide a grounded, professional foundation.
- **Soft Gold (#D4AF37):** A muted, premium metallic tone used sparingly for primary actions, active states, and "Premium" status indicators.
- **Clean White (#FFFFFF):** The canvas for all cards and surfaces, ensuring maximum legibility.
- **Warm Gray (#F9F9F7):** Used for background layering to create subtle separation between the workspace and the navigation.
- **Semantic Accents:** Success (Muted Sage), Warning (Soft Ochre), and Error (Dusty Rose) should be desaturated to maintain the high-end aesthetic.

## Typography
This design system utilizes a sophisticated typographic pairing to balance editorial elegance with functional clarity. 
- **Noto Serif** is reserved for headings, page titles, and client names, providing a literary and authoritative touch. 
- **Inter** handles all UI-related tasks, including navigation, data grids, and button labels, ensuring high readability at small sizes. 
- All labels and metadata use an uppercase tracking (letter-spacing) of 5% to enhance the "luxury brand" feel.

## Layout & Spacing
The layout follows a **Hybrid Grid** model. 
- **Navigation:** A fixed left sidebar (280px) provides consistent access to core modules.
- **Content Area:** A fluid container with a maximum width of 1600px, utilizing 32px of internal padding.
- **Timeline Grid:** A specialized horizontal scrolling area where each column represents a Stylist and each row represents a 15-minute time increment.
- **Rhythm:** We use an 8px baseline grid. Components should favor large internal padding (minimum 16px) to maintain the "Spacious Minimalist" requirement.

## Elevation & Depth
Hierarchy is established through **Tonal Layering** and **Ambient Shadows**.
- **Level 0 (Background):** Soft Warm Gray (#F9F9F7).
- **Level 1 (Cards/Surface):** Pure White with a subtle 1px border (#EEEEEE) and no shadow.
- **Level 2 (Active/Floating):** Pure White with an "Ambient Glow" shadow—a very soft, desaturated charcoal shadow (Y: 4, Blur: 20, Opacity: 0.04).
- **Glassmorphism:** Use a light backdrop blur (12px) for modal overlays and sticky header navigation to maintain a sense of context.

## Shapes
The shape language is defined by generous, friendly curves. Following the `roundedness: 2` standard, core UI components like buttons and input fields utilize a 0.5rem (8px) radius. 

However, for **Appointment Cards** and **Professional Profile Containers**, we utilize `rounded-2xl` (2rem / 32px) to create a soft, high-end "tablet" feel that differentiates this system from standard enterprise tools.

## Components
- **Appointment Cards:** White surfaces with a vertical accent bar on the left (using the status color). They should include the client name in Noto Serif and the service type in Inter.
- **Timeline Grid:** The background grid should use very faint horizontal lines (#F0F0F0). The "current time" indicator is a horizontal line in Soft Gold with a small circular pin.
- **Buttons:**
    - *Primary:* Deep Charcoal background with White text.
    - *Secondary:* Transparent background with a 1px Soft Gold border and Gold text.
- **Professional Profiles:** Circular avatars with a 2px White border and a 1px Charcoal outer ring. Stylist names appear below in Noto Serif Sm.
- **Status Indicators:** Small, pill-shaped chips with desaturated background tints (e.g., "Confirmed" is a very pale sage with dark forest green text).
- **Input Fields:** Minimalist design with only a bottom border that transitions to a Soft Gold 2px border on focus. Labels should be small, uppercase Inter.