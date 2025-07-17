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
        'relative z-10 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200',
        activeValue === option.value
          ? 'text-primary-foreground'
          : 'text-muted-foreground hover:text-foreground'
      ]"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue';
import { gsap } from 'gsap';

interface ToggleOption {
  label: string;
  value: string;
}

interface BouncyToggleProps {
  options: ToggleOption[];
  modelValue: string;
}

const props = defineProps<BouncyToggleProps>();
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
      // Bouncy background animation
      gsap.to(backgroundSlider.value, {
        width: newWidth,
        x: activeButton.offsetLeft,
        duration: 0.4,
        ease: "back.out(2.5)"
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

  // Ultra-bouncy button press animation
  gsap.timeline()
    .to(activeButton, {
      scale: 0.88,
      rotationZ: -1,
      duration: 0.08,
      ease: "power2.out"
    })
    .to(activeButton, {
      scale: 1.08,
      rotationZ: 0.5,
      duration: 0.2,
      ease: "back.out(3.5)"
    })
    .to(activeButton, {
      scale: 1,
      rotationZ: 0,
      duration: 0.12,
      ease: "elastic.out(1, 0.3)"
    });

  // Update background position with bounce
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