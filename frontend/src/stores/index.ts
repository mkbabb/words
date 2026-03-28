// Auth store
import { useAuthStore } from './auth'

// Core stores
import { useContentStore } from './content/content'
import { useHistoryStore } from './content/history'
import { useSearchBarStore } from './search/search-bar'

// UI stores
import { useUIStore } from './ui/ui-state'
import { useLoadingState } from './ui/loading'

// Mode stores
import { useLookupMode } from './search/modes/lookup'
import { useWordlistMode } from './search/modes/wordlist'

// Composables
import { useNotifications } from './composables/useNotifications'
import { useRouterSync } from './composables/useRouterSync'

// Re-export all
export {
  useAuthStore,
  useContentStore,
  useHistoryStore,
  useSearchBarStore,
  useUIStore,
  useLoadingState,
  useLookupMode,
  useWordlistMode,
  useNotifications,
  useRouterSync,
}

// Types
export type { Theme } from './types/constants'
export type { Notification } from './composables/useNotifications'

// Store aggregator for components
export function useStores() {
  return {
    auth: useAuthStore(),
    content: useContentStore(),
    history: useHistoryStore(),
    searchBar: useSearchBarStore(),
    notifications: useNotifications(),
    ui: useUIStore(),
    loading: useLoadingState(),
    lookupMode: useLookupMode(),
    wordlistMode: useWordlistMode(),
  }
}

// Backward compatibility aliases
export { useUIStore as useUIState } from './ui/ui-state'
export { useNotifications as useNotificationStore } from './composables/useNotifications'
export { useLoadingState as useLoadingStore } from './ui/loading'
