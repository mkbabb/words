<template>
  <TabsList
    v-bind="delegatedProps"
    :class="
      cn(
        'transition-smooth relative inline-grid h-12 auto-cols-auto items-center justify-center rounded-xl border border-white/30 bg-white/20 p-1 shadow-lg backdrop-blur-sm dark:border-white/20 dark:bg-white/10',
        props.class
      )
    "
  >
    <!-- Animated background slider -->
    <div
      ref="backgroundSlider"
      class="bg-primary/10 absolute top-0 left-0 rounded-lg shadow-sm transition-all duration-300 ease-out inset-2 mt-2 z-[1]"
      :style="backgroundStyle"
    />

    <slot />
  </TabsList>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { ref, onMounted, nextTick } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { TabsList, type TabsListProps } from 'reka-ui'
import { cn } from '@/utils'

const props = defineProps<TabsListProps & { class?: HTMLAttributes['class'] }>()

const delegatedProps = reactiveOmit(props, 'class')

const backgroundSlider = ref<HTMLElement>()

const backgroundStyle = ref({
  width: '0px',
  transform: 'translateX(0px)',
  opacity: '0',
})

const updateBackground = () => {
  nextTick(() => {
    if (!backgroundSlider.value) return

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
  // Initial background position
  updateBackground()

  // Watch for tab changes using MutationObserver
  const observer = new MutationObserver(() => {
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
</script>