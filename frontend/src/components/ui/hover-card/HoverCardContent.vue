<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { useAttrs } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import {
  HoverCardContent,
  type HoverCardContentProps,
  HoverCardPortal,
  useForwardProps,
} from 'reka-ui'
import { cn } from '@/utils'

defineOptions({
  inheritAttrs: false,
})

const props = withDefaults(
  defineProps<HoverCardContentProps & { class?: HTMLAttributes['class'] }>(),
  {
    sideOffset: 4,
  },
)

const attrs = useAttrs()

const delegatedProps = reactiveOmit(props, 'class')

const forwardedProps = useForwardProps(delegatedProps)
</script>

<template>
  <HoverCardPortal>
    <HoverCardContent
      data-slot="hover-card-content"
      v-bind="{ ...forwardedProps, ...attrs }"
      :class="
        cn(
          'hovercard-animated bg-popover/20 backdrop-blur-md text-popover-foreground border-border/30 z-50 w-64 rounded-2xl border-2 cartoon-shadow-sm p-4 outline-none',
          props.class,
        )
      "
    >
      <slot />
    </HoverCardContent>
  </HoverCardPortal>
</template>

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

@keyframes hovercard-out {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
  to {
    opacity: 0;
    transform: scale(0.9) translateY(8px);
  }
}

.hovercard-animated {
  animation: hovercard-in 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.hovercard-animated[data-state="closed"] {
  animation: hovercard-out 0.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
</style>