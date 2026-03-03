<template>
  <button
    ref="fancyFButton"
    :class="[
      'inline-flex items-baseline gap-0 cursor-pointer transition-all duration-200 hover:scale-105 active:scale-95 rounded-lg p-0',
      clickable ? 'hover-lift' : '',
      !clickable && mode === 'suggestions' ? 'relative overflow-hidden' : ''
    ]"
    :disabled="!clickable"
    @click="handleClick"
    :title="clickable ? getTooltipText() : undefined"
  >
    <LaTeX
      ref="fancyFMain"
      :expression="'\\mathfrak{F}'"
      :class="[
        'font-bold transition-all duration-300',
        {
          'text-lg': size === 'sm',
          'text-2xl': size === 'base',
          'text-3xl': size === 'lg',
          'text-4xl': size === 'xl',
          'shimmer-text bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-400 bg-clip-text': !clickable && mode === 'suggestions'
        }
      ]"
    />
    <div
      ref="subscriptWrapper"
      :class="[
        'inline-flex items-baseline justify-center subscript-wrapper',
        {
          'subscript-hidden': !showSubscript,
          'subscript-visible': showSubscript,
        }
      ]"
    >
      <LaTeX
        ref="fancyFSubscript"
        :expression="`_{\\text{${getModeSubscript()}}}`"
        :class="[
          'transition-all duration-300',
          {
            'text-xs': size === 'sm',
            'text-base': size === 'base',
            'text-lg': size === 'lg',
            'text-xl': size === 'xl',
            'shimmer-text bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-400 bg-clip-text': !clickable && mode === 'suggestions'
          }
        ]"
      />
    </div>
  </button>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { gsap } from 'gsap';
import { LaTeX } from '@/components/custom/latex';
import type { LookupMode, ComponentSize } from '@/types';

interface FancyFProps {
  mode: LookupMode;
  size?: ComponentSize;
  clickable?: boolean;
  showSubscript?: boolean;
}

const props = withDefaults(defineProps<FancyFProps>(), {
  size: 'base',
  clickable: false,
  showSubscript: true,
});

const emit = defineEmits<{
  'toggle-mode': [];
}>();

// Refs for animation (fancyFButton bound via template ref="fancyFButton")
const fancyFButton = ref<HTMLButtonElement>(); void fancyFButton;
const fancyFMain = ref<HTMLElement>();
const fancyFSubscript = ref<HTMLElement>();
const subscriptWrapper = ref<HTMLElement>();

// Track whether the subscript has ever been shown (for entrance animation)
const hasAnimatedIn = ref(false);

// Animate subscript entrance on first show
watch(() => props.showSubscript, (visible) => {
  if (visible && !hasAnimatedIn.value && subscriptWrapper.value) {
    hasAnimatedIn.value = true;
    // Bounce-in entrance animation
    gsap.fromTo(subscriptWrapper.value,
      { scale: 0, opacity: 0 },
      {
        scale: 1,
        opacity: 1,
        duration: 0.5,
        ease: "back.out(3)",
      }
    );
  }
});

// Handle click with bouncy animation
const handleClick = () => {
  if (!props.clickable || !fancyFMain.value || !fancyFSubscript.value) return;

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

// Helper function to get mode subscript
const getModeSubscript = () => {
  switch (props.mode) {
    case 'dictionary': return 'd';
    case 'thesaurus': return 't';
    case 'suggestions': return 'w';
    default: return 'd';
  }
};

// Helper function to get tooltip text
const getTooltipText = () => {
  switch (props.mode) {
    case 'dictionary': return 'Switch to thesaurus mode';
    case 'thesaurus': return 'Switch to dictionary mode';
    case 'suggestions': return 'AI-generated word suggestions';
    default: return '';
  }
};

// Continuous subtle breathing animation when not clicked
const startBreathingAnimation = () => {
  if (!props.clickable || !fancyFMain.value || !fancyFSubscript.value) return;

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

<style scoped>
.subscript-wrapper {
  transition: opacity 0.3s ease, max-width 0.3s ease, transform 0.3s ease;
  transform-origin: left bottom;
}

.subscript-hidden {
  opacity: 0;
  max-width: 0;
  overflow: hidden;
  transform: scale(0);
}

.subscript-visible {
  opacity: 1;
  max-width: 2rem;
  overflow: visible;
}
</style>