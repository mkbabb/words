<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center"
        @click="handleBackdropClick"
      >
        <!-- Backdrop with subtle blur and bg/30 -->
        <div
          class="absolute inset-0"
          :class="[
            'bg-black/30 dark:bg-black/30',
            'backdrop-blur-sm',
            'transition-opacity duration-300',
            'transform-gpu',
          ]"
        />
        
        <!-- Clean modal container -->
        <div class="relative z-10 w-full max-w-4xl p-4">
          <div class="relative mx-auto max-w-3xl rounded-2xl bg-background/95 backdrop-blur-sm border border-border/50 shadow-2xl overflow-hidden">
            <div class="p-8">
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
  
  if (event.target === event.currentTarget) {
    emit('update:modelValue', false)
  }
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