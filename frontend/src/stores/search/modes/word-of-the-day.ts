import { ref, readonly } from 'vue'
import type { WordOfTheDayConfig, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode } from '@/types'

/**
 * Word of the Day mode configuration store
 * Handles date selection and archive viewing
 */
export function useWordOfTheDayModeConfig() {
  // ==========================================================================
  // WORD-OF-THE-DAY-SPECIFIC CONFIGURATION
  // ==========================================================================
  
  const currentDate = ref(new Date().toISOString().split('T')[0])
  const archiveView = ref(false)
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setCurrentDate = (date: string) => {
    currentDate.value = date
  }
  
  const setToday = () => {
    currentDate.value = new Date().toISOString().split('T')[0]
  }
  
  const toggleArchiveView = () => {
    archiveView.value = !archiveView.value
  }
  
  const setArchiveView = (enabled: boolean) => {
    archiveView.value = enabled
  }
  
  const getConfig = (): WordOfTheDayConfig => ({
    currentDate: currentDate.value,
    archiveView: archiveView.value
  })
  
  const setConfig = (config: Partial<WordOfTheDayConfig>) => {
    if (config.currentDate) setCurrentDate(config.currentDate)
    if (config.archiveView !== undefined) setArchiveView(config.archiveView)
  }
  
  const reset = () => {
    setToday()
    archiveView.value = false
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<any, WordOfTheDayConfig> = {
    onEnter: async (previousMode: SearchMode) => {
      console.log('📅 Entering word-of-the-day mode from:', previousMode)
      setToday() // Always start with today's word
    },
    
    onExit: async (nextMode: SearchMode) => {
      console.log('👋 Exiting word-of-the-day mode to:', nextMode)
    },
    
    validateConfig: (config: WordOfTheDayConfig) => {
      // Validate date format
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/
      return dateRegex.test(config.currentDate)
    },
    
    getDefaultConfig: () => ({
      currentDate: new Date().toISOString().split('T')[0],
      archiveView: false
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    currentDate: readonly(currentDate),
    archiveView: readonly(archiveView),
    
    // Actions
    setCurrentDate,
    setToday,
    toggleArchiveView,
    setArchiveView,
    
    // Config management
    getConfig,
    setConfig,
    reset,
    
    // Mode handler
    handler
  }
}