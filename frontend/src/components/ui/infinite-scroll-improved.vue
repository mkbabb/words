<template>
  <div ref="wrapperRef" class="w-full">
    <!-- Content slot -->
    <slot />
    
    <!-- Sentinel element that triggers loading -->
    <div 
      ref="sentinelRef" 
      :class="[
        'w-full flex items-center justify-center',
        loading ? 'py-4' : 'py-2'
      ]"
    >
      <div v-if="loading" class="flex items-center gap-2">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
        <span class="text-sm text-muted-foreground">Loading more...</span>
      </div>
      <div v-else-if="hasMore" class="text-xs text-muted-foreground/60">
        <!-- Silent sentinel -->
      </div>
      <div v-else class="text-xs text-muted-foreground text-center py-2">
        No more items to load
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

interface Props {
  hasMore?: boolean
  loading?: boolean
  threshold?: number
  rootMargin?: string
  disabled?: boolean
}

interface Emits {
  (e: 'load-more'): void
}

const props = withDefaults(defineProps<Props>(), {
  hasMore: true,
  loading: false,
  threshold: 0.1,
  rootMargin: '200px',
  disabled: false
})

const emit = defineEmits<Emits>()

const sentinelRef = ref<HTMLElement>()
const wrapperRef = ref<HTMLElement>()
let observer: IntersectionObserver | null = null

const createObserver = () => {
  if (!sentinelRef.value || props.disabled) return

  observer = new IntersectionObserver(
    (entries) => {
      const entry = entries[0]
      
      // Only trigger if:
      // 1. Element is intersecting
      // 2. We have more items to load
      // 3. Not currently loading
      if (entry.isIntersecting && props.hasMore && !props.loading) {
        emit('load-more')
      }
    },
    {
      // Use wrapper as root for better performance
      root: wrapperRef.value,
      threshold: props.threshold,
      rootMargin: props.rootMargin
    }
  )

  observer.observe(sentinelRef.value)
}

const destroyObserver = () => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

onMounted(() => {
  nextTick(() => {
    createObserver()
  })
})

onUnmounted(() => {
  destroyObserver()
})

// Re-create observer when loading finishes to ensure proper observation
// This is the key fix - simple recreation after loading
defineExpose({
  refresh: () => {
    destroyObserver()
    nextTick(() => {
      createObserver()
    })
  }
})
</script>