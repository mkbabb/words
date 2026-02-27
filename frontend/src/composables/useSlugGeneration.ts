import { ref } from 'vue'
import { wordlistsApi } from '@/api'
import { useToast } from '@/components/ui/toast/use-toast'
import { logger } from '@/utils/logger'

export function useSlugGeneration() {
  const { toast } = useToast()
  
  // State - only for loading indicator
  const isGenerating = ref(false)
  
  // Generate a new slug name - always fresh, no caching
  const generateSlug = async (): Promise<string | null> => {
    try {
      isGenerating.value = true
      const response = await wordlistsApi.generateSlugName()
      return response.name
    } catch (error) {
      logger.error('Failed to generate slug name:', error)
      toast({
        title: "Error",
        description: "Failed to generate a name. Please try again.",
        variant: "destructive",
      })
      return null
    } finally {
      isGenerating.value = false
    }
  }
  
  // Generate slug with fallback to timestamp-based name
  const generateSlugWithFallback = async (): Promise<string> => {
    const slug = await generateSlug()
    if (slug) {
      return slug
    }
    
    // Fallback to timestamp-based name if API fails
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')
    const fallbackName = `wordlist-${timestamp}`
    return fallbackName
  }
  
  return {
    // State
    isGenerating,
    
    // Methods
    generateSlug,
    generateSlugWithFallback,
  }
}