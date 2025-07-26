import type { Config } from 'tailwindcss';
import * as animate from 'tailwindcss-animate';

const config: Config = {
  darkMode: 'selector',

  prefix: '',

  content: ['./src/**/*.{ts,tsx,vue}'],

  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      fontFamily: {
        sans: ['Fraunces', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
        serif: ['Fraunces', 'Georgia', 'Cambria', 'Times New Roman', 'serif'],
        mono: ['Fira Code', 'Consolas', 'Monaco', 'Andale Mono', 'monospace'],
      },
      colors: {
        border: 'var(--color-border)',
        input: 'var(--color-input)',
        ring: 'var(--color-ring)',
        background: 'var(--color-background)',
        foreground: 'var(--color-foreground)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          foreground: 'var(--color-primary-foreground)',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          foreground: 'var(--color-secondary-foreground)',
        },
        destructive: {
          DEFAULT: 'var(--color-destructive)',
          foreground: 'var(--color-destructive-foreground)',
        },
        muted: {
          DEFAULT: 'var(--color-muted)',
          foreground: 'var(--color-muted-foreground)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          foreground: 'var(--color-accent-foreground)',
        },
        popover: {
          DEFAULT: 'var(--color-popover)',
          foreground: 'var(--color-popover-foreground)',
        },
        card: {
          DEFAULT: 'var(--color-card)',
          foreground: 'var(--color-card-foreground)',
        },
        bronze: {
          100: '#fed7aa',
          200: '#fdba74', 
          300: '#fb923c',
          400: '#f97316',
          500: '#ea580c',
          600: '#dc2626',
          700: '#c2410c',
          800: '#9a3412',
          900: '#7c2d12',
        },
      },
      borderRadius: {
        xl: 'calc(var(--radius) + 4px)',
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'collapsible-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-collapsible-content-height)' },
        },
        'collapsible-up': {
          from: { height: 'var(--radix-collapsible-content-height)' },
          to: { height: '0' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        'sparkle-slide': {
          '0%': { transform: 'translateX(-100%) rotate(45deg)', opacity: '0' },
          '50%': { opacity: '1' },
          '100%': { transform: 'translateX(300%) rotate(45deg)', opacity: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'fade-out': {
          from: { opacity: '1' },
          to: { opacity: '0' },
        },
        'slide-up': {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          from: { transform: 'translateY(-8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        'scale-in': {
          from: { transform: 'scale(0.95)', opacity: '0' },
          to: { transform: 'scale(1)', opacity: '1' },
        },
        'scale-out': {
          from: { transform: 'scale(1)', opacity: '1' },
          to: { transform: 'scale(0.95)', opacity: '0' },
        },
        'bounce-in': {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '50%': { transform: 'scale(1.03)' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        'bounce-out': {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.03)' },
          '100%': { transform: 'scale(0.9)', opacity: '0' },
        },
        'shrink-bounce': {
          '0%': { transform: 'scale(1)' },
          '40%': { transform: 'scale(0.95)' },
          '60%': { transform: 'scale(1.02)' },
          '80%': { transform: 'scale(0.98)' },
          '100%': { transform: 'scale(1)' },
        },
        'scroll-shrink': {
          '0%': { 
            transform: 'scale(1)',
            opacity: '1',
            maxWidth: '24rem'
          },
          '100%': { 
            transform: 'scale(0.85)',
            opacity: '0.9',
            maxWidth: '18rem'
          },
        },
        'icon-fade': {
          '0%': { 
            opacity: '1',
            transform: 'scale(1)'
          },
          '100%': { 
            opacity: '0',
            transform: 'scale(0.8)'
          },
        },
        'elastic-bounce': {
          '0%': { transform: 'scale(1)' },
          '30%': { transform: 'scale(1.05)' },
          '50%': { transform: 'scale(0.95)' },
          '70%': { transform: 'scale(1.02)' },
          '100%': { transform: 'scale(1)' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'collapsible-down': 'collapsible-down 0.2s ease-in-out',
        'collapsible-up': 'collapsible-up 0.2s ease-in-out',
        shimmer: 'shimmer 3s ease-in-out infinite',
        'sparkle-slide': 'sparkle-slide 4s ease-in-out infinite',
        'fade-in': 'fade-in 0.2s ease-out',
        'fade-out': 'fade-out 0.2s ease-out',
        'slide-up': 'slide-up 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-down': 'slide-down 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scale-in 0.2s ease-out',
        'scale-out': 'scale-out 0.2s ease-out',
        'bounce-in': 'bounce-in 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'bounce-out': 'bounce-out 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'shrink-bounce': 'shrink-bounce 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'scroll-shrink': 'scroll-shrink 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        'icon-fade': 'icon-fade 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        'elastic-bounce': 'elastic-bounce 0.6s cubic-bezier(0.25, 0.1, 0.25, 1)',
        'spin-slow': 'spin-slow 3s linear infinite',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.19, 1, 0.22, 1)',
        'in-out-expo': 'cubic-bezier(0.87, 0, 0.13, 1)',
        'bounce-spring': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        'apple-smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'apple-bounce': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
      },
      boxShadow: {
        'card': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.12)',
        'subtle': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 20px rgba(var(--color-primary), 0.3)',
      },
      backgroundImage: {
        'paper-clean': 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence baseFrequency="0.9" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%" height="100%" filter="url(%23noise)" opacity="0.03"/%3E%3C/svg%3E")',
        'paper-aged': 'url("data:image/svg+xml,%3Csvg width="80" height="80" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence baseFrequency="0.7" numOctaves="4" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%" height="100%" filter="url(%23noise)" opacity="0.05"/%3E%3C/svg%3E")',
        'paper-handmade': 'url("data:image/svg+xml,%3Csvg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence baseFrequency="0.5" numOctaves="5" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%" height="100%" filter="url(%23noise)" opacity="0.04"/%3E%3C/svg%3E")',
        'paper-kraft': 'url("data:image/svg+xml,%3Csvg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence baseFrequency="0.6" numOctaves="4" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%" height="100%" filter="url(%23noise)" opacity="0.06"/%3E%3C/svg%3E")',
      },
    },
  },
  plugins: [
    animate,
    function({ addUtilities, matchUtilities, theme }) {
      const newUtilities = {
        '.hover-lift': {
          '@apply transition-all duration-200 hover:scale-[1.02] hover:brightness-95': {},
        },
        '.hover-lift-sm': {
          '@apply transition-all duration-200 hover:scale-[1.01] hover:brightness-97': {},
        },
        '.hover-text-grow': {
          '@apply transition-[font-size] duration-200 hover:text-[1.02em]': {},
        },
        '.hover-shadow-lift': {
          '@apply transition-shadow duration-200 hover:shadow-card-hover': {},
        },
        '.focus-ring': {
          '@apply focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background': {},
        },
        '.transition-smooth': {
          '@apply transition-all duration-200 ease-in-out': {},
        },
        '.delay-0': {
          'animation-delay': '0ms',
        },
        '.delay-150': {
          'animation-delay': '150ms',
        },
        '.delay-300': {
          'animation-delay': '300ms',
        },
        // Animation state utilities
        '.animate-show': {
          '@apply animate-scale-in': {},
        },
        '.animate-hide': {
          '@apply animate-scale-out': {},
        },
        '.animate-show-bounce': {
          '@apply animate-bounce-in': {},
        },
        '.animate-hide-bounce': {
          '@apply animate-bounce-out': {},
        },
        // Transition utilities for show/hide
        '.transition-visibility': {
          '@apply transition-[opacity,transform] duration-300': {},
        },
        '.show': {
          '@apply opacity-100 scale-100 translate-y-0': {},
        },
        '.hide': {
          '@apply opacity-0 scale-95 -translate-y-2 pointer-events-none': {},
        },
        '.show-from-top': {
          '@apply opacity-100 scale-y-100 origin-top visible': {},
        },
        '.hide-to-top': {
          '@apply opacity-0 scale-y-0 origin-top invisible': {},
        },
        // Scroll-based animation states
        '.scroll-shrunk': {
          '@apply transform-gpu': {},
          transform: 'scale(0.85)',
          opacity: '0.9',
          maxWidth: '18rem', // ~288px - mobile friendly
        },
        '.scroll-normal': {
          '@apply transform-gpu': {},
          transform: 'scale(1)',
          opacity: '1',
          maxWidth: '24rem', // ~384px - desktop friendly
        },
        '.icons-hidden': {
          '@apply opacity-0 pointer-events-none': {},
          transform: 'scale(0.8)',
        },
        '.icons-visible': {
          '@apply opacity-100 pointer-events-auto': {},
          transform: 'scale(1)',
        },
        // Smooth transitions for scroll animations
        '.transition-scroll': {
          '@apply transition-all duration-300 ease-apple-smooth': {},
        },
        '.transition-bounce': {
          '@apply transition-all duration-600 ease-apple-bounce': {},
        },
        // Paper texture utilities - visible textures that don't break elements
        '.texture-paper-clean': {
          backgroundImage: 'var(--paper-clean-texture)',
          backgroundRepeat: 'repeat',
        },
        '.texture-paper-aged': {
          backgroundImage: 'var(--paper-aged-texture)',
          backgroundRepeat: 'repeat',
        },
        '.texture-paper-handmade': {
          backgroundImage: 'var(--paper-handmade-texture)',
          backgroundRepeat: 'repeat',
        },
        '.texture-paper-kraft': {
          backgroundImage: 'var(--paper-kraft-texture)',
          backgroundRepeat: 'repeat',
        },
        '.texture-subtle': {
          backgroundSize: '60px 60px',
        },
        '.texture-medium': {
          backgroundSize: '80px 80px',
        },
        '.texture-strong': {
          backgroundSize: '100px 100px',
        },
      }
      addUtilities(newUtilities, ['responsive', 'hover'])
      
      // Dynamic transition timing utilities
      matchUtilities(
        {
          'transition-timing': (value: string) => ({
            'transition-timing-function': value,
          }),
        },
        { values: theme('transitionTimingFunction') }
      )
    }
  ],
};

export default config;
