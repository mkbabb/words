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
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'collapsible-down': 'collapsible-down 0.2s ease-in-out',
        'collapsible-up': 'collapsible-up 0.2s ease-in-out',
        shimmer: 'shimmer 3s ease-in-out infinite',
        'sparkle-slide': 'sparkle-slide 4s ease-in-out infinite',
      },
      transitionTimingFunction: {
        'out-expo': 'cubic-bezier(0.19, 1, 0.22, 1)',
        'in-out-expo': 'cubic-bezier(0.87, 0, 0.13, 1)',
        'bounce-spring': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
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
    function({ addUtilities }) {
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
      }
      addUtilities(newUtilities, ['responsive', 'hover'])
    }
  ],
};

export default config;
