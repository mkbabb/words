<template>
  <button
    ref="fancyFButton"
    :class="[
      'inline-flex items-baseline gap-0 cursor-pointer transition-all duration-200 hover:scale-105 active:scale-95 rounded-lg p-0',
      clickable ? 'hover-lift' : ''
    ]"
    :disabled="!clickable"
    @click="handleClick"
    :title="clickable ? (mode === 'dictionary' ? 'Switch to thesaurus mode' : 'Switch to dictionary mode') : undefined"
  >
    <LaTeX
      ref="fancyFMain"
      :expression="'\\mathfrak{F}'"
      :class="[
        'text-primary font-bold transition-all duration-300',
        {
          'text-lg': size === 'sm',
          'text-2xl': size === 'base',
          'text-3xl': size === 'lg',
          'text-4xl': size === 'xl'
        }
      ]"
    />
    <div 
      :class="[
        'inline-flex items-baseline justify-center min-w-fit',
        {
          'w-1': size === 'sm',
          'w-2': size === 'base', 
          'w-3': size === 'lg',
          'w-4': size === 'xl'
        }
      ]"
    >
      <LaTeX
        ref="fancyFSubscript"
        :expression="`_{\\text{${mode === 'dictionary' ? 'd' : 't'}}}`"
        :class="[
          'text-primary transition-all duration-300',
          {
            'text-xs': size === 'sm',
            'text-base': size === 'base',
            'text-lg': size === 'lg',
            'text-xl': size === 'xl'
          }
        ]"
      />
    </div>
  </button>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { gsap } from 'gsap';
import { LaTeX } from '@/components/custom/latex';

interface FancyFProps {
  mode: 'dictionary' | 'thesaurus';
  size?: 'sm' | 'base' | 'lg' | 'xl';
  clickable?: boolean;
}

const props = withDefaults(defineProps<FancyFProps>(), {
  size: 'base',
  clickable: false,
});

const emit = defineEmits<{
  'toggle-mode': [];
}>();

// Refs for animation
const fancyFButton = ref<HTMLButtonElement>();
const fancyFMain = ref<HTMLElement>();
const fancyFSubscript = ref<HTMLElement>();

// Handle click with bouncy animation
const handleClick = () => {
  if (!props.clickable) return;
  
  // Ultra-bouncy click animation
  const timeline = gsap.timeline();
  
  timeline
    // Squash on click
    .to([fancyFMain.value, fancyFSubscript.value], {
      scale: 0.85,
      rotationZ: -2,
      duration: 0.1,
      ease: "power2.out"
    })
    // Big bounce back with overshoot
    .to([fancyFMain.value, fancyFSubscript.value], {
      scale: 1.2,
      rotationZ: 2,
      duration: 0.3,
      ease: "back.out(4)",
      stagger: 0.05
    })
    // Settle back to normal
    .to([fancyFMain.value, fancyFSubscript.value], {
      scale: 1,
      rotationZ: 0,
      duration: 0.4,
      ease: "elastic.out(1, 0.5)",
      stagger: 0.02
    });
  
  // Emit the toggle event
  emit('toggle-mode');
};

// Continuous subtle breathing animation when not clicked
const startBreathingAnimation = () => {
  if (!props.clickable) return;
  
  gsap.to([fancyFMain.value, fancyFSubscript.value], {
    scale: 1.02,
    duration: 2,
    ease: "power2.inOut",
    yoyo: true,
    repeat: -1,
    stagger: 0.1
  });
};

// Start breathing animation after component mounts
nextTick(() => {
  if (props.clickable) {
    startBreathingAnimation();
  }
});
</script>