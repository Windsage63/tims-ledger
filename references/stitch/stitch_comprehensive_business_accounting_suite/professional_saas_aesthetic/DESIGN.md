---
name: Professional SaaS Aesthetic
colors:
  surface: '#f9f9ff'
  surface-dim: '#dad9e0'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3fa'
  surface-container: '#eeedf4'
  surface-container-high: '#e8e7ee'
  surface-container-highest: '#e2e2e9'
  on-surface: '#1a1b20'
  on-surface-variant: '#404751'
  inverse-surface: '#2f3035'
  inverse-on-surface: '#f0f0f7'
  outline: '#707882'
  outline-variant: '#c0c7d3'
  surface-tint: '#0061a3'
  primary: '#005e9d'
  on-primary: '#ffffff'
  primary-container: '#0077c5'
  on-primary-container: '#fafaff'
  inverse-primary: '#9ecaff'
  secondary: '#096e00'
  on-secondary: '#ffffff'
  secondary-container: '#86f96d'
  on-secondary-container: '#0a7300'
  tertiary: '#8f4700'
  on-tertiary: '#ffffff'
  tertiary-container: '#b45b00'
  on-tertiary-container: '#fff9f7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d1e4ff'
  primary-fixed-dim: '#9ecaff'
  on-primary-fixed: '#001d36'
  on-primary-fixed-variant: '#00497c'
  secondary-fixed: '#89fc6f'
  secondary-fixed-dim: '#6ddf56'
  on-secondary-fixed: '#012200'
  on-secondary-fixed-variant: '#055300'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb785'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#f9f9ff'
  on-background: '#1a1b20'
  surface-variant: '#e2e2e9'
typography:
  display:
    fontFamily: Work Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Work Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Work Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Work Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Work Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 40px
---

## Brand & Style

The visual identity of the design system is anchored in clarity, efficiency, and professional trust. It is designed for high-utility environments where data density must coexist with visual breathing room. The style follows a **Corporate/Modern** approach, prioritizing functional grouping over decorative elements.

The aesthetic evokes a sense of reliability and precision. By utilizing a "light-first" philosophy, the interface remains airy and approachable even when displaying complex financial or technical information. The emotional response should be one of organized calm and institutional confidence.

## Colors

The palette is optimized for long-duration work sessions, utilizing a sophisticated range of grays to create hierarchy without overwhelming the user. 

- **Primary:** A professional, high-vibrancy blue (#0077C5) used for primary actions, navigation states, and brand presence.
- **Accents:** A vibrant green (#2CA01C) is reserved for success states and positive financial growth, while a warm amber (#EF7D11) signals warnings and pending items.
- **Neutrals:** The background uses a specific off-white (#F4F5F8) to reduce screen glare, with borders utilizing a crisp light gray (#D4D7DC) to define functional boundaries.

## Typography

This design system uses a dual-font strategy to balance character with utility. **Work Sans** is used for headlines to provide a grounded, professional personality. **Inter** is the workhorse for all UI elements and body text, chosen for its exceptional legibility at small sizes in data-heavy tables.

For numerical data that requires vertical alignment (such as ledger entries or balance sheets), use the optional `data-mono` role to ensure figures remain easily scannable. Text contrast always meets or exceeds WCAG AA standards against the light background palette.

## Layout & Spacing

The layout model follows a **Fluid Grid** philosophy for data dashboards and a **Fixed Grid** (max-width 1200px) for settings and form-entry pages. We utilize a 12-column system to allow for flexible sidebars and content panes.

- **Data Density:** Use the `md` (16px) spacing unit as the default for padding within cards and containers. For "High Density" views, drop to `sm` (8px).
- **Functional Grouping:** Use white-space to separate major task areas rather than heavy lines. 
- **Breakpoints:**
  - **Mobile:** < 600px (1 column, 16px margins)
  - **Tablet:** 601px - 1024px (6 columns, 24px margins)
  - **Desktop:** > 1025px (12 columns, 40px margins)

## Elevation & Depth

Hierarchy is established primarily through **Tonal Layers** and subtle **Ambient Shadows**. 

1. **Floor:** The background layer (#F4F5F8).
2. **Card/Surface:** Pure white (#FFFFFF) containers used to group related information. These should have a 1px border (#D4D7DC).
3. **Lifted State:** Use a very soft, diffused shadow (0px 2px 4px rgba(0,0,0,0.05)) for elements that are interactive or currently active.
4. **Overlay:** For modals and dropdowns, use a deeper shadow (0px 8px 16px rgba(0,0,0,0.1)) to clearly separate the utility from the underlying data.

Avoid heavy blurs or vibrant shadows; the goal is to feel like paper sheets stacked neatly on a desk.

## Shapes

The design system uses a **Soft** shape language. This subtle rounding (4px default) removes the harshness of sharp corners while maintaining a precise, structured appearance.

- **Small elements:** (Buttons, Checkboxes, Inputs) use `rounded-sm` (4px).
- **Medium elements:** (Cards, Modals) use `rounded-lg` (8px).
- **Large elements:** (Full-page containers) use `rounded-xl` (12px).

Icons should follow this logic, using a 2px stroke weight and slightly rounded caps to match the UI components.

## Components

### Buttons
Primary buttons use the Brand Blue (#0077C5) with white text. Secondary buttons are outlined with a 1px border. Hover states should darken the background color by 10% rather than changing the hue.

### Input Fields
Inputs use a white background with a 1px border (#D4D7DC). On focus, the border transitions to Primary Blue with a 2px thickness or a subtle outer glow. Labels are always positioned above the field in `label-md` style for maximum accessibility.

### Cards & Functional Groups
Cards are the primary container for data. They must include a `headline-sm` title and use `md` (16px) internal padding. Group related cards with consistent margins to create "functional zones."

### Data Tables
Tables are the heart of the system. Use a zebra-striping pattern with #F8F9FA on even rows. Headers should be sticky, utilizing a light gray background and `label-md` typography. Row height is fixed at 48px for standard views and 36px for condensed views.

### Status Chips
Status indicators use a "Soft Background" approach: the background is a 10% opacity version of the status color (e.g., light green background), while the text is the full-saturation color (vibrant green) for contrast.