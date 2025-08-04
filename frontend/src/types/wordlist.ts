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

export interface ReviewData {
  repetitions: number;
  ease_factor: number;
  interval: number;
  next_review_date: string;
  last_review_date: string | null;
  lapse_count: number;
  review_history: ReviewHistoryItem[];
}

export interface ReviewHistoryItem {
  date: string;
  quality: number;
  interval: number;
  ease_factor: number;
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

export enum MasteryLevel {
  DEFAULT = 'default',
  BRONZE = 'bronze', 
  SILVER = 'silver',
  GOLD = 'gold'
}

export enum Temperature {
  HOT = 'hot',
  COLD = 'cold'
}

export type CardVariant = MasteryLevel;

// Sorting types for wordlist components
export interface SortCriterion {
  id: string;
  field: SortField;
  direction: 'asc' | 'desc';
}

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
  words: string[];
  tags?: string[];
  is_public?: boolean;
  owner_id?: string;
}

export interface AddWordsRequest {
  words: string[];
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

export interface WordListSearchItem {
  word: string;
  score: number;
  mastery_level: MasteryLevel;
  review_count: number;
  notes?: string;
  tags: string[];
  frequency?: number;
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