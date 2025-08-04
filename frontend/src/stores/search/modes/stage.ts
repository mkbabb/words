import { ref, readonly } from 'vue'
import type { StageConfig, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode } from '@/types'
import { DebugLevels, DEFAULT_DEBUG_LEVEL, type DebugLevel } from '@/stores/types/constants'

/**
 * Stage mode configuration store
 * Handles debug and test settings
 */
export function useStageModeConfig() {
  // ==========================================================================
  // STAGE-SPECIFIC CONFIGURATION
  // ==========================================================================
  
  const debugLevel = ref<DebugLevel>(DEFAULT_DEBUG_LEVEL)
  const testMode = ref(false)
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setDebugLevel = (level: DebugLevel) => {
    debugLevel.value = level
  }
  
  const toggleTestMode = () => {
    testMode.value = !testMode.value
  }
  
  const setTestMode = (enabled: boolean) => {
    testMode.value = enabled
  }
  
  const getConfig = (): StageConfig => ({
    debugLevel: debugLevel.value,
    testMode: testMode.value
  })
  
  const setConfig = (config: Partial<StageConfig>) => {
    if (config.debugLevel) setDebugLevel(config.debugLevel)
    if (config.testMode !== undefined) setTestMode(config.testMode)
  }
  
  const reset = () => {
    debugLevel.value = DEFAULT_DEBUG_LEVEL
    testMode.value = false
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<any, StageConfig> = {
    onEnter: async (previousMode: SearchMode) => {
      console.log('🔧 Entering stage mode from:', previousMode)
      console.log('Debug level:', debugLevel.value)
    },
    
    onExit: async (nextMode: SearchMode) => {
      console.log('👋 Exiting stage mode to:', nextMode)
      // Disable test mode when leaving
      testMode.value = false
    },
    
    validateConfig: (config: StageConfig) => {
      return Object.values(DebugLevels).includes(config.debugLevel as DebugLevel)
    },
    
    getDefaultConfig: () => ({
      debugLevel: DEFAULT_DEBUG_LEVEL,
      testMode: false
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    debugLevel: readonly(debugLevel),
    testMode: readonly(testMode),
    
    // Actions
    setDebugLevel,
    toggleTestMode,
    setTestMode,
    
    // Config management
    getConfig,
    setConfig,
    reset,
    
    // Mode handler
    handler
  }
}