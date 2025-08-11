// Re-export the core API instance and utilities for direct usage
export { api, transformError, type APIError } from './core';

// Import all isomorphic API modules
import { lookupApi } from './lookup';
import { searchApi } from './search';
import { aiApi } from './ai';
import { suggestionsApi } from './suggestions';
import { definitionsApi } from './definitions';
import { examplesApi } from './examples';
import { entriesApi } from './entries';
import { mediaApi } from './media';
import { wordlistsApi } from './wordlists';
import { healthApi } from './health';

// Isomorphic API exports - mirrors backend structure
export { lookupApi } from './lookup';         // /lookup/*
export { searchApi } from './search';         // /search/*
export { aiApi } from './ai';                 // /ai/*
export { suggestionsApi } from './suggestions'; // /suggestions
export { definitionsApi } from './definitions'; // /definitions/*
export { examplesApi } from './examples';     // /examples/*
export { entriesApi } from './entries';       // /words/entries/*
export { mediaApi } from './media';           // /images/*, /audio/*
export { wordlistsApi } from './wordlists';   // /wordlists/*
export { healthApi } from './health';         // /health



export const imageApi = {
  // Image operations (from media module)
  ...mediaApi,
};

export const wordlistApi = {
  // Wordlist operations (from wordlists module)  
  ...wordlistsApi,
};

// Default export for convenience
export default {
  lookup: lookupApi,
  search: searchApi,
  ai: aiApi,
  suggestions: suggestionsApi,
  definitions: definitionsApi,
  examples: examplesApi,
  entries: entriesApi,
  media: mediaApi,
  wordlists: wordlistsApi,
  health: healthApi,
};