export interface Example {
  sentence: string;
  regenerable?: boolean;
  source?: string;
}

export interface Definition {
  word_type: string;
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
  facts?: FactItem[]; // AI-generated facts about the word
  etymology?: string;
  frequency?: number;
  last_updated?: string;

  // Enhanced metadata
  created_at: string; // ISO date string
  accessed_at?: string; // ISO date string
  synthesis_version?: string; // AI synthesis model version
  synthesis_quality?: number; // Overall synthesis quality score (0.0-1.0)
  definition_count: number; // Number of definitions synthesized
  fact_count: number; // Number of facts generated
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

export interface FactItem {
  content: string;
  category: string;
  confidence: number;
  generated_at: string; // ISO date string
}

export interface FactsAPIResponse {
  word: string;
  facts: FactItem[];
  confidence: number;
  categories: string[];
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

// Re-export wordlist types
export * from './wordlist';
