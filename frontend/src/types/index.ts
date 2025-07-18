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
