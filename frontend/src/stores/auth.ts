import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import { useAuth, useUser } from '@clerk/vue';
import { usersApi } from '@/api/users';
import { setAuthTokenGetter } from '@/api/core';
import type { UserProfile, UserRole } from '@/types/api/models';

export const useAuthStore = defineStore('auth', () => {
  // Clerk composables (reactive)
  const { isSignedIn, getToken } = useAuth();
  const { user: clerkUser } = useUser();

  // Backend profile state
  const profile = ref<UserProfile | null>(null);
  const profileLoading = ref(false);
  const profileError = ref<string | null>(null);

  // Dev mode: grant admin access without login (dev only)
  const devAdmin = import.meta.env.DEV && import.meta.env.VITE_DEV_ADMIN === 'true';

  // Computed auth state
  const isAuthenticated = computed(() => devAdmin || isSignedIn.value === true);
  const user = computed(() => {
    if (!clerkUser.value) return null;
    return {
      name: clerkUser.value.fullName || clerkUser.value.username || '',
      email: clerkUser.value.primaryEmailAddress?.emailAddress || '',
      avatar: clerkUser.value.imageUrl || undefined,
    };
  });

  const role = computed<UserRole>(() => {
    if (devAdmin) return 'admin';
    return profile.value?.role ?? 'user';
  });
  const isAdmin = computed(() => role.value === 'admin');
  const isPremium = computed(
    () => role.value === 'premium' || role.value === 'admin'
  );

  // Token getter for API interceptor
  async function getAuthToken(): Promise<string | null> {
    if (!isSignedIn.value) return null;
    try {
      return await getToken.value();
    } catch {
      return null;
    }
  }

  // Fetch backend profile (role, preferences)
  async function fetchProfile(): Promise<void> {
    if (!isSignedIn.value) return;
    profileLoading.value = true;
    profileError.value = null;
    try {
      profile.value = await usersApi.getProfile();
    } catch (e: any) {
      profileError.value = e.message || 'Failed to load profile';
      profile.value = null;
    } finally {
      profileLoading.value = false;
    }
  }

  // Sign out (Clerk handles the actual sign-out flow)
  function clearProfile(): void {
    profile.value = null;
    profileError.value = null;
  }

  // Wire up token getter for API interceptor
  setAuthTokenGetter(getAuthToken);

  // Auto-fetch profile when sign-in state changes
  watch(isSignedIn, async (signedIn) => {
    if (signedIn) {
      await fetchProfile();
    } else {
      clearProfile();
    }
  }, { immediate: true });

  return {
    // State
    profile,
    profileLoading,
    profileError,

    // Computed
    isAuthenticated,
    isAdmin,
    isPremium,
    role,
    user,

    // Actions
    getAuthToken,
    fetchProfile,
    clearProfile,
  };
});
