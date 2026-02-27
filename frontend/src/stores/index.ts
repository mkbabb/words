// Core stores
export { useContentStore } from './content/content'
export { useHistoryStore } from './content/history'
export { useSearchBarStore } from './search/search-bar'

// UI stores
export { useUIStore } from './ui/ui-state'
export { useLoadingState } from './ui/loading'

// Mode stores
export { useLookupMode } from './search/modes/lookup'
export { useWordlistMode } from './search/modes/wordlist'

// Composables
export { useNotifications } from './composables/useNotifications'
export { useRouterSync } from './composables/useRouterSync'

// Types
export type { Theme } from './types/constants'
export type { Notification } from './composables/useNotifications'

// Import for useStores function
import { useContentStore } from './content/content'
import { useHistoryStore } from './content/history'
import { useSearchBarStore } from './search/search-bar'
import { useUIStore } from './ui/ui-state'
import { useNotifications } from './composables/useNotifications'
import { useLoadingState } from './ui/loading'
import { useLookupMode } from './search/modes/lookup'

// Store aggregator for components
export function useStores() {
  return {
    content: useContentStore(),
    history: useHistoryStore(),
    searchBar: useSearchBarStore(),
    notifications: useNotifications(),
    ui: useUIStore(),
    loading: useLoadingState(),
    lookupMode: useLookupMode()
  }
}

// Backward compatibility aliases
export { useUIStore as useUIState } from './ui/ui-state'
export { useNotifications as useNotificationStore } from './composables/useNotifications'
export { useLoadingState as useLoadingStore } from './ui/loading'
