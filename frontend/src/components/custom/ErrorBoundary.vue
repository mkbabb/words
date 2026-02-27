<template>
  <slot v-if="!hasError" />
  <div
    v-else
    class="flex flex-col items-center justify-center gap-4 rounded-xl border border-destructive/30 bg-destructive/5 p-8 text-center"
  >
    <div class="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-6 w-6 text-destructive"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
        />
      </svg>
    </div>

    <div class="space-y-1">
      <p class="text-sm font-medium text-foreground">
        {{ fallbackMessage }}
      </p>
      <p
        v-if="errorMessage"
        class="text-xs text-muted-foreground"
      >
        {{ errorMessage }}
      </p>
    </div>

    <button
      class="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      @click="retry"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182"
        />
      </svg>
      Try again
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

interface Props {
  fallbackMessage?: string
}

const props = withDefaults(defineProps<Props>(), {
  fallbackMessage: 'Something went wrong while rendering this section.',
})

const hasError = ref(false)
const errorMessage = ref<string | null>(null)

onErrorCaptured((error: Error, _instance, _info) => {
  hasError.value = true
  errorMessage.value = error.message || null

  // Return false to prevent the error from propagating further
  return false
})

const retry = () => {
  hasError.value = false
  errorMessage.value = null
}
</script>
