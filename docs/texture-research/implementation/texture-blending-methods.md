# Texture Blending Methods for Web Applications (2025)

A comprehensive guide to modern texture blending techniques, CSS blend modes, and performance optimization for creating sophisticated visual effects in web applications.

## Table of Contents

1. [CSS Blend Modes](#css-blend-modes)
2. [Multiple Texture Layering Techniques](#multiple-texture-layering-techniques)
3. [Opacity and Masking](#opacity-and-masking)
4. [CSS Filters for Texture Enhancement](#css-filters-for-texture-enhancement)
5. [JavaScript Libraries for Advanced Blending](#javascript-libraries-for-advanced-blending)
6. [Performance Optimization](#performance-optimization)
7. [Realistic Paper-Like Effects](#realistic-paper-like-effects)
8. [Browser Support and Compatibility](#browser-support-and-compatibility)

## CSS Blend Modes

CSS blend modes allow you to control how an element's content blends with its background and parent elements. Two primary properties enable this functionality:

- `mix-blend-mode`: Blends an element's content with its parent and background
- `background-blend-mode`: Blends an element's background images with each other and background color

### Core Blend Modes for Texture Effects

#### Multiply
Creates darker colors by multiplying top and bottom color values. Perfect for adding shadows and depth to textures.

```css
.texture-multiply {
  background-image: url('paper-texture.jpg'), url('grain-texture.jpg');
  background-blend-mode: multiply;
}

.overlay-multiply {
  mix-blend-mode: multiply;
  background: rgba(0, 0, 0, 0.3);
}
```

#### Overlay
Combines multiply and screen modes - darkens dark colors and lightens light colors, creating high contrast effects.

```css
.texture-overlay {
  background-image: url('base-texture.jpg');
  background-blend-mode: overlay;
  background-color: #f4f4f4;
}

.element-overlay {
  mix-blend-mode: overlay;
  background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
}
```

#### Soft-Light
A gentler version of overlay, providing subtle texture enhancement without harsh contrasts.

```css
.subtle-texture {
  background-image: url('paper.jpg'), url('noise.png');
  background-blend-mode: soft-light;
  background-size: cover, 200px;
}
```

#### Screen
Inverts colors, multiplies them, then inverts again, creating lighter effects similar to projecting images.

```css
.light-texture {
  background-image: url('dark-texture.jpg');
  background-blend-mode: screen;
  background-color: #ffffff;
}
```

### Complete Blend Mode Reference

```css
.blend-modes-demo {
  /* Available blend modes */
  mix-blend-mode: normal;        /* Default */
  mix-blend-mode: multiply;      /* Darker colors */
  mix-blend-mode: screen;        /* Lighter colors */
  mix-blend-mode: overlay;       /* High contrast */
  mix-blend-mode: darken;        /* Keep darker pixels */
  mix-blend-mode: lighten;       /* Keep lighter pixels */
  mix-blend-mode: color-dodge;   /* Brightens background */
  mix-blend-mode: color-burn;    /* Darkens background */
  mix-blend-mode: hard-light;    /* Strong contrast */
  mix-blend-mode: soft-light;    /* Gentle contrast */
  mix-blend-mode: difference;    /* Subtracts colors */
  mix-blend-mode: exclusion;     /* Similar to difference, lower contrast */
  mix-blend-mode: hue;          /* Preserves hue */
  mix-blend-mode: saturation;   /* Preserves saturation */
  mix-blend-mode: color;        /* Preserves color */
  mix-blend-mode: luminosity;   /* Preserves luminosity */
}
```

## Multiple Texture Layering Techniques

Modern CSS supports sophisticated layering through multiple backgrounds and advanced positioning.

### Multi-Background Layering

```css
.layered-texture {
  background-image: 
    url('noise-overlay.png'),     /* Top layer */
    url('paper-grain.jpg'),       /* Middle layer */
    url('base-paper.jpg');        /* Bottom layer */
  
  background-size: 
    100px 100px,                  /* Tiled noise */
    cover,                        /* Full grain */
    cover;                        /* Full base */
  
  background-repeat: 
    repeat,
    no-repeat,
    no-repeat;
  
  background-blend-mode: 
    overlay,                      /* Noise overlay */
    multiply,                     /* Grain multiply */
    normal;                       /* Base normal */
}
```

### Advanced Layering with Pseudo-Elements

```css
.complex-texture {
  position: relative;
  background: url('base-texture.jpg') center/cover;
}

.complex-texture::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url('grain-texture.png') repeat;
  mix-blend-mode: multiply;
  opacity: 0.7;
  z-index: 1;
}

.complex-texture::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, transparent 30%, rgba(0,0,0,0.1) 100%);
  mix-blend-mode: overlay;
  z-index: 2;
}
```

### Dynamic Layer Management

```css
.dynamic-layers {
  --layer-opacity: 0.8;
  --blend-mode: multiply;
  
  background-image: 
    var(--texture-overlay, url('overlay.png')),
    var(--texture-base, url('base.jpg'));
  
  background-blend-mode: var(--blend-mode), normal;
}

/* CSS Custom Properties for runtime control */
.dynamic-layers[data-theme="dark"] {
  --layer-opacity: 0.9;
  --blend-mode: screen;
  --texture-overlay: url('dark-overlay.png');
}
```

## Opacity and Masking

CSS masking provides precise control over texture visibility and blending through alpha channels and luminance.

### Alpha Masking

```css
.alpha-masked-texture {
  background: url('paper-texture.jpg') center/cover;
  mask: radial-gradient(circle, black 40%, transparent 70%);
  -webkit-mask: radial-gradient(circle, black 40%, transparent 70%);
}

.gradient-mask {
  background: url('wood-texture.jpg');
  mask: linear-gradient(to bottom, black 0%, transparent 100%);
  -webkit-mask: linear-gradient(to bottom, black 0%, transparent 100%);
}
```

### Luminance Masking

```css
.luminance-mask {
  background: url('base-texture.jpg');
  mask: url('mask-image.png') luminance;
  mask-mode: luminance;
  -webkit-mask: url('mask-image.png') luminance;
}
```

### Multiple Mask Layers

```css
.multi-mask {
  background: url('complex-texture.jpg');
  mask: 
    radial-gradient(circle at 30% 30%, black 20%, transparent 50%),
    linear-gradient(45deg, black 0%, transparent 100%),
    url('custom-mask.svg');
  
  mask-composite: intersect;
  -webkit-mask-composite: source-in;
}
```

### Opacity Optimization Formula

For multiple semitransparent layers, you can optimize performance by combining layers mathematically:

```css
/* Instead of multiple layers with individual opacities */
.inefficient {
  background: rgba(255, 255, 255, 0.3);
}
.inefficient::before {
  background: rgba(0, 0, 0, 0.2);
}

/* Use calculated equivalent opacity: a0 + a1 - (a0 * a1) */
.optimized {
  background: rgba(128, 128, 128, 0.44); /* 0.3 + 0.2 - (0.3 * 0.2) = 0.44 */
}
```

## CSS Filters for Texture Enhancement

CSS filters and backdrop-filter provide powerful texture enhancement capabilities with hardware acceleration.

### Standard Filters

```css
.enhanced-texture {
  background: url('base-texture.jpg');
  filter: 
    contrast(1.2)           /* Increase contrast */
    brightness(1.1)         /* Slight brightness boost */
    saturate(0.9)          /* Reduce saturation */
    blur(0.5px)            /* Subtle blur for smoothness */
    sepia(0.1)             /* Warm tone */
    hue-rotate(5deg);      /* Slight hue shift */
}

.vintage-effect {
  filter: 
    sepia(0.8) 
    contrast(1.3) 
    brightness(0.9) 
    saturate(0.7);
}
```

### Backdrop Filter for Glassmorphism

```css
.glass-texture {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: 
    blur(10px)              /* Background blur */
    saturate(180%)          /* Enhance colors behind */
    brightness(1.1);        /* Lighten backdrop */
  
  -webkit-backdrop-filter: 
    blur(10px) 
    saturate(180%) 
    brightness(1.1);
  
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
}

.frosted-paper {
  backdrop-filter: blur(8px) contrast(1.1);
  -webkit-backdrop-filter: blur(8px) contrast(1.1);
  background: rgba(248, 248, 248, 0.8);
}
```

### Advanced Filter Combinations

```css
.complex-filter {
  filter: 
    drop-shadow(2px 2px 4px rgba(0,0,0,0.1))
    contrast(1.15)
    saturate(1.05)
    url('#custom-svg-filter');
}

/* SVG filter for custom effects */
.svg-enhanced {
  filter: url('#paper-texture-filter');
}
```

### Browser Support Fallbacks

```css
.filter-with-fallback {
  /* Fallback for older browsers */
  background: url('enhanced-texture.jpg');
  
  /* Modern browsers */
  background: url('base-texture.jpg');
  filter: contrast(1.2) brightness(1.1);
}

/* Feature detection */
@supports (backdrop-filter: blur(1px)) {
  .modern-glass {
    backdrop-filter: blur(10px);
    background: rgba(255, 255, 255, 0.1);
  }
}

@supports not (backdrop-filter: blur(1px)) {
  .modern-glass {
    background: rgba(255, 255, 255, 0.8);
  }
}
```

## JavaScript Libraries for Advanced Blending

Modern JavaScript libraries provide sophisticated texture blending capabilities beyond CSS limitations.

### Three.js for 3D Texture Blending

```javascript
// Three.js texture blending setup
import * as THREE from 'three';

const scene = new THREE.Scene();
const renderer = new THREE.WebGLRenderer({ antialias: true });

// Load textures
const textureLoader = new THREE.TextureLoader();
const baseTexture = textureLoader.load('base-paper.jpg');
const overlayTexture = textureLoader.load('grain-overlay.png');
const normalMap = textureLoader.load('paper-normal.jpg');

// Create material with multiple textures
const material = new THREE.MeshStandardMaterial({
  map: baseTexture,
  normalMap: normalMap,
  roughnessMap: overlayTexture,
  transparent: true
});

// Advanced blending with custom shader
const customMaterial = new THREE.ShaderMaterial({
  uniforms: {
    baseTexture: { value: baseTexture },
    overlayTexture: { value: overlayTexture },
    blendMode: { value: 1.0 }, // 0 = multiply, 1 = overlay, 2 = screen
    opacity: { value: 0.8 }
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D baseTexture;
    uniform sampler2D overlayTexture;
    uniform float blendMode;
    uniform float opacity;
    varying vec2 vUv;
    
    vec3 blendMultiply(vec3 base, vec3 overlay) {
      return base * overlay;
    }
    
    vec3 blendOverlay(vec3 base, vec3 overlay) {
      return mix(2.0 * base * overlay, 1.0 - 2.0 * (1.0 - base) * (1.0 - overlay), step(0.5, base));
    }
    
    void main() {
      vec3 base = texture2D(baseTexture, vUv).rgb;
      vec3 overlay = texture2D(overlayTexture, vUv).rgb;
      
      vec3 blended = mix(
        blendMultiply(base, overlay),
        blendOverlay(base, overlay),
        blendMode
      );
      
      gl_FragColor = vec4(blended, opacity);
    }
  `
});
```

### Fabric.js for Canvas-Based Blending

```javascript
// Fabric.js texture blending
import { fabric } from 'fabric';

const canvas = new fabric.Canvas('texture-canvas');

// Load and blend textures
fabric.Image.fromURL('base-texture.jpg', (baseImg) => {
  baseImg.set({
    left: 0,
    top: 0,
    scaleX: canvas.width / baseImg.width,
    scaleY: canvas.height / baseImg.height
  });
  canvas.add(baseImg);
  
  fabric.Image.fromURL('overlay-texture.png', (overlayImg) => {
    overlayImg.set({
      left: 0,
      top: 0,
      scaleX: canvas.width / overlayImg.width,
      scaleY: canvas.height / overlayImg.height,
      globalCompositeOperation: 'multiply', // Blend mode
      opacity: 0.7
    });
    canvas.add(overlayImg);
  });
});

// Custom filter for advanced blending
fabric.Image.filters.CustomBlend = fabric.util.createClass(fabric.Image.filters.BaseFilter, {
  type: 'CustomBlend',
  
  applyTo2d: function(options) {
    const imageData = options.imageData;
    const data = imageData.data;
    
    for (let i = 0; i < data.length; i += 4) {
      // Custom blending algorithm
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      
      // Apply paper-like texture enhancement
      data[i] = Math.min(255, r * 1.1 + 10);     // Red
      data[i + 1] = Math.min(255, g * 1.05 + 5); // Green
      data[i + 2] = Math.min(255, b * 0.95 + 15); // Blue
    }
  }
});
```

### Konva.js for High-Performance 2D Blending

```javascript
// Konva.js texture blending
import Konva from 'konva';

const stage = new Konva.Stage({
  container: 'texture-container',
  width: 800,
  height: 600
});

const layer = new Konva.Layer();
stage.add(layer);

// Load base texture
Konva.Image.fromURL('paper-base.jpg', (baseImage) => {
  baseImage.setAttrs({
    x: 0,
    y: 0,
    width: stage.width(),
    height: stage.height()
  });
  layer.add(baseImage);
  
  // Add overlay with blend mode
  Konva.Image.fromURL('grain-overlay.png', (overlayImage) => {
    overlayImage.setAttrs({
      x: 0,
      y: 0,
      width: stage.width(),
      height: stage.height(),
      globalCompositeOperation: 'multiply',
      opacity: 0.6
    });
    layer.add(overlayImage);
    layer.draw();
  });
});

// Custom filter for paper texture
const paperFilter = function(imageData) {
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    // Add subtle noise and texture
    const noise = (Math.random() - 0.5) * 10;
    data[i] = Math.max(0, Math.min(255, data[i] + noise));
    data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + noise));
    data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + noise));
  }
};
```

### Performance Comparison (2025)

| Library | Use Case | Performance | Learning Curve | Texture Features |
|---------|----------|-------------|----------------|------------------|
| Three.js | 3D scenes, WebGL | Excellent | Steep | Advanced shaders, multiple textures |
| Fabric.js | Interactive canvas | Good | Moderate | Object manipulation, filters |
| Konva.js | 2D animations | Excellent | Easy | High-performance 2D, mobile-friendly |

## Performance Optimization

Optimizing texture blending for production requires careful attention to file sizes, rendering performance, and browser compatibility.

### Image Optimization

```css
/* Use optimized image formats */
.optimized-texture {
  background-image: 
    url('texture-overlay.webp'),  /* Modern browsers */
    url('texture-overlay.png');   /* Fallback */
}

/* Responsive textures */
.responsive-texture {
  background-image: url('texture-small.webp');
}

@media (min-width: 768px) {
  .responsive-texture {
    background-image: url('texture-medium.webp');
  }
}

@media (min-width: 1200px) {
  .responsive-texture {
    background-image: url('texture-large.webp');
  }
}
```

### CSS Performance Optimization

```css
/* Use transform and opacity for animations (GPU acceleration) */
.animated-texture {
  background: url('base-texture.jpg');
  transform: translateZ(0); /* Force hardware acceleration */
  will-change: transform, opacity; /* Hint browser for optimization */
}

/* Avoid expensive properties in animations */
.efficient-blend {
  /* Good - GPU accelerated */
  transform: scale(1.05);
  opacity: 0.9;
  
  /* Avoid - CPU intensive */
  /* filter: blur(5px); */
  /* background-position: 50% 50%; */
}

/* Use containment for isolated effects */
.contained-texture {
  contain: layout style paint;
  background-blend-mode: multiply;
}
```

### Lazy Loading Implementation

```html
<!-- Lazy load texture images -->
<div class="texture-container" data-bg="paper-texture.jpg">
  <div class="content">Content here</div>
</div>
```

```javascript
// Intersection Observer for lazy loading
const textureObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const element = entry.target;
      const textureSrc = element.dataset.bg;
      
      // Preload image
      const img = new Image();
      img.onload = () => {
        element.style.backgroundImage = `url(${textureSrc})`;
        element.classList.add('texture-loaded');
      };
      img.src = textureSrc;
      
      textureObserver.unobserve(element);
    }
  });
});

document.querySelectorAll('.texture-container').forEach(el => {
  textureObserver.observe(el);
});
```

### CSS Minification and Compression

```css
/* Before minification - 2MB file */
.texture-element {
  background-image: url('large-texture.jpg');
  background-blend-mode: multiply;
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center center;
  filter: contrast(1.2) brightness(1.1) saturate(0.9);
}

/* After minification - 350KB file */
.texture-element{background:url('large-texture.jpg') center/cover no-repeat;background-blend-mode:multiply;filter:contrast(1.2) brightness(1.1) saturate(.9)}
```

### Critical CSS for Texture Loading

```html
<!-- Inline critical texture CSS -->
<style>
  .hero-texture {
    background: url('hero-texture-small.webp') center/cover;
    background-blend-mode: overlay;
    min-height: 100vh;
  }
</style>

<!-- Load non-critical texture CSS asynchronously -->
<link rel="preload" href="textures.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
```

## Realistic Paper-Like Effects

Creating authentic paper textures requires combining multiple techniques for grain, fibers, aging, and lighting effects.

### Basic Paper Texture

```css
.paper-base {
  background-color: #f8f6f0;
  background-image: 
    /* Paper grain */
    url('paper-grain.png'),
    /* Subtle fibers */
    url('paper-fibers.png'),
    /* Base texture */
    radial-gradient(circle at 30% 40%, rgba(0,0,0,0.02) 0%, transparent 50%),
    radial-gradient(circle at 70% 60%, rgba(0,0,0,0.01) 0%, transparent 30%);
  
  background-size: 
    200px 200px,    /* Grain pattern */
    400px 400px,    /* Fiber pattern */
    800px 600px,    /* Shadow 1 */
    600px 800px;    /* Shadow 2 */
  
  background-blend-mode: multiply, overlay, normal, normal;
  background-repeat: repeat, repeat, no-repeat, no-repeat;
}
```

### Aged Paper Effect

```css
.aged-paper {
  background: 
    /* Stain overlays */
    radial-gradient(ellipse at 20% 30%, rgba(139, 115, 85, 0.1) 0%, transparent 40%),
    radial-gradient(ellipse at 80% 70%, rgba(160, 130, 98, 0.08) 0%, transparent 35%),
    /* Edge darkening */
    linear-gradient(to right, rgba(0,0,0,0.05) 0%, transparent 10%, transparent 90%, rgba(0,0,0,0.05) 100%),
    linear-gradient(to bottom, rgba(0,0,0,0.03) 0%, transparent 8%, transparent 92%, rgba(0,0,0,0.03) 100%),
    /* Base paper color */
    #f4f1e8;
  
  background-blend-mode: multiply, overlay, multiply, multiply, normal;
  
  /* Add texture */
  position: relative;
}

.aged-paper::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url('old-paper-texture.jpg') repeat;
  mix-blend-mode: overlay;
  opacity: 0.3;
  pointer-events: none;
}
```

### Handmade Paper Texture

```css
.handmade-paper {
  background: 
    /* Fiber texture */
    url('paper-fibers-dense.png'),
    /* Irregular edges effect */
    radial-gradient(ellipse 100% 80% at 50% 0%, transparent 98%, rgba(0,0,0,0.1) 100%),
    radial-gradient(ellipse 100% 80% at 50% 100%, transparent 98%, rgba(0,0,0,0.1) 100%),
    /* Base color variations */
    linear-gradient(45deg, #faf8f5 0%, #f6f3ee 25%, #faf8f5 50%, #f2efe8 75%, #faf8f5 100%);
  
  background-size: 150px 150px, 100% 20px, 100% 20px, 100% 100%;
  background-blend-mode: overlay, multiply, multiply, normal;
  background-repeat: repeat, no-repeat, no-repeat, no-repeat;
  background-position: 0 0, 0 0, 0 100%, 0 0;
  
  /* Add subtle shadow for depth */
  box-shadow: 
    inset 0 1px 2px rgba(0,0,0,0.05),
    inset 0 -1px 2px rgba(0,0,0,0.05);
}
```

### Parchment Effect

```css
.parchment {
  background: 
    /* Burn marks */
    radial-gradient(ellipse at 5% 10%, rgba(101, 67, 33, 0.2) 0%, transparent 25%),
    radial-gradient(ellipse at 95% 90%, rgba(139, 115, 85, 0.15) 0%, transparent 30%),
    /* Age spots */
    radial-gradient(circle at 30% 60%, rgba(160, 130, 98, 0.1) 0%, transparent 15%),
    radial-gradient(circle at 70% 20%, rgba(139, 115, 85, 0.08) 0%, transparent 20%),
    /* Base parchment color */
    linear-gradient(135deg, #f7f3e9 0%, #f2ede0 50%, #ede8db 100%);
  
  background-blend-mode: multiply, overlay, soft-light, soft-light, normal;
  
  /* Parchment texture overlay */
  position: relative;
}

.parchment::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: url('parchment-texture.png') center/cover;
  mix-blend-mode: overlay;
  opacity: 0.4;
  pointer-events: none;
}
```

### Interactive Paper Effects

```css
.interactive-paper {
  background: #f8f6f0 url('paper-base.jpg') center/cover;
  background-blend-mode: multiply;
  transition: all 0.3s ease;
  cursor: pointer;
}

.interactive-paper:hover {
  background-blend-mode: overlay;
  filter: brightness(1.05) contrast(1.1);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.15);
}

.interactive-paper:active {
  transform: translateY(0);
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  filter: brightness(0.98) contrast(1.05);
}
```

## Browser Support and Compatibility

Understanding browser support is crucial for implementing texture blending effects across different platforms in 2025.

### CSS Blend Modes Support

```css
/* Modern browsers support */
@supports (mix-blend-mode: multiply) {
  .modern-blend {
    mix-blend-mode: multiply;
    background-blend-mode: overlay;
  }
}

/* Fallback for older browsers */
@supports not (mix-blend-mode: multiply) {
  .modern-blend {
    /* Use pre-blended texture images */
    background: url('pre-blended-texture.jpg');
  }
}
```

### Backdrop Filter Compatibility

```css
/* Webkit prefix for Safari */
.glass-effect {
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

/* Feature detection */
@supports (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)) {
  .glass-effect {
    background: rgba(255, 255, 255, 0.1);
  }
}

@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .glass-effect {
    background: rgba(255, 255, 255, 0.8);
  }
}
```

### Cross-Browser JavaScript Detection

```javascript
// Feature detection for advanced blending
const browserSupport = {
  blendModes: CSS.supports('mix-blend-mode', 'multiply'),
  backdropFilter: CSS.supports('backdrop-filter', 'blur(1px)') || 
                  CSS.supports('-webkit-backdrop-filter', 'blur(1px)'),
  webgl: !!document.createElement('canvas').getContext('webgl'),
  webp: false
};

// WebP support detection
const webpTest = new Image();
webpTest.onload = webpTest.onerror = function() {
  browserSupport.webp = webpTest.height === 2;
};
webpTest.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';

// Apply appropriate texture strategy
function applyTextureStrategy() {
  const textureElement = document.querySelector('.adaptive-texture');
  
  if (browserSupport.blendModes && browserSupport.webp) {
    // Use modern CSS blend modes with WebP
    textureElement.classList.add('modern-texture');
  } else if (browserSupport.blendModes) {
    // Use blend modes with PNG fallback
    textureElement.classList.add('blend-texture');
  } else {
    // Use pre-processed texture images
    textureElement.classList.add('fallback-texture');
  }
}
```

### Progressive Enhancement Example

```css
/* Base texture for all browsers */
.progressive-texture {
  background: #f8f6f0 url('base-texture.jpg') center/cover;
}

/* Enhanced for blend mode support */
.blend-modes .progressive-texture {
  background-image: 
    url('overlay-texture.png'),
    url('base-texture.jpg');
  background-blend-mode: multiply, normal;
}

/* Advanced effects for modern browsers */
.backdrop-filter.blend-modes .progressive-texture {
  position: relative;
}

.backdrop-filter.blend-modes .progressive-texture::before {
  backdrop-filter: blur(1px) brightness(1.1);
  -webkit-backdrop-filter: blur(1px) brightness(1.1);
}
```

## Best Practices Summary

1. **Performance First**: Always optimize images and use appropriate formats (WebP with fallbacks)
2. **Progressive Enhancement**: Build base functionality first, then enhance with modern features
3. **Browser Testing**: Test across different browsers and devices regularly
4. **Accessibility**: Ensure texture effects don't interfere with readability
5. **Fallback Strategies**: Always provide fallbacks for unsupported features
6. **Resource Management**: Use lazy loading and intersection observers for texture-heavy pages
7. **CSS Organization**: Keep texture-related CSS modular and maintainable

This comprehensive guide provides the foundation for implementing sophisticated texture blending effects in modern web applications while maintaining performance and compatibility across different browsers and devices.