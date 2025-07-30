# Vue.js Frontend Refactoring Implementation Guide

## Phase 1: Immediate High-Impact Refactoring

### 1. Create Base Modal Component

**File**: `/frontend/src/components/custom/base/BaseModal.vue`

```vue
<template>
  <Dialog v-model:open="isOpen">
    <DialogContent :class="modalClasses">
      <DialogHeader v-if="!hideHeader">
        <DialogTitle>
          <slot name="title">{{ title }}</slot>
        </DialogTitle>
        <DialogDescription v-if="description || $slots.description">
          <slot name="description">{{ description }}</slot>
        </DialogDescription>
      </DialogHeader>
      
      <div :class="contentClasses">
        <slot />
      </div>
      
      <DialogFooter v-if="!hideFooter" :class="footerClasses">
        <slot name="footer">
          <Button 
            v-if="showCancel" 
            variant="outline" 
            @click="handleCancel"
          >
            {{ cancelText }}
          </Button>
          <Button 
            v-if="showConfirm"
            :disabled="confirmDisabled"
            @click="handleConfirm"
          >
            {{ confirmText }}
          </Button>
        </slot>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

interface Props {
  modelValue: boolean;
  title?: string;
  description?: string;
  hideHeader?: boolean;
  hideFooter?: boolean;
  showCancel?: boolean;
  showConfirm?: boolean;
  cancelText?: string;
  confirmText?: string;
  confirmDisabled?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  contentClass?: string;
  footerClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  showCancel: true,
  showConfirm: true,
  cancelText: 'Cancel',
  confirmText: 'Confirm',
  size: 'md',
});

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'confirm': [];
  'cancel': [];
}>();

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const modalClasses = computed(() => {
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };
  return sizeClasses[props.size];
});

const contentClasses = computed(() => [
  'py-4',
  props.contentClass,
]);

const footerClasses = computed(() => [
  'flex justify-end gap-2',
  props.footerClass,
]);

function handleConfirm() {
  emit('confirm');
}

function handleCancel() {
  emit('cancel');
  isOpen.value = false;
}
</script>
```

### 2. Consolidate Store Computed Properties

**File**: `/frontend/src/stores/helpers.ts`

```typescript
import { computed, Ref, WritableComputedRef } from 'vue';

/**
 * Creates a computed property that syncs with a nested state value
 */
export function createStateRef<T, K extends keyof T>(
  state: Ref<T>,
  key: K,
  defaultValue?: T[K]
): WritableComputedRef<T[K]> {
  return computed({
    get: () => state.value[key] ?? defaultValue,
    set: (value) => {
      state.value[key] = value;
    },
  });
}

/**
 * Creates multiple computed properties from state object
 */
export function createStateRefs<T extends Record<string, any>>(
  state: Ref<T>,
  keys: (keyof T)[]
): Record<keyof T, WritableComputedRef<T[keyof T]>> {
  const refs: any = {};
  
  keys.forEach((key) => {
    refs[key] = createStateRef(state, key);
  });
  
  return refs;
}

/**
 * Generic history management for any entity type
 */
export function createHistoryManager<T extends { id: string }>(
  historyRef: Ref<T[]>,
  options: {
    maxItems?: number;
    getKey?: (item: T) => string;
    createItem: (data: any) => T;
  } = {}
) {
  const { maxItems = 50, getKey = (item) => item.id, createItem } = options;

  function add(data: any) {
    const item = createItem(data);
    const key = getKey(item);
    
    // Remove existing entry
    const existingIndex = historyRef.value.findIndex(
      (h) => getKey(h) === key
    );
    if (existingIndex >= 0) {
      historyRef.value.splice(existingIndex, 1);
    }
    
    // Add new entry at beginning
    historyRef.value.unshift(item);
    
    // Trim to max size
    if (historyRef.value.length > maxItems) {
      historyRef.value = historyRef.value.slice(0, maxItems);
    }
  }

  function clear() {
    historyRef.value = [];
  }

  function remove(key: string) {
    const index = historyRef.value.findIndex((h) => getKey(h) === key);
    if (index >= 0) {
      historyRef.value.splice(index, 1);
    }
  }

  return { add, clear, remove };
}
```

### 3. API Service Layer with Consistent Error Handling

**File**: `/frontend/src/services/api-service.ts`

```typescript
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { z } from 'zod';

export interface ApiServiceConfig {
  baseURL: string;
  timeout?: number;
  onProgress?: (progress: number) => void;
}

export class ApiService {
  private api: AxiosInstance;

  constructor(config: ApiServiceConfig) {
    this.api = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 60000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(this.transformError(error));
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.config.url}`, response.data);
        return response;
      },
      (error) => {
        console.error('API Response Error:', error);
        return Promise.reject(this.transformError(error));
      }
    );
  }

  private transformError(error: any): ApiError {
    if (error.response?.data?.error) {
      return new ApiError(
        error.response.data.error,
        error.response.status,
        error.response.data.details
      );
    }
    
    if (error.message) {
      return new ApiError(error.message, error.response?.status);
    }
    
    return new ApiError('An unknown error occurred');
  }

  /**
   * Type-safe GET request with schema validation
   */
  async get<T>(
    url: string,
    schema: z.ZodSchema<T>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.api.get(url, config);
    return this.validateResponse(response.data, schema);
  }

  /**
   * Type-safe POST request with schema validation
   */
  async post<T>(
    url: string,
    data: any,
    schema: z.ZodSchema<T>,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.api.post(url, data, config);
    return this.validateResponse(response.data, schema);
  }

  /**
   * Server-Sent Events with progress tracking
   */
  async sse<T>(
    url: string,
    schema: z.ZodSchema<T>,
    onProgress?: (stage: string, progress: number, message?: string) => void
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(url);
      let hasReceivedData = false;

      const cleanup = () => {
        eventSource.close();
      };

      // Set connection timeout
      const timeout = setTimeout(() => {
        if (!hasReceivedData) {
          cleanup();
          reject(new ApiError('Connection timeout', 408));
        }
      }, 5000);

      eventSource.addEventListener('progress', (event) => {
        hasReceivedData = true;
        clearTimeout(timeout);
        
        try {
          const data = JSON.parse(event.data);
          onProgress?.(data.stage, data.progress, data.message);
        } catch (e) {
          console.error('Failed to parse progress event:', e);
        }
      });

      eventSource.addEventListener('complete', (event) => {
        try {
          const data = JSON.parse(event.data);
          const result = this.validateResponse(data.result || data, schema);
          cleanup();
          resolve(result);
        } catch (e) {
          cleanup();
          reject(new ApiError('Failed to parse response', 422));
        }
      });

      eventSource.addEventListener('error', () => {
        cleanup();
        reject(new ApiError('Stream connection error', 500));
      });
    });
  }

  private validateResponse<T>(data: unknown, schema: z.ZodSchema<T>): T {
    try {
      return schema.parse(data);
    } catch (error) {
      if (error instanceof z.ZodError) {
        throw new ApiError(
          'Invalid response format',
          422,
          error.errors
        );
      }
      throw error;
    }
  }
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
```

### 4. Refactored Store with Helpers

**File**: `/frontend/src/stores/index.ts` (refactored excerpt)

```typescript
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useStorage } from '@vueuse/core';
import { createStateRefs, createHistoryManager } from './helpers';
import type { SearchHistory, LookupHistory } from '@/types';

export const useAppStore = defineStore('app', () => {
  // Group related runtime state
  const searchState = ref({
    isSearching: false,
    hasSearched: false,
    searchResults: [] as SearchResult[],
    loadingProgress: 0,
    loadingStage: '',
    showLoadingModal: false,
  });

  const uiSearchState = ref({
    showSearchResults: false,
    searchSelectedIndex: 0,
    isSearchBarFocused: false,
    showSearchControls: false,
    isAIQuery: false,
    showSparkle: false,
    showErrorAnimation: false,
    autocompleteText: '',
    aiSuggestions: [] as string[],
    isDirectLookup: false,
  });

  // Persisted state with validation
  const persistedState = useStorage('app-state', {
    ui: {
      mode: 'dictionary' as 'dictionary' | 'thesaurus' | 'suggestions',
      pronunciationMode: 'phonetic' as const,
      sidebarOpen: false,
      sidebarCollapsed: true,
      selectedCardVariant: 'default' as const,
      searchMode: 'lookup' as const,
      selectedSources: ['wiktionary'] as string[],
      selectedLanguages: ['en'] as string[],
      showControls: false,
      noAI: true,
      selectedWordlist: null as string | null,
    },
    session: {
      searchQueries: {
        lookup: '',
        wordlist: '',
        wordOfTheDay: '',
        stage: '',
      },
      currentWord: null as string | null,
      currentEntry: null as SynthesizedDictionaryEntry | null,
      currentThesaurus: null as ThesaurusEntry | null,
    },
  });

  // Create computed refs using helper
  const uiRefs = createStateRefs(persistedState.value.ui, [
    'mode',
    'pronunciationMode',
    'sidebarOpen',
    'sidebarCollapsed',
    'selectedCardVariant',
    'searchMode',
    'selectedSources',
    'selectedLanguages',
    'showControls',
    'noAI',
    'selectedWordlist',
  ]);

  const sessionRefs = createStateRefs(persistedState.value.session, [
    'currentWord',
    'currentEntry',
    'currentThesaurus',
  ]);

  // History management
  const searchHistory = useStorage<SearchHistory[]>('search-history', []);
  const lookupHistory = useStorage<LookupHistory[]>('lookup-history', []);

  const searchHistoryManager = createHistoryManager(searchHistory, {
    maxItems: 50,
    getKey: (item) => item.query,
    createItem: (data) => ({
      id: generateId(),
      query: data.query,
      timestamp: new Date(),
      results: data.results,
    }),
  });

  const lookupHistoryManager = createHistoryManager(lookupHistory, {
    maxItems: 50,
    getKey: (item) => item.word.toLowerCase(),
    createItem: (data) => ({
      id: generateId(),
      word: normalizeWord(data.word),
      timestamp: new Date(),
      entry: data.entry,
    }),
  });

  // Simplified search query computed
  const searchQuery = computed({
    get: () => {
      const mode = uiRefs.searchMode.value === 'word-of-the-day' 
        ? 'wordOfTheDay' 
        : uiRefs.searchMode.value;
      return persistedState.value.session.searchQueries[mode] || '';
    },
    set: (value) => {
      const mode = uiRefs.searchMode.value === 'word-of-the-day' 
        ? 'wordOfTheDay' 
        : uiRefs.searchMode.value;
      persistedState.value.session.searchQueries[mode] = value;
    },
  });

  // Return simplified API
  return {
    // State groups
    ...searchState.value,
    ...uiSearchState.value,
    ...uiRefs,
    ...sessionRefs,
    searchQuery,

    // History
    searchHistory: searchHistoryManager,
    lookupHistory: lookupHistoryManager,

    // Actions remain the same but use new state structure
    async searchWord(query: string) {
      // Implementation using new state structure
    },
  };
});
```

### 5. Extract Common Component Patterns

**File**: `/frontend/src/composables/useComponentPatterns.ts`

```typescript
import { ref, computed, Ref } from 'vue';

/**
 * Standard loading state management
 */
export function useLoadingState() {
  const isLoading = ref(false);
  const loadingMessage = ref('');
  const error = ref<Error | null>(null);

  async function withLoading<T>(
    fn: () => Promise<T>,
    message = 'Loading...'
  ): Promise<T | null> {
    isLoading.value = true;
    loadingMessage.value = message;
    error.value = null;

    try {
      const result = await fn();
      return result;
    } catch (e) {
      error.value = e as Error;
      return null;
    } finally {
      isLoading.value = false;
      loadingMessage.value = '';
    }
  }

  return {
    isLoading,
    loadingMessage,
    error,
    withLoading,
  };
}

/**
 * Reusable form validation
 */
export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  validators: Partial<Record<keyof T, (value: any) => string | null>>
) {
  const values = ref<T>({ ...initialValues });
  const errors = ref<Partial<Record<keyof T, string>>>({});
  const touched = ref<Partial<Record<keyof T, boolean>>>({});

  const isValid = computed(() => {
    return Object.keys(errors.value).length === 0;
  });

  function validate(field?: keyof T) {
    if (field) {
      const validator = validators[field];
      if (validator) {
        const error = validator(values.value[field]);
        if (error) {
          errors.value[field] = error;
        } else {
          delete errors.value[field];
        }
      }
    } else {
      // Validate all fields
      Object.keys(validators).forEach((key) => {
        validate(key as keyof T);
      });
    }
  }

  function touch(field: keyof T) {
    touched.value[field] = true;
    validate(field);
  }

  function reset() {
    values.value = { ...initialValues };
    errors.value = {};
    touched.value = {};
  }

  return {
    values,
    errors,
    touched,
    isValid,
    validate,
    touch,
    reset,
  };
}

/**
 * Standardized modal state management
 */
export function useModalState() {
  const isOpen = ref(false);
  const data = ref<any>(null);

  function open(modalData?: any) {
    data.value = modalData;
    isOpen.value = true;
  }

  function close() {
    isOpen.value = false;
    // Clear data after animation
    setTimeout(() => {
      data.value = null;
    }, 300);
  }

  return {
    isOpen,
    data,
    open,
    close,
  };
}
```

## Implementation Priority & Effort Estimates

### Week 1: Foundation (20 hours)
1. **BaseModal Component** (4 hours)
   - Create component
   - Migrate 2-3 existing modals
   - Test thoroughly

2. **Store Helpers** (6 hours)
   - Implement helper functions
   - Refactor store computed properties
   - Update component references

3. **API Service Layer** (8 hours)
   - Create service class
   - Add schema validation
   - Migrate 5-10 API calls

4. **Constants Extraction** (2 hours)
   - Create constants file
   - Replace magic numbers/strings

### Week 2: Component Refactoring (24 hours)
1. **Split SearchBar** (8 hours)
   - Extract SearchInput component
   - Create SearchBarContainer
   - Move AI logic to separate component

2. **Unify TypewriterText** (4 hours)
   - Merge implementations
   - Add feature flags
   - Update all usages

3. **Base List Components** (6 hours)
   - Create BaseListItem
   - Migrate recent items
   - Test interactions

4. **Form Composables** (6 hours)
   - Implement validation composable
   - Apply to 3-4 forms
   - Document patterns

### Week 3: Type Safety (20 hours)
1. **Replace Any Types** (8 hours)
   - Define proper interfaces
   - Update type imports
   - Add type guards

2. **API Response Validation** (8 hours)
   - Add Zod schemas
   - Implement validation layer
   - Update error handling

3. **Strict TypeScript** (4 hours)
   - Update tsconfig
   - Fix type errors
   - Add missing types

## Verification Checklist

- [ ] All components compile without TypeScript errors
- [ ] No runtime errors in console
- [ ] API calls work with new service layer
- [ ] Modals function correctly with base component
- [ ] Store state persists properly
- [ ] Performance metrics remain stable
- [ ] Code coverage maintained or improved