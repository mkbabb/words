<template>
  <button
    :class="[
      'flex h-10 w-10 items-center justify-center rounded-lg',
      'hover:bg-muted/50 active:scale-95',
      className
    ]"
    style="transition: background-color 150ms ease-out, transform 150ms ease-out"
    @click="$emit('toggle')"
  >
    <div class="relative flex h-5 w-5 flex-col items-center justify-center">
      <span
        :class="[
          'absolute h-0.5 w-full bg-current',
          isOpen ? 'rotate-45 translate-y-0' : '-translate-y-1.5'
        ]"
        style="transition: transform 650ms cubic-bezier(0.175, 0.885, 0.32, 1.4), opacity 300ms ease-out"
      />
      <span
        :class="[
          'absolute h-0.5 w-full bg-current',
          isOpen ? 'opacity-0 scale-0' : 'opacity-100 scale-100'
        ]"
        style="transition: transform 600ms cubic-bezier(0.175, 0.885, 0.32, 1.3), opacity 400ms ease-out"
      />
      <span
        :class="[
          'absolute h-0.5 w-full bg-current',
          isOpen ? '-rotate-45 translate-y-0' : 'translate-y-1.5'
        ]"
        style="transition: transform 650ms cubic-bezier(0.175, 0.885, 0.32, 1.4), opacity 300ms ease-out"
      />
    </div>
  </button>
</template>

<script setup lang="ts">
interface HamburgerIconProps {
  isOpen?: boolean;
  className?: string;
}

withDefaults(defineProps<HamburgerIconProps>(), {
  isOpen: false,
  className: ''
});

defineEmits<{
  toggle: [];
}>();
</script>