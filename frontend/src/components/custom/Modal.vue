<template>
  <Teleport to="body">
    <Transition
      :css="false"
      @enter="modalEnter"
      @leave="modalLeave"
      @before-enter="beforeEnter"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4"
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
        
        <!-- Modal container with proper height management and scrolling -->
        <div 
          ref="contentRef"
          class="modal-content relative z-30 w-full rounded-2xl bg-background/80 backdrop-blur-md shadow-2xl cartoon-shadow-lg border border-border/30 overflow-hidden flex flex-col"
          :class="[
            maxWidthClass,
            maxHeightClass,
          ]"
        >
          <!-- Scrollable content area -->
          <div 
            class="flex-1 overflow-y-auto scrollbar-thin"
            :class="paddingClass"
          >
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  closeOnBackdrop?: boolean
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl'
  maxHeight?: 'sm' | 'md' | 'lg' | 'xl' | 'screen' | 'viewport'
  padding?: 'sm' | 'md' | 'lg' | 'xl'
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  closeOnBackdrop: true,
  maxWidth: '3xl',
  maxHeight: 'viewport',
  padding: 'lg',
})

const emit = defineEmits<Emits>()

// Computed classes for configurability
const maxWidthClass = computed(() => {
  const widthMap = {
    'sm': 'max-w-sm',
    'md': 'max-w-md', 
    'lg': 'max-w-lg',
    'xl': 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
  }
  return widthMap[props.maxWidth]
})

const maxHeightClass = computed(() => {
  const heightMap = {
    'sm': 'max-h-96',
    'md': 'max-h-[32rem]',
    'lg': 'max-h-[40rem]',
    'xl': 'max-h-[48rem]',
    'screen': 'max-h-screen',
    'viewport': 'max-h-[calc(100dvh-2rem)]',
  }
  return heightMap[props.maxHeight]
})

const paddingClass = computed(() => {
  const paddingMap = {
    'sm': 'p-4',
    'md': 'p-6',
    'lg': 'p-8',
    'xl': 'p-10',
  }
  return paddingMap[props.padding]
})

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

// Before enter - prepare elements for animation
const beforeEnter = () => {
  // Use refs directly since beforeEnter happens after element mount
  if (backdropRef.value && contentRef.value) {
    // Set initial states without transitions
    backdropRef.value.style.transition = 'none'
    contentRef.value.style.transition = 'none'
    backdropRef.value.style.opacity = '0'
    contentRef.value.style.opacity = '0'
    contentRef.value.style.transform = 'scale(0.9) translateY(30px)'
  }
}

// Smooth enter animation
const modalEnter = (_el: Element, done: () => void) => {
  // Use refs directly for consistent element access
  if (!backdropRef.value || !contentRef.value) {
    done()
    return
  }
  
  // Force reflow to ensure initial styles are applied
  backdropRef.value.offsetHeight
  
  // Start animations
  requestAnimationFrame(() => {
    // Check refs are still valid before animating
    if (!backdropRef.value || !contentRef.value) {
      done()
      return
    }
    
    // Backdrop fades in first
    backdropRef.value.style.transition = 'opacity 250ms cubic-bezier(0.25, 0.1, 0.25, 1)'
    backdropRef.value.style.opacity = '1'
    
    // Content appears with spring-like easing
    setTimeout(() => {
      // Check refs are still valid before animating content
      if (!contentRef.value) {
        done()
        return
      }
      
      contentRef.value.style.transition = 'all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)'
      contentRef.value.style.opacity = '1'
      contentRef.value.style.transform = 'scale(1) translateY(0)'
      
      setTimeout(done, 400)
    }, 50)
  })
}

// Smooth leave animation with better lifecycle handling
const modalLeave = (el: Element, done: () => void) => {
  // Find elements directly in the leaving element to avoid ref issues
  const backdrop = el.querySelector('.absolute.inset-0') as HTMLElement
  const content = el.querySelector('.modal-content') as HTMLElement
  
  if (!backdrop || !content) {
    done()
    return
  }
  
  // Get current computed styles
  const backdropOpacity = window.getComputedStyle(backdrop).opacity
  const contentOpacity = window.getComputedStyle(content).opacity
  const contentTransform = window.getComputedStyle(content).transform
  
  // Set explicit starting values to prevent jumps
  backdrop.style.transition = 'none'
  content.style.transition = 'none'
  backdrop.style.opacity = backdropOpacity
  content.style.opacity = contentOpacity
  content.style.transform = contentTransform
  
  // Force reflow
  void (el as HTMLElement).offsetHeight
  
  // Animate out
  requestAnimationFrame(() => {
    backdrop.style.transition = 'opacity 250ms cubic-bezier(0.4, 0, 1, 1)'
    content.style.transition = 'all 250ms cubic-bezier(0.6, -0.28, 0.735, 0.045)'
    
    backdrop.style.opacity = '0'
    content.style.opacity = '0'
    content.style.transform = 'scale(0.95) translateY(20px)'
    
    setTimeout(done, 250)
  })
}

// Handle escape key and body scroll prevention
onMounted(() => {
  const handleEscape = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && props.modelValue) {
      emit('update:modelValue', false)
    }
  }
  
  document.addEventListener('keydown', handleEscape)
  
  // Prevent body scroll when modal is open
  watch(() => props.modelValue, (isOpen) => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }, { immediate: true })
  
  onUnmounted(() => {
    document.removeEventListener('keydown', handleEscape)
    document.body.style.overflow = '' // Restore scroll on unmount
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