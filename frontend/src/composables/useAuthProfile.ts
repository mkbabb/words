import { watch } from 'vue'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

/**
 * Manages auth profile fetching lifecycle.
 * Call once at app initialization (e.g., App.vue setup).
 */
export function useAuthProfile() {
  const authStore = useAuthStore()

  async function fetchProfile(): Promise<void> {
    if (!authStore.isAuthenticated) return
    authStore.setProfileLoading(true)
    authStore.setProfileError(null)
    try {
      const profile = await usersApi.getProfile()
      authStore.setProfile(profile)
    } catch (e: any) {
      authStore.setProfileError(e.message || 'Failed to load profile')
      authStore.setProfile(null)
    } finally {
      authStore.setProfileLoading(false)
    }
  }

  function clearProfile(): void {
    authStore.setProfile(null)
    authStore.setProfileError(null)
  }

  // Auto-fetch on auth state changes
  watch(
    () => authStore.isAuthenticated,
    async (signedIn) => {
      if (signedIn) {
        await fetchProfile()
      } else {
        clearProfile()
      }
    },
    { immediate: true }
  )

  return { fetchProfile, clearProfile }
}
