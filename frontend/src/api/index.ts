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
import { wordlistApi } from './wordlists';
import { healthApi } from './health';
import { versionsApi } from './versions';
import { audioApi } from './audio';
import { usersApi } from './users';

// Isomorphic API exports - mirrors backend structure
export { lookupApi } from './lookup';         // /lookup/*
export { searchApi } from './search';         // /search/*
export { aiApi } from './ai';                 // /ai/*
export { suggestionsApi } from './suggestions'; // /suggestions
export { definitionsApi } from './definitions'; // /definitions/*
export { examplesApi } from './examples';     // /examples/*
export { entriesApi } from './entries';       // /words/entries/*
export { mediaApi } from './media';           // /images/*, /audio/*
export { audioApi } from './audio';           // /audio/tts/*
export { wordlistApi } from './wordlists';     // /wordlists/*
export { healthApi } from './health';         // /health
export { versionsApi } from './versions';     // /words/{word}/versions/*
export { usersApi } from './users';           // /users/*



export const imageApi = {
  // Image operations (from media module)
  ...mediaApi,
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
  audio: audioApi,
  wordlists: wordlistApi,
  health: healthApi,
  versions: versionsApi,
  users: usersApi,
};