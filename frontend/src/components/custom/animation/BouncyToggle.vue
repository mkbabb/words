<template>
  <div class="relative flex space-x-2">
    <!-- Animated background slider -->
    <div
      ref="backgroundSlider"
      class="absolute inset-y-0 rounded-lg bg-primary shadow-sm transition-all duration-300 ease-out"
      :style="backgroundStyle"
    />
    
    <!-- Toggle buttons -->
    <button
      v-for="(option, index) in options"
      :key="option.value"
      ref="buttonRefs"
      @click="handleSelect(option.value, index)"
      :class="[
        'relative z-10 px-3 py-1.5 rounded-lg font-medium transition-all duration-200',
        activeValue === option.value
          ? 'text-primary-foreground'
          : 'text-muted-foreground hover:text-foreground',
        inheritedClass
      ]"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, useAttrs } from 'vue';
import { gsap } from 'gsap';

// Disable automatic attribute inheritance
defineOptions({
  inheritAttrs: false
});

interface ToggleOption {
  label: string;
  value: string;
  icon?: string;
}

interface BouncyToggleProps {
  options: ToggleOption[];
  modelValue: string;
}

const props = defineProps<BouncyToggleProps>();
const attrs = useAttrs();
const inheritedClass = computed(() => attrs.class || 'text-sm');
const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const backgroundSlider = ref<HTMLElement>();
const buttonRefs = ref<HTMLButtonElement[]>([]);

const activeValue = computed(() => props.modelValue);

const backgroundStyle = ref({
  width: '0px',
  transform: 'translateX(0px)'
});

const updateBackground = (activeIndex: number, animate = true) => {
  nextTick(() => {
    const activeButton = buttonRefs.value[activeIndex];
    if (!activeButton || !backgroundSlider.value) return;

    const newWidth = `${activeButton.offsetWidth}px`;
    const newTransform = `translateX(${activeButton.offsetLeft}px)`;

    if (animate) {
      // Simple bouncy background animation
      gsap.to(backgroundSlider.value, {
        width: newWidth,
        x: activeButton.offsetLeft,
        duration: 0.4,
        ease: "back.out(1.7)"
      });
    } else {
      // Immediate update for initial state
      backgroundStyle.value = {
        width: newWidth,
        transform: newTransform
      };
    }
  });
};

const handleSelect = (value: string, index: number) => {
  const activeButton = buttonRefs.value[index];
  if (!activeButton) return;

  // Simple button press animation
  gsap.timeline()
    .to(activeButton, {
      scale: 0.95,
      duration: 0.1,
      ease: "power2.out"
    })
    .to(activeButton, {
      scale: 1,
      duration: 0.2,
      ease: "back.out(1.7)"
    });

  // Update background position
  updateBackground(index, true);
  
  // Emit the new value
  emit('update:modelValue', value);
};

// Initialize background position
onMounted(() => {
  const activeIndex = props.options.findIndex(option => option.value === activeValue.value);
  if (activeIndex !== -1) {
    updateBackground(activeIndex, false);
  }
});

// Watch for external value changes
computed(() => {
  const activeIndex = props.options.findIndex(option => option.value === activeValue.value);
  if (activeIndex !== -1) {
    updateBackground(activeIndex, true);
  }
});
</script>

