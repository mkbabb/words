<template>
  <svg 
    width="0" 
    height="0" 
    style="position: absolute; pointer-events: none;"
  >
    <defs>
      <filter id="goo-effect">
        <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur" />
        <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7" result="goo" />
        <feComposite in="SourceGraphic" in2="goo" operator="atop"/>
      </filter>
    </defs>
  </svg>
</template>

<script setup lang="ts">
// Pure SVG filter component - no props needed for simplicity
</script>