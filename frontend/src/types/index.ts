// Frontend-specific types that extend or adapt backend types
import type { 
  DictionaryEntryResponse,
  SearchResult,
  Definition,
  Example,
  ImageMedia
} from './api';

// Import centralized mode types for internal use in this file
import type {
  LookupMode,
  ThemeMode,
  PronunciationMode
} from './modes';

// Re-export backend-aligned types
export { 
  type Example,
  type MeaningCluster,
  type Definition,
  type SearchResult,
  type SearchMethod,
  Language,
  DictionaryProvider,
  SearchMethod as SearchMethodEnum,
  type DictionaryEntryResponse,
  type SearchResponse,
  type Pronunciation,
  type AudioFile,
  type ImageMedia,
  type WordForm,
  type UsageNote,
  type GrammarPattern,
  type Collocation,
  type Etymology,
  type ModelInfo,
  type LiteratureSource
} from './api';

// Frontend version of Definition - extends the definition from a DictionaryEntryResponse
export interface TransformedDefinition extends Definition {
  definition?: string; // Alias for 'text' to maintain compatibility
  source?: string; // Added for provider tracking
  examples: Example[]; // Always populated from response
  images: ImageMedia[]; // Always populated from response
  providers_data: Array<Record<string, any>>; // Provider data
}

// Frontend SynthesizedDictionaryEntry is actually the DictionaryEntryResponse from the API
// with optional UI-specific fields
export interface SynthesizedDictionaryEntry extends DictionaryEntryResponse {
  // UI-specific fields
  lookup_count?: number; // Number of times accessed (optional for backward compatibility)
  regeneration_count?: number; // Number of times content was regenerated (optional)
  status?: string; // Entry status (active, archived, flagged, needs_review) (optional)
}


export interface SearchHistory {
  id: string;
  query: string;
  timestamp: Date;
  results: SearchResult[];
}

export interface LookupHistory {
  id: string;
  word: string;
  timestamp: Date;
  entry: SynthesizedDictionaryEntry;
}

export interface VocabularySuggestion {
  word: string;
  reasoning?: string;
  reason?: string; // Legacy field for backward compatibility
  difficulty_level?: number;
  semantic_category?: string;
}

export interface VocabularySuggestionsResponse {
  words: string[];
  confidence: number;
}

export interface SynonymData {
  word: string;
  score: number;
  confidence?: number;
  efflorescence_score?: number;
  language_origin?: string;
  part_of_speech?: string;
  usage_note?: string;
}

export interface ThesaurusEntry {
  word: string;
  synonyms: SynonymData[];
  confidence?: number;
}

export interface WordSuggestion {
  word: string;
  confidence: number;
  efflorescence: number;
  reasoning: string;
  example_usage?: string;
}

export interface WordSuggestionResponse {
  suggestions: WordSuggestion[];
  query_type: string;
  original_query: string;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  timestamp: Date;
}

export interface PronunciationState {
  current: PronunciationMode;
  toggle: () => void;
}

export interface SearchState {
  query: string;
  isSearching: boolean;
  hasSearched: boolean;
  results: SearchResult[];
  currentEntry?: SynthesizedDictionaryEntry;
  mode: LookupMode;
}

export interface AppState {
  search: SearchState;
  history: SearchHistory[];
  pronunciation: PronunciationState;
  theme: ThemeMode;
}

// Card variant types
export const CARD_VARIANTS = ['default', 'gold', 'silver', 'bronze'] as const;
export type CardVariant = typeof CARD_VARIANTS[number];

// Provider/Source configuration
export interface SourceConfig {
    id: string;
    name: string;
    icon: any; // Component type
}

// Language configuration
export interface LanguageConfig {
    value: string;
    label: string;
    icon: any; // Component type
}

// Texture system types
export const TEXTURE_TYPES = ['clean', 'aged', 'handmade', 'kraft'] as const;
export type TextureType = typeof TEXTURE_TYPES[number];

export const TEXTURE_INTENSITIES = ['subtle', 'medium', 'strong'] as const;
export type TextureIntensity = typeof TEXTURE_INTENSITIES[number];

export interface TextureOptions {
  type: TextureType;
  intensity: TextureIntensity;
  blendMode?: 'multiply' | 'overlay' | 'soft-light' | 'normal';
  opacity?: number;
}

export interface TextureConfig {
  enabled: boolean;
  options: TextureOptions;
  customCSS?: string;
}

export interface AnimationOptions {
  speed: number;
  delay: number;
  easing: string;
  autoplay: boolean;
  loop: boolean;
}

export interface TypewriterOptions extends AnimationOptions {
  cursorVisible: boolean;
  cursorChar: string;
  pauseOnPunctuation: number;
}

export interface HandwritingOptions extends AnimationOptions {
  strokeWidth: number;
  pressure: number;
  style: 'pen' | 'pencil';
}

export interface LatexFillOptions extends AnimationOptions {
  fillDirection: 'left-to-right' | 'top-to-bottom' | 'center-out' | '3b1b-radial' | '3b1b-diamond' | '3b1b-morph';
  mathMode: boolean;
}

// Re-export wordlist types
export * from './wordlist';

// ==========================================================================
// CENTRALIZED MODE AND CONFIGURATION TYPES
// ==========================================================================

// Re-export centralized mode and configuration types
export type {
  // Core mode types (replaces 76+ inline union type instances)
  LookupMode,           // Replaces 11 instances of 'dictionary' | 'thesaurus' | 'suggestions'
  SearchMode,           // Replaces 9 instances of 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage'
  SearchSubMode,        // Generalized sub-mode type for all search modes
  SearchSubModeMap,     // Map of search modes to their sub-modes
  LoadingMode,          // Replaces 4 instances across loading components
  
  // Configuration types
  ErrorType,            // Replaces scattered error type definitions
  NotificationType,     // Replaces 6 instances across notification system
  ThemeMode,            // Replaces 3 instances: 'light' | 'dark'
  PronunciationMode,    // Replaces 4 instances: 'phonetic' | 'ipa'
  SortDirection,        // Replaces 4 instances: 'asc' | 'desc'
  ComponentSize,        // Replaces multiple size-related patterns
  
  // Mode configuration interfaces
  BaseModeConfig,
  LookupModeConfig,
  WordlistModeConfig,
  WordOfTheDayModeConfig,
  StageModeConfig,
  ModeConfigMap,
  
  // Operation interfaces
  ModeOperationOptions,
  ModeTransitionResult,
  
  // Utility types
  ConfigForMode,
  AnyModeConfig,
  ModeConfigKeys
} from './modes';

// Export type guards and utilities
export {
  isSearchMode,
  isLookupMode,
  isLoadingMode,
  isErrorType,
  DEFAULT_MODE_CONFIGS
} from './modes';
