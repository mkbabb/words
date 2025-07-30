/**
 * Centralized pipeline stages configuration
 * Single source of truth for all pipeline stage definitions, messages, and descriptions
 */

export interface PipelineStage {
  progress: number;
  label: string;
  description: string;
}

export interface StageMessages {
  [stageName: string]: string;
}

export interface StageDescriptions {
  [stageName: string]: string;
}

// Default pipeline stages by category
export const DEFAULT_PIPELINE_STAGES: Record<string, PipelineStage[]> = {
  lookup: [
    { progress: 5, label: 'Start', description: 'Pipeline initialization and setup' },
    { progress: 10, label: 'Search Start', description: 'Beginning multi-method word search' },
    { progress: 20, label: 'Search Complete', description: 'Found best matching word' },
    { progress: 25, label: 'Provider Fetch', description: 'Fetching from dictionary providers' },
    { progress: 60, label: 'Providers Complete', description: 'All provider data collected' },
    { progress: 70, label: 'AI Clustering', description: 'AI analyzing and clustering definitions' },
    { progress: 85, label: 'AI Synthesis', description: 'AI synthesizing comprehensive definitions' },
    { progress: 95, label: 'Storage', description: 'Saving to knowledge base' },
    { progress: 100, label: 'Complete', description: 'Pipeline complete!' },
  ],
  
  suggestions: [
    { progress: 5, label: 'Start', description: 'Initializing AI language models' },
    { progress: 20, label: 'Query Validation', description: 'Validating query intent' },
    { progress: 40, label: 'AI Generation', description: 'AI generating word suggestions' },
    { progress: 80, label: 'Ranking', description: 'Evaluating and ranking suggestions' },
    { progress: 100, label: 'Complete', description: 'Suggestions generated successfully!' },
  ],
  
  upload: [
    { progress: 5, label: 'Start', description: 'Initializing upload process' },
    { progress: 15, label: 'Reading File', description: 'Reading uploaded file content' },
    { progress: 30, label: 'Parsing', description: 'Parsing words from file' },
    { progress: 60, label: 'Processing', description: 'Creating word entries' },
    { progress: 80, label: 'Creating List', description: 'Finalizing wordlist creation' },
    { progress: 95, label: 'Finalizing', description: 'Completing upload process' },
    { progress: 100, label: 'Complete', description: 'Upload complete!' },
  ],
  
  image: [
    { progress: 10, label: 'Start', description: 'Starting image upload' },
    { progress: 30, label: 'Validation', description: 'Validating image format and size' },
    { progress: 60, label: 'Processing', description: 'Processing image data' },
    { progress: 90, label: 'Storing', description: 'Storing image data' },
    { progress: 100, label: 'Complete', description: 'Image uploaded successfully!' },
  ],
};

// Stage messages for LoadingModal
export const STAGE_MESSAGES: Record<string, StageMessages> = {
  lookup: {
    // Main pipeline stages
    START: 'Initializing lookup pipeline...',
    SEARCH_START: 'Beginning word search...',
    SEARCH_COMPLETE: 'Search results found...',
    PROVIDER_FETCH_START: 'Fetching from dictionary providers...',
    PROVIDER_FETCH_COMPLETE: 'Provider data collected...',
    AI_CLUSTERING: 'Clustering definitions by meaning...',
    AI_SYNTHESIS: 'AI synthesizing comprehensive definitions...',
    AI_FALLBACK: 'Using AI fallback for definitions...',
    STORAGE_SAVE: 'Saving to knowledge base...',
    COMPLETE: 'Lookup complete!',
    complete: 'Lookup complete!',
    
    // Provider-specific stages
    PROVIDER_FETCH_HTTP_CONNECTING: 'Connecting to dictionary APIs...',
    PROVIDER_FETCH_HTTP_DOWNLOADING: 'Downloading dictionary data...',
    PROVIDER_FETCH_HTTP_RATE_LIMITED: 'Rate limited - waiting...',
    PROVIDER_FETCH_HTTP_PARSING: 'Parsing provider responses...',
    PROVIDER_FETCH_HTTP_COMPLETE: 'Provider fetch complete...',
    PROVIDER_FETCH_ERROR: 'Provider error - retrying...',
    
    // Error state
    error: 'An error occurred',
  },
  
  suggestions: {
    START: 'Understanding your query...',
    QUERY_VALIDATION: 'Validating query intent...',
    WORD_GENERATION: 'Generating word suggestions...',
    SCORING: 'Evaluating word relevance...',
    COMPLETE: 'Suggestions ready!',
  },
};

// Detailed stage descriptions
export const STAGE_DESCRIPTIONS: Record<string, StageDescriptions> = {
  lookup: {
    START: 'Setting up search engines, AI models, and database connections.',
    SEARCH_START: 'Searching exact matches, fuzzy matches, and semantic similarities.',
    SEARCH_COMPLETE: 'Best match identified with confidence scoring.',
    PROVIDER_FETCH_START: 'Connecting to multiple dictionary APIs simultaneously.',
    PROVIDER_FETCH_COMPLETE: 'All available definitions have been retrieved.',
    AI_CLUSTERING: 'Grouping similar meanings to eliminate redundancy.',
    AI_SYNTHESIS: 'Creating comprehensive definitions with examples and usage notes.',
    AI_FALLBACK: 'Generating definitions from AI knowledge when sources are unavailable.',
    STORAGE_SAVE: 'Persisting results for faster future lookups.',
    COMPLETE: 'Your word is ready to explore!',
    complete: 'Your word is ready to explore!',
    
    // Provider-specific stages
    PROVIDER_FETCH_HTTP_CONNECTING: 'Establishing secure connections to dictionary services.',
    PROVIDER_FETCH_HTTP_DOWNLOADING: 'Retrieving raw definition data from providers.',
    PROVIDER_FETCH_HTTP_RATE_LIMITED: 'Respecting API limits - brief pause required.',
    PROVIDER_FETCH_HTTP_PARSING: 'Extracting structured data from provider responses.',
    PROVIDER_FETCH_HTTP_COMPLETE: 'Provider data successfully processed.',
    PROVIDER_FETCH_ERROR: 'Encountering issues - trying alternative sources.',
    
    // Error state
    error: 'Something went wrong. Please try again.',
  },
  
  suggestions: {
    START: 'Analyzing your descriptive query for semantic meaning.',
    QUERY_VALIDATION: 'Ensuring your query seeks word suggestions.',
    WORD_GENERATION: 'AI is finding the perfect words to match your description.',
    SCORING: 'Ranking words by relevance and aesthetic quality.',
    COMPLETE: 'Your curated word suggestions are ready!',
  },
};

// Detailed checkpoint descriptions for hover tooltips (progress-based)
export const CHECKPOINT_DESCRIPTIONS: Record<string, Record<number, string>> = {
  lookup: {
    5: 'Pipeline initialization and setup. Preparing search engines and AI processing systems.',
    10: 'Beginning multi-method word search through dictionary indices and semantic databases.',
    20: 'Search complete. Found best matching word across all available sources.',
    25: 'Starting parallel fetches from dictionary providers (Wiktionary, Oxford, Dictionary.com).',
    60: 'All provider data collected. Ready for AI processing and synthesis.',
    70: 'AI analyzing and clustering definitions by semantic meaning to reduce redundancy.',
    85: 'AI synthesizing comprehensive definitions from clustered meanings and generating examples.',
    95: 'Saving processed entry to knowledge base and updating search indices for future lookups.',
    100: 'Pipeline complete! Ready to display comprehensive word information with examples, synonyms, and pronunciation.',
  },
  
  suggestions: {
    5: 'Initializing AI language models and preparing to analyze your descriptive query.',
    20: 'Validating that your query is seeking word suggestions based on meaning or description.',
    40: 'AI is creatively generating words that match your description, considering nuance and context.',
    80: 'Evaluating and ranking suggestions by relevance, aesthetic quality, and semantic accuracy.',
    100: 'Your curated word suggestions are ready! Each word includes confidence and efflorescence scores.',
  },
  
  upload: {
    5: 'Starting upload process and preparing to read your file.',
    15: 'Reading file content and validating format.',
    30: 'Parsing words from file and extracting metadata.',
    60: 'Creating word entries and processing vocabulary.',
    80: 'Finalizing wordlist creation and organizing content.',
    95: 'Completing upload process and saving to database.',
    100: 'Upload complete! Your wordlist is ready for use.',
  },
  
  image: {
    10: 'Starting image upload process.',
    30: 'Validating image format, size, and processing metadata.',
    60: 'Processing image data and generating thumbnails.',
    90: 'Storing image data and updating references.',
    100: 'Image uploaded successfully!',
  },
};

/**
 * Get default pipeline stages for a category
 */
export function getDefaultStages(category: string): PipelineStage[] {
  return DEFAULT_PIPELINE_STAGES[category] || DEFAULT_PIPELINE_STAGES.lookup;
}

/**
 * Get stage message for a category and stage name
 */
export function getStageMessage(category: string, stageName: string): string {
  const categoryMessages = STAGE_MESSAGES[category];
  if (categoryMessages && categoryMessages[stageName]) {
    return categoryMessages[stageName];
  }
  
  // Fallback: convert stage name to readable format
  return stageName
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase()) + '...';
}

/**
 * Get stage description for a category and stage name
 */
export function getStageDescription(category: string, stageName: string): string {
  const categoryDescriptions = STAGE_DESCRIPTIONS[category];
  if (categoryDescriptions && categoryDescriptions[stageName]) {
    return categoryDescriptions[stageName];
  }
  
  return 'Processing your request...';
}

/**
 * Get checkpoint description for a category and progress value
 */
export function getCheckpointDescription(category: string, progress: number): string {
  const categoryDescriptions = CHECKPOINT_DESCRIPTIONS[category];
  if (categoryDescriptions && categoryDescriptions[progress]) {
    return categoryDescriptions[progress];
  }
  
  return `Processing pipeline stage... (${progress}%)`;
}