import { ref } from 'vue';
import type { WordList, WordListItem } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';

/**
 * Composable for wordlist operations (API calls and state management)
 */
export function useWordlistOperations() {
  const { toast } = useToast();
  
  // State
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const currentWordlist = ref<WordList | null>(null);
  const currentWords = ref<WordListItem[]>([]);
  
  // Load wordlist metadata
  const loadWordlist = async (id: string): Promise<WordList | null> => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await wordlistApi.getWordlist(id);
      const wordlist: WordList = {
        id: response.data._id || response.data.id,
        name: response.data.name,
        description: response.data.description,
        hash_id: response.data.hash_id,
        words: [],
        total_words: response.data.total_words,
        unique_words: response.data.unique_words,
        learning_stats: response.data.learning_stats,
        last_accessed: response.data.last_accessed,
        created_at: response.data.created_at,
        updated_at: response.data.updated_at,
        metadata: response.data.metadata || {},
        tags: response.data.tags || [],
        is_public: response.data.is_public || false,
        owner_id: response.data.owner_id
      };
      
      currentWordlist.value = wordlist;
      return wordlist;
    } catch (err: any) {
      error.value = err.message || 'Failed to load wordlist';
      toast({
        title: "Error",
        description: error.value || undefined,
        variant: "destructive"
      });
      return null;
    } finally {
      isLoading.value = false;
    }
  };
  
  // Load wordlist words
  const loadWords = async (wordlistId: string, offset = 0, limit = 100): Promise<WordListItem[]> => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await wordlistApi.getWordlistWords(wordlistId, { offset, limit });
      const words = response.items || [];
      
      if (offset === 0) {
        currentWords.value = words;
      } else {
        currentWords.value = [...currentWords.value, ...words];
      }
      
      return words;
    } catch (err: any) {
      error.value = err.message || 'Failed to load words';
      toast({
        title: "Error",
        description: error.value || undefined,
        variant: "destructive"
      });
      return [];
    } finally {
      isLoading.value = false;
    }
  };
  
  // Submit word review
  const submitReview = async (wordlistId: string, word: string, quality: number): Promise<boolean> => {
    try {
      const response = await wordlistApi.submitWordReview(wordlistId, { word, quality });
      
      // Update local word data
      const wordIndex = currentWords.value.findIndex(w => w.word === word);
      if (wordIndex >= 0 && response.data) {
        currentWords.value[wordIndex] = {
          ...currentWords.value[wordIndex],
          mastery_level: response.data.mastery_level || currentWords.value[wordIndex].mastery_level,
          review_data: {
            ...currentWords.value[wordIndex].review_data,
            last_review_date: response.data.last_reviewed || new Date().toISOString()
          }
        };
      }
      
      return true;
    } catch (err: any) {
      toast({
        title: "Review Error",
        description: err.message || 'Failed to submit review',
        variant: "destructive"
      });
      return false;
    }
  };
  
  // Update word notes
  const updateWordNotes = async (wordlistId: string, word: string, notes: string): Promise<boolean> => {
    try {
      // Note: Backend endpoint may not exist yet, update locally for now
      const wordIndex = currentWords.value.findIndex(w => w.word === word);
      if (wordIndex >= 0) {
        currentWords.value[wordIndex] = {
          ...currentWords.value[wordIndex],
          notes
        };
      }
      
      toast({
        title: "Success",
        description: "Notes updated",
      });
      return true;
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || 'Failed to update notes',
        variant: "destructive"
      });
      return false;
    }
  };
  
  // Create new wordlist
  const createWordlist = async (data: {
    name: string;
    description?: string;
    words?: string[];
    hash_id?: string;
  }): Promise<WordList | null> => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await wordlistApi.createWordlist(data);
      
      toast({
        title: "Success",
        description: `Created wordlist "${data.name}"`,
      });
      
      return response.data;
    } catch (err: any) {
      error.value = err.message || 'Failed to create wordlist';
      toast({
        title: "Error",
        description: error.value || undefined,
        variant: "destructive"
      });
      return null;
    } finally {
      isLoading.value = false;
    }
  };
  
  // Add words to wordlist
  const addWords = async (wordlistId: string, words: string[]): Promise<boolean> => {
    try {
      await wordlistApi.addWords(wordlistId, words);
      
      toast({
        title: "Success",
        description: `Added ${words.length} words`,
      });
      
      return true;
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || 'Failed to add words',
        variant: "destructive"
      });
      return false;
    }
  };
  
  // Clear state
  const clearState = () => {
    currentWordlist.value = null;
    currentWords.value = [];
    error.value = null;
  };
  
  return {
    // State
    isLoading,
    error,
    currentWordlist,
    currentWords,
    
    // Operations
    loadWordlist,
    loadWords,
    submitReview,
    updateWordNotes,
    createWordlist,
    addWords,
    clearState
  };
}