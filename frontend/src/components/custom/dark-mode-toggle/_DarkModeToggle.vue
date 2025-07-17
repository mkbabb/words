<template>
  <!-- Credit to Kevin Powell at https://codepen.io/kevinpowell/pen/PomqjxO -->
  <button
    class="dark-mode-toggle-button"
    v-bind="$attrs"
    @click="changeTheme()"
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="472.39"
      height="472.39"
      viewBox="0 0 472.39 472.39"
    >
      <g class="toggle-sun">
        <path
          d="M403.21,167V69.18H305.38L236.2,0,167,69.18H69.18V167L0,236.2l69.18,69.18v97.83H167l69.18,69.18,69.18-69.18h97.83V305.38l69.18-69.18Zm-167,198.17a129,129,0,1,1,129-129A129,129,0,0,1,236.2,365.19Z"
        />
      </g>
      <g class="toggle-circle">
        <circle cx="236.2" cy="236.2" r="90" />
      </g>
    </svg>
  </button>
</template>

<script setup lang="ts">
import { changeTheme } from '.';

interface Props {
  size?: string;
}

withDefaults(defineProps<Props>(), {
  size: '2rem',
});
</script>

<style scoped lang="scss">
.dark-mode-toggle-button {
  cursor: pointer;
  border: 0;
  opacity: 0.8;
  padding: 0;
  border-radius: 50%;
  position: relative;
  isolation: isolate;
  z-index: 999;
  background: transparent;
  transition: opacity 0.15s ease, transform 0.15s ease;

  svg {
    fill: hsl(0 0% 10%);
    width: 100%;
    height: 100%;
  }

  &:hover,
  &:focus {
    outline: none;
    opacity: 1;
    transform: scale(1.05);
  }
  
  &::before {
    content: '';
    position: absolute;
    inset: -200%;
    z-index: -1;
    border-radius: 50%;
    opacity: 0;
    transition: opacity 0.15s ease;
    background: radial-gradient(
      circle closest-side,
      hsl(0 0% 0% / 0.15),
      transparent
    );
  }
}

.dark-mode-toggle-button::before {
  animation: pulse 650ms ease-out;
}

.toggle-sun {
  transform-origin: center center;
  transition: transform 750ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.toggle-circle {
  transform: translateX(0);
  transition: transform 500ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.dark {
  .dark-mode-toggle-button {
    background: transparent;
    
    svg {
      fill: hsl(0 0% 90%);
    }
    
    &::before {
      background: radial-gradient(
        circle closest-side,
        hsl(0 0% 100% / 0.15),
        transparent
      );
    }
  }
  
  .dark-mode-toggle-button::before {
    animation: pulse 650ms ease-out;
  }

  .toggle-sun {
    transform: rotate(0.5turn);
  }

  .toggle-circle {
    transform: translateX(-15%);
  }
}

@keyframes pulse {
  0% {
    opacity: 0;
    transform: scale(0.5);
  }
  50% {
    transform: scale(1.5);
  }
  100% {
    opacity: 0;
    transform: scale(2.5);
  }
}
</style>
