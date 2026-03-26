import { watch, ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import { useAuthStore } from '@/stores/auth';
import { useHistoryStore } from '@/stores/content/history';
import { useUIStore } from '@/stores/ui/ui-state';
import { usersApi } from '@/api/users';
import { logger } from '@/utils/logger';

/** Sync status indicator */
export type SyncStatusValue = 'synced' | 'pending' | 'error';

/**
 * Retry a function with exponential backoff.
 */
async function syncWithRetry(fn: () => Promise<void>, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      await fn();
      return;
    } catch {
      if (i < maxRetries - 1) {
        await new Promise((r) => setTimeout(r, 1000 * Math.pow(2, i)));
      }
    }
  }
  // All retries exhausted — caller should handle
  throw new Error('Sync failed after retries');
}

/**
 * Composable that syncs user state (preferences, history) with the backend.
 *
 * - On sign-in: pulls preferences + history from backend, merges with localStorage.
 * - On preference change: debounced push (2s) to PUT /users/me/preferences.
 * - On history update: debounced push (5s) to POST /users/me/history/sync.
 * - Retry with exponential backoff on failures (3 attempts).
 * - Exports syncStatus reactive ref.
 */
export function useStateSync() {
  const auth = useAuthStore();
  const history = useHistoryStore();
  const ui = useUIStore();

  /** Reactive sync status */
  const syncStatus = ref<SyncStatusValue>('synced');

  // Debounced preference sync (2s) with retry
  const syncPreferences = useDebounceFn(async () => {
    if (!auth.isAuthenticated) return;
    syncStatus.value = 'pending';
    try {
      await syncWithRetry(async () => {
        await usersApi.updatePreferences({
          theme: ui.theme,
          // Add other prefs as needed
        });
      });
      syncStatus.value = 'synced';
    } catch (e) {
      syncStatus.value = 'error';
      logger.warn('Failed to sync preferences:', e);
    }
  }, 2000);

  // Debounced history sync (5s) with retry
  const syncHistory = useDebounceFn(async () => {
    if (!auth.isAuthenticated) return;
    syncStatus.value = 'pending';
    try {
      await syncWithRetry(async () => {
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
      });
      syncStatus.value = 'synced';
    } catch (e) {
      syncStatus.value = 'error';
      logger.warn('Failed to sync history:', e);
    }
  }, 5000);

  // Pull state from backend on sign-in (bidirectional merge)
  async function pullState() {
    if (!auth.isAuthenticated) return;
    syncStatus.value = 'pending';

    try {
      await syncWithRetry(async () => {
        // Fetch and merge preferences
        const prefs = await usersApi.getPreferences();
        if (prefs.theme && prefs.theme !== ui.theme) {
          ui.setTheme(prefs.theme as any);
        }
      });
    } catch (e) {
      logger.warn('Failed to pull preferences:', e);
    }

    try {
      await syncWithRetry(async () => {
        // Fetch and merge history (bidirectional merge via mergeRemoteHistory)
        const remoteHistory = await usersApi.getHistory();
        if (remoteHistory.search_history?.length || remoteHistory.lookup_history?.length) {
          // mergeRemoteHistory deduplicates by timestamp and merges both directions
          history.mergeRemoteHistory(remoteHistory);
        }
      });
      syncStatus.value = 'synced';
    } catch (e) {
      syncStatus.value = 'error';
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

  return {
    syncStatus,
  };
}
