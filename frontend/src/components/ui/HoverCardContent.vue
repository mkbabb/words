<template>
  <HoverCardPortal>
    <HoverCardContent
      :side="side"
      :side-offset="sideOffset"
      :align="align"
      :align-offset="alignOffset"
      :collision-padding="collisionPadding"
      :avoid-collisions="avoidCollisions"
      class="hovercard-animated bg-popover/20 backdrop-blur-md text-popover-foreground border-border/30 z-50 w-64 rounded-md border p-4 shadow-card-hover outline-none"
    >
      <slot />
    </HoverCardContent>
  </HoverCardPortal>
</template>

<script setup lang="ts">
import { HoverCardContent, HoverCardPortal } from 'radix-vue';

interface Props {
  side?: 'top' | 'right' | 'bottom' | 'left';
  sideOffset?: number;
  align?: 'start' | 'center' | 'end';
  alignOffset?: number;
  collisionPadding?: number;
  avoidCollisions?: boolean;
}

withDefaults(defineProps<Props>(), {
  side: 'bottom',
  sideOffset: 4,
  align: 'center',
  alignOffset: 0,
  collisionPadding: 8,
  avoidCollisions: true,
});
</script>

<style>
@keyframes hovercard-in {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.hovercard-animated {
  animation: hovercard-in 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
</style>
