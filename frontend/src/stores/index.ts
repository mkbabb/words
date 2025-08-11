// Core stores
export { useContentStore } from './content/content'
export { useHistoryStore } from './content/history'
export { useSearchBarStore } from './search/search-bar'

// Composables
export { useNotifications } from './composables/useNotifications'
export { useUIState } from './composables/useUIState'
export { usePersistedState } from './composables/usePersistedState'

// Import for useStores function
import { useContentStore } from './content/content'
import { useHistoryStore } from './content/history'
import { useSearchBarStore } from './search/search-bar'
import { useNotifications } from './composables/useNotifications'
import { useUIState } from './composables/useUIState'

// Event bus
export { eventBus, useEventBus, StoreEvents } from './EventBus'
export type { StoreEventType } from './EventBus'

// State providers
export { localStorageProvider } from './providers/LocalStorageProvider'
export { migrationHelper } from './providers/MigrationHelper'
export type { StateProvider, PersistedState, StateProviderOptions } from './providers/StateProvider'
export type { Migration, MigrationFunction } from './providers/MigrationHelper'

// Types
export type { Theme } from './composables/useUIState'
export type { Notification } from './composables/useNotifications'

// Store aggregator for components
export function useStores() {
  return {
    content: useContentStore(),
    history: useHistoryStore(),
    searchBar: useSearchBarStore(),
    notifications: useNotifications(),
    ui: useUIState()
  }
}

// Alias for backward compatibility
export { useNotifications as useNotificationStore } from './composables/useNotifications'