<template>
  <div
    :class="cn('relative h-10 w-10 transition-all duration-300', starClasses)"
  >
    <!-- Custom shaped background that follows star outline -->
    <div
      class="absolute inset-0 opacity-20 blur-sm"
      :style="{ 
        background: 'currentColor',
        clipPath: 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)'
      }"
    ></div>
    
    <!-- More rounded, cartoon-like star -->
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      class="relative z-10 h-full w-full drop-shadow-sm"
    >
      <path
        d="M12 1.5c.5 0 .9.3 1.1.8l1.8 5.4h5.6c.5 0 1 .4 1 .9 0 .3-.1.5-.4.7l-4.5 3.3 1.7 5.3c.2.5-.1 1.1-.6 1.3-.2.1-.5.1-.7 0L12 15.9l-4 2.9c-.5.3-1.1.1-1.4-.4-.1-.2-.1-.4 0-.6l1.7-5.3L4.8 9.2c-.4-.3-.5-.9-.2-1.3.1-.2.3-.3.5-.4h5.7L12.9 2.3c.2-.5.7-.8 1.1-.8z"
        style="filter: drop-shadow(0 1px 2px rgba(0,0,0,0.1))"
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
      return 'text-yellow-400 drop-shadow-xl star-shimmer-gold';
    case 'silver':
      return 'text-gray-300 drop-shadow-xl star-shimmer-silver';
    case 'bronze':
      return 'text-amber-600 drop-shadow-xl star-shimmer-bronze';
    default:
      return 'text-yellow-400 drop-shadow-xl star-shimmer-gold';
  }
});
</script>
