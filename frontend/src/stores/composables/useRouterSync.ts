import { getCurrentInstance } from 'vue'
import type { SynthesizedDictionaryEntry } from '@/types'

export function useRouterSync() {
  // Helper function to update router for current lookup state
  const updateRouterForCurrentEntry = (
    currentEntry: SynthesizedDictionaryEntry | null,
    mode: 'dictionary' | 'thesaurus' | 'suggestions',
    searchMode: string
  ) => {
    // Only update router if we're in lookup mode and have an entry
    if (searchMode !== 'lookup' || !currentEntry?.word) {
      return
    }

    try {
      // Try to get router from current Vue instance
      const instance = getCurrentInstance()
      const router = instance?.appContext.app.config.globalProperties.$router

      if (!router) {
        console.log('🧭 Router not available for URL update')
        return
      }

      const word = currentEntry.word
      const currentRoute = router.currentRoute?.value

      // Determine target route based on mode
      const targetRoute = mode === 'thesaurus' ? 'Thesaurus' : 'Definition'
      const targetPath = mode === 'thesaurus' ? `/thesaurus/${word}` : `/definition/${word}`

      // Only update if we're not already on the correct route
      if (currentRoute?.name !== targetRoute || currentRoute.params.word !== word) {
        console.log('🧭 Updating router for lookup:', {
          word,
          mode,
          targetRoute,
          targetPath,
          currentRouteName: currentRoute?.name,
          currentRouteParams: currentRoute?.params
        })
        router.push(targetPath)
      } else {
        console.log('🧭 Already on correct route, no update needed:', {
          currentRoute: currentRoute?.name,
          targetRoute,
          word: currentRoute?.params.word
        })
      }
    } catch (error) {
      console.log('🧭 Could not update router:', error)
    }
  }

  const navigateToWordlist = async (wordlistId: string | null) => {
    try {
      const instance = getCurrentInstance()
      const router = instance?.appContext.app.config.globalProperties.$router

      if (!router) {
        console.log('🧭 Router not available for wordlist navigation')
        return
      }

      if (wordlistId) {
        console.log('🧭 Navigating to wordlist:', wordlistId)
        router.push(`/wordlist/${wordlistId}`)
      } else {
        console.log('🧭 No wordlist selected, going to home')
        router.push('/')
      }
    } catch (error) {
      console.error('🧭 Failed to navigate to wordlist:', error)
    }
  }

  const navigateToHome = () => {
    try {
      const instance = getCurrentInstance()
      const router = instance?.appContext.app.config.globalProperties.$router

      if (router) {
        router.push('/')
      }
    } catch (error) {
      console.error('🧭 Failed to navigate to home:', error)
    }
  }

  return {
    updateRouterForCurrentEntry,
    navigateToWordlist,
    navigateToHome
  }
}