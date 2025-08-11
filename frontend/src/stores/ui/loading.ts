import { ref, readonly } from 'vue'

// Simple loading state composable
const isLoading = ref(false)

export function useLoadingState() {
  const setLoading = (loading: boolean) => {
    isLoading.value = loading
  }

  const toggleLoading = () => {
    isLoading.value = !isLoading.value
  }

  return {
    isLoading: readonly(isLoading),
    setLoading,
    toggleLoading
  }
}