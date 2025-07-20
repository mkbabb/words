<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    class="transition-all duration-200"
    :class="className"
  >
    <!-- Oxford O symbol with academic styling -->
    <circle
      cx="12"
      cy="12"
      r="8"
      fill="none"
      :stroke="stroke"
      :stroke-width="strokeWidth * 2"
    />
    <circle
      cx="12"
      cy="12"
      r="4"
      fill="none"
      :stroke="stroke"
      :stroke-width="strokeWidth"
    />
    <!-- Academic laurel leaves -->
    <path
      d="M6 6c1-1 2-1 3 0s1 2 0 3-2 1-3 0-1-2 0-3z"
      :fill="fill"
      opacity="0.6"
    />
    <path
      d="M18 6c-1-1-2-1-3 0s-1 2 0 3 2 1 3 0 1-2 0-3z"
      :fill="fill"
      opacity="0.6"
    />
    <path
      d="M6 18c1 1 2 1 3 0s1-2 0-3-2-1-3 0-1 2 0 3z"
      :fill="fill"
      opacity="0.6"
    />
    <path
      d="M18 18c-1 1-2 1-3 0s-1-2 0-3 2-1 3 0 1 2 0 3z"
      :fill="fill"
      opacity="0.6"
    />
  </svg>
</template>

<script setup lang="ts">
interface OxfordIconProps {
  size?: number;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  className?: string;
}

withDefaults(defineProps<OxfordIconProps>(), {
  size: 16,
  fill: 'currentColor',
  stroke: 'currentColor',
  strokeWidth: 1,
  className: ''
});
</script>