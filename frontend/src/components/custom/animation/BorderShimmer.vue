<template>
  <div
    v-if="active"
    class="pointer-events-none absolute inset-0 z-[25]"
    :style="{ borderRadius: radius }"
    aria-hidden="true"
  >
    <div
      class="border-shimmer-overlay"
      :style="overlayStyle"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  active?: boolean
  /** Tailwind color token for glow, e.g. 'rgb(251 191 36)' */
  color?: string
  /** Thickness of the shimmering ring in px */
  thickness?: number
  /** Border radius (inherits by default) */
  radius?: string
  /** Duration in ms for one full perimeter sweep */
  duration?: number
  /** Intensity 0..1 controls glow strength */
  intensity?: number
  /** Match the host element's border width in px to draw on the border itself */
  borderWidth?: number
}

const props = withDefaults(defineProps<Props>(), {
  active: true,
  color: 'rgb(251 191 36)', // amber-400 default (golden)
  thickness: 3,
  radius: 'inherit',
  duration: 2600,
  intensity: 0.9,
  borderWidth: 2,
})

const overlayStyle = computed(() => ({
  '--shimmer-color': props.color,
  '--shimmer-thickness': `${props.thickness}px`,
  '--shimmer-speed': `${props.duration}ms`,
  '--shimmer-opacity': String(props.intensity),
  '--ring-width': `${props.borderWidth}px`,
}))
</script>

<style scoped>
.border-shimmer-overlay {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  /* Draw gradient in the border ring via background-clip */
  border: var(--ring-width) solid transparent;
  background:
    linear-gradient(#0000, #0000) padding-box,
    conic-gradient(
      from 0deg at 50% 50%,
      transparent 0deg,
      transparent 334deg,
      color-mix(in srgb, var(--shimmer-color), white 25%) 342deg,
      color-mix(in srgb, var(--shimmer-color), white 55%) 350deg,
      color-mix(in srgb, var(--shimmer-color), transparent 35%) 356deg,
      transparent 360deg
    ) border-box;
  background-clip: padding-box, border-box;
  /* Slight softening to remove harsh edges and imply bulge */
  filter: blur(0.35px)
          drop-shadow(0 0 5px color-mix(in srgb, var(--shimmer-color), white 20%))
          drop-shadow(0 0 1px color-mix(in srgb, var(--shimmer-color), white 10%));
  animation: shimmer-rotate var(--shimmer-speed) linear infinite, shimmer-pulse 2000ms ease-in-out infinite;
  opacity: var(--shimmer-opacity);
}

@keyframes shimmer-rotate {
  from { transform: rotate(0turn); }
  to { transform: rotate(1turn); }
}

@keyframes shimmer-pulse {
  0%, 100% { opacity: calc(var(--shimmer-opacity) * 0.85); }
  50% { opacity: calc(var(--shimmer-opacity) * 1); }
}

@media (prefers-reduced-motion: reduce) {
  .border-shimmer-overlay { animation: none; opacity: 0.6; }
}
</style>
