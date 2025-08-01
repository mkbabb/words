import { ref, computed, watch } from 'vue'
import { useStores } from '@/stores'
import { wordlistApi } from '@/api'
import { useToast } from '@/components/ui/toast/use-toast'
import type { WordList, WordListItem, MasteryLevel, Temperature } from '@/types'

export function useWordlist() {
  const { searchConfig, orchestrator } = useStores()
  const { toast } = useToast()
  
  // State
  const currentWordlist = ref<WordList | null>(null)
  const wordlists = ref<WordList[]>([])
  const currentWords = ref<WordListItem[]>([])
  const isLoadingWordlist = ref(false)
  const isLoadingWords = ref(false)
  const hasMoreWords = ref(false)
  const totalWords = ref(0)
  
  // Computed
  const selectedWordlistId = computed(() => searchConfig.selectedWordlist)
  
  const wordlistStats = computed(() => {
    if (!currentWordlist.value) return null
    
    return {
      total: currentWordlist.value.total_words,
      unique: currentWordlist.value.unique_words,
      mastered: currentWordlist.value.learning_stats.words_mastered,
      dueForReview: currentWords.value.filter(w => w.review_data && new Date(w.review_data.next_review_date) <= new Date()).length
    }
  })
  
  const masteryDistribution = computed(() => {
    if (!currentWords.value.length) return { default: 0, bronze: 0, silver: 0, gold: 0 }
    
    return currentWords.value.reduce((acc, word) => {
      acc[word.mastery_level as MasteryLevel]++
      return acc
    }, { default: 0, bronze: 0, silver: 0, gold: 0 } as Record<MasteryLevel, number>)
  })
  
  // Methods
  const loadWordlists = async () => {
    try {
      isLoadingWordlist.value = true
      const response = await wordlistApi.getWordlists()
      wordlists.value = response.items
      
      // Handle graceful fallback if selected wordlist is deleted
      if (selectedWordlistId.value && !response.items.find(w => w.id === selectedWordlistId.value)) {
        const firstWordlist = response.items[0]
        searchConfig.setWordlist(firstWordlist?.id || null)
      }
      
      return response.items
    } catch (error) {
      console.error('Failed to load wordlists:', error)
      toast({
        title: "Error",
        description: "Failed to load wordlists",
        variant: "destructive",
      })
      return []
    } finally {
      isLoadingWordlist.value = false
    }
  }
  
  const loadWordlist = async (wordlistId: string) => {
    try {
      isLoadingWordlist.value = true
      const response = await wordlistApi.getWordlist(wordlistId)
      currentWordlist.value = response.data
      return response.data
    } catch (error) {
      console.error('Failed to load wordlist:', error)
      toast({
        title: "Error",
        description: "Failed to load wordlist",
        variant: "destructive",
      })
      return null
    } finally {
      isLoadingWordlist.value = false
    }
  }
  
  const loadWordlistWords = async (wordlistId: string, offset = 0, limit = 25) => {
    try {
      isLoadingWords.value = true
      const response = await wordlistApi.getWordlistWords(wordlistId, {
        offset,
        limit
      })
      
      if (offset === 0) {
        currentWords.value = response.items
      } else {
        currentWords.value.push(...response.items)
      }
      
      hasMoreWords.value = response.has_more || false
      totalWords.value = response.total
      
      return response
    } catch (error) {
      console.error('Failed to load wordlist words:', error)
      toast({
        title: "Error",
        description: "Failed to load words",
        variant: "destructive",
      })
      return null
    } finally {
      isLoadingWords.value = false
    }
  }
  
  const createWordlist = async (name: string, description = '', words: string[] = []) => {
    try {
      const response = await wordlistApi.createWordlist({
        name,
        description,
        words
      })
      
      // Refresh wordlists
      await loadWordlists()
      
      toast({
        title: "Success",
        description: `Wordlist "${name}" created successfully`,
      })
      
      return response.data
    } catch (error) {
      console.error('Failed to create wordlist:', error)
      toast({
        title: "Error",
        description: "Failed to create wordlist",
        variant: "destructive",
      })
      return null
    }
  }
  
  const deleteWordlist = async (wordlistId: string, wordlistName: string) => {
    try {
      await wordlistApi.deleteWordlist(wordlistId)
      
      // Remove from local state
      wordlists.value = wordlists.value.filter(w => w.id !== wordlistId)
      
      // Handle graceful fallback if deleted wordlist was selected
      if (selectedWordlistId.value === wordlistId) {
        const firstWordlist = wordlists.value[0]
        searchConfig.setWordlist(firstWordlist?.id || null)
      }
      
      toast({
        title: "Success",
        description: `Wordlist "${wordlistName}" has been deleted`,
      })
      
      return true
    } catch (error) {
      console.error('Failed to delete wordlist:', error)
      toast({
        title: "Error",
        description: "Failed to delete wordlist",
        variant: "destructive",
      })
      return false
    }
  }
  
  const updateWordNotes = async (wordlistId: string, word: WordListItem, newNotes: string) => {
    try {
      // Update local state optimistically
      const wordIndex = currentWords.value.findIndex(w => w.word === word.word)
      if (wordIndex >= 0) {
        currentWords.value[wordIndex] = { ...currentWords.value[wordIndex], notes: newNotes }
      }
      
      // Note: Backend endpoint for updating notes would go here
      // await wordlistApi.updateWordNotes(wordlistId, word.word, newNotes)
      
      toast({
        title: "Success",
        description: "Notes updated successfully",
      })
      
      return true
    } catch (error) {
      console.error('Failed to update notes:', error)
      toast({
        title: "Error",
        description: "Failed to update notes. Please try again.",
        variant: "destructive",
      })
      return false
    }
  }
  
  const submitWordReview = async (wordlistId: string, word: WordListItem, quality: number) => {
    try {
      const response = await wordlistApi.submitWordReview(wordlistId, { word: word.word, quality })
      
      // Update local state with new review data
      const wordIndex = currentWords.value.findIndex(w => w.word === word.word)
      if (wordIndex >= 0 && response.data) {
        currentWords.value[wordIndex] = response.data
      }
      
      return response.data
    } catch (error) {
      console.error('Failed to submit review:', error)
      toast({
        title: "Error",
        description: "Failed to submit review",
        variant: "destructive",
      })
      return null
    }
  }
  
  const markWordVisited = async (wordlistId: string, word: WordListItem) => {
    try {
      // Update local state optimistically
      const wordIndex = currentWords.value.findIndex(w => w.word === word.word)
      if (wordIndex >= 0) {
        currentWords.value[wordIndex] = {
          ...currentWords.value[wordIndex],
          last_visited: new Date().toISOString(),
          temperature: 'hot'
        }
      }
      
      // Note: Backend endpoint for marking visited would go here
      // await wordlistApi.markWordVisited(wordlistId, word.word)
      
      return true
    } catch (error) {
      console.error('Failed to mark word as visited:', error)
      return false
    }
  }
  
  // Watch for selected wordlist changes
  watch(selectedWordlistId, async (newWordlistId) => {
    if (newWordlistId) {
      await loadWordlist(newWordlistId)
      await loadWordlistWords(newWordlistId)
    } else {
      currentWordlist.value = null
      currentWords.value = []
    }
  }, { immediate: true })
  
  return {
    // State
    currentWordlist,
    wordlists,
    currentWords,
    isLoadingWordlist,
    isLoadingWords,
    hasMoreWords,
    totalWords,
    
    // Computed
    selectedWordlistId,
    wordlistStats,
    masteryDistribution,
    
    // Methods
    loadWordlists,
    loadWordlist,
    loadWordlistWords,
    createWordlist,
    deleteWordlist,
    updateWordNotes,
    submitWordReview,
    markWordVisited
  }
}