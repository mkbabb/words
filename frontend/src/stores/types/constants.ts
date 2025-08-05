/**
 * Store constants and enums
 * Provides type-safe constants for store values
 */

import type { CardVariant, SortCriterion, SortField } from '@/types'
export type { CardVariant, SortCriterion, SortField }

// ==========================================================================
// UI CONSTANTS
// ==========================================================================

export const PronunciationModes = {
  PHONETIC: 'phonetic',
  IPA: 'ipa'
} as const

export type PronunciationMode = typeof PronunciationModes[keyof typeof PronunciationModes]

export const ViewModes = {
  LIST: 'list',
  GRID: 'grid'
} as const

export type ViewMode = typeof ViewModes[keyof typeof ViewModes]

export const Themes = {
  LIGHT: 'light',
  DARK: 'dark'
} as const

export type Theme = typeof Themes[keyof typeof Themes]

// ==========================================================================
// SEARCH CONSTANTS
// ==========================================================================

export const DictionarySources = {
  WIKTIONARY: 'wiktionary',
  WEBSTER: 'webster',
  OXFORD: 'oxford',
  CAMBRIDGE: 'cambridge',
  COLLINS: 'collins',
  URBAN: 'urban'
} as const

export type DictionarySource = typeof DictionarySources[keyof typeof DictionarySources]

export const Languages = {
  EN: 'en',
  ES: 'es',
  FR: 'fr',
  DE: 'de',
  IT: 'it',
  PT: 'pt',
  RU: 'ru',
  JA: 'ja',
  ZH: 'zh',
  KO: 'ko',
  AR: 'ar',
  HI: 'hi'
} as const

export type Language = typeof Languages[keyof typeof Languages]

export const LanguageNames: Record<Language, string> = {
  [Languages.EN]: 'English',
  [Languages.ES]: 'Spanish',
  [Languages.FR]: 'French',
  [Languages.DE]: 'German',
  [Languages.IT]: 'Italian',
  [Languages.PT]: 'Portuguese',
  [Languages.RU]: 'Russian',
  [Languages.JA]: 'Japanese',
  [Languages.ZH]: 'Chinese',
  [Languages.KO]: 'Korean',
  [Languages.AR]: 'Arabic',
  [Languages.HI]: 'Hindi'
}

// ==========================================================================
// WORDLIST CONSTANTS
// ==========================================================================

export const WordlistFilterTypes = {
  SHOW_BRONZE: 'showBronze',
  SHOW_SILVER: 'showSilver',
  SHOW_GOLD: 'showGold',
  SHOW_HOT_ONLY: 'showHotOnly',
  SHOW_DUE_ONLY: 'showDueOnly'
} as const

export type WordlistFilterType = typeof WordlistFilterTypes[keyof typeof WordlistFilterTypes]

export type WordlistFilters = {
  showBronze: boolean
  showSilver: boolean
  showGold: boolean
  showHotOnly: boolean
  showDueOnly: boolean
}

export const SortDirections = {
  ASC: 'asc',
  DESC: 'desc'
} as const

export type SortDirection = typeof SortDirections[keyof typeof SortDirections]

// ==========================================================================
// MODE CONSTANTS
// ==========================================================================

export const DebugLevels = {
  NONE: 'none',
  BASIC: 'basic',
  VERBOSE: 'verbose'
} as const

export type DebugLevel = typeof DebugLevels[keyof typeof DebugLevels]

// ==========================================================================
// DEFAULT VALUES
// ==========================================================================

export const DEFAULT_CARD_VARIANT: CardVariant = 'default'
export const DEFAULT_PRONUNCIATION_MODE: PronunciationMode = PronunciationModes.PHONETIC
export const DEFAULT_VIEW_MODE: ViewMode = ViewModes.LIST
export const DEFAULT_THEME: Theme = Themes.LIGHT
export const DEFAULT_LANGUAGE: Language = Languages.EN
export const DEFAULT_SOURCE: DictionarySource = DictionarySources.WIKTIONARY
export const DEFAULT_DEBUG_LEVEL: DebugLevel = DebugLevels.NONE

export const DEFAULT_SOURCES: DictionarySource[] = [DictionarySources.WIKTIONARY]
export const DEFAULT_LANGUAGES: Language[] = [Languages.EN]

export const DEFAULT_WORDLIST_FILTERS: WordlistFilters = {
  showBronze: true,
  showSilver: true,
  showGold: true,
  showHotOnly: false,
  showDueOnly: false
}

// ==========================================================================
// VALIDATION
// ==========================================================================

export function isValidCardVariant(value: string): value is CardVariant {
  return ['default', 'gold', 'silver', 'bronze'].includes(value)
}

export function isValidPronunciationMode(value: string): value is PronunciationMode {
  return Object.values(PronunciationModes).includes(value as PronunciationMode)
}

export function isValidViewMode(value: string): value is ViewMode {
  return Object.values(ViewModes).includes(value as ViewMode)
}

export function isValidTheme(value: string): value is Theme {
  return Object.values(Themes).includes(value as Theme)
}

export function isValidLanguage(value: string): value is Language {
  return Object.values(Languages).includes(value as Language)
}

export function isValidDictionarySource(value: string): value is DictionarySource {
  return Object.values(DictionarySources).includes(value as DictionarySource)
}

export function isValidDebugLevel(value: string): value is DebugLevel {
  return Object.values(DebugLevels).includes(value as DebugLevel)
}