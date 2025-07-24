# Tailwind CSS Texture Integration Guide - 2025

A comprehensive guide for integrating texture effects with Tailwind CSS, focusing on modern approaches, best practices, and performance considerations.

## Table of Contents

1. [Tailwind CSS v4.0 Revolution](#tailwind-css-v40-revolution)
2. [Custom Tailwind Utilities for Textures](#custom-tailwind-utilities-for-textures)
3. [Extending Tailwind Config](#extending-tailwind-config)
4. [Tailwind Plugins for Texture Effects](#tailwind-plugins-for-texture-effects)
5. [Best Practices for Utility-First Approach](#best-practices-for-utility-first-approach)
6. [Performance Considerations](#performance-considerations)
7. [Modern Implementation Examples](#modern-implementation-examples)
8. [Integration with Design Systems](#integration-with-design-systems)

## Tailwind CSS v4.0 Revolution

### CSS-First Configuration

Tailwind CSS v4.0 introduces a groundbreaking CSS-first configuration approach, eliminating the need for `tailwind.config.js` files:

```css
/* styles.css - New v4 configuration approach */
@theme {
  /* Custom texture-related design tokens */
  --texture-grain: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><filter id='grain'><feTurbulence baseFrequency='0.9' /></filter></svg>");
  --texture-paper: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'><pattern id='paper'><rect fill='%23fafafa' width='100' height='100'/><circle fill='%23f0f0f0' cx='50' cy='50' r='20'/></pattern></svg>");
  
  /* Custom spacing for texture effects */
  --spacing-texture: 0.125rem;
  
  /* Custom colors for texture overlays */
  --color-texture-overlay: rgba(0, 0, 0, 0.05);
  --color-neon-lime: #32d74b;
}

/* Custom texture utilities */
@utility texture-grain {
  background-image: var(--texture-grain);
  background-repeat: repeat;
  background-size: 100px 100px;
}

@utility texture-paper {
  background-image: var(--texture-paper);
  background-repeat: repeat;
  background-size: 200px 200px;
}

@utility texture-overlay {
  position: relative;
}

@utility texture-overlay::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-texture-overlay);
  pointer-events: none;
}
```

### Enhanced Gradient Support

Tailwind v4.0 provides advanced gradient utilities perfect for texture effects:

```html
<!-- Angular gradients for texture depth -->
<div class="bg-linear-45 from-stone-100 to-stone-200 texture-grain">
  <p>Textured background with 45-degree gradient</p>
</div>

<!-- Radial gradients for spotlight effects -->
<div class="bg-radial from-white via-gray-100 to-gray-200 texture-paper">
  <p>Paper texture with radial lighting</p>
</div>

<!-- Conic gradients for dynamic textures -->
<div class="bg-conic from-amber-100 via-orange-100 to-amber-200">
  <p>Warm textured surface</p>
</div>
```

### Performance Improvements

V4.0 delivers significant performance enhancements:
- **Full rebuilds**: 3.5x faster
- **Incremental builds**: 8x faster
- **CSS variables by default**: All design tokens available at runtime

## Custom Tailwind Utilities for Textures

### Method 1: CSS-First Approach (v4.0+)

```css
/* Define texture utilities directly in CSS */
@utility texture-canvas {
  background-image: 
    radial-gradient(circle at 25% 25%, #fff 2px, transparent 2px),
    radial-gradient(circle at 75% 75%, #f8f8f8 1px, transparent 1px);
  background-size: 20px 20px;
  background-position: 0 0, 10px 10px;
}

@utility texture-fabric {
  background-image: 
    repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(0,0,0,.1) 2px, rgba(0,0,0,.1) 4px),
    repeating-linear-gradient(-45deg, transparent, transparent 2px, rgba(0,0,0,.05) 2px, rgba(0,0,0,.05) 4px);
}

@utility texture-noise {
  background-image: url("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><filter id='noise'><feTurbulence baseFrequency='0.9' numOctaves='1' result='noise'/><feColorMatrix in='noise' type='saturate' values='0'/></filter><rect width='100%' height='100%' filter='url(%23noise)' opacity='0.1'/></svg>");
}
```

### Method 2: Traditional Config (v3.x and v4.x compatible)

```javascript
// tailwind.config.js
const plugin = require('tailwindcss/plugin');

module.exports = {
  theme: {
    extend: {
      backgroundImage: {
        'texture-grain': "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><defs><filter id=\"grain\"><feTurbulence baseFrequency=\"0.9\" numOctaves=\"1\" result=\"noise\"/><feColorMatrix in=\"noise\" type=\"saturate\" values=\"0\"/></filter></defs><rect width=\"100%\" height=\"100%\" filter=\"url(%23grain)\" opacity=\"0.1\"/></svg>')",
        'texture-linen': "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><defs><pattern id=\"linen\" x=\"0\" y=\"0\" width=\"4\" height=\"4\" patternUnits=\"userSpaceOnUse\"><rect fill=\"%23ffffff\" width=\"4\" height=\"4\"/><circle fill=\"%23f8f8f8\" cx=\"2\" cy=\"2\" r=\"1\"/></pattern></defs><rect fill=\"url(%23linen)\" width=\"100%\" height=\"100%\"/></svg>')",
        'texture-concrete': "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><defs><filter id=\"concrete\"><feTurbulence baseFrequency=\"0.04\" numOctaves=\"3\" result=\"noise\"/><feColorMatrix in=\"noise\" type=\"saturate\" values=\"0\"/></filter></defs><rect width=\"100%\" height=\"100%\" filter=\"url(%23concrete)\" opacity=\"0.15\"/></svg>')"
      },
      animation: {
        'texture-shift': 'textureShift 20s linear infinite',
        'grain-move': 'grainMove 8s linear infinite',
      },
      keyframes: {
        textureShift: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '100px 100px' }
        },
        grainMove: {
          '0%': { transform: 'translate(0, 0)' },
          '25%': { transform: 'translate(-1px, -1px)' },
          '50%': { transform: 'translate(1px, -1px)' },
          '75%': { transform: 'translate(-1px, 1px)' },
          '100%': { transform: 'translate(0, 0)' }
        }
      }
    }
  },
  plugins: [
    plugin(function({ addUtilities, theme }) {
      const textureUtilities = {
        '.texture-overlay': {
          position: 'relative',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: '0',
            left: '0',
            right: '0',
            bottom: '0',
            backgroundImage: 'var(--texture-overlay-pattern, none)',
            opacity: 'var(--texture-overlay-opacity, 0.1)',
            pointerEvents: 'none',
            zIndex: '1'
          }
        },
        '.texture-layered': {
          backgroundImage: `
            ${theme('backgroundImage.texture-grain')},
            linear-gradient(45deg, transparent 25%, rgba(0,0,0,0.02) 25%, rgba(0,0,0,0.02) 50%, transparent 50%, transparent 75%, rgba(0,0,0,0.02) 75%)
          `,
          backgroundSize: '100px 100px, 20px 20px'
        }
      };
      
      addUtilities(textureUtilities);
    })
  ]
}
```

## Extending Tailwind Config

### Texture-Specific Theme Extensions

```javascript
// tailwind.config.js - Comprehensive texture configuration
module.exports = {
  theme: {
    extend: {
      // Texture-specific spacing
      spacing: {
        'texture-xs': '0.125rem',
        'texture-sm': '0.25rem',
        'texture-md': '0.5rem',
        'texture-lg': '1rem',
      },
      
      // Texture opacity scales
      opacity: {
        '2': '0.02',
        '3': '0.03',
        '4': '0.04',
        '6': '0.06',
        '8': '0.08',
      },
      
      // Texture-specific colors
      colors: {
        texture: {
          light: 'rgba(255, 255, 255, 0.1)',
          medium: 'rgba(0, 0, 0, 0.05)',
          dark: 'rgba(0, 0, 0, 0.1)',
          accent: 'rgba(59, 130, 246, 0.05)'
        }
      },
      
      // Advanced background patterns
      backgroundImage: {
        // Geometric textures
        'texture-dots': "radial-gradient(circle at 1px 1px, rgba(0,0,0,0.15) 1px, transparent 0)",
        'texture-grid': "linear-gradient(rgba(0,0,0,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.1) 1px, transparent 1px)",
        'texture-diagonal': "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.05) 10px, rgba(0,0,0,0.05) 20px)",
        
        // Organic textures
        'texture-organic': "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><defs><filter id=\"organic\"><feTurbulence baseFrequency=\"0.02\" numOctaves=\"2\" result=\"noise\"/><feDisplacementMap in=\"SourceGraphic\" in2=\"noise\" scale=\"5\"/></filter></defs><rect width=\"100%\" height=\"100%\" fill=\"%23ffffff\" filter=\"url(%23organic)\"/></svg>')",
        
        // Material textures
        'texture-metal': "linear-gradient(90deg, transparent 40%, rgba(255,255,255,0.3) 50%, transparent 60%), linear-gradient(0deg, rgba(0,0,0,0.1) 0%, transparent 50%, rgba(255,255,255,0.1) 100%)",
        'texture-glass': "linear-gradient(135deg, rgba(255,255,255,0.3) 0%, transparent 50%, rgba(255,255,255,0.1) 100%)",
      },
      
      // Background sizes for textures
      backgroundSize: {
        'texture-fine': '10px 10px',
        'texture-medium': '50px 50px',
        'texture-coarse': '100px 100px',
        'texture-large': '200px 200px',
      },
      
      // Box shadows for texture depth
      boxShadow: {
        'texture-inset': 'inset 0 1px 3px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.3)',
        'texture-raised': '0 1px 3px rgba(0,0,0,0.1), 0 1px 0 rgba(255,255,255,0.3)',
        'texture-embossed': 'inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -1px 0 rgba(0,0,0,0.1)',
      }
    }
  }
}
```

## Tailwind Plugins for Texture Effects

### Hero Patterns Integration

```javascript
// Install: npm install tailwindcss-hero-patterns
const heroPatterns = require('tailwindcss-hero-patterns');

module.exports = {
  plugins: [
    heroPatterns({
      // Specify which patterns to generate
      patterns: ['topography', 'texture', 'hideout', 'graph-paper', 'yyy', 'squares'],
      
      // Define available colors
      colors: {
        default: '#9C92AC',
        'blue-dark': '#000044',
        'gray-light': '#F0F0F0'
      },
      
      // Set opacity range
      opacity: {
        default: '0.4',
        '10': '0.1',
        '20': '0.2'
      }
    })
  ]
}
```

Usage:
```html
<div class="bg-topography-gray-light opacity-20">
  <p>Hero pattern background</p>
</div>
```

### SVG Patterns Plugin

```javascript
// Install: npm install svg-patterns-for-tailwindcss
const svgPatterns = require('svg-patterns-for-tailwindcss');

module.exports = {
  plugins: [
    svgPatterns({
      patterns: ['dots', 'vertical-lines', 'horizontal-lines', 'diagonal-lines'],
      colors: ['#000000', '#ffffff', '#f3f4f6'],
      opacity: [0.1, 0.2, 0.3]
    })
  ]
}
```

### Custom Texture Plugin

```javascript
// Custom texture plugin for advanced effects
const plugin = require('tailwindcss/plugin');

const texturePlugin = plugin(function({ addUtilities, addVariant, theme, e }) {
  // Add texture variants
  addVariant('texture-hover', '&:hover .texture-layer');
  addVariant('texture-focus', '&:focus .texture-layer');
  
  // Generate texture utilities
  const textureUtilities = {};
  
  // Material-based textures
  const materials = {
    paper: {
      pattern: "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\"><rect fill=\"%23ffffff\" width=\"100\" height=\"100\"/><circle fill=\"%23f8f8f8\" cx=\"20\" cy=\"20\" r=\"2\"/><circle fill=\"%23f8f8f8\" cx=\"80\" cy=\"80\" r=\"1\"/><circle fill=\"%23f0f0f0\" cx=\"60\" cy=\"30\" r=\"1.5\"/></svg>')",
      size: '100px 100px'
    },
    canvas: {
      pattern: "url('data:image/svg+xml;charset=UTF-8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"50\" height=\"50\"><rect fill=\"%23fafafa\" width=\"50\" height=\"50\"/><rect fill=\"%23f0f0f0\" x=\"0\" y=\"0\" width=\"1\" height=\"50\"/><rect fill=\"%23f0f0f0\" x=\"0\" y=\"0\" width=\"50\" height=\"1\"/></svg>')",
      size: '50px 50px'
    },
    fabric: {
      pattern: "repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(0,0,0,0.1) 2px, rgba(0,0,0,0.1) 4px), repeating-linear-gradient(-45deg, transparent, transparent 2px, rgba(0,0,0,0.05) 2px, rgba(0,0,0,0.05) 4px)",
      size: '20px 20px'
    }
  };
  
  Object.entries(materials).forEach(([name, config]) => {
    textureUtilities[`.texture-${name}`] = {
      backgroundImage: config.pattern,
      backgroundSize: config.size,
      backgroundRepeat: 'repeat'
    };
    
    textureUtilities[`.texture-${name}-animated`] = {
      backgroundImage: config.pattern,
      backgroundSize: config.size,
      backgroundRepeat: 'repeat',
      animation: 'textureShift 20s linear infinite'
    };
  });
  
  // Texture overlay system
  textureUtilities['.texture-overlay-system'] = {
    position: 'relative',
    '&::before': {
      content: '""',
      position: 'absolute',
      top: '0',
      left: '0',
      right: '0',
      bottom: '0',
      backgroundImage: 'var(--texture-pattern)',
      backgroundSize: 'var(--texture-size, 50px 50px)',
      opacity: 'var(--texture-opacity, 0.1)',
      pointerEvents: 'none',
      zIndex: '1'
    }
  };
  
  addUtilities(textureUtilities);
});

module.exports = {
  plugins: [texturePlugin]
}
```

## Best Practices for Utility-First Approach

### Component Abstraction with @apply

```css
/* components.css - Reusable texture components */
.card-textured {
  @apply bg-white rounded-lg shadow-lg texture-paper;
  @apply border border-gray-200;
  @apply transition-all duration-300;
}

.card-textured:hover {
  @apply shadow-xl texture-paper-animated;
}

.btn-textured {
  @apply px-4 py-2 rounded texture-fabric;
  @apply bg-blue-500 text-white;
  @apply hover:bg-blue-600 active:texture-fabric-pressed;
}

.section-textured {
  @apply relative overflow-hidden;
  @apply bg-gradient-to-br from-gray-50 to-gray-100;
  @apply texture-overlay-system;
  
  --texture-pattern: var(--texture-grain);
  --texture-opacity: 0.05;
}
```

### Semantic Texture Classes

```html
<!-- Good: Semantic and purposeful -->
<section class="hero-textured">
  <div class="card-elevated-texture">
    <h1 class="heading-embossed">Welcome</h1>
    <p class="text-on-texture">Beautiful textured backgrounds</p>
  </div>
</section>

<!-- Avoid: Too many utility classes -->
<section class="bg-gray-100 texture-grain opacity-10 relative overflow-hidden">
  <div class="bg-white rounded-lg shadow-lg texture-paper border border-gray-200 p-6">
    <h1 class="text-2xl font-bold texture-embossed">Welcome</h1>
    <p class="text-gray-700">Beautiful textured backgrounds</p>
  </div>
</section>
```

### CSS Custom Properties for Dynamic Textures

```css
.texture-dynamic {
  @apply texture-overlay-system;
  
  /* Default texture */
  --texture-pattern: var(--texture-paper);
  --texture-opacity: 0.1;
  --texture-size: 100px 100px;
}

/* Context-specific variations */
.texture-dynamic[data-theme="dark"] {
  --texture-pattern: var(--texture-grain-dark);
  --texture-opacity: 0.15;
}

.texture-dynamic[data-intensity="subtle"] {
  --texture-opacity: 0.05;
}

.texture-dynamic[data-intensity="bold"] {
  --texture-opacity: 0.2;
}
```

## Performance Considerations

### JIT Mode Optimization

```javascript
// tailwind.config.js - Performance-focused configuration
module.exports = {
  mode: 'jit', // v3.x - JIT enabled by default in v4
  content: [
    './src/**/*.{html,js,vue,ts,tsx}',
    './components/**/*.{vue,js,ts}',
    // Be specific about texture usage
    './texture-components/**/*.{vue,js,ts}'
  ],
  
  // Safelist frequently used texture classes
  safelist: [
    'texture-paper',
    'texture-grain',
    'texture-overlay',
    {
      pattern: /texture-(paper|grain|fabric)-(animated|static)/,
      variants: ['hover', 'focus', 'active']
    }
  ],
  
  theme: {
    extend: {
      // Only include textures you actually use
      backgroundImage: {
        'texture-grain': "url('...')", // Only if used
        'texture-paper': "url('...')", // Only if used
        // Remove unused textures
      }
    }
  }
}
```

### CSS Bundle Size Optimization

```javascript
// PostCSS configuration for texture optimization
module.exports = {
  plugins: [
    require('tailwindcss'),
    require('autoprefixer'),
    
    // Production optimizations
    process.env.NODE_ENV === 'production' && require('cssnano')({
      preset: ['default', {
        // Optimize SVG data URLs in textures
        svgo: {
          plugins: [
            { removeViewBox: false },
            { removeDimensions: true }
          ]
        }
      }]
    }),
    
    // Remove unused CSS
    process.env.NODE_ENV === 'production' && require('@fullhuman/postcss-purgecss')({
      content: ['./src/**/*.{vue,js,ts,jsx,tsx}'],
      defaultExtractor: content => content.match(/[\w-/:]+(?<!:)/g) || [],
      // Preserve texture-related classes
      safelist: [/^texture-/, /^bg-texture/]
    })
  ].filter(Boolean)
}
```

### Runtime Performance

```css
/* Use CSS transforms for texture animations (GPU accelerated) */
.texture-animated-optimized {
  @apply texture-grain;
  transform: translateZ(0); /* Force GPU layer */
  will-change: transform; /* Optimize for animations */
}

.texture-animated-optimized:hover {
  animation: textureShiftGPU 10s linear infinite;
}

@keyframes textureShiftGPU {
  from { transform: translateZ(0) translate(0, 0); }
  to { transform: translateZ(0) translate(100px, 100px); }
}

/* Prefer opacity changes over background changes */
.texture-fade {
  @apply texture-paper;
  transition: opacity 0.3s ease;
}

.texture-fade:hover {
  opacity: 0.8; /* Better than changing background-image */
}
```

## Modern Implementation Examples

### Advanced Texture Compositions

```html
<!-- Multi-layered texture effect -->
<div class="relative bg-gradient-to-br from-stone-100 to-stone-200">
  <!-- Base texture -->
  <div class="absolute inset-0 texture-paper opacity-20"></div>
  
  <!-- Overlay texture for depth -->
  <div class="absolute inset-0 texture-grain opacity-10 animate-grain-move"></div>
  
  <!-- Content with proper z-index -->
  <div class="relative z-10 p-8">
    <h2 class="text-3xl font-bold text-stone-800">Layered Textures</h2>
    <p class="text-stone-600">Multiple texture layers create depth</p>
  </div>
</div>
```

### Responsive Texture Systems

```html
<!-- Responsive texture scaling -->
<div class="
  texture-grain 
  bg-texture-fine sm:bg-texture-medium lg:bg-texture-coarse
  opacity-5 sm:opacity-10 lg:opacity-15
  transition-all duration-500
">
  <div class="container mx-auto px-4 py-16">
    <h1 class="text-4xl font-bold">Responsive Textures</h1>
  </div>
</div>
```

### Interactive Texture States

```html
<!-- State-based texture changes -->
<button class="
  group relative overflow-hidden
  px-6 py-3 rounded-lg
  bg-blue-500 hover:bg-blue-600
  text-white font-medium
  transition-all duration-300
">
  <!-- Default texture -->
  <div class="
    absolute inset-0 texture-fabric 
    opacity-0 group-hover:opacity-20
    transition-opacity duration-300
  "></div>
  
  <!-- Active state texture -->
  <div class="
    absolute inset-0 texture-metal
    opacity-0 group-active:opacity-30
    transition-opacity duration-150
  "></div>
  
  <span class="relative z-10">Textured Button</span>
</button>
```

### CSS Grid with Textured Backgrounds

```html
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
  <div class="bg-white texture-paper rounded-lg p-6 shadow-lg">
    <h3 class="font-bold mb-2">Paper Texture</h3>
    <p>Subtle organic texture</p>
  </div>
  
  <div class="bg-gray-50 texture-linen rounded-lg p-6 shadow-lg">
    <h3 class="font-bold mb-2">Linen Texture</h3>
    <p>Fabric-like appearance</p>
  </div>
  
  <div class="bg-stone-100 texture-concrete rounded-lg p-6 shadow-lg">
    <h3 class="font-bold mb-2">Concrete Texture</h3>
    <p>Industrial surface feel</p>
  </div>
</div>
```

## Integration with Design Systems

### Design Token Structure

```javascript
// design-tokens.js - Systematic texture approach
export const textureTokens = {
  surfaces: {
    paper: {
      pattern: 'texture-paper',
      opacity: 'opacity-10',
      color: 'bg-white',
      shadow: 'shadow-sm'
    },
    canvas: {
      pattern: 'texture-canvas',
      opacity: 'opacity-15',
      color: 'bg-gray-50',
      shadow: 'shadow-md'
    },
    fabric: {
      pattern: 'texture-fabric',
      opacity: 'opacity-20',
      color: 'bg-stone-100',
      shadow: 'shadow-lg'
    }
  },
  
  elevation: {
    base: 'texture-overlay opacity-5',
    raised: 'texture-overlay opacity-10 shadow-md',
    floating: 'texture-overlay opacity-15 shadow-xl'
  },
  
  interaction: {
    hover: 'hover:texture-grain-animated hover:opacity-80',
    active: 'active:texture-pressed active:scale-95',
    focus: 'focus:ring-2 focus:ring-blue-500 focus:texture-highlight'
  }
};
```

### Component Library Integration

```vue
<!-- TexturedCard.vue - Design system component -->
<template>
  <div 
    :class="[
      'relative overflow-hidden rounded-lg transition-all duration-300',
      textureClass,
      elevationClass,
      interactionClass
    ]"
  >
    <!-- Texture layer -->
    <div 
      :class="[
        'absolute inset-0 pointer-events-none',
        texturePattern,
        textureOpacity
      ]"
    ></div>
    
    <!-- Content -->
    <div class="relative z-10 p-6">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  surface?: 'paper' | 'canvas' | 'fabric';
  elevation?: 'base' | 'raised' | 'floating';
  interactive?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  surface: 'paper',
  elevation: 'base',
  interactive: false
});

const textureClass = computed(() => {
  const surfaces = {
    paper: 'bg-white',
    canvas: 'bg-gray-50', 
    fabric: 'bg-stone-100'
  };
  return surfaces[props.surface];
});

const texturePattern = computed(() => {
  const patterns = {
    paper: 'texture-paper',
    canvas: 'texture-canvas',
    fabric: 'texture-fabric'
  };
  return patterns[props.surface];
});

const textureOpacity = computed(() => {
  const opacities = {
    paper: 'opacity-10',
    canvas: 'opacity-15',
    fabric: 'opacity-20'
  };
  return opacities[props.surface];
});

const elevationClass = computed(() => {
  const elevations = {
    base: 'shadow-sm',
    raised: 'shadow-md',
    floating: 'shadow-xl'
  };
  return elevations[props.elevation];
});

const interactionClass = computed(() => {
  return props.interactive 
    ? 'hover:shadow-lg hover:scale-105 cursor-pointer'
    : '';
});
</script>
```

### Usage in Design System

```html
<!-- Design system usage examples -->
<TexturedCard surface="paper" elevation="raised" :interactive="true">
  <h3 class="font-bold text-lg mb-2">Paper Surface</h3>
  <p class="text-gray-600">Interactive card with paper texture</p>
</TexturedCard>

<TexturedCard surface="canvas" elevation="floating">
  <h3 class="font-bold text-lg mb-2">Canvas Surface</h3>
  <p class="text-gray-600">Elevated card with canvas texture</p>
</TexturedCard>

<TexturedCard surface="fabric" elevation="base">
  <h3 class="font-bold text-lg mb-2">Fabric Surface</h3>
  <p class="text-gray-600">Base elevation with fabric texture</p>
</TexturedCard>
```

## Conclusion

Tailwind CSS v4.0's CSS-first approach revolutionizes texture implementation, offering:

- **Performance**: 8x faster incremental builds
- **Flexibility**: CSS variables and custom utilities
- **Modern CSS**: Advanced gradients and effects
- **Maintainability**: Systematic design token approach
- **Scalability**: Plugin ecosystem and custom implementations

The utility-first philosophy remains intact while providing powerful tools for creating sophisticated texture effects that enhance user experience without compromising performance.

### Key Takeaways

1. **Use CSS-first configuration** for v4.0+ projects
2. **Leverage plugins** for common texture patterns
3. **Optimize for performance** with JIT mode and purging
4. **Create reusable components** with @apply directive
5. **Implement systematic design tokens** for consistency
6. **Consider runtime performance** for animations
7. **Maintain utility-first principles** while creating abstractions

This approach ensures your texture implementations are modern, performant, and maintainable while fully embracing Tailwind's utility-first philosophy.