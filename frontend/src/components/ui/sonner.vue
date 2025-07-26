<template>
  <Teleport to="body">
    <div />
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { Toaster } from 'vue-sonner'

onMounted(() => {
  // Mount the toaster when component is ready
})
</script>