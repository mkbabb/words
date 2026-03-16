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
      },
      zIndex: {
        'overlay': '0',
        'content': '1',
        'float': '10',
        'bar': '30',
        'dropdown': '40',
        'modal': '50',
        'mobile-nav': '60',
        'hovercard': '80',
        'critical': '100',
        'toggle': '999',
        'max': '9999',
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
        wiggle: {
          '0%, 100%': { transform: 'rotate(-3deg) scale(1)' },
          '25%': { transform: 'rotate(3deg) scale(1.02)' },
          '75%': { transform: 'rotate(-3deg) scale(0.98)' },
        },
        'wiggle-bounce': {
          '0%, 100%': { transform: 'rotate(-2deg) translateY(0)' },
          '25%': { transform: 'rotate(2deg) translateY(-2px)' },
          '75%': { transform: 'rotate(-2deg) translateY(2px)' },
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
        'icon-fade': 'icon-fade 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        'elastic-bounce': 'elastic-bounce 0.6s cubic-bezier(0.25, 0.1, 0.25, 1)',
        'spin-slow': 'spin-slow 3s linear infinite',
        wiggle: 'wiggle 2.5s ease-in-out infinite',
        'wiggle-bounce': 'wiggle-bounce 2.5s ease-in-out infinite',
      },
      transitionTimingFunction: {
        // Primary Apple-like easings
        'apple-default': 'cubic-bezier(0.25, 0.1, 0.25, 1)',
        'apple-smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'apple-spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        
        // Directional easings
        'apple-ease-in': 'cubic-bezier(0.42, 0, 1, 1)',
        'apple-ease-out': 'cubic-bezier(0, 0, 0.58, 1)',
        
        // Specialized easings
        'apple-elastic': 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',
        'apple-bounce-in': 'cubic-bezier(0.6, -0.28, 0.735, 0.045)',
        'apple-bounce-out': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
      },
      transitionDuration: {
        '150': '150ms',  // Micro-interactions
        '250': '250ms',  // Fast transitions
        '350': '350ms',  // Normal transitions
        '500': '500ms',  // Smooth transitions
        '700': '700ms',  // Slow transitions
      },
      boxShadow: {
        'card': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 8px 24px rgba(0, 0, 0, 0.12)',
        'subtle': '0 2px 8px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 20px rgba(var(--color-primary), 0.3)',
      },
    },
  },
  plugins: [
    animate,
    function({ addUtilities, matchUtilities, theme }) {
      const newUtilities = {
        // Standardized hover effects
        '.hover-lift': {
          '@apply transition-all duration-250 ease-apple-default hover:scale-[1.02]': {},
        },
        '.hover-lift-md': {
          '@apply transition-all duration-250 ease-apple-default hover:scale-[1.05]': {},
        },
        '.hover-lift-lg': {
          '@apply transition-all duration-250 ease-apple-default hover:scale-[1.1]': {},
        },
        '.hover-shadow-lift': {
          '@apply transition-shadow duration-250 ease-apple-smooth hover:shadow-card-hover': {},
        },
        '.focus-ring': {
          '@apply focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background': {},
        },
        // Standardized transition utilities
        '.transition-micro': {
          '@apply transition-all duration-150 ease-apple-smooth': {},
        },
        '.transition-fast': {
          '@apply transition-all duration-250 ease-apple-default': {},
        },
        '.transition-normal': {
          '@apply transition-all duration-350 ease-apple-default': {},
        },
        '.transition-smooth': {
          '@apply transition-all duration-500 ease-apple-smooth': {},
        },
        '.transition-spring': {
          '@apply transition-all duration-350 ease-apple-spring': {},
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
          '@apply transition-[opacity,transform] duration-350 ease-apple-default': {},
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
          '@apply transform-gpu transition-all duration-350 ease-apple-spring': {},
          transform: 'scale(0.85)',
          opacity: '0.9',
          maxWidth: '18rem',
        },
        '.scroll-normal': {
          '@apply transform-gpu transition-all duration-350 ease-apple-spring': {},
          transform: 'scale(1)',
          opacity: '1',
          maxWidth: '24rem',
        },
        '.icons-hidden': {
          '@apply opacity-0 pointer-events-none': {},
          transform: 'scale(0.8)',
        },
        '.icons-visible': {
          '@apply opacity-100 pointer-events-auto': {},
          transform: 'scale(1)',
        },
        // Glass-morphism utilities
        '.glass-light': {
          '@apply bg-background/80 backdrop-blur-sm border border-border/30': {},
        },
        '.glass-medium': {
          '@apply bg-background/80 backdrop-blur-md border border-border/30': {},
        },
        '.glass-heavy': {
          '@apply bg-background/80 backdrop-blur-xl border border-border/30': {},
        },
        '.glass-overlay': {
          '@apply bg-black/60 backdrop-blur-sm': {},
        },
        // Active states
        '.active-scale': {
          '@apply active:scale-[0.97] active:transition-transform active:duration-150': {},
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
        // Mastery level utilities (text, bg, border)
        '.mastery-default': { color: 'var(--mastery-default)' },
        '.mastery-bronze':  { color: 'var(--mastery-bronze)' },
        '.mastery-silver':  { color: 'var(--mastery-silver)' },
        '.mastery-gold':    { color: 'var(--mastery-gold)' },
        '.bg-mastery-default': { backgroundColor: 'color-mix(in srgb, var(--mastery-default) 10%, transparent)' },
        '.bg-mastery-bronze':  { backgroundColor: 'color-mix(in srgb, var(--mastery-bronze) 10%, transparent)' },
        '.bg-mastery-silver':  { backgroundColor: 'color-mix(in srgb, var(--mastery-silver) 10%, transparent)' },
        '.bg-mastery-gold':    { backgroundColor: 'color-mix(in srgb, var(--mastery-gold) 10%, transparent)' },
        '.border-mastery-default': { borderColor: 'color-mix(in srgb, var(--mastery-default) 25%, transparent)' },
        '.border-mastery-bronze':  { borderColor: 'color-mix(in srgb, var(--mastery-bronze) 25%, transparent)' },
        '.border-mastery-silver':  { borderColor: 'color-mix(in srgb, var(--mastery-silver) 25%, transparent)' },
        '.border-mastery-gold':    { borderColor: 'color-mix(in srgb, var(--mastery-gold) 25%, transparent)' },
        // Card state utilities
        '.state-new':         { color: 'var(--card-state-new)' },
        '.state-learning':    { color: 'var(--card-state-learning)' },
        '.state-young':       { color: 'var(--card-state-young)' },
        '.state-mature':      { color: 'var(--card-state-mature)' },
        '.state-relearning':  { color: 'var(--card-state-relearning)' },
        '.bg-state-new':         { backgroundColor: 'color-mix(in srgb, var(--card-state-new) 10%, transparent)' },
        '.bg-state-learning':    { backgroundColor: 'color-mix(in srgb, var(--card-state-learning) 10%, transparent)' },
        '.bg-state-young':       { backgroundColor: 'color-mix(in srgb, var(--card-state-young) 10%, transparent)' },
        '.bg-state-mature':      { backgroundColor: 'color-mix(in srgb, var(--card-state-mature) 10%, transparent)' },
        '.bg-state-relearning':  { backgroundColor: 'color-mix(in srgb, var(--card-state-relearning) 10%, transparent)' },
        // Review quality button styles
        '.review-btn-again': {
          '@apply border transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-again) 15%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-again) 30%, transparent)',
          color: 'var(--review-again)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-again) 25%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-again) 50%, transparent)',
          },
        },
        '.review-btn-hard': {
          '@apply border transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-hard) 15%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-hard) 30%, transparent)',
          color: 'var(--review-hard)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-hard) 25%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-hard) 50%, transparent)',
          },
        },
        '.review-btn-good': {
          '@apply border transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-good) 15%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-good) 30%, transparent)',
          color: 'var(--review-good)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-good) 25%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-good) 50%, transparent)',
          },
        },
        '.review-btn-easy': {
          '@apply border transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-easy) 15%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-easy) 30%, transparent)',
          color: 'var(--review-easy)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-easy) 25%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-easy) 50%, transparent)',
          },
        },
        // Mastery stat card
        '.stat-mastery': {
          '@apply rounded-xl border p-3 backdrop-blur-md transition-all duration-200': {},
          '&:hover': { transform: 'translateY(-1px)', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' },
        },
      }
      addUtilities(newUtilities, ['responsive', 'hover'])
      
    }
  ],
};

export default config;
