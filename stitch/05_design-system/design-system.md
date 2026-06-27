---
name: Liquid Glass
colors:
  surface: '#12121f'
  surface-dim: '#12121f'
  surface-bright: '#383847'
  surface-container-lowest: '#0d0d1a'
  surface-container-low: '#1a1a28'
  surface-container: '#1e1e2c'
  surface-container-high: '#292937'
  surface-container-highest: '#343342'
  on-surface: '#e3e0f4'
  on-surface-variant: '#ccc3d8'
  inverse-surface: '#e3e0f4'
  inverse-on-surface: '#2f2f3d'
  outline: '#958da1'
  outline-variant: '#4a4455'
  surface-tint: '#d2bbff'
  primary: '#d2bbff'
  on-primary: '#3f008e'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#732ee4'
  secondary: '#4cd7f6'
  on-secondary: '#003640'
  secondary-container: '#03b5d3'
  on-secondary-container: '#00424e'
  tertiary: '#ffb784'
  on-tertiary: '#4f2500'
  tertiary-container: '#a15100'
  on-tertiary-container: '#ffe0cd'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#acedff'
  secondary-fixed-dim: '#4cd7f6'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5c'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#12121f'
  on-background: '#e3e0f4'
  surface-variant: '#343342'
  background-start: '#0D0D1A'
  background-end: '#1A0A2E'
  success-emerald: '#10B981'
  text-primary: '#F1F0FF'
  text-muted: '#9991CC'
  glass-fill: rgba(255, 255, 255, 0.06)
  glass-stroke: rgba(255, 255, 255, 0.12)
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.12em
  label-xs:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.15em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  lg: 0.75rem
  xl: 1rem
  2xl: 1.5rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
The design system embodies a "Sci-Fi Command Center" aesthetic, tailored for a high-end AI writing platform. It targets professionals and creatives who seek a premium, immersive environment that feels both cutting-edge and effortless.

The visual style is a sophisticated blend of **Glassmorphism** and **Modern Corporate**, utilizing deep radial gradients to create infinite depth. Surfaces are treated as "wet frosted acrylic"—highly translucent, luminous, and ethereal. The emotional response should be one of focused calm, technical precision, and futuristic intelligence. Interactions are not just functional; they are "springy" and physical, mimicking high-end hardware interfaces.

## Colors
The palette is rooted in a deep, nocturnal base of indigo and violet.

- **Primary Electric Violet**: Used for primary actions, focus states, and AI-driven highlights.
- **Secondary Cyan-Teal**: Used for data visualization, accent strokes, and interactive feedback.
- **Background**: A radial gradient starting from `#0D0D1A` at the center to `#1A0A2E` at the edges.
- **Surface**: All containers use the `glass-fill` with a heavy backdrop blur.
- **Typography**: `text-primary` is slightly off-white to reduce eye strain against the dark background, while `text-muted` pulls in violet undertones for harmony.

## Typography
The system uses **Sora** (as a high-quality alternative for modern tech headlines) to provide a geometric, futuristic feel. **Inter** is utilized for all functional UI elements and body copy to ensure maximum legibility within the "liquid glass" containers.

A critical signature of the design system is the treatment of labels: all `label` roles must utilize wide letter-spacing and uppercase styling to evoke a "technical readout" or HUD aesthetic. Headlines should remain tight and bold to contrast against the airy, translucent backgrounds.

## Layout & Spacing
This design system employs a **fluid grid** model with generous safe areas to maintain the premium feel.

- **Desktop**: 12-column grid with 24px gutters. Content is capped at 1280px to prevent excessive line lengths in the writing interface.
- **Mobile**: 4-column grid with 16px margins.
- **Rhythm**: All spacing follows an 8px base unit.
- **Layout Philosophy**: Elements should feel "floating." Use dynamic padding within glass cards (typically 24px or 32px) to ensure content doesn't feel cramped against the frosted edges.

## Elevation & Depth
Depth is not communicated through traditional black shadows, but through **Tonal Layers** and **Backdrop Blurs**.

- **Base Level**: The deep radial gradient background.
- **Surface Level (Cards)**: `rgba(255, 255, 255, 0.06)` background with a `24px` backdrop-filter blur.
- **Borders**: 1px solid `rgba(255, 255, 255, 0.12)`. For higher-tier elements, use a "top-light" border—a linear gradient on the stroke from semi-transparent white at the top to transparent at the bottom.
- **Overlays (Modals/Popovers)**: Increased backdrop blur (`40px`) and a subtle outer glow using the primary color (`#7C3AED`) at 10% opacity to simulate light emitting from the glass.

## Shapes
The shape language is sophisticated and modern. All glass containers and primary UI elements use a **0.5rem (8px)** base radius.

Large sections or "Master Containers" (like the main text editor area) should use `rounded-2xl` (1.5rem) to emphasize the soft, "liquid" nature of the design. Interactive components like buttons should maintain the standard `rounded` (0.5rem) setting to feel precise and clickable.

## Components
- **Buttons**: Primary buttons use a solid Electric Violet to Cyan-Teal gradient. Secondary buttons use the glass style with a 1px border. All buttons should have a `0.2s cubic-bezier(0.34, 1.56, 0.64, 1)` transition for a "springy" feel on hover.
- **Input Fields**: Ghost-style inputs with `glass-fill`. On focus, the border color shifts to Cyan-Teal with a subtle inner glow.
- **Glass Cards**: The foundational component. Always include a 1px inner-light border and 24px blur.
- **Chips**: Pill-shaped with a low-opacity Electric Violet background (`rgba(124, 58, 237, 0.2)`). Labels inside must use the `label-xs` typography.
- **Progress Indicators**: Use glowing Cyan-Teal lines. Avoid solid blocks; use gradients that imply movement.
- **Writing Area**: The main canvas should be a large glass pane with a "focused" state that dims the rest of the UI, intensifying the backdrop blur of background elements.
