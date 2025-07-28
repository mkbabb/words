export interface WordListItem {
  text: string;
  frequency: number;
  selected_definitions: number[];
  mastery_level: MasteryLevel;
  temperature: Temperature;
  review_data: ReviewData;
  last_visited: string | null;
  added_date: string;
  created_at: string;
  updated_at: string;
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
  BRONZE = 'bronze',
  SILVER = 'silver',
  GOLD = 'gold'
}

export enum Temperature {
  HOT = 'hot',
  COLD = 'cold'
}

export type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

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