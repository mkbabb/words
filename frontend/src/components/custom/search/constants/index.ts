// Re-export all constants
export * from './sources';

// Search Bar Constants
export const SEARCH_BAR_CONSTANTS = {
    // Dimensions
    DEFAULT_HEIGHT: 64,
    TEXTAREA_MIN_HEIGHT: 48,
    ICON_SIZE: 48,
    
    // Animation durations (ms)
    SEARCH_DEBOUNCE: 200,
    BLUR_DELAY: 150,
    INTERACTION_DELAY: 100,
    ERROR_ANIMATION_DURATION: 600,
    REGENERATE_ROTATION: 180,
    REGENERATE_FULL_ROTATION: 360,
    
    // Search constraints
    MIN_QUERY_LENGTH: 2,
    MAX_RESULTS: 8,
    DEFAULT_WORD_COUNT: 12,
    MAX_WORD_COUNT: 25,
    AI_QUERY_MIN_LENGTH: 10,
    AI_QUERY_MIN_WORDS: 3,
    EXPAND_BUTTON_CHAR_THRESHOLD: 80,
    
    // Scroll behavior
    DEFAULT_SCROLL_INFLECTION: 0.25, // 25% of page height
    ICON_FADE_START: 0.4,
    ICON_FADE_END: 0.85,
    MIN_ICON_OPACITY: 0.1,
    MAX_SCALE: 1.0,
    MIN_SCALE: 0.88,
    MAX_OPACITY: 1.0,
    MIN_OPACITY: 0.92,
    MAX_WIDTH_START: 32, // rem
    MAX_WIDTH_END: 24, // rem
    
    // Timing
    HIDE_DELAY: 3000,
    SCROLL_THRESHOLD: 100,
    MODAL_BACKDROP_DELAY: 50,
    MODAL_CONTENT_DURATION: 250,
    MODAL_LEAVE_DURATION: 200,
} as const;

// Written number mappings
export const WRITTEN_NUMBERS: Record<string, number> = {
    'twenty-five': 25, 'twenty five': 25,
    'twenty-four': 24, 'twenty four': 24,
    'twenty-three': 23, 'twenty three': 23,
    'twenty-two': 22, 'twenty two': 22,
    'twenty-one': 21, 'twenty one': 21,
    'twenty': 20, 'nineteen': 19, 'eighteen': 18, 'seventeen': 17,
    'sixteen': 16, 'fifteen': 15, 'fourteen': 14, 'thirteen': 13,
    'twelve': 12, 'eleven': 11, 'ten': 10, 'nine': 9, 'eight': 8,
    'seven': 7, 'six': 6, 'five': 5, 'four': 4, 'three': 3, 'two': 2, 'one': 1
};

// Common phrases to word count mapping
export const PHRASE_TO_COUNT: Record<string, number> = {
    'a few': 3,
    'few': 3,
    'several': 5,
    'many': 10,
    'a lot': 10,
    'lots': 10,
    'a couple': 2,
    'couple': 2,
};

// Search modes
export const SEARCH_MODES = {
    LOOKUP: 'lookup',
    WORDLIST: 'wordlist',
    STAGE: 'stage',
} as const;

// State names
export const SEARCH_BAR_STATES = {
    NORMAL: 'normal',
    HOVERING: 'hovering',
    FOCUSED: 'focused',
} as const;