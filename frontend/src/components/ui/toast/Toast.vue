<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import {
  ToastAction,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastRoot,
  ToastTitle,
  ToastViewport,
  type ToastRootEmits,
  type ToastRootProps,
} from 'radix-vue'
import { cn } from '@/lib/utils'
import { X } from 'lucide-vue-next'

interface ToastProps extends ToastRootProps {
  class?: HTMLAttributes['class']
  variant?: 'default' | 'destructive'
  onOpenChange?: ((value: boolean) => void) | undefined
}

interface ToastEmits extends ToastRootEmits {}

const props = withDefaults(defineProps<ToastProps>(), {
  variant: 'default',
})

const emits = defineEmits<ToastEmits>()

const delegatedProps = computed(() => {
  const { class: _, variant, ...delegated } = props
  return delegated
})
</script>

<template>
  <ToastProvider>
    <ToastRoot
      v-bind="delegatedProps"
      :class="
        cn(
          'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full',
          {
            'bg-background text-foreground border': variant === 'default',
            'bg-destructive text-destructive-foreground border-destructive': variant === 'destructive',
          },
          props.class,
        )
      "
      @update:open="emits('update:open', $event)"
      @escapeKeyDown="emits('escapeKeyDown', $event)"
      @pause="emits('pause', $event)"
      @resume="emits('resume', $event)"
      @swipeStart="emits('swipeStart', $event)"
      @swipeMove="emits('swipeMove', $event)"
      @swipeEnd="emits('swipeEnd', $event)"
      @swipeCancel="emits('swipeCancel', $event)"
    >
      <slot />
    </ToastRoot>
    <ToastViewport />
  </ToastProvider>
</template>