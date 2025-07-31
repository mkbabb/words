<template>
  <div ref="triggerRef" :class="cn('w-full', $attrs.class as string)" v-bind="$attrs">
    <slot v-if="$slots.default" />
    <div v-else-if="loading" class="flex items-center justify-center py-4">
      <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
      <span class="ml-2 text-sm text-muted-foreground">Loading...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { cn } from '@/lib/utils'

interface Props {
  /**
   * Whether more data is available to load
   */
  hasMore?: boolean
  /**
   * Whether data is currently being loaded
   */
  loading?: boolean
  /**
   * The threshold for triggering the load function (0-1)
   */
  threshold?: number
  /**
   * Root margin for the intersection observer
   */
  rootMargin?: string
  /**
   * Whether infinite scroll is disabled
   */
  disabled?: boolean
}

interface Emits {
  (e: 'load-more'): void
}

const props = withDefaults(defineProps<Props>(), {
  hasMore: true,
  loading: false,
  threshold: 0.1,
  rootMargin: '100px',
  disabled: false
})

const emit = defineEmits<Emits>()

const triggerRef = ref<HTMLElement>()
let observer: IntersectionObserver | null = null
let isTriggering = ref(false)

const startObserving = () => {
  if (!triggerRef.value || props.disabled) return

  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      if (entry.isIntersecting && props.hasMore && !props.loading && !isTriggering.value) {
        // Store current scroll position to prevent jumping
        const scrollContainer = document.scrollingElement || document.documentElement
        const currentScrollTop = scrollContainer.scrollTop
        
        isTriggering.value = true
        emit('load-more')
        
        // Restore scroll position after a frame to prevent jump
        requestAnimationFrame(() => {
          scrollContainer.scrollTop = currentScrollTop
        })
        
        // Reset triggering flag after a brief delay to prevent rapid firing
        setTimeout(() => {
          isTriggering.value = false
        }, 800)
      }
    },
    {
      threshold: props.threshold,
      rootMargin: props.rootMargin
    }
  )

  observer.observe(triggerRef.value)
}

const stopObserving = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

onMounted(() => {
  nextTick(() => {
    startObserving()
  })
})

onUnmounted(() => {
  stopObserving()
})

// Watch for loading state changes to restart observing
watch(() => props.loading, (newLoading, oldLoading) => {
  if (oldLoading && !newLoading) {
    // Just finished loading, give time for DOM to settle
    setTimeout(() => {
      stopObserving()
      nextTick(() => {
        startObserving()
      })
    }, 300)
  }
})

// Restart observer when relevant props change
watch([() => props.disabled, () => props.hasMore], () => {
  if (!props.loading) {
    stopObserving()
    nextTick(() => {
      startObserving()
    })
  }
})
</script>