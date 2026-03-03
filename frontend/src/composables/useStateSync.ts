import { watch } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { useAuthStore } from '@/stores/auth';
import { useHistoryStore } from '@/stores/content/history';
import { useUIStore } from '@/stores/ui/ui-state';
import { usersApi } from '@/api/users';
import { logger } from '@/utils/logger';

/**
 * Composable that syncs user state (preferences, history) with the backend.
 *
 * - On sign-in: pulls preferences + history from backend, merges with localStorage.
 * - On preference change: debounced push (2s) to PUT /users/me/preferences.
 * - On history update: debounced push (5s) to POST /users/me/history/sync.
 */
export function useStateSync() {
  const auth = useAuthStore();
  const history = useHistoryStore();
  const ui = useUIStore();

  // Debounced preference sync (2s)
  const syncPreferences = useDebounceFn(async () => {
    if (!auth.isAuthenticated) return;
    try {
      await usersApi.updatePreferences({
        theme: ui.theme,
        // Add other prefs as needed
      });
    } catch (e) {
      logger.warn('Failed to sync preferences:', e);
    }
  }, 2000);

  // Debounced history sync (5s)
  const syncHistory = useDebounceFn(async () => {
    if (!auth.isAuthenticated) return;
    try {
      await usersApi.syncHistory({
        search_history: history.searchHistory.map((item: any) => ({
          query: item.query,
          timestamp: item.timestamp,
          mode: item.mode,
        })),
        lookup_history: history.lookupHistory.map((item: any) => ({
          word: item.word,
          timestamp: item.timestamp,
        })),
      });
    } catch (e) {
      logger.warn('Failed to sync history:', e);
    }
  }, 5000);

  // Pull state from backend on sign-in
  async function pullState() {
    if (!auth.isAuthenticated) return;

    try {
      // Fetch and merge preferences
      const prefs = await usersApi.getPreferences();
      if (prefs.theme && prefs.theme !== ui.theme) {
        ui.setTheme(prefs.theme as any);
      }
    } catch (e) {
      logger.warn('Failed to pull preferences:', e);
    }

    try {
      // Fetch and merge history
      const remoteHistory = await usersApi.getHistory();
      if (remoteHistory.search_history?.length || remoteHistory.lookup_history?.length) {
        // Merge remote history into local store
        // The store will deduplicate internally
        history.mergeRemoteHistory?.(remoteHistory);
      }
    } catch (e) {
      logger.warn('Failed to pull history:', e);
    }
  }

  // Watch auth state → pull on sign-in
  watch(
    () => auth.isAuthenticated,
    (signedIn) => {
      if (signedIn) {
        pullState();
      }
    },
    { immediate: true }
  );

  // Watch preferences → push on change
  watch(() => ui.theme, () => {
    if (auth.isAuthenticated) syncPreferences();
  });

  // Watch history → push on change
  watch(
    () => [history.searchHistory?.length, history.lookupHistory?.length],
    () => {
      if (auth.isAuthenticated) syncHistory();
    }
  );
}
