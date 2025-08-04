/**
 * Centralized Mode Type Definitions
 * 
 * This file consolidates all mode-related types found scattered across the codebase.
 * Replaces 76+ instances of inline union types with centralized, reusable type definitions.
 */

import type { Router } from 'vue-router'
import type { SynthesizedDictionaryEntry } from './index'

// ==========================================================================
// CORE MODE TYPES
// ==========================================================================

/**
 * Dictionary/UI display modes within lookup mode
 * Replaces 11 instances of: 'dictionary' | 'thesaurus' | 'suggestions'
 */
export type LookupMode = 'dictionary' | 'thesaurus' | 'suggestions'

/**
 * Primary application search modes
 * Replaces 9 instances of: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage'
 */
export type SearchMode = 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage'

/**
 * Generalized search sub-modes for different search modes
 * Each mode can have its own set of sub-modes
 */
export type SearchSubMode<T extends SearchMode = SearchMode> = 
  T extends 'lookup' ? LookupMode :
  T extends 'wordlist' ? 'all' | 'filtered' | 'search' :
  T extends 'word-of-the-day' ? 'current' | 'archive' :
  T extends 'stage' ? 'test' | 'debug' :
  never

/**
 * Map of search modes to their available sub-modes
 */
export type SearchSubModeMap = {
  lookup: LookupMode
  wordlist: 'all' | 'filtered' | 'search'
  'word-of-the-day': 'current' | 'archive'
  stage: 'test' | 'debug'
}

/**
 * Loading operation types
 * Replaces 4 instances across loading components
 */
export type LoadingMode = 'lookup' | 'suggestions' | 'upload' | 'image'

// ==========================================================================
// CONFIGURATION TYPES
// ==========================================================================

/**
 * Error classification types
 * Replaces scattered error type definitions
 */
export type ErrorType = 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown'

/**
 * Notification types for user feedback
 * Replaces 6 instances across notification system
 */
export type NotificationType = 'success' | 'error' | 'info' | 'warning'

/**
 * Theme appearance modes
 * Replaces 3 instances across UI components
 */
export type ThemeMode = 'light' | 'dark'

/**
 * Pronunciation display modes
 * Replaces 4 instances across pronunciation components
 */
export type PronunciationMode = 'phonetic' | 'ipa'

/**
 * Sort direction for data ordering
 * Replaces 4 instances across sorting components
 */
export type SortDirection = 'asc' | 'desc'

/**
 * Component size variants
 * Replaces multiple size-related patterns
 */
export type ComponentSize = 'sm' | 'base' | 'lg' | 'xl'

/**
 * Card appearance variants (already exists in wordlist.ts but not consistently used)
 * Consolidates 4 instances
 */

// ==========================================================================
// MODE CONFIGURATION INTERFACES
// ==========================================================================

/**
 * Base configuration interface for all modes
 * Provides common structure while allowing mode-specific extensions
 */
export interface BaseModeConfig {
  /** Query string for this mode */
  query?: string
  /** Router instance for navigation */
  router?: Router
  /** Current dictionary entry (for lookup modes) */
  currentEntry?: SynthesizedDictionaryEntry | null
}

/**
 * Lookup mode specific configuration
 * Replaces scattered parameters in setSearchMode function
 */
export interface LookupModeConfig extends BaseModeConfig {
  /** Display sub-mode within lookup */
  displayMode?: LookupMode
  /** Generalized sub-mode */
  subMode?: SearchSubMode<'lookup'>
  /** Selected dictionary sources */
  sources?: string[]
  /** Selected languages */
  languages?: string[]
  /** AI processing disabled */
  noAI?: boolean
}

/**
 * Wordlist mode specific configuration
 * Consolidates scattered wordlist parameters from UI store
 */
export interface WordlistModeConfig extends BaseModeConfig {
  /** Target wordlist ID */
  wordlistId?: string | null
  /** Generalized sub-mode */
  subMode?: SearchSubMode<'wordlist'>
  /** Display filters */
  filters?: {
    showBronze?: boolean
    showSilver?: boolean
    showGold?: boolean
    showHotOnly?: boolean
    showDueOnly?: boolean
  }
  /** Chunking preferences */
  chunking?: {
    byMastery?: boolean
    byDate?: boolean
    byLastVisited?: boolean
    byFrequency?: boolean
  }
  /** Sort criteria */
  sortCriteria?: Array<{
    field: string
    direction: SortDirection
  }>
}

/**
 * Word-of-the-day mode configuration
 * Simple mode with minimal configuration needs
 */
export interface WordOfTheDayModeConfig extends BaseModeConfig {
  /** Optional date for specific word-of-the-day */
  date?: Date
  /** Generalized sub-mode */
  subMode?: SearchSubMode<'word-of-the-day'>
}

/**
 * Stage mode configuration  
 * For testing and development workflows
 */
export interface StageModeConfig extends BaseModeConfig {
  /** Debug level for stage operations */
  debugLevel?: 'minimal' | 'verbose' | 'full'
  /** Generalized sub-mode */
  subMode?: SearchSubMode<'stage'>
}

// ==========================================================================
// MODE CONFIGURATION MAP
// ==========================================================================

/**
 * Type-safe mapping of modes to their specific configurations
 * Enables generic programming with mode-specific type safety
 */
export type ModeConfigMap = {
  lookup: LookupModeConfig
  wordlist: WordlistModeConfig
  'word-of-the-day': WordOfTheDayModeConfig
  stage: StageModeConfig
}

// ==========================================================================
// MODE OPERATION INTERFACES
// ==========================================================================

/**
 * Generic mode switching options
 * Replaces the problematic 6-parameter setSearchMode function
 */
export interface ModeOperationOptions<T extends SearchMode> {
  /** Target mode */
  mode: T
  /** Mode-specific configuration */
  config?: Partial<ModeConfigMap[T]>
  /** Save current query before switching */
  saveCurrentQuery?: boolean
  /** Force mode switch even if already in target mode */
  force?: boolean
}

/**
 * Mode transition result
 * Provides feedback on mode switching operations
 */
export interface ModeTransitionResult {
  /** Whether the transition was successful */
  success: boolean
  /** Previous mode */
  previousMode: SearchMode
  /** New mode */
  newMode: SearchMode
  /** Any error that occurred */
  error?: string
  /** Navigation result */
  navigationSuccess?: boolean
}

// ==========================================================================
// TYPE GUARDS
// ==========================================================================

/**
 * Type guard for SearchMode
 * Provides safe runtime type checking
 */
export function isSearchMode(value: unknown): value is SearchMode {
  return typeof value === 'string' && 
    ['lookup', 'wordlist', 'word-of-the-day', 'stage'].includes(value)
}

/**
 * Type guard for LookupMode  
 * Provides safe runtime type checking for display modes
 */
export function isLookupMode(value: unknown): value is LookupMode {
  return typeof value === 'string' && 
    ['dictionary', 'thesaurus', 'suggestions'].includes(value)
}

/**
 * Type guard for LoadingMode
 * Provides safe runtime type checking for loading operations
 */
export function isLoadingMode(value: unknown): value is LoadingMode {
  return typeof value === 'string' && 
    ['lookup', 'suggestions', 'upload', 'image'].includes(value)
}

/**
 * Type guard for ErrorType
 * Provides safe runtime type checking for error classification
 */
export function isErrorType(value: unknown): value is ErrorType {
  return typeof value === 'string' && 
    ['network', 'not-found', 'server', 'ai-failed', 'empty', 'unknown'].includes(value)
}

// ==========================================================================
// MODE DEFAULTS
// ==========================================================================

/**
 * Default configurations for each mode
 * Provides sensible defaults while maintaining type safety
 */
export const DEFAULT_MODE_CONFIGS: ModeConfigMap = {
  lookup: {
    displayMode: 'dictionary',
    sources: ['wiktionary'],
    languages: ['en'],
    noAI: true
  },
  wordlist: {
    wordlistId: null,
    filters: {
      showBronze: true,
      showSilver: true,
      showGold: true,
      showHotOnly: false,
      showDueOnly: false
    },
    chunking: {
      byMastery: false,
      byDate: false,
      byLastVisited: false,
      byFrequency: false
    },
    sortCriteria: []
  },
  'word-of-the-day': {
    date: new Date()
  },
  stage: {
    debugLevel: 'minimal'
  }
}

// ==========================================================================
// UTILITY TYPES
// ==========================================================================

/**
 * Extract configuration type for a specific mode
 * Utility type for type-safe generic programming
 */
export type ConfigForMode<T extends SearchMode> = ModeConfigMap[T]

/**
 * Union of all mode configuration types
 * Useful for generic functions that work with any mode
 */
export type AnyModeConfig = ModeConfigMap[SearchMode]

/**
 * Mode configuration keys
 * Useful for dynamic configuration access
 */
export type ModeConfigKeys<T extends SearchMode> = keyof ModeConfigMap[T]