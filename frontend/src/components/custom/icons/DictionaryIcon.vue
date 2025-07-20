<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    class="transition-all duration-200"
    :class="className"
  >
    <!-- Dictionary book icon -->
    <path
      d="M6 2C4.89 2 4 2.89 4 4v16c0 1.11.89 2 2 2h12c1.11 0 2-.89 2-2V4c0-1.11-.89-2-2-2H6z"
      :fill="fill"
      opacity="0.8"
    />
    <path
      d="M4 4h16v1H4V4zm0 15h16v1H4v-1z"
      :fill="stroke"
      :stroke-width="strokeWidth"
    />
    <!-- Dictionary.com D symbol -->
    <path
      d="M8 8h3c2 0 3 1 3 3v2c0 2-1 3-3 3H8V8z"
      fill="none"
      :stroke="stroke"
      :stroke-width="strokeWidth"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <path
      d="M8 8v8"
      :stroke="stroke"
      :stroke-width="strokeWidth * 1.5"
      stroke-linecap="round"
    />
    <!-- .com indicator -->
    <circle
      cx="16"
      cy="16"
      r="1.5"
      :fill="fill"
      opacity="0.6"
    />
  </svg>
</template>

<script setup lang="ts">
interface DictionaryIconProps {
  size?: number;
  fill?: string;
  stroke?: string;
  strokeWidth?: number;
  className?: string;
}

withDefaults(defineProps<DictionaryIconProps>(), {
  size: 16,
  fill: 'currentColor',
  stroke: 'currentColor',
  strokeWidth: 1,
  className: ''
});
</script>