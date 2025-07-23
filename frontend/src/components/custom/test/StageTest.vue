<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h2 
        class="text-3xl font-bold tracking-tight"
        style="font-family: 'Fraunces', serif"
      >
        Loading Pipeline Demo
      </h2>
    </div>

    <!-- Demo Controls -->
    <ThemedCard class="w-full">
      <CardContent class="space-y-6">
        <!-- Current Word Display -->
        <div v-if="store.searchQuery" class="text-left space-y-4">
          <h3 class="text-word-title themed-title">{{ store.searchQuery }}</h3>
          
          <!-- Gradient Divider -->
          <div class="relative h-px w-full overflow-hidden">
            <div class="via-primary/30 absolute inset-0 bg-gradient-to-r from-transparent to-transparent" />
          </div>
        </div>

        <!-- Progress Display - Always Visible -->
        <div class="space-y-2">
          <Label>Pipeline Progress (Interactive)</Label>
          <div class="w-full">
            <LoadingProgress 
              :progress="simulatedProgress" 
              :interactive="true"
              @progress-change="handleProgressChange"
            />
          </div>
          <div class="text-sm text-muted-foreground text-center">
            {{ simulatedStage }}
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3 justify-center">
          <Button
            @click="startMockTest"
            :disabled="isTestRunning || !store.searchQuery"
            variant="outline"
            size="sm"
            class="px-6"
          >
            {{ isTestRunning ? 'Running...' : 'Mock Pipeline' }}
          </Button>
          <Button
            @click="startRealTest"
            :disabled="!store.searchQuery || isTestRunning"
            size="sm"
            class="px-6"
          >
            Real Lookup
          </Button>
        </div>
      </CardContent>
    </ThemedCard>

    <!-- Loading Modal -->
    <LoadingModal
      v-model="showLoadingModal"
      :word="store.searchQuery || 'serendipity'"
      :progress="isRealPipeline ? store.loadingProgress : simulatedProgress"
      :current-stage="isRealPipeline ? store.loadingStage : simulatedStage"
      :allow-dismiss="true"
      @progress-change="handleProgressChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button, Label, CardContent } from '@/components/ui'
import { ThemedCard } from '@/components/custom/card'
import { LoadingModal, LoadingProgress } from '@/components/custom/loading'
import { useAppStore } from '@/stores'

const store = useAppStore()

// State
const showLoadingModal = ref(false)
const isTestRunning = ref(false)
const simulatedProgress = ref(0)
const simulatedStage = ref('Initializing...')
const isRealPipeline = ref(false)


// Pipeline stages for mock - using keys that match LoadingModal's stageMessages
const stages = [
  { progress: 0, stage: 'initialization' },
  { progress: 10, stage: 'search' },
  { progress: 30, stage: 'provider_fetch' },
  { progress: 50, stage: 'ai_clustering' },
  { progress: 70, stage: 'ai_synthesis' },
  { progress: 90, stage: 'storage_save' },
  { progress: 100, stage: 'complete' },
]

// Mock pipeline simulation - purely interactive, no auto-progression
const runMockPipeline = async () => {
  isTestRunning.value = true
  isRealPipeline.value = false
  showLoadingModal.value = true
  
  // Start at the beginning stage
  simulatedProgress.value = 0
  simulatedStage.value = stages[0].stage
}

// Real pipeline using store
const runRealPipeline = async () => {
  if (!store.searchQuery.trim()) return
  
  isTestRunning.value = true
  isRealPipeline.value = true
  showLoadingModal.value = true
  
  try {
    // Use store's force refresh to get real pipeline progress
    store.forceRefreshMode = true
    await store.getDefinition(store.searchQuery.trim())
    
  } catch (error) {
    console.error('Pipeline test failed:', error)
  } finally {
    store.forceRefreshMode = false
    
    setTimeout(() => {
      showLoadingModal.value = false
      isTestRunning.value = false
      isRealPipeline.value = false
    }, 1500)
  }
}

// Actions
const startMockTest = () => {
  runMockPipeline()
}

const startRealTest = () => {
  runRealPipeline()
}

// Handle interactive progress changes
const handleProgressChange = (newProgress: number) => {
  if (!isTestRunning.value || isRealPipeline.value) return
  
  simulatedProgress.value = newProgress
  
  // Find the appropriate stage based on progress
  const stage = stages.find((s, index) => {
    const nextStage = stages[index + 1]
    return newProgress >= s.progress && (!nextStage || newProgress < nextStage.progress)
  })
  
  if (stage) {
    simulatedStage.value = stage.stage
  }
}

// Watch for modal close to reset running state
watch(showLoadingModal, (newVal) => {
  if (!newVal) {
    // Modal closed - reset running state after a short delay
    setTimeout(() => {
      isTestRunning.value = false
      isRealPipeline.value = false
      simulatedProgress.value = 0
      simulatedStage.value = stages[0].stage
    }, 500)
  }
})

// Expose functions to parent component
defineExpose({
  startMockTest,
  startRealTest
})
</script>