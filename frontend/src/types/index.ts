export interface Definition {
  id: string;
  text: string;
  example?: string;
  synonyms?: string[];
  antonyms?: string[];
}

export interface WordEntry {
  id: string;
  word: string;
  pronunciation?: {
    ipa?: string;
    phonetic?: string;
  };
  partOfSpeech: string;
  definitions: Definition[];
  etymology?: string;
  frequency?: number;
}

export interface SynthesizedDictionaryEntry {
  id: string;
  word: string;
  pronunciation?: {
    ipa?: string;
    phonetic?: string;
  };
  meanings: Array<{
    partOfSpeech: string;
    definitions: Definition[];
  }>;
  etymology?: string;
  frequency?: number;
  lastUpdated: Date;
}

export interface SearchResult {
  word: string;
  score: number;
  type: 'exact' | 'fuzzy' | 'semantic' | 'ai';
  entry?: SynthesizedDictionaryEntry;
}

export interface SearchHistory {
  id: string;
  query: string;
  timestamp: Date;
  results: SearchResult[];
}

export interface SynonymData {
  word: string;
  similarity: number;
  partOfSpeech?: string;
}

export interface ThesaurusEntry {
  word: string;
  synonyms: SynonymData[];
  antonyms: SynonymData[];
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