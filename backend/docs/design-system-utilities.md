# Design System Utilities Reference

## Typography Classes

### Font Families
- `font-sans` - System font stack for body text
- `font-serif` - Fraunces for headings and emphasis
- `font-mono` - Fira Code for technical content

### Usage Examples
```vue
<!-- Heading with serif font -->
<h1 class="font-serif text-3xl font-bold">Dictionary</h1>

<!-- Code or pronunciation with monospace -->
<span class="font-mono text-sm">/prəˌnʌnsiˈeɪʃən/</span>

<!-- Body text with system font -->
<p class="font-sans text-base">Definition content here...</p>
```

## Hover Effects

### Interactive Elements
- `hover-lift` - Scale 1.02x + slight darkening (primary interactions)
- `hover-lift-sm` - Scale 1.01x + subtle darkening (secondary interactions)
- `hover-text-grow` - Text grows by 2% on hover
- `hover-shadow-lift` - Elevates shadow on hover

### Usage Examples
```vue
<!-- Primary button -->
<button class="hover-lift bg-primary text-white px-4 py-2 rounded">
  Search
</button>

<!-- Card with shadow lift -->
<div class="shadow-card hover-shadow-lift rounded-lg p-4">
  Card content
</div>

<!-- Link with text growth -->
<a href="#" class="hover-text-grow text-primary">
  Learn more
</a>
```

## Shadow Utilities
- `shadow-card` - Standard card shadow
- `shadow-card-hover` - Elevated card shadow
- `shadow-subtle` - Very light shadow
- `shadow-glow` - Primary color glow effect

## Focus States
- `focus-ring` - Consistent focus ring for accessibility

## Transition Helper
- `transition-smooth` - Standard 200ms ease-in-out transition

## Migration Guide

### Before (Custom CSS)
```css
.text-word-title {
  font-family: 'Fraunces', serif;
  /* other styles */
}
```

### After (Tailwind Utilities)
```vue
<h1 class="font-serif text-2xl font-bold">Title</h1>
```

### Before (Inline Hover)
```vue
<button :class="{ 'transform scale-105': isHovered }">
```

### After (Hover Utility)
```vue
<button class="hover-lift">
```

## Best Practices

1. **Consistency**: Use the same hover effect for similar interactions
2. **Hierarchy**: Use `hover-lift` for primary actions, `hover-lift-sm` for secondary
3. **Typography**: Always use font utilities instead of custom CSS
4. **Transitions**: Include transition utilities with interactive elements
5. **Dark Mode**: These utilities work with Tailwind's dark mode automatically