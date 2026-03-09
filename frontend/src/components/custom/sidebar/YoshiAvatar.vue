<template>
  <div
    class="yoshi-avatar from-primary/20 to-primary/10 border-primary/20 flex aspect-square items-center justify-center rounded-full border bg-gradient-to-br cursor-pointer select-none transition-transform duration-300 ease-apple-spring hover:scale-125"
    :class="{ 'animate-yoshi-bounce': bouncing, 'admin-shimmer': props.isAdmin }"
    :style="{ width: size, height: size }"
    @click="handleClick"
  >
    <img
      :src="selectedSprite"
      :alt="`Yoshi avatar (${selectedColor})`"
      class="h-[75%] w-[75%] object-contain pointer-events-none"
      draggable="false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

// Import all standing sprites statically for Vite asset hashing
import blueYoshi from '@/assets/yoshi/standing/yoshi_blue_standing.png';
import greenYoshi from '@/assets/yoshi/standing/yoshi_green_standing.png';
import lightBlueYoshi from '@/assets/yoshi/standing/yoshi_light_blue_standing.png';
import purpleYoshi from '@/assets/yoshi/standing/yoshi_purple_standing.png';
import redYoshi from '@/assets/yoshi/standing/yoshi_red_standing.png';
import yellowYoshi from '@/assets/yoshi/standing/yoshi_yellow_standing.png';

interface YoshiAvatarProps {
  size?: string;
  color?: string;
  isAdmin?: boolean;
}

const props = withDefaults(defineProps<YoshiAvatarProps>(), {
  size: '2.5rem',
  isAdmin: false,
});

const sprites: Record<string, string> = {
  blue: blueYoshi,
  green: greenYoshi,
  light_blue: lightBlueYoshi,
  purple: purpleYoshi,
  red: redYoshi,
  yellow: yellowYoshi,
};

const colors = Object.keys(sprites);

// Persist selection per session
const sessionKey = 'floridify-yoshi-color';
const getOrSetColor = (): string => {
  if (props.color) return props.color;
  const stored = sessionStorage.getItem(sessionKey);
  if (stored && colors.includes(stored)) return stored;
  const random = colors[Math.floor(Math.random() * colors.length)];
  sessionStorage.setItem(sessionKey, random);
  return random;
};

const selectedColor = ref(getOrSetColor());
const selectedSprite = computed(() => sprites[selectedColor.value] || sprites.green);

const bouncing = ref(false);
const handleClick = () => {
  bouncing.value = true;
  // Cycle color on click
  const currentIdx = colors.indexOf(selectedColor.value);
  const nextColor = colors[(currentIdx + 1) % colors.length];
  selectedColor.value = nextColor;
  sessionStorage.setItem(sessionKey, nextColor);
  // Remove animation class after it completes so it can re-trigger
  setTimeout(() => { bouncing.value = false; }, 600);
};
</script>

<style scoped>
@keyframes yoshi-bounce {
  0% { transform: scale(1); }
  20% { transform: scale(1.35); }
  40% { transform: scale(0.9); }
  60% { transform: scale(1.15); }
  80% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

.animate-yoshi-bounce {
  animation: yoshi-bounce 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes golden-shimmer {
  0% { box-shadow: 0 0 4px rgba(234, 179, 8, 0.3); border-color: rgba(234, 179, 8, 0.4); }
  50% { box-shadow: 0 0 12px rgba(234, 179, 8, 0.6); border-color: rgba(234, 179, 8, 0.8); }
  100% { box-shadow: 0 0 4px rgba(234, 179, 8, 0.3); border-color: rgba(234, 179, 8, 0.4); }
}

.admin-shimmer {
  border-width: 2px;
  animation: golden-shimmer 3s ease-in-out infinite;
}
</style>
