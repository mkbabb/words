<template>
    <!-- Credit to Kevin Powell at https://codepen.io/kevinpowell/pen/PomqjxO -->
    <button class="dark-mode-toggle-button" v-bind="$attrs" :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'" @click="handleToggle()">
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="472.39"
            height="472.39"
            viewBox="0 0 472.39 472.39"
        >
            <g ref="sunRef" class="toggle-sun">
                <path
                    d="M403.21,167V69.18H305.38L236.2,0,167,69.18H69.18V167L0,236.2l69.18,69.18v97.83H167l69.18,69.18,69.18-69.18h97.83V305.38l69.18-69.18Zm-167,198.17a129,129,0,1,1,129-129A129,129,0,0,1,236.2,365.19Z"
                />
            </g>
            <g ref="circleRef" class="toggle-circle">
                <circle cx="236.2" cy="236.2" r="90" />
            </g>
        </svg>
    </button>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { changeTheme, isDark, createSunAnimation, createCircleAnimation } from ".";

const sunRef = ref<SVGGElement>();
const circleRef = ref<SVGGElement>();

const handleToggle = () => {
    const toDark = !isDark.value;

    // Start animations FIRST — before the theme class change triggers a repaint
    if (sunRef.value) {
        createSunAnimation(sunRef.value as unknown as HTMLElement, toDark).play();
    }
    if (circleRef.value) {
        createCircleAnimation(circleRef.value as unknown as HTMLElement, toDark).play();
    }

    // Defer theme change to next frame so animation is already in-flight
    requestAnimationFrame(() => {
        changeTheme();
    });
};
</script>

<style scoped lang="scss">
.dark-mode-toggle-button {
    cursor: pointer;
    border: 0;
    opacity: 0.65;
    padding: 0;
    border-radius: 50%;
    position: relative;
    background: 0;

    transition: opacity 200ms, background 200ms, transform 200ms;

    z-index: auto;

    svg {
        fill: var(--color-foreground);
        width: 100%;
        height: 100%;
        pointer-events: none;
        // Smooth fill color transition when theme changes
        transition: fill 300ms ease;
    }

    &:hover,
    &:focus {
        outline: none;
        opacity: 1;
        background: hsl(0 0% 50% / 0.15);
    }

    &:active {
        transform: scale(0.9);
    }
}

.toggle-sun {
    transform-origin: center center;
    will-change: transform;
}

.toggle-circle {
    will-change: transform;
}
</style>
