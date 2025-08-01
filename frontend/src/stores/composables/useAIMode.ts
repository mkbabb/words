import { computed, ref, watch, readonly, type Ref } from 'vue'
import { shouldTriggerAIMode } from '@/components/custom/search/utils/ai-query'

export function useAIMode(query: Ref<string>) {
  const isAIQuery = ref(false)
  const showSparkle = ref(false)

  // Reactive AI mode detection
  const shouldBeAI = computed(() => shouldTriggerAIMode(query.value))

  // Watch for changes in AI eligibility
  watch(shouldBeAI, (newValue) => {
    isAIQuery.value = newValue
    showSparkle.value = newValue
  }, { immediate: true })

  // Manual override functions
  const enableAIMode = () => {
    isAIQuery.value = true
    showSparkle.value = true
  }

  const disableAIMode = () => {
    isAIQuery.value = false
    showSparkle.value = false
  }

  return {
    isAIQuery: readonly(isAIQuery),
    showSparkle: readonly(showSparkle),
    shouldBeAI,
    enableAIMode,
    disableAIMode
  }
}