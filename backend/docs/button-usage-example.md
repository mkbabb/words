# Button Component Usage Examples

## Improved Button Implementation

The Button component has been refactored to use our design system utilities for consistency and simplicity.

### Key Improvements
- Uses `hover-lift` utility for consistent hover effects
- Implements `focus-ring` for accessibility
- Cleaner, more readable base classes
- Consistent shadow system with `shadow-subtle`
- Link variant uses `hover-text-grow` for text enlargement

### Usage Examples

```vue
<!-- Primary Button -->
<Button>Search</Button>

<!-- Secondary Button -->
<Button variant="secondary">Cancel</Button>

<!-- Outline Button -->
<Button variant="outline">Options</Button>

<!-- Destructive Button -->
<Button variant="destructive">Delete</Button>

<!-- Ghost Button (no background) -->
<Button variant="ghost">
  <Settings class="h-4 w-4 mr-2" />
  Settings
</Button>

<!-- Link Button -->
<Button variant="link">Learn more</Button>

<!-- Size Variants -->
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>

<!-- Icon Button -->
<Button size="icon" variant="ghost">
  <X class="h-4 w-4" />
</Button>

<!-- Disabled State -->
<Button disabled>Disabled</Button>
```

### Migration Guide

#### Before
```vue
<button class="inline-flex items-center justify-center rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-200 hover:scale-105 hover:brightness-95 focus-visible:ring-1 focus-visible:outline-none active:scale-95 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 shadow h-9 px-4 py-2">
  Click me
</button>
```

#### After
```vue
<Button>Click me</Button>
```

### Dark Mode Support
All button variants automatically adapt to dark mode using CSS variables:
- Background colors adjust appropriately
- Text colors maintain proper contrast
- Shadows remain subtle but visible

### Accessibility Features
- Focus ring with proper offset for keyboard navigation
- Disabled state with reduced opacity
- Proper ARIA attributes inherited from base button element
- Minimum touch target size (44px) maintained