<template>
  <div
    class="yoshi-avatar from-primary/20 to-primary/10 border-primary/20 flex items-center justify-center rounded-full border bg-gradient-to-br"
    :style="{ width: size, height: size }"
  >
    <img
      :src="selectedSprite"
      :alt="`Yoshi avatar (${selectedColor})`"
      class="h-[75%] w-[75%] object-contain"
      draggable="false"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

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
}

const props = withDefaults(defineProps<YoshiAvatarProps>(), {
  size: '2.5rem',
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

const selectedColor = getOrSetColor();
const selectedSprite = computed(() => sprites[selectedColor] || sprites.green);
</script>
