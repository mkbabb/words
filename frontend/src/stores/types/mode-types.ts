import type { 
  SearchMode,
  SynthesizedDictionaryEntry,
  ThesaurusEntry,
  WordSuggestionResponse,
  WordList,
  WordListItem
} from '@/types'
import type { 
  CardVariant, 
  PronunciationMode, 
  ViewMode, 
  DictionarySource, 
  Language, 
  WordlistFilters, 
  SortCriterion,
  DebugLevel 
} from './constants'

/**
 * Mode-specific configuration interfaces
 */
export interface LookupConfig {
  selectedSources: DictionarySource[]
  selectedLanguages: Language[]
  noAI: boolean
}

export interface WordlistConfig {
  filters: WordlistFilters
  sortCriteria: SortCriterion[]
  selectedWordlist: string | null
}

export interface WordOfTheDayConfig {
  currentDate: string
  archiveView: boolean
}

export interface StageConfig {
  debugLevel: DebugLevel
  testMode: boolean
}

/**
 * Mode configuration map
 */
export interface ModeConfigMap {
  lookup: LookupConfig
  wordlist: WordlistConfig
  'word-of-the-day': WordOfTheDayConfig
  stage: StageConfig
}

/**
 * Mode-specific UI state
 */
export interface LookupUIState {
  selectedCardVariant: CardVariant
  pronunciationMode: PronunciationMode
}

export interface WordlistUIState {
  viewMode: ViewMode
  itemsPerPage: number
}

export interface WordOfTheDayUIState {
  showArchive: boolean
  dateFormat: 'short' | 'long'
}

export interface StageUIState {
  showDebugPanel: boolean
  overlayOpacity: number
}

/**
 * Mode UI state map
 */
export interface ModeUIStateMap {
  lookup: LookupUIState
  wordlist: WordlistUIState
  'word-of-the-day': WordOfTheDayUIState
  stage: StageUIState
}

/**
 * Mode-specific search bar state
 */
export interface LookupSearchBarState {
  isAIQuery: boolean
  showSparkle: boolean
  aiSuggestions: string[]
}

export interface WordlistSearchBarState {
  batchMode: boolean
  processingQueue: string[]
}

export interface WordOfTheDaySearchBarState {
  dateSelection: string | null
}

export interface StageSearchBarState {
  testQueries: string[]
  debugOutput: boolean
}

/**
 * Mode search bar state map
 */
export interface ModeSearchBarStateMap {
  lookup: LookupSearchBarState
  wordlist: WordlistSearchBarState
  'word-of-the-day': WordOfTheDaySearchBarState
  stage: StageSearchBarState
}

/**
 * Mode-specific content state
 */
export interface LookupContentState {
  currentEntry: SynthesizedDictionaryEntry | null
  currentThesaurus: ThesaurusEntry | null
  wordSuggestions: WordSuggestionResponse | null
  partialEntry: Partial<SynthesizedDictionaryEntry> | null
  isStreamingData: boolean
}

export interface WordlistContentState {
  currentWordlist: WordList | null
  processingQueue: string[]
  batchResults: Map<string, WordListItem>
}

export interface WordOfTheDayContentState {
  dailyWord: SynthesizedDictionaryEntry | null
  archive: Map<string, SynthesizedDictionaryEntry>
}

export interface StageContentState {
  testContent: Record<string, unknown> | null
  debugInfo: Map<string, unknown>
}

/**
 * Mode content state map
 */
export interface ModeContentStateMap {
  lookup: LookupContentState
  wordlist: WordlistContentState
  'word-of-the-day': WordOfTheDayContentState
  stage: StageContentState
}

/**
 * Base mode handler interface
 */
export interface ModeHandler<TState = any, TConfig = any> {
  onEnter?: (previousMode: SearchMode, config?: TConfig) => Promise<void>
  onExit?: (nextMode: SearchMode) => Promise<void>
  onConfigChange?: (config: Partial<TConfig>) => void
  validateConfig?: (config: TConfig) => boolean
  getDefaultState?: () => TState
  getDefaultConfig?: () => TConfig
}

/**
 * Mode store interface
 */
export interface ModeStore<TState, TConfig> {
  state: TState
  config: TConfig
  handler: ModeHandler<TState, TConfig>
  
  // Actions
  setState: (state: Partial<TState>) => void
  setConfig: (config: Partial<TConfig>) => void
  reset: () => void
}

/**
 * Store mode registry
 */
export interface ModeRegistry<T> {
  register: (mode: SearchMode, store: ModeStore<any, any>) => void
  unregister: (mode: SearchMode) => void
  get: <M extends SearchMode>(mode: M) => ModeStore<T, ModeConfigMap[M]> | undefined
  has: (mode: SearchMode) => boolean
  list: () => SearchMode[]
}