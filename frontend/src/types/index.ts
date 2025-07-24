export interface Example {
  sentence: string;
  regenerable?: boolean;
  source?: string;
}

export interface Definition {
  part_of_speech: string;
  definition: string;
  synonyms?: string[];
  antonyms?: string[];
  examples?: {
    generated: Example[];
    literature: Example[];
  };
  meaning_cluster?: string;
  raw_metadata?: Record<string, any>;

  // Enhanced metadata
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
  accessed_at?: string; // ISO date string
  created_by?: string; // Creator attribution
  updated_by?: string; // Last modifier attribution
  source_attribution?: string; // AI model or provider source
  version: number; // Version number for change tracking
  quality_score?: number; // Quality/confidence score (0.0-1.0)
  relevancy?: number; // Relevancy score for meaning cluster ordering (0.0-1.0)
  validation_status?: string; // Validation state
  metadata: Record<string, any>; // Extensible metadata
}

export interface SynthesizedDictionaryEntry {
  word: string;
  pronunciation?: {
    ipa?: string;
    phonetic?: string;
  };
  definitions: Definition[];
  etymology?: string;
  frequency?: number;
  last_updated?: string;

  // Enhanced metadata
  created_at: string; // ISO date string
  accessed_at?: string; // ISO date string
  synthesis_version?: string; // AI synthesis model version
  synthesis_quality?: number; // Overall synthesis quality score (0.0-1.0)
  definition_count: number; // Number of definitions synthesized
  lookup_count: number; // Number of times accessed
  regeneration_count: number; // Number of times content was regenerated
  status: string; // Entry status (active, archived, flagged, needs_review)
  metadata: Record<string, any>; // Extensible synthesis metadata
}

export interface SearchResult {
  word: string;
  score: number;
  method: 'exact' | 'fuzzy' | 'semantic' | 'prefix' | 'hybrid';
  is_phrase?: boolean;
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
  results: SearchResult[];
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
  fillDirection: 'left-to-right' | 'top-to-bottom' | 'center-out';
  mathMode: boolean;
}

// Re-export wordlist types
export * from './wordlist';
