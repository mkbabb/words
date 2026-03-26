<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { ref, onMounted, nextTick, onBeforeUnmount, computed, provide, watch } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { TabsList, type TabsListProps } from 'reka-ui'
import { cn } from '@/utils'

type TabsListVariant = 'pill' | 'underline'

const props = withDefaults(defineProps<TabsListProps & {
  class?: HTMLAttributes['class']
  variant?: TabsListVariant
}>(), {
  variant: 'pill',
})

const delegatedProps = reactiveOmit(props, 'class', 'variant')

provide('tabs-list-variant', props.variant)

const backgroundSlider = ref<HTMLElement>()
const isPill = computed(() => props.variant === 'pill')
let observer: MutationObserver | null = null

const backgroundStyle = ref({
  width: '0px',
  transform: 'translateX(0px)',
  opacity: '0',
})

const updateBackground = () => {
  nextTick(() => {
    if (!isPill.value || !backgroundSlider.value) return

    const parentElement = backgroundSlider.value.parentElement
    if (!parentElement) return

    const activeTab = parentElement.querySelector(
      '[data-state="active"]'
    ) as HTMLElement
    if (!activeTab) return

    const newWidth = `${activeTab.offsetWidth}px`
    const newTransform = `translateX(${activeTab.offsetLeft}px)`

    backgroundStyle.value = {
      width: newWidth,
      transform: newTransform,
      opacity: '1',
    }
  })
}

onMounted(() => {
  if (!isPill.value) return
  updateBackground()

  observer = new MutationObserver(() => {
    updateBackground()
  })

  if (backgroundSlider.value?.parentElement) {
    observer.observe(backgroundSlider.value.parentElement, {
      attributes: true,
      attributeFilter: ['data-state'],
      subtree: true,
    })
  }
})

watch(isPill, (pillEnabled) => {
  if (pillEnabled) {
    updateBackground()
    return
  }

  observer?.disconnect()
  backgroundStyle.value = {
    width: '0px',
    transform: 'translateX(0px)',
    opacity: '0',
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <TabsList
    v-bind="delegatedProps"
    :data-variant="variant"
    :class="
      cn(
        variant === 'pill'
          ? 'transition-smooth relative inline-grid h-12 auto-cols-auto items-center justify-center rounded-2xl glass-light p-1 shadow-lg dark:border-white/20 dark:bg-white/10'
          : 'relative inline-flex h-auto items-center gap-6 border-b border-border/40 bg-transparent p-0 shadow-none backdrop-blur-none',
        props.class
      )
    "
  >
    <div
      v-if="variant === 'pill'"
      ref="backgroundSlider"
      class="bg-primary/10 absolute top-0 left-0 inset-2 mt-2 z-0 rounded-xl shadow-sm transition-normal"
      :style="backgroundStyle"
    />

    <slot />
  </TabsList>
</template>
