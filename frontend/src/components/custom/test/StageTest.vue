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
      <p 
        class="text-muted-foreground/70 dark:text-muted-foreground/50 mt-2"
        style="font-family: 'Fraunces', serif"
      >
        Test the dramatic loading experience
      </p>
    </div>

    <!-- Demo Controls -->
    <ThemedCard class="w-full">
      <CardContent class="space-y-6">
        <!-- Test Word Input -->
        <div class="space-y-4">
          <div class="space-y-2">
            <Label for="test-word">Test Word</Label>
            <Input
              id="test-word"
              v-model="testWord"
              placeholder="Enter a word..."
              @keydown.enter="startRealTest"
            />
          </div>
          
          <!-- Action Buttons -->
          <div class="flex gap-3">
            <Button
              @click="startMockTest"
              :disabled="isTestRunning"
              variant="outline"
              class="flex-1"
            >
              {{ isTestRunning ? 'Running...' : 'Mock Pipeline' }}
            </Button>
            <Button
              @click="startRealTest"
              :disabled="!testWord.trim() || isTestRunning"
              class="flex-1"
            >
              Real Lookup
            </Button>
          </div>
        </div>

        <!-- Progress Display -->
        <div v-if="isTestRunning" class="space-y-2">
          <Label>Current Progress</Label>
          <LoadingProgress :progress="simulatedProgress" />
          <div class="text-sm text-muted-foreground text-center">
            {{ simulatedStage }}
          </div>
        </div>
      </CardContent>
    </ThemedCard>

    <!-- Loading Modal -->
    <LoadingModal
      v-model="showLoadingModal"
      :word="testWord || 'serendipity'"
      :progress="simulatedProgress"
      :current-stage="simulatedStage"
      :facts="mockFacts"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button, Input, Label, CardContent } from '@/components/ui'
import { ThemedCard } from '@/components/custom/card'
import { LoadingModal, LoadingProgress } from '@/components/custom/loading'
import { useAppStore } from '@/stores'

const store = useAppStore()

// State
const testWord = ref('serendipity')
const showLoadingModal = ref(false)
const isTestRunning = ref(false)
const simulatedProgress = ref(0)
const simulatedStage = ref('Initializing...')

// Mock facts for demo
const mockFacts = ref([
  { content: 'This word was coined by Horace Walpole in 1754', category: 'etymology', confidence: 0.95 },
  { content: 'Derived from the Persian fairy tale "The Three Princes of Serendip"', category: 'origin', confidence: 0.88 },
])

// Pipeline stages for mock
const stages = [
  { progress: 0, stage: 'Initializing search...' },
  { progress: 10, stage: 'Searching dictionaries...' },
  { progress: 30, stage: 'Fetching definitions...' },
  { progress: 50, stage: 'Analyzing meanings...' },
  { progress: 70, stage: 'Generating examples...' },
  { progress: 90, stage: 'Finalizing...' },
  { progress: 100, stage: 'Complete!' },
]

// Mock pipeline simulation
const runMockPipeline = async () => {
  isTestRunning.value = true
  showLoadingModal.value = true
  
  for (const stageData of stages) {
    simulatedProgress.value = stageData.progress
    simulatedStage.value = stageData.stage
    
    // Wait between stages
    await new Promise(resolve => setTimeout(resolve, 800))
  }
  
  // Show completion briefly
  setTimeout(() => {
    showLoadingModal.value = false
    isTestRunning.value = false
    simulatedProgress.value = 0
  }, 1500)
}

// Real pipeline using store
const runRealPipeline = async () => {
  if (!testWord.value.trim()) return
  
  isTestRunning.value = true
  showLoadingModal.value = true
  
  try {
    // Use store's force refresh to get real pipeline progress
    store.forceRefreshMode = true
    await store.getDefinition(testWord.value.trim())
    
    // Sync with store progress
    simulatedProgress.value = store.loadingProgress
    simulatedStage.value = store.loadingStage
    
  } catch (error) {
    console.error('Pipeline test failed:', error)
  } finally {
    store.forceRefreshMode = false
    
    setTimeout(() => {
      showLoadingModal.value = false
      isTestRunning.value = false
      simulatedProgress.value = 0
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
</script>