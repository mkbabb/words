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

// Backward compatibility: Re-export APIs in original structure
export const dictionaryApi = {
  // Basic lookup (from lookup module)
  getDefinition: lookupApi.lookup, // ⚠️ RENAMED: getDefinition -> lookup
  getDefinitionStream: lookupApi.lookupStream, // ⚠️ MOVED from ai module
  
  // Search (from search module) 
  searchWord: searchApi.search, // ⚠️ MOVED to search module
  getSearchSuggestions: searchApi.getSuggestions, // ⚠️ MOVED to search module
  
  // AI-powered functionality (from ai module)
  getSynonyms: aiApi.synthesize.synonyms, // ⚠️ RESTRUCTURED
  regenerateExamples: aiApi.generate.examples, // ⚠️ RESTRUCTURED
  getAISuggestions: aiApi.suggestWords, // ⚠️ RENAMED
  getAISuggestionsStream: aiApi.suggestWordsStream, // ⚠️ RENAMED
  
  // Vocabulary suggestions (from suggestions module)
  getVocabularySuggestions: suggestionsApi.getVocabulary, // ⚠️ MOVED to suggestions module
  
  // Definition management (from definitions module)
  updateDefinition: definitionsApi.updateDefinition, // ⚠️ MOVED to definitions module
  regenerateDefinitionComponent: definitionsApi.regenerateComponents, // ⚠️ MOVED to definitions module
  getDefinitionById: definitionsApi.getDefinition, // ⚠️ MOVED to definitions module
  
  // Example management (from examples module)
  updateExample: examplesApi.updateExample, // ⚠️ MOVED to examples module
  
  // Entry management (from entries module)
  refreshSynthEntry: entriesApi.refreshEntryImages, // ⚠️ NEW: Refresh entry with updated images
  addImagesToEntry: entriesApi.addImagesToEntry, // ⚠️ NEW: Add images to synthesized entry
  removeImageFromEntry: entriesApi.removeImageFromEntry, // ⚠️ NEW: Remove image from synthesized entry
  
  // Health check (from health module)
  healthCheck: healthApi.healthCheck,
};

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