// Export all modular stores for direct usage
export { useSearchBarStore } from './search/search-bar'
export { useSearchConfigStore } from './search/search-config'
export { useSearchResultsStore } from './search/search-results'
export { useUIStore } from './ui/ui-state'
export { useLoadingStore } from './ui/loading'
export { useNotificationStore } from './utils/notifications'
export { useHistoryStore } from './content/history'

// Export composables
export { useSearchOrchestrator } from './composables/useSearchOrchestrator'
export { useAIMode } from './composables/useAIMode'
export { useRouterSync } from './composables/useRouterSync'

// For components that need the orchestrator pattern, provide a unified composable
import { useSearchBarStore } from './search/search-bar'
import { useSearchConfigStore } from './search/search-config'
import { useSearchResultsStore } from './search/search-results'
import { useUIStore } from './ui/ui-state'
import { useLoadingStore } from './ui/loading'
import { useNotificationStore } from './utils/notifications'
import { useHistoryStore } from './content/history'
import { useSearchOrchestrator } from './composables/useSearchOrchestrator'

/**
 * Unified stores composable for components that need multiple stores
 * This provides all stores in one import while encouraging direct store usage
 */
export function useStores() {
  return {
    searchBar: useSearchBarStore(),
    searchConfig: useSearchConfigStore(),
    searchResults: useSearchResultsStore(),
    ui: useUIStore(),
    loading: useLoadingStore(),
    notifications: useNotificationStore(),
    history: useHistoryStore(),
    orchestrator: useSearchOrchestrator()
  }
}

// Legacy export removed - this will cause TypeScript errors to guide migration
// export const useAppStore = () => {
//   throw new Error('useAppStore has been replaced with modular stores. Use useStores() or import specific stores directly.')
// }