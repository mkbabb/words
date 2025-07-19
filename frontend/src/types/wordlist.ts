/**
 * WordList and Learning System Types
 * Matches backend models in backend/src/floridify/list/models.py
 */

export enum MasteryLevel {
  BRONZE = 'bronze',
  SILVER = 'silver',
  GOLD = 'gold'
}

export enum Temperature {
  HOT = 'hot',
  COLD = 'cold'
}

export interface ReviewData {
  repetitions: number;
  ease_factor: number;
  interval: number;
  next_review_date: string; // ISO date string
  last_review_date?: string; // ISO date string
  lapse_count: number;
  review_history: Array<{
    date: string;
    quality: number;
    interval: number;
    ease_factor: number;
  }>;
}

export interface WordListItem {
  text: string;
  frequency: number;
  selected_definitions: number[];
  mastery_level: MasteryLevel;
  temperature: Temperature;
  review_data: ReviewData;
  last_visited?: string; // ISO date string
  added_date: string; // ISO date string
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
  notes: string;
  tags: string[];
}

export interface LearningStats {
  total_reviews: number;
  words_mastered: number;
  average_ease_factor: number;
  retention_rate: number;
  streak_days: number;
  last_study_date?: string; // ISO date string
  study_time_minutes: number;
}

export interface WordList {
  id?: string; // MongoDB _id
  name: string;
  description: string;
  hash_id: string;
  words: WordListItem[];
  total_words: number;
  unique_words: number;
  learning_stats: LearningStats;
  last_accessed?: string; // ISO date string
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
  metadata: Record<string, any>;
  tags: string[];
  is_public: boolean;
  owner_id?: string;
}

// API Request/Response types
export interface CreateWordListRequest {
  name: string;
  description?: string;
  words: string[];
  metadata?: Record<string, any>;
  tags?: string[];
  is_public?: boolean;
}

export interface UpdateWordListRequest {
  name?: string;
  description?: string;
  words?: string[];
  metadata?: Record<string, any>;
  tags?: string[];
  is_public?: boolean;
}

export interface WordListResponse {
  wordlist: WordList;
  message?: string;
}

export interface WordListsResponse {
  wordlists: WordList[];
  total: number;
}

export interface ReviewWordRequest {
  word: string;
  quality: number; // 0-5 scale
}

export interface StudySessionRequest {
  wordlist_id: string;
  duration_minutes: number;
  words_reviewed: Array<{
    word: string;
    quality: number;
  }>;
}

// Store state extension
export interface WordListState {
  wordlists: WordList[];
  currentWordList: WordList | null;
  isLoadingWordLists: boolean;
  wordListError: string | null;
  dueForReview: WordListItem[];
  studySession: {
    active: boolean;
    startTime?: Date;
    wordsReviewed: number;
  };
}

// Helper types for UI
export interface WordListSummary {
  id: string;
  name: string;
  description: string;
  wordCount: number;
  mastered: number;
  dueForReview: number;
  lastAccessed?: Date;
  tags: string[];
}

export interface ReviewSession {
  wordlist: WordList;
  currentWord: WordListItem;
  currentIndex: number;
  totalWords: number;
  sessionStartTime: Date;
}

// Quality rating helpers
export const QualityRatings = {
  COMPLETE_BLACKOUT: 0,
  INCORRECT_REMEMBERED: 1,
  INCORRECT_EASY: 2,
  CORRECT_DIFFICULT: 3,
  CORRECT_HESITATION: 4,
  PERFECT: 5
} as const;

export type QualityRating = typeof QualityRatings[keyof typeof QualityRatings];

// Utility type for date conversion
export type DateString = string;

// Export all types
export * from './index'; // Re-export existing types