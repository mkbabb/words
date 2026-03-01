import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ name: string; email: string; avatar?: string } | null>(null);
  const isAuthenticated = computed(() => user.value !== null);
  const isAdmin = computed(() => {
    // For now, use a localStorage flag for dev access
    return typeof window !== 'undefined' && localStorage.getItem('floridify-admin-mode') === 'true';
  });

  const setUser = (userData: typeof user.value) => {
    user.value = userData;
  };

  const logout = () => {
    user.value = null;
  };

  return { user, isAuthenticated, isAdmin, setUser, logout };
});
