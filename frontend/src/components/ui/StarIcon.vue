<template>
  <div
    :class="cn('relative h-10 w-10 transition-all duration-300', starClasses)"
  >
    <!-- Background glow effect -->
    <div
      class="absolute inset-0 scale-110 rounded-full bg-current opacity-20 blur-sm"
    ></div>
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      class="relative z-10 h-full w-full"
    >
      <path
        d="M12 2l2.4 7.4h7.6l-6 4.6 2.3 7.4-6.3-4.6-6.3 4.6 2.3-7.4-6-4.6h7.6z"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/utils';

type StarVariant = 'gold' | 'silver' | 'bronze';

interface StarIconProps {
  variant: StarVariant;
}

const props = defineProps<StarIconProps>();

const starClasses = computed(() => {
  switch (props.variant) {
    case 'gold':
      return 'text-yellow-400 drop-shadow-xl animate-pulse';
    case 'silver':
      return 'text-gray-300 drop-shadow-xl';
    case 'bronze':
      return 'text-amber-600 drop-shadow-xl';
    default:
      return 'text-yellow-400 drop-shadow-xl animate-pulse';
  }
});
</script>
