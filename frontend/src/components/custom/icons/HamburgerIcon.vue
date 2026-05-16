<template>
  <button
    :class="[
      'group relative flex h-10 w-10 items-center justify-center rounded-lg',
      'transition-[transform,opacity,background-color] duration-fast ease-spring-smooth',
      'active:scale-95',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2',
      aiMode
        ? 'hover:bg-[var(--color-gold)]/15 scale-on-hover text-[var(--color-gold)]'
        : 'hover:bg-muted/60 scale-on-hover',
      className
    ]"
    @click="$emit('toggle')"
  >
    <div class="relative flex h-5 w-5 flex-col items-center justify-center">
      <!-- Top line -->
      <span
        :class="[
          'absolute h-0.5 w-full rounded-full bg-current transition-[transform,opacity]',
          isOpen ? 'rotate-45 translate-y-0' : '-translate-y-1.5'
        ]"
        :style="{
          transitionDuration: isOpen ? '650ms' : '550ms',
          transitionTimingFunction: isOpen ? 'var(--spring-bouncy)' : 'var(--ease-standard)',
          transitionDelay: isOpen ? '0ms' : '100ms'
        }"
      />
      <!-- Middle line -->
      <span
        :class="[
          'absolute h-0.5 w-full rounded-full bg-current transition-[transform,opacity]',
          isOpen ? 'opacity-0 scale-0' : 'opacity-100 scale-100'
        ]"
        :style="{
          transitionDuration: isOpen ? '400ms' : '550ms',
          transitionTimingFunction: isOpen ? 'var(--ease-standard)' : 'var(--spring-bouncy)',
          transitionDelay: isOpen ? '0ms' : '50ms'
        }"
      />
      <!-- Bottom line -->
      <span
        :class="[
          'absolute h-0.5 w-full rounded-full bg-current transition-[transform,opacity]',
          isOpen ? '-rotate-45 translate-y-0' : 'translate-y-1.5'
        ]"
        :style="{
          transitionDuration: isOpen ? '650ms' : '550ms',
          transitionTimingFunction: isOpen ? 'var(--spring-bouncy)' : 'var(--ease-standard)',
          transitionDelay: isOpen ? '0ms' : '0ms'
        }"
      />
    </div>
  </button>
</template>

<script setup lang="ts">
interface HamburgerIconProps {
  isOpen?: boolean;
  aiMode?: boolean;
  className?: string;
}

withDefaults(defineProps<HamburgerIconProps>(), {
  isOpen: false,
  aiMode: false,
  className: ''
});

defineEmits<{
  toggle: [];
}>();
</script>