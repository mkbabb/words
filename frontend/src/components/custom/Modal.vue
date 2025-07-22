<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-95 translate-y-4"
      enter-to-class="opacity-100 scale-100 translate-y-0"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-100 translate-y-0"
      leave-to-class="opacity-0 scale-95 translate-y-4"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[9999] flex items-center justify-center"
        @click="handleBackdropClick"
      >
        <!-- Backdrop with standard blue modal styling -->
        <div
          class="absolute inset-0 z-0"
          :class="[
            'bg-blue-900/20 dark:bg-blue-950/30',
            'backdrop-blur-md',
            'transition-all duration-300',
            'transform-gpu',
          ]"
        />
        
        <!-- Clean modal container -->
        <div class="relative z-30 w-full max-w-4xl p-4">
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
import { onMounted, onUnmounted } from 'vue'

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

const handleBackdropClick = (event: Event) => {
  if (!props.closeOnBackdrop) return
  
  // Check if the click was on the backdrop (not on modal content)
  const target = event.target as Element
  if (target.closest('.modal-content')) return
  
  emit('update:modelValue', false)
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