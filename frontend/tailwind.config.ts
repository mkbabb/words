import type { Config } from 'tailwindcss';

/**
 * Tailwind v4: CSS-first configuration.
 *
 * All theme tokens (colors, spacing, z-index, keyframes, animations, fonts,
 * radii, easings, durations, shadows) are defined in:
 *   - glass-ui/src/styles/   (design system tokens)
 *   - glass-ui/presets/words.css  (project preset)
 *   - src/assets/index.css   (project-specific @theme block)
 *   - src/assets/theme.css   (project-specific CSS variables)
 *
 * This file contains ONLY plugins that generate utility classes.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx,vue}'],

  plugins: [
    function({ addUtilities }: any) {
      addUtilities({
        // ── Animation delays ──
        '.delay-0':   { 'animation-delay': '0ms' },
        '.delay-150': { 'animation-delay': '150ms' },
        '.delay-300': { 'animation-delay': '300ms' },

        // ── Show/hide states ──
        '.animate-show':        { '@apply animate-scale-in': {} },
        '.animate-hide':        { '@apply animate-scale-out': {} },
        '.animate-show-bounce': { '@apply animate-bounce-in': {} },
        '.animate-hide-bounce': { '@apply animate-bounce-out': {} },

        '.transition-visibility': { '@apply transition-[opacity,transform] duration-350 ease-apple-default': {} },
        '.show':           { '@apply opacity-100 scale-100 translate-y-0': {} },
        '.hide':           { '@apply opacity-0 scale-95 -translate-y-2 pointer-events-none': {} },
        '.show-from-top':  { '@apply opacity-100 scale-y-100 origin-top visible': {} },
        '.hide-to-top':    { '@apply opacity-0 scale-y-0 origin-top invisible': {} },

        // ── Scroll-responsive states ──
        '.scroll-shrunk': {
          '@apply transform-gpu transition-all duration-350 ease-apple-spring': {},
          transform: 'scale(0.85)', opacity: '0.9', maxWidth: '18rem',
        },
        '.scroll-normal': {
          '@apply transform-gpu transition-all duration-350 ease-apple-spring': {},
          transform: 'scale(1)', opacity: '1', maxWidth: '24rem',
        },

        // ── Icon visibility ──
        '.icons-hidden':  { '@apply opacity-0 pointer-events-none': {}, transform: 'scale(0.8)' },
        '.icons-visible': { '@apply opacity-100 pointer-events-auto': {}, transform: 'scale(1)' },

        // ── Paper texture utilities ──
        '.texture-paper-clean':    { backgroundImage: 'var(--paper-clean-texture)', backgroundRepeat: 'repeat' },
        '.texture-paper-aged':     { backgroundImage: 'var(--paper-aged-texture)', backgroundRepeat: 'repeat' },
        '.texture-paper-handmade': { backgroundImage: 'var(--paper-handmade-texture)', backgroundRepeat: 'repeat' },
        '.texture-paper-kraft':    { backgroundImage: 'var(--paper-kraft-texture)', backgroundRepeat: 'repeat' },
        '.texture-subtle':  { backgroundSize: '60px 60px' },
        '.texture-medium':  { backgroundSize: '80px 80px' },
        '.texture-strong':  { backgroundSize: '100px 100px' },

        // ── Mastery level utilities ──
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

        // ── Card state utilities ──
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

        // ── Review quality buttons ──
        '.review-btn-again': {
          '@apply border-2 transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-again) 18%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-again) 40%, transparent)',
          color: 'var(--review-again)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-again) 30%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-again) 60%, transparent)',
          },
        },
        '.review-btn-hard': {
          '@apply border-2 transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-hard) 18%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-hard) 40%, transparent)',
          color: 'var(--review-hard)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-hard) 30%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-hard) 60%, transparent)',
          },
        },
        '.review-btn-good': {
          '@apply border-2 transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-good) 18%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-good) 40%, transparent)',
          color: 'var(--review-good)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-good) 30%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-good) 60%, transparent)',
          },
        },
        '.review-btn-easy': {
          '@apply border-2 transition-all duration-200': {},
          backgroundColor: 'color-mix(in srgb, var(--review-easy) 18%, transparent)',
          borderColor: 'color-mix(in srgb, var(--review-easy) 40%, transparent)',
          color: 'var(--review-easy)',
          '&:hover': {
            backgroundColor: 'color-mix(in srgb, var(--review-easy) 30%, transparent)',
            borderColor: 'color-mix(in srgb, var(--review-easy) 60%, transparent)',
          },
        },

        // ── Mastery stat card ──
        '.stat-mastery': {
          '@apply rounded-xl border p-3 backdrop-blur-md transition-all duration-200': {},
          '&:hover': { transform: 'translateY(-1px)', boxShadow: '0 4px 12px rgba(0,0,0,0.08)' },
        },

        // ── Definition display ──
        '.def-spacing':       { '@apply space-y-3': {} },
        '.def-item-spacing':  { '@apply space-y-2': {} },
        '.def-padding':       { '@apply px-4 sm:px-6 py-6': {} },
        '.def-border-subtle': { '@apply border-border/30': {} },
        '.def-border-normal': { '@apply border-border/50': {} },
      });
    },
  ],
};

export default config;
