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
        <!-- Backdrop with blur -->
        <div
          class="absolute inset-0 bg-black/30 backdrop-blur-md"
          :class="[
            'dark:bg-black/50',
            'transition-all duration-300'
          ]"
        />
        
        <!-- Stage lighting container -->
        <div class="relative z-10 w-full max-w-4xl p-4">
          <!-- Main stage with downlighting effect -->
          <div
            class="relative mx-auto max-w-3xl"
            :class="[
              'stage-lighting',
              'rounded-2xl',
              'bg-gradient-to-b from-white/10 to-white/5',
              'dark:from-white/5 dark:to-white/2',
              'backdrop-blur-xl',
              'border border-white/20',
              'dark:border-white/10',
              'shadow-2xl',
              'overflow-hidden'
            ]"
          >
            <!-- Spotlight effect -->
            <div
              class="absolute inset-0 spotlight-glow"
              :class="[
                'bg-gradient-radial from-yellow-100/20 via-yellow-50/10 to-transparent',
                'dark:from-yellow-200/10 dark:via-yellow-100/5 dark:to-transparent',
                'animate-spotlight'
              ]"
            />
            
            <!-- Content container -->
            <div class="relative z-10 p-8">
              <slot />
            </div>
            
            <!-- Stage rim lighting -->
            <div
              class="absolute inset-0 rounded-2xl"
              :class="[
                'bg-gradient-to-b from-transparent via-transparent to-white/5',
                'dark:to-white/2',
                'pointer-events-none'
              ]"
            />
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
@keyframes spotlight {
  0%, 100% {
    background-position: 50% 20%;
    opacity: 0.8;
  }
  50% {
    background-position: 50% 40%;
    opacity: 1;
  }
}

.animate-spotlight {
  animation: spotlight 4s ease-in-out infinite;
  background-size: 200% 200%;
}

.stage-lighting {
  box-shadow:
    0 0 30px rgba(255, 215, 0, 0.1),
    0 20px 40px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.dark .stage-lighting {
  box-shadow:
    0 0 30px rgba(255, 215, 0, 0.05),
    0 20px 40px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.spotlight-glow {
  background: radial-gradient(
    ellipse 80% 50% at 50% 30%,
    rgba(255, 215, 0, 0.15) 0%,
    rgba(255, 235, 59, 0.08) 30%,
    transparent 70%
  );
}

.dark .spotlight-glow {
  background: radial-gradient(
    ellipse 80% 50% at 50% 30%,
    rgba(255, 215, 0, 0.08) 0%,
    rgba(255, 235, 59, 0.04) 30%,
    transparent 70%
  );
}

/* Custom gradient for stage lighting */
.bg-gradient-radial {
  background: radial-gradient(var(--tw-gradient-stops));
}
</style>