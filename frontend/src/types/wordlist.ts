export interface WordListItem {
  word: string; // Always word text from backend
  frequency: number;
  selected_definition_ids: string[];
  mastery_level: MasteryLevel;
  temperature: Temperature;
  review_data: ReviewData;
  last_visited: string | null;
  added_date: string;
  notes: string;
  tags: string[];
}

export type CardState = 'new' | 'learning' | 'young' | 'mature' | 'relearning';

export const CardState = {
  NEW: 'new' as const,
  LEARNING: 'learning' as const,
  YOUNG: 'young' as const,
  MATURE: 'mature' as const,
  RELEARNING: 'relearning' as const,
} as const;

export interface ReviewData {
  repetitions: number;
  ease_factor: number;
  interval: number;
  next_review_date: string;
  last_review_date: string | null;
  lapse_count: number;
  review_history: ReviewHistoryItem[];
  card_state: CardState;
  learning_step: number;
  is_leech: boolean;
  graduated_interval: number;
}

export interface ReviewHistoryItem {
  date: string;
  quality: number;
  interval: number;
  ease_factor: number;
  card_state: CardState;
}

// SM-2 Quality scores
export type SM2Quality = 0 | 1 | 2 | 3 | 4 | 5;

export const SM2_LABELS: Record<SM2Quality, { label: string; description: string; color: string }> = {
  0: { label: 'Again', description: 'Complete failure to recall', color: 'destructive' },
  1: { label: 'Hard', description: 'Incorrect; answer remembered after reveal', color: 'destructive' },
  2: { label: 'Difficult', description: 'Incorrect but close', color: 'warning' },
  3: { label: 'Okay', description: 'Correct with significant difficulty', color: 'warning' },
  4: { label: 'Good', description: 'Correct with minor hesitation', color: 'primary' },
  5: { label: 'Easy', description: 'Perfect, effortless recall', color: 'success' },
};

// Review result from backend
export interface ReviewResult {
  word: string;
  card_state: CardState;
  mastery_level: MasteryLevel;
  ease_factor: number;
  interval_days: number;
  next_review_date: string;
  repetitions: number;
  lapse_count: number;
  is_leech: boolean;
  mastery_changed: boolean;
  previous_mastery: MasteryLevel | null;
  predicted_intervals: Record<number, number>;
}

// Review session types
export interface ReviewSession {
  wordlistId: string;
  words: DueWordItem[];
  currentIndex: number;
  results: ReviewSessionResult[];
  startedAt: string;
}

export interface ReviewSessionResult {
  word: string;
  quality: SM2Quality;
  timestamp: string;
  result: ReviewResult;
}

// Due word item from backend
export interface DueWordItem {
  word: string;
  mastery_level: MasteryLevel;
  card_state: CardState;
  ease_factor: number;
  interval_days: number;
  last_reviewed: string | null;
  review_count: number;
  lapse_count: number;
  is_leech: boolean;
  due_priority: number;
  predicted_intervals: Record<number, number>;
  notes: string;
}

export interface LearningStats {
  total_reviews: number;
  words_mastered: number;
  average_ease_factor: number;
  retention_rate: number;
  streak_days: number;
  last_study_date: string | null;
  study_time_minutes: number;
}

export interface WordList {
  id: string;
  name: string;
  description: string;
  hash_id: string;
  words: WordListItem[];
  total_words: number;
  unique_words: number;
  learning_stats: LearningStats;
  last_accessed: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
  tags: string[];
  is_public: boolean;
  owner_id: string | null;
}

// UI-specific types merged from wordlist-ui.ts
export type MasteryLevel = 'default' | 'bronze' | 'silver' | 'gold';
export type Temperature = 'hot' | 'cold';

// Const objects for runtime usage (dual type/value export)
export const MasteryLevel = {
  DEFAULT: 'default' as const,
  BRONZE: 'bronze' as const,
  SILVER: 'silver' as const,
  GOLD: 'gold' as const
} as const;

export const Temperature = {
  HOT: 'hot' as const,
  COLD: 'cold' as const
} as const;

// Filter types
export interface WordlistFilters {
  mastery: MasteryLevel[];
  temperature: Temperature[];
  showHotOnly: boolean;
  showDueOnly: boolean;
  minScore: number;
}

// Statistics types
export interface MasteryStats {
  default: number;
  bronze: number;
  silver: number;
  gold: number;
  total: number;
  dueForReview: number;
  [key: string]: number;
}

// File parsing types
export interface ParsedWord {
  text: string;
  frequency?: number;
  notes?: string;
  mastery?: MasteryLevel;
}

export interface WordlistEntryInput {
  source_text: string;
  resolved_text?: string;
  frequency?: number;
  notes?: string;
  tags?: string[];
}

// Upload progress types
export interface UploadProgress {
  stage: 'parsing' | 'validating' | 'uploading' | 'complete';
  progress: number;
  category: string;
  message?: string;
}

// Batch processing types
export interface BatchResult {
  word: string;
  success: boolean;
  entry?: any; // SynthesizedDictionaryEntry
  error?: string;
}

export interface BatchProcessingState {
  isProcessing: boolean;
  processed: number;
  total: number;
  currentWord: string;
  errors: string[];
}

// Modal state types
export interface ModalState {
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
}

// Form validation types
export interface ValidationRules {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
}

export interface ValidationErrors {
  [key: string]: string | undefined;
}

export type CardVariant = MasteryLevel;

// Sorting types for wordlist components - Two variants:
// Simple version for composables
export interface SimpleSortCriterion {
  key: 'word' | 'mastery' | 'temperature' | 'next_review' | 'created';
  order: 'asc' | 'desc';
}

// Advanced version for UI components
export interface AdvancedSortCriterion {
  id: string;
  field: SortField;
  direction: 'asc' | 'desc';
}

// Union type that supports both
export type SortCriterion = SimpleSortCriterion | AdvancedSortCriterion;

export type SortField = 'word' | 'mastery_level' | 'frequency' | 'added_at' | 'last_visited' | 'next_review';

export interface SortOption {
  field: SortField;
  label: string;
  icon: any;
  defaultDirection: 'asc' | 'desc';
}

export interface CreateWordListRequest {
  name: string;
  description?: string;
  words: Array<string | WordlistEntryInput>;
  tags?: string[];
  is_public?: boolean;
  owner_id?: string;
}

export interface AddWordsRequest {
  words: Array<string | WordlistEntryInput>;
}

export interface WordListsResponse {
  items: WordList[];
  total: number;
  offset: number;
  limit: number;
}

export interface WordListResponse {
  data: WordList;
  metadata?: Record<string, any>;
}

export interface WordListStats {
  basic_stats: LearningStats;
  word_counts: {
    total: number;
    unique: number;
    due_for_review: number;
  };
  mastery_distribution: {
    default: number;
    bronze: number;
    silver: number;
    gold: number;
  };
  temperature_distribution: {
    hot: number;
    cold: number;
  };
  most_frequent: WordListItem[];
  hot_words: WordListItem[];
}

export interface WordListSearchItem extends Partial<WordListItem> {
  word: string;
  score: number;
  method?: string;
  matches?: Array<{ method: string; score: number }>;
  wordlist_id?: string;
  wordlist_name?: string;
}

export interface WordListSearchResponse {
  items: WordListSearchItem[];
  total: number;
  offset: number;
  limit: number;
}

// Query parameter types that match backend models
export interface WordListQueryParams {
  // Filters
  mastery_levels?: string[];  // Filter by mastery levels (bronze, silver, gold)
  hot_only?: boolean;         // Show only hot items
  due_only?: boolean;         // Show only items due for review
  min_views?: number;
  max_views?: number;
  reviewed?: boolean;
  
  // Sorting
  sort_by?: string;           // Can be comma-separated for multiple criteria
  sort_order?: string;        // Can be comma-separated to match sort_by
  
  // Pagination
  offset?: number;
  limit?: number;
}

export interface WordListSearchQueryParams extends WordListQueryParams {
  // Search-specific parameters
  query: string;
  max_results?: number;
  min_score?: number;
  mode?: 'smart' | 'exact' | 'fuzzy' | 'semantic';

  // Override default sort to use relevance for search
  sort_by?: 'relevance' | 'added_at' | 'last_visited' | 'mastery_level' | 'view_count';
}

export interface WordListsQueryParams {
  // Wordlist filters
  name?: string;
  name_pattern?: string;
  owner_id?: string;
  is_public?: boolean;
  has_tag?: string;
  min_words?: number;
  max_words?: number;
  created_after?: string;
  created_before?: string;
  
  // Pagination and sorting
  offset?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface WordListNamesSearchParams {
  limit?: number;
}
