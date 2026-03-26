<template>
  <div class="relative flex space-x-2 rounded-lg p-0.5">
    <!-- Animated background sliders -->
    <div
      v-for="(_slider, idx) in sliderElements"
      :key="'slider-' + idx"
      :ref="(el) => { if (el) sliderRefs[idx] = el as HTMLElement }"
      class="absolute inset-y-0 rounded-lg bg-primary shadow-sm"
    />
    <!-- Single slider fallback for non-multi mode -->
    <div
      v-if="!multiSelect"
      ref="backgroundSlider"
      class="absolute inset-y-0 rounded-lg bg-primary shadow-sm"
    />

    <!-- Toggle buttons -->
    <template v-for="(option, index) in options" :key="option.value">
      <TooltipProvider v-if="option.tooltip" :delay-duration="200">
        <Tooltip>
          <TooltipTrigger as-child>
            <button
              ref="buttonRefs"
              @click="handleSelect(option.value, index)"
              :class="[
                'relative z-10 px-3 py-1.5 rounded-lg font-medium transition-[color,background-color] duration-200',
                option.disabled
                  ? 'opacity-40 blur-sm cursor-not-allowed'
                  : isActive(option.value)
                    ? 'text-primary-foreground'
                    : 'text-muted-foreground/80 bg-muted/40 hover:bg-muted/60 hover:text-foreground',
                inheritedClass
              ]"
            >
              {{ option.label }}
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom" :side-offset="8">
            {{ option.tooltip }}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <button
        v-else
        ref="buttonRefs"
        @click="handleSelect(option.value, index)"
        :class="[
          'relative z-10 px-3 py-1.5 rounded-lg font-medium transition-colors duration-200',
          option.disabled
            ? 'opacity-40 blur-sm cursor-not-allowed'
            : isActive(option.value)
              ? 'text-primary-foreground'
              : 'text-muted-foreground/80 hover:text-foreground',
          inheritedClass
        ]"
      >
        {{ option.label }}
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch, onUnmounted, useAttrs } from 'vue';
import { gsap } from 'gsap';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { GSAP_EASE, GSAP_DURATION } from '@/lib/design-tokens';

// Disable automatic attribute inheritance
defineOptions({
  inheritAttrs: false
});

interface ToggleOption {
  label: string;
  value: string;
  icon?: string;
  disabled?: boolean;
  tooltip?: string;
}

interface BouncyToggleProps {
  options: ToggleOption[];
  modelValue: string | string[];
  multiSelect?: boolean;
}

const props = withDefaults(defineProps<BouncyToggleProps>(), {
  multiSelect: false,
});
const attrs = useAttrs();
const inheritedClass = computed(() => attrs.class || 'text-sm');
const emit = defineEmits<{
  'update:modelValue': [value: string | string[]];
}>();

const backgroundSlider = ref<HTMLElement>();
const buttonRefs = ref<HTMLButtonElement[]>([]);
const sliderRefs = ref<Record<number, HTMLElement>>({});

// Store current timeline for cancellation on rapid clicks
let currentSliderTimeline: gsap.core.Timeline | null = null;
let currentButtonTimeline: gsap.core.Timeline | null = null;

// For multi-select, track which values are active
const activeValues = computed<string[]>(() => {
  if (props.multiSelect) {
    return Array.isArray(props.modelValue) ? props.modelValue : [props.modelValue];
  }
  return [props.modelValue as string];
});

const isActive = (value: string) => activeValues.value.includes(value);

// For multi-select sliders
const sliderElements = computed(() => {
  if (!props.multiSelect) return [];
  return activeValues.value;
});

const updateBackground = (activeIndex: number, animate = true) => {
  if (props.multiSelect) return; // Multi-select handles its own sliders
  nextTick(() => {
    const activeButton = buttonRefs.value[activeIndex];
    if (!activeButton || !backgroundSlider.value) return;

    // Kill any in-flight slider animation
    if (currentSliderTimeline) {
      currentSliderTimeline.kill();
      currentSliderTimeline = null;
    }

    // Use GSAP for both paths — duration: 0 for instant, GSAP_DURATION.slide for animated
    const tl = gsap.timeline();
    tl.to(backgroundSlider.value, {
      width: activeButton.offsetWidth,
      x: activeButton.offsetLeft,
      duration: animate ? GSAP_DURATION.slide : 0,
      ease: animate ? GSAP_EASE.spring : 'none',
    });
    currentSliderTimeline = tl;
  });
};

const updateMultiSliders = (animate = true) => {
  if (!props.multiSelect) return;
  nextTick(() => {
    activeValues.value.forEach((value, sliderIdx) => {
      const optionIdx = props.options.findIndex(o => o.value === value);
      const button = buttonRefs.value[optionIdx];
      const slider = sliderRefs.value[sliderIdx];
      if (!button || !slider) return;

      gsap.to(slider, {
        width: button.offsetWidth,
        x: button.offsetLeft,
        duration: animate ? GSAP_DURATION.slide : 0,
        ease: animate ? GSAP_EASE.spring : 'none',
      });
    });
  });
};

const handleSelect = (value: string, index: number) => {
  const option = props.options[index];
  if (option?.disabled) return;

  const activeButton = buttonRefs.value[index];
  if (!activeButton) return;

  // Kill previous button press animation before starting new one
  if (currentButtonTimeline) {
    currentButtonTimeline.kill();
    currentButtonTimeline = null;
  }

  // Button press animation
  const tl = gsap.timeline();
  tl.to(activeButton, {
      scale: 0.95,
      duration: GSAP_DURATION.press,
      ease: GSAP_EASE.press,
    })
    .to(activeButton, {
      scale: 1,
      duration: GSAP_DURATION.release,
      ease: GSAP_EASE.spring,
    });
  currentButtonTimeline = tl;

  if (props.multiSelect) {
    const current = [...activeValues.value];
    const idx = current.indexOf(value);
    if (idx > -1) {
      // Don't deselect the last one
      if (current.length > 1) {
        current.splice(idx, 1);
      }
    } else {
      current.push(value);
    }
    emit('update:modelValue', current);
  } else {
    updateBackground(index, true);
    emit('update:modelValue', value);
  }
};

// Cleanup GSAP timelines on unmount
onUnmounted(() => {
  currentSliderTimeline?.kill();
  currentButtonTimeline?.kill();
});

// Initialize background position
onMounted(() => {
  if (props.multiSelect) {
    updateMultiSliders(false);
  } else {
    const activeIndex = props.options.findIndex(option => option.value === (props.modelValue as string));
    if (activeIndex !== -1) {
      updateBackground(activeIndex, false);
    }
  }
});

// Watch for external value changes
watch(() => props.modelValue, () => {
  if (props.multiSelect) {
    updateMultiSliders(true);
  } else {
    const activeIndex = props.options.findIndex(option => option.value === (props.modelValue as string));
    if (activeIndex !== -1) {
      updateBackground(activeIndex, true);
    }
  }
}, { deep: true });
</script>
