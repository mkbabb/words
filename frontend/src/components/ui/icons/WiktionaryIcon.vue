<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    class="transition-all duration-200"
    :class="className"
  >
    <!-- Wiktionary W symbol -->
    <path
      d="M3 4h18v2H3V4zm0 14h18v2H3v-2zm3-7l3 6h2l2-4 2 4h2l3-6h-2l-2 4-2-4h-2l-2 4-2-4H6z"
      :fill="fill"
      :stroke="stroke"
      :stroke-width="strokeWidth"
    />
    <circle
      cx="12"
      cy="12"
      r="9"
      fill="none"
      :stroke="stroke"
      :stroke-width="strokeWidth"
      opacity="0.3"
    />
  </svg>
</template>

<script setup lang="ts">
interface WiktionaryIconProps {
  size?: number;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  className?: string;
}

withDefaults(defineProps<WiktionaryIconProps>(), {
  size: 16,
  fill: 'currentColor',
  stroke: 'currentColor',
  strokeWidth: 1,
  className: ''
});
</script>