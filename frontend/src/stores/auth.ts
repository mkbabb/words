import { defineStore } from 'pinia';
import { ref, computed, type Ref } from 'vue';
import { useAuth, useUser } from '@clerk/vue';
import { setAuthTokenGetter } from '@/api/core';
import type { UserProfile, UserRole } from '@/types/api';

// Dev mode: grant admin access without Clerk login
const DEV_ADMIN = import.meta.env.DEV && import.meta.env.VITE_DEV_ADMIN === 'true';

export const useAuthStore = defineStore('auth', () => {
  // Default refs — used when Clerk is unavailable
  let isSignedIn: Ref<boolean> = ref(false);
  let clerkUser: Ref<any> = ref(null);
  let getToken: Ref<() => Promise<string | null>> = ref(async () => null);

  // Clerk composables must be called in setup context (here).
  // When Clerk plugin is not installed (no publishable key), they throw.
  try {
    const auth = useAuth();
    const user = useUser();
    isSignedIn = auth.isSignedIn as Ref<boolean>;
    clerkUser = user.user as Ref<any>;
    getToken = auth.getToken as Ref<() => Promise<string | null>>;
  } catch {
    // Clerk not installed — fall through to dev admin or unauthenticated
  }

  // Backend profile state
  const profile = ref<UserProfile | null>(null);
  const profileLoading = ref(false);
  const profileError = ref<string | null>(null);

  // Computed auth state
  const isAuthenticated = computed(() => DEV_ADMIN || isSignedIn.value === true);
  const user = computed(() => {
    if (DEV_ADMIN && !clerkUser.value) {
      return { name: 'Dev Admin', email: '', avatar: undefined };
    }
    if (!clerkUser.value) return null;
    return {
      name: clerkUser.value.fullName || clerkUser.value.username || '',
      email: clerkUser.value.primaryEmailAddress?.emailAddress || '',
      avatar: clerkUser.value.imageUrl || undefined,
    };
  });

  const role = computed<UserRole>(() => {
    if (DEV_ADMIN) return 'admin';
    return profile.value?.role ?? 'user';
  });
  const isAdmin = computed(() => role.value === 'admin');
  const isPremium = computed(
    () => role.value === 'premium' || role.value === 'admin'
  );

  async function getAuthToken(): Promise<string | null> {
    if (!isSignedIn.value) return null;
    try {
      return await getToken.value();
    } catch {
      return null;
    }
  }

  // Pure state setters — API calls live in useAuthProfile composable
  function setProfile(value: UserProfile | null): void {
    profile.value = value;
  }

  function setProfileLoading(value: boolean): void {
    profileLoading.value = value;
  }

  function setProfileError(value: string | null): void {
    profileError.value = value;
  }

  function clearProfile(): void {
    profile.value = null;
    profileError.value = null;
  }

  setAuthTokenGetter(getAuthToken);

  return {
    profile,
    profileLoading,
    profileError,
    isAuthenticated,
    isAdmin,
    isPremium,
    role,
    user,
    getAuthToken,
    setProfile,
    setProfileLoading,
    setProfileError,
    clearProfile,
  };
});
