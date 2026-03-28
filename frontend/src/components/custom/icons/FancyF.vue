<template>
  <button
    ref="fancyFButton"
    :class="[
      'inline-flex items-baseline gap-0 cursor-pointer transition-fast hover:scale-105 active:scale-95 rounded-lg p-0',
      clickable ? 'hover-lift' : '',
      !clickable && mode === 'suggestions' ? 'relative overflow-hidden' : ''
    ]"
    :disabled="!clickable"
    @click="handleClick"
    :title="clickable ? getTooltipText() : undefined"
  >
    <span
      ref="fancyFMain"
      v-html="mainHtml"
      :class="[
        'font-bold transition-[transform,opacity] duration-300',
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
      <span
        ref="fancyFSubscript"
        v-html="subscriptHtml"
        :class="[
          'transition-normal',
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
import { computed, ref, watch, nextTick, onUnmounted } from 'vue';
import { CSSKeyframesAnimation } from '@mkbabb/keyframes.js';
import { useKatex } from '@mkbabb/latex-paper/vue';
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

// Helper functions (hoisted before computed properties that use them)
function getModeSubscript() {
  switch (props.mode) {
    case 'dictionary': return 'd';
    case 'thesaurus': return 't';
    case 'suggestions': return 'w';
    default: return 'd';
  }
}

function getTooltipText() {
  switch (props.mode) {
    case 'dictionary': return 'Switch to thesaurus mode';
    case 'thesaurus': return 'Switch to dictionary mode';
    case 'suggestions': return 'AI-generated word suggestions';
    default: return '';
  }
}

// KaTeX rendering (replaces the old LaTeX component)
const { renderInline } = useKatex({
  '\\ornate': '\\mathfrak',
});
const mainHtml = renderInline('\\mathfrak{F}');
const subscriptHtml = computed(() =>
  renderInline(`_{\\text{${getModeSubscript()}}}`),
);

const fancyFButton = ref<HTMLButtonElement>(); void fancyFButton;
const fancyFMain = ref<HTMLElement>();
const fancyFSubscript = ref<HTMLElement>();
const subscriptWrapper = ref<HTMLElement>();

const hasAnimatedIn = ref(false);
let breathingAnimations: CSSKeyframesAnimation<any>[] = [];

// Bounce-in entrance on first show
watch(() => props.showSubscript, (visible) => {
  if (visible && !hasAnimatedIn.value && subscriptWrapper.value) {
    hasAnimatedIn.value = true;
    const anim = new CSSKeyframesAnimation<any>({ duration: 500, fillMode: 'forwards' }, subscriptWrapper.value);
    anim.fromKeyframes({
      '0%': { transform: 'scale(0)', opacity: '0' },
      '70%': { transform: 'scale(1.1)', opacity: '0.8' },
      '100%': { transform: 'scale(1)', opacity: '1' },
    });
    anim.play();
  }
});

// Squash → overshoot → settle on click
const handleClick = () => {
  if (!props.clickable || !fancyFMain.value || !fancyFSubscript.value) return;

  [fancyFMain.value, fancyFSubscript.value].forEach((el, i) => {
    const anim = new CSSKeyframesAnimation<any>({ duration: 800, delay: i * 30, fillMode: 'forwards' }, el);
    anim.fromKeyframes({
      '0%':    { transform: 'scale(1) rotate(0deg)' },
      '12.5%': { transform: 'scale(0.85) rotate(-2deg)' },
      '50%':   { transform: 'scale(1.2) rotate(2deg)' },
      '100%':  { transform: 'scale(1) rotate(0deg)' },
    });
    anim.play();
  });

  emit('toggle-mode');
};

// Subtle breathing animation (infinite)
const startBreathingAnimation = () => {
  if (!props.clickable || !fancyFMain.value || !fancyFSubscript.value) return;

  breathingAnimations = [fancyFMain.value, fancyFSubscript.value].map((el, i) => {
    const anim = new CSSKeyframesAnimation<any>(
      { duration: 4000, iterationCount: Infinity, delay: i * 100 },
      el,
    );
    anim.fromVars([
      { transform: 'scale(1)' },
      { transform: 'scale(1.02)' },
      { transform: 'scale(1)' },
    ]);
    anim.play();
    return anim;
  });
};

nextTick(() => {
  if (props.clickable) startBreathingAnimation();
});

onUnmounted(() => {
  breathingAnimations.forEach(a => a.stop());
  breathingAnimations = [];
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