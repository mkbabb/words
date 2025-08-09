<template>
  <div
    v-if="active"
    class="pointer-events-none absolute inset-0 z-[25]"
    :style="{ borderRadius: radius }"
    aria-hidden="true"
    ref="rootEl"
  >
    <svg
      class="absolute inset-0 w-full h-full"
      :style="{ borderRadius: radius }"
      xmlns="http://www.w3.org/2000/svg"
      :viewBox="`0 0 ${vbWidth} ${vbHeight}`"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <filter :id="filterId" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceGraphic" :stdDeviation="glowBlur" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <rect
        :x="ringView/2"
        :y="ringView/2"
        :width="vbWidth - ringView"
        :height="vbHeight - ringView"
        :rx="corner"
        :ry="corner"
        fill="none"
        :stroke="props.color"
        :stroke-width="ringView"
        stroke-linecap="round"
        :pathLength="pathLength"
        :stroke-dasharray="`${bead} ${gap}`"
        :style="rectStyle"
        :filter="`url(#${filterId})`"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'

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
  /** Optional numeric corner radius for the path; otherwise auto-measured */
  cornerRadius?: number
}

const props = withDefaults(defineProps<Props>(), {
  active: true,
  color: 'rgb(251 191 36)', // amber-400 default (golden)
  thickness: 3,
  radius: 'inherit',
  duration: 2600,
  intensity: 0.9,
  borderWidth: 2,
  cornerRadius: undefined,
})

const filterId = `border-glow-${Math.random().toString(36).slice(2)}`

// Fixed viewBox to normalize path length and animation
const vbWidth = 1000
const vbHeight = 600

const pathLength = 1000
const bead = 22
const gap = pathLength - bead

// Dynamic mapping from px to viewBox units via ResizeObserver
const ringView = ref(2)
const corner = ref(16)

const rootEl = ref<HTMLElement | null>(null)
let ro: ResizeObserver | null = null

const recalc = () => {
  const el = rootEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const width = Math.max(1, rect.width)
  const scaleX = vbWidth / width
  // Border width to viewBox units (slightly thicker than exact for visibility)
  ringView.value = Math.max(1, (props.borderWidth || 2) * scaleX * 1.0)
  // Corner radius from computed style (fallback to prop or 16)
  const cs = getComputedStyle(el)
  const br = cs.borderTopLeftRadius || cs.borderRadius || '16px'
  const px = parseFloat(br)
  const sourceCorner = props.cornerRadius ?? (Number.isFinite(px) ? px : 16)
  corner.value = Math.max(2, sourceCorner * scaleX)
}

onMounted(() => {
  const wrapper = rootEl.value
  if (!wrapper) return
  recalc()
  if ('ResizeObserver' in window) {
    ro = new ResizeObserver(() => recalc())
    ro.observe(wrapper)
  } else {
    // Fallback: recalc once more after a paint
    requestAnimationFrame(recalc)
  }
})

onBeforeUnmount(() => { if (ro) { ro.disconnect(); ro = null } })

const speedMs = computed(() => Math.max(1200, props.duration))
const glowBlur = 0.9
const rectStyle = computed(() => ({
  animation: `border-sweep ${speedMs.value}ms cubic-bezier(0.55,0.12,0.18,1) infinite`,
  opacity: String(props.intensity ?? 0.8),
}))
</script>

<style scoped>
@keyframes border-sweep {
  0%   { stroke-dashoffset: 0; opacity: 0.0; }
  30%  { stroke-dashoffset: -120; opacity: 0.08; }
  70%  { stroke-dashoffset: -820; opacity: 1.0; }
  100% { stroke-dashoffset: -1000; opacity: 0.0; }
}

@keyframes border-pulse {
  0%, 100% { opacity: calc(var(--shimmer-opacity) * 0.85); }
  50% { opacity: calc(var(--shimmer-opacity) * 1); }
}

@media (prefers-reduced-motion: reduce) { rect { animation: none !important; opacity: 0.6; } }
</style>
