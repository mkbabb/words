// Frontend-specific types that extend or adapt backend types
import type { 
  LookupResponse, 
  Definition as APIDefinition,
  SearchResult as APISearchResult 
} from './api';

// Re-export backend-aligned types
export { 
  type Example,
  type MeaningCluster,
  type Definition,
  type SearchResult,
  type SearchMethod,
  type Language,
  type DictionaryProvider,
  type LookupResponse,
  type SearchResponse,
  type Pronunciation,
  type AudioFile,
  type WordForm,
  type UsageNote,
  type GrammarPattern,
  type Collocation,
  type Etymology,
  type ModelInfo,
  type LiteratureSource
} from './api';

// Frontend version of Definition with transformed examples
export interface TransformedDefinition extends Omit<APIDefinition, 'examples'> {
  definition: string; // Alias for 'text' to maintain compatibility
  examples: {
    generated: SimpleExample[];
    literature: SimpleExample[];
  };
}

export interface SynthesizedDictionaryEntry extends Omit<LookupResponse, 'definitions'> {
  definitions: TransformedDefinition[];
  etymology?: string;
  frequency?: number;
  // Frontend-specific fields for UI state
  lookup_count: number; // Number of times accessed
  regeneration_count: number; // Number of times content was regenerated
  status: string; // Entry status (active, archived, flagged, needs_review)
}

// Frontend display types
export interface SimpleExample {
  sentence: string;
  regenerable?: boolean;
  source?: string;
}

export interface SearchHistory {
  id: string;
  query: string;
  timestamp: Date;
  results: APISearchResult[];
}

export interface LookupHistory {
  id: string;
  word: string;
  timestamp: Date;
  entry: SynthesizedDictionaryEntry;
}

export interface VocabularySuggestion {
  word: string;
  reasoning: string;
  difficulty_level: number;
  semantic_category: string;
}

export interface VocabularySuggestionsResponse {
  words: string[];
  confidence: number;
}

export interface SynonymData {
  word: string;
  score: number;
}

export interface ThesaurusEntry {
  word: string;
  synonyms: SynonymData[];
  confidence?: number;
}


export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  timestamp: Date;
}

export interface PronunciationMode {
  current: 'phonetic' | 'ipa';
  toggle: () => void;
}

export interface SearchState {
  query: string;
  isSearching: boolean;
  hasSearched: boolean;
  results: APISearchResult[];
  currentEntry?: SynthesizedDictionaryEntry;
  mode: 'dictionary' | 'thesaurus';
}

export interface AppState {
  search: SearchState;
  history: SearchHistory[];
  pronunciation: PronunciationMode;
  theme: 'light' | 'dark';
}

// Card variant types
export const CARD_VARIANTS = ['default', 'gold', 'silver', 'bronze'] as const;
export type CardVariant = typeof CARD_VARIANTS[number];

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
