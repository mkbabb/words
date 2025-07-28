<template>
  <Teleport to="body">
    <Transition
      :css="false"
      @enter="modalEnter"
      @leave="modalLeave"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[9999] flex items-center justify-center"
        @click="handleBackdropClick"
      >
        <!-- Backdrop with standard blue modal styling -->
        <div
          ref="backdropRef"
          class="absolute inset-0 z-0"
          :class="[
            'bg-blue-900/20 dark:bg-blue-950/30',
            'backdrop-blur-md',
            'transform-gpu',
          ]"
        />
        
        <!-- Clean modal container -->
        <div ref="contentRef" class="relative z-30 w-full max-w-4xl p-4">
          <div class="modal-content relative mx-auto max-w-3xl rounded-2xl bg-background/80 backdrop-blur-md shadow-2xl cartoon-shadow-lg border border-border/30 overflow-hidden">
            <div class="p-8 relative z-20">
              <slot />
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

interface Props {
  modelValue: boolean
  closeOnBackdrop?: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  closeOnBackdrop: true,
})

const emit = defineEmits<Emits>()

// Refs for animation targets
const backdropRef = ref<HTMLDivElement>()
const contentRef = ref<HTMLDivElement>()

const handleBackdropClick = (event: Event) => {
  if (!props.closeOnBackdrop) return
  
  // Check if the click was on the backdrop (not on modal content)
  const target = event.target as Element
  if (target.closest('.modal-content')) return
  
  emit('update:modelValue', false)
}

// Smooth enter animation
const modalEnter = (_el: Element, done: () => void) => {
  const backdrop = backdropRef.value
  const content = contentRef.value
  
  if (!backdrop || !content) {
    done()
    return
  }
  
  // Initial states
  backdrop.style.opacity = '0'
  content.style.opacity = '0'
  content.style.transform = 'scale(0.9) translateY(30px) rotate(0.5deg)'
  
  // Force reflow
  backdrop.offsetHeight
  
  // Animate
  requestAnimationFrame(() => {
    // Backdrop fades in first
    backdrop.style.transition = 'opacity 250ms cubic-bezier(0.25, 0.1, 0.25, 1)'
    backdrop.style.opacity = '1'
    
    // Content appears slightly after with spring-like easing
    setTimeout(() => {
      content.style.transition = 'all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)'
      content.style.opacity = '1'
      content.style.transform = 'scale(1) translateY(0) rotate(0)'
      
      setTimeout(done, 400)
    }, 50)
  })
}

// Smooth leave animation
const modalLeave = (el: Element, done: () => void) => {
  const backdrop = backdropRef.value
  const content = contentRef.value
  
  if (!backdrop || !content) {
    done()
    return
  }
  
  // Force current styles to be computed
  const currentBackdropOpacity = window.getComputedStyle(backdrop).opacity
  const currentContentOpacity = window.getComputedStyle(content).opacity
  const currentContentTransform = window.getComputedStyle(content).transform
  
  // Set current state explicitly
  backdrop.style.opacity = currentBackdropOpacity
  content.style.opacity = currentContentOpacity
  content.style.transform = currentContentTransform
  
  // Force reflow
  void (el as HTMLElement).offsetHeight
  
  // Animate out with smooth easing
  requestAnimationFrame(() => {
    content.style.transition = 'all 250ms cubic-bezier(0.6, -0.28, 0.735, 0.045)'
    content.style.opacity = '0'
    content.style.transform = 'scale(0.95) translateY(20px) rotate(-0.5deg)'
    
    // Backdrop fades out simultaneously
    backdrop.style.transition = 'opacity 250ms cubic-bezier(0.4, 0, 1, 1)'
    backdrop.style.opacity = '0'
  })
  
  // Wait for the longest animation to complete
  setTimeout(done, 250)
}

// Handle escape key
onMounted(() => {
  const handleEscape = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && props.modelValue) {
      emit('update:modelValue', false)
    }
  }
  
  document.addEventListener('keydown', handleEscape)
  
  onUnmounted(() => {
    document.removeEventListener('keydown', handleEscape)
  })
})
</script>

<style scoped>

/* Safari-specific fixes for backdrop blur flickering */
@supports (-webkit-backdrop-filter: blur(1px)) {
  [style*="backdrop-filter"] {
    -webkit-transform: translateZ(0);
    transform: translateZ(0);
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
  }
}
</style>