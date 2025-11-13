# Home Page Design System

This document defines the design system used by the home page of the Portfolio Management System application.

## Table of Contents

1. [Overview](#overview)
2. [Color Palette](#color-palette)
3. [Typography](#typography)
4. [Layout & Spacing](#layout--spacing)
5. [Components](#components)
6. [Interactions & Animations](#interactions--animations)
7. [Responsive Design](#responsive-design)

## Overview

The home page design system follows a clean, modern aesthetic inspired by Apple's design language, emphasizing clarity, simplicity, and usability. The layout uses a two-column grid structure with a fixed sidebar and flexible content area.

### Design Principles

- **Clarity**: Clear visual hierarchy and readable typography
- **Consistency**: Uniform spacing, colors, and component patterns
- **Accessibility**: High contrast ratios and readable font sizes
- **Responsiveness**: Mobile-first approach with desktop enhancements
- **Smooth Interactions**: Subtle animations and transitions for better UX

## Color Palette

### Primary Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Primary Blue | `#0071e3` | Primary buttons, active states, links |
| Primary Blue Hover | `#0077ed` | Button hover states |
| Primary Blue Light | `#e8f4fd` | Selected item backgrounds, active link backgrounds |
| Primary Blue Light Hover | `#d9edfc` | Selected item hover states |

### Neutral Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Background | `#f5f5f7` | Main page background |
| White | `#ffffff` | Card backgrounds, sidebar backgrounds |
| Text Primary | `#1d1d1f` | Main text, headings |
| Text Secondary | `#86868b` | Secondary text, labels, placeholders |
| Border | `#e5e5e7` | Borders, dividers |
| Border Hover | `#d2d2d7` | Border hover states |

### Semantic Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Error | `#d70015` | Error messages, error states |
| Error Background | `#fff5f5` | Error container backgrounds |
| Error Border | `#ffebee` | Error container borders |
| Success Positive | `#007bff` | Positive values, success states |
| Gray Button | `#3c4d65` | Secondary buttons |
| Gray Button Hover | `#4a5e7a` | Secondary button hover |

### Additional Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Modal Overlay | `rgba(0, 0, 0, 0.5)` | Modal backdrop |
| Header Background | `rgba(255, 255, 255, 0.8)` | Header with backdrop blur |
| Shadow | `rgba(0, 0, 0, 0.1)` | Box shadows |
| Shadow Blue | `rgba(0, 113, 227, 0.3)` | Blue-tinted shadows |
| Shadow Blue Light | `rgba(0, 113, 227, 0.1)` | Light blue shadows |

## Typography

### Font Family

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
```

The application uses the system font stack for optimal performance and native feel across platforms.

### Font Smoothing

```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

### Type Scale

| Element | Font Size | Font Weight | Line Height | Letter Spacing | Color |
|---------|-----------|-------------|-------------|----------------|-------|
| H1 (Header) | `1.25rem` (mobile)<br>`1.5rem` (desktop) | `600` | `1.1` | `-0.02em` | `#1d1d1f` |
| H2 (Section) | `2rem` | `600` | `1.1` | `-0.02em` | `#1d1d1f` |
| H3 (Subsection) | `1.3rem` | `600` | `1.3` | `-0.01em` | `#555` |
| Body Text | `0.9375rem` | `400` | `1.4` | `0` | `#1d1d1f` |
| Secondary Text | `0.8125rem` | `400` | `1.4` | `0` | `#86868b` |
| Small Text | `0.875rem` | `400` | `1.4` | `0` | `#666` |
| Button Text | `0.9375rem` | `500` | `1` | `0` | Varies |
| Navigation Link | `0.9375rem` | `500` | `1` | `0` | `#1d1d1f` |
| Fallback Text | `1.15rem` (mobile)<br>`1.5rem` (desktop) | `400` | `1.4` | `0` | `#86868b` |

### Text Wrapping

```css
text-wrap: balance;
```

Used for headings to improve readability.

## Layout & Spacing

### Grid System

The main layout uses a CSS Grid system:

**Mobile (< 768px):**
- Single column layout
- Stacked components vertically

**Desktop (≥ 768px):**
- Two-column grid: `380px` (sidebar) + `1fr` (content)
- Sidebar fixed width, content area flexible

```css
main {
  display: grid;
  grid-auto-flow: row; /* Mobile */
}

@media (min-width: 768px) {
  main {
    grid-template-columns: 380px 1fr;
  }
}
```

### Spacing Scale

| Size | Value | Usage |
|------|-------|-------|
| XS | `0.25rem` (4px) | Tight spacing, form gaps |
| SM | `0.5rem` (8px) | Small gaps, icon spacing |
| MD | `1rem` (16px) | Standard spacing, component gaps |
| LG | `1.5rem` (24px) | Section spacing, form groups |
| XL | `2rem` (32px) | Large sections, container padding |
| XXL | `3rem` (48px) | Extra large spacing, empty states |

### Border Radius

| Size | Value | Usage |
|------|-------|-------|
| Small | `4px` | Input fields, small buttons |
| Medium | `8px` | Cards, navigation links |
| Large | `12px` | Buttons, user items, cards |
| Extra Large | `50%` | Avatars, circular elements |

### Padding & Margins

**Header:**
- Mobile: `1rem 2rem`
- Desktop: `1.25rem 2rem`

**Sidebar (User List):**
- Header: `2rem 1.5rem 1.5rem 1.5rem`
- Content: `1rem`
- Item: `1rem`

**Content Area:**
- Container: `2rem` (mobile), `6rem 4rem` (desktop fallback)
- Sections: `1.5rem` (cards), `2rem` (between sections)

## Components

### Header Component

**Structure:**
- Sticky positioning (`position: sticky`, `top: 0`, `z-index: 100`)
- Backdrop blur effect (`backdrop-filter: saturate(180%) blur(20px)`)
- Semi-transparent white background (`rgba(255, 255, 255, 0.8)`)
- Bottom border (`1px solid #e5e5e7`)

**Navigation Links:**
- Padding: `0.5rem 1rem`
- Border radius: `8px`
- Transition: `all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`
- Hover: Background `#f5f5f7`, color `#0071e3`
- Active: Background `#e8f4fd`, color `#0071e3`

### User List Component

**Container:**
- Background: `#ffffff`
- Border right: `1px solid #e5e5e7`
- Height: `100%`
- Display: `flex`, `flex-direction: column`
- Overflow: `hidden`

**Header Section:**
- Border bottom: `1px solid #e5e5e7`
- Padding: `2rem 1.5rem 1.5rem 1.5rem`

**User Grid:**
- Display: `flex`, `flex-direction: column`
- Gap: `0.5rem`
- Padding: `1rem`
- Overflow-y: `auto`
- Flex: `1` (fills remaining space)

### User Item Component

**Structure:**
- Display: `flex`, `align-items: center`
- Gap: `1rem`
- Padding: `1rem`
- Border radius: `12px`
- Background: `transparent` (default)
- Transition: `all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`

**States:**
- Hover: Background `#f5f5f7`, transform `translateX(2px)`
- Selected: Background `#e8f4fd`, box-shadow `0 1px 3px rgba(0, 113, 227, 0.1)`
- Selected Hover: Background `#d9edfc`

**Avatar:**
- Size: `56px × 56px`
- Border radius: `50%`
- Border: `2px solid #e5e5e7`
- Selected border: `#0071e3`
- Object-fit: `cover`

**User Info:**
- Flex: `1`
- Min-width: `0` (for text truncation)
- Text overflow: `ellipsis`
- White-space: `nowrap`

### Primary Button

**Base Styles:**
- Padding: `0.625rem 1.25rem`
- Border: `none`
- Border radius: `12px`
- Font size: `0.9375rem`
- Font weight: `500`
- Display: `inline-flex`
- Align items: `center`
- Justify content: `center`
- White-space: `nowrap`
- Transition: `all 0.2s cubic-bezier(0.4, 0, 0.2, 1)`

**Primary Variant:**
- Background: `#0071e3`
- Color: `white`
- Box-shadow: `0 1px 3px rgba(0, 0, 0, 0.1)`

**Hover State:**
- Background: `#0077ed`
- Box-shadow: `0 2px 6px rgba(0, 113, 227, 0.3)`
- Transform: `translateY(-1px)`

**Active State:**
- Transform: `translateY(0)`
- Box-shadow: `0 1px 3px rgba(0, 0, 0, 0.1)`

### Secondary Button (Back Button)

**Styles:**
- Background: `#3c4d65`
- Color: `white`
- Border: `none`
- Border radius: `0.5rem`
- Font size: `1rem`
- Padding: `0.75rem 1.5rem`
- Margin bottom: `1.5rem`
- Transition: `background-color 0.2s`

**Hover:**
- Background: `#4a5e7a`

### Create User Modal

**Overlay:**
- Position: `fixed`
- Full viewport coverage
- Background: `rgba(0, 0, 0, 0.5)`
- Display: `flex`
- Align items: `center`
- Justify content: `center`
- Z-index: `1000`

**Modal Content:**
- Background: `white`
- Border radius: `8px`
- Width: `90%`
- Max width: `600px`
- Max height: `90vh`
- Overflow-y: `auto`
- Box-shadow: `0 4px 20px rgba(0, 0, 0, 0.3)`

**Modal Header:**
- Display: `flex`
- Justify content: `space-between`
- Align items: `center`
- Padding: `1.5rem`
- Border bottom: `1px solid #e0e0e0`

**Close Button:**
- Background: `none`
- Border: `none`
- Font size: `2rem`
- Color: `#666`
- Size: `32px × 32px`
- Border radius: `4px`
- Hover: Background `#f0f0f0`

**Form:**
- Padding: `1.5rem`

**Form Group:**
- Margin bottom: `1.5rem`

**Form Label:**
- Display: `block`
- Margin bottom: `0.5rem`
- Font weight: `500`
- Color: `#333`

**Form Input:**
- Width: `100%`
- Padding: `0.75rem`
- Border: `1px solid #ddd`
- Border radius: `4px`
- Font size: `1rem`
- Box-sizing: `border-box`

**Error State:**
- Border color: `#dc3545`
- Error message: `#dc3545`, `0.875rem`, margin top `0.25rem`

**Form Actions:**
- Display: `flex`
- Gap: `1rem`
- Justify content: `flex-end`
- Margin top: `2rem`

### Portfolio Component

**Container:**
- Padding: `2rem`
- Max width: `1400px`
- Margin: `0 auto`

**Sections:**
- Background: `white`
- Border radius: `8px`
- Box-shadow: `0 2px 4px rgba(0, 0, 0, 0.1)`
- Padding: `1.5rem`
- Margin bottom: `2rem`

**Summary Cards:**
- Display: `flex`
- Gap: `1rem`
- Margin bottom: `1.5rem`

**Summary Card:**
- Flex: `1`
- Padding: `1rem`
- Background: `#f8f9fa`
- Border radius: `6px`
- Border left: `4px solid #007bff`
- Display: `flex`
- Flex direction: `column`
- Gap: `0.5rem`

**Card Label:**
- Font size: `0.9rem`
- Color: `#666`

**Card Value:**
- Font size: `1.5rem`
- Font weight: `bold`
- Color: `#333`

### Empty States

**Loading/Empty:**
- Text align: `center`
- Padding: `3rem 1.5rem`
- Color: `#86868b`
- Font size: `0.9375rem`

**Error State:**
- Color: `#d70015`
- Background: `#fff5f5`
- Border: `1px solid #ffebee`
- Border radius: `12px`
- Margin: `1rem`
- Padding: `1rem`
- Display: `flex`
- Flex direction: `column`
- Gap: `1rem`
- Align items: `center`

### Fallback Message

**Styles:**
- Font weight: `400`
- Font size: `1.15rem` (mobile) / `1.5rem` (desktop)
- Margin: `0`
- Text align: `center` (mobile) / `left` (desktop)
- Color: `#86868b`
- Padding: `4rem 2rem` (mobile) / `6rem 4rem` (desktop)

## Interactions & Animations

### Transitions

**Standard Transition:**
```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
```

**Background Transition:**
```css
transition: background-color 0.2s;
```

**Border Transition:**
```css
transition: border-color 0.2s;
```

### Hover Effects

**Buttons:**
- Background color change
- Box-shadow enhancement
- Transform: `translateY(-1px)` (primary buttons)
- Transform: `translateX(2px)` (user items)

**Links:**
- Background color change
- Color change to primary blue

**User Items:**
- Background color change
- Border color change (avatar)
- Transform: `translateX(2px)`

### Active States

**Buttons:**
- Transform reset to `translateY(0)`
- Box-shadow reduction

**Selected Items:**
- Distinct background color
- Border color change
- Box-shadow for depth

## Responsive Design

### Breakpoint

**Primary Breakpoint:** `768px`

### Mobile (< 768px)

**Layout:**
- Single column layout
- Stacked components
- Full-width elements

**Header:**
- Vertical flex layout
- Centered alignment
- Padding: `1rem 2rem`

**Typography:**
- H1: `1.25rem`
- Fallback text: `1.15rem`
- Centered text alignment

**Spacing:**
- Reduced padding
- Tighter gaps

### Desktop (≥ 768px)

**Layout:**
- Two-column grid (`380px` + `1fr`)
- Side-by-side components

**Header:**
- Horizontal flex layout
- Space-between alignment
- Padding: `1.25rem 2rem`

**Typography:**
- H1: `1.5rem`
- Fallback text: `1.5rem`
- Left-aligned text

**Spacing:**
- Increased padding
- Larger gaps

## Accessibility

### Color Contrast

- Text on white: `#1d1d1f` (WCAG AAA compliant)
- Text on gray: `#86868b` (WCAG AA compliant)
- Primary blue on white: `#0071e3` (WCAG AA compliant)

### Focus States

Buttons and interactive elements should have visible focus indicators (not currently defined in CSS, but should be added).

### Semantic HTML

- Proper heading hierarchy (h1 → h2 → h3)
- Semantic form elements
- ARIA labels where appropriate

## Usage Guidelines

### When to Use Primary Blue

- Primary actions (Create, Submit, Save)
- Active navigation states
- Selected items
- Links
- Important highlights

### When to Use Gray Scale

- Secondary actions
- Disabled states
- Borders and dividers
- Secondary text
- Backgrounds

### When to Use Error Colors

- Error messages
- Invalid form inputs
- Critical alerts
- Failed operations

### Spacing Guidelines

- Use consistent spacing scale
- Maintain visual rhythm
- Group related elements
- Separate distinct sections

### Component Guidelines

- Follow established component patterns
- Maintain consistent styling
- Use semantic HTML
- Ensure accessibility

## Future Enhancements

1. **Dark Mode Support**: Add dark mode color palette
2. **Focus States**: Define consistent focus indicators
3. **Loading States**: Standardize loading spinners and skeletons
4. **Toast Notifications**: Define notification component styles
5. **Tooltips**: Add tooltip component styles
6. **Data Tables**: Standardize table component styles
7. **Form Validation**: Enhance error state styling
8. **Icon System**: Document icon usage and sizing

