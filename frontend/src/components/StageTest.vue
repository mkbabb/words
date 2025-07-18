<template>
  <div class="space-y-6">
    <!-- Header Section (following visualizer pattern) -->
    <div>
      <h2 
        class="text-3xl font-bold tracking-tight"
        style="font-family: 'Fraunces', serif"
      >
        Loading Pipeline Stage
      </h2>
      <p 
        class="text-muted-foreground/70 dark:text-muted-foreground/50 mt-2 italic"
        style="font-family: 'Fraunces', serif"
      >
        Test and preview the theatrical loading visualization pipeline
      </p>
    </div>

    <!-- Main Content Card -->
    <div class="relative">
      <div class="absolute -top-3 right-6 left-6 h-1 rounded-full bg-gradient-to-r from-transparent via-primary to-transparent opacity-60" />
      
      <ThemedCard class="relative w-full overflow-hidden">
        <CardContent class="space-y-6">
          <!-- Pipeline Mode Toggle -->
          <div class="text-center space-y-3">
            <h3 class="text-lg font-semibold">Pipeline Mode</h3>
            <BouncyToggle
              v-model="pipelineMode"
              :options="pipelineModeOptions"
            />
            <p class="text-sm text-muted-foreground">
              {{ pipelineModeDescription }}
            </p>
          </div>

          <!-- Test Controls -->
          <div class="grid md:grid-cols-2 gap-6 items-center">
            <div class="space-y-4">
              <div class="space-y-2">
                <Label for="test-word">Test Word</Label>
                <Input
                  id="test-word"
                  v-model="testWord"
                  placeholder="Enter a word to test..."
                  @keydown.enter="startTest"
                />
              </div>
              
              <div class="space-y-2">
                <Label>Quick Select</Label>
                <div class="grid grid-cols-2 gap-2">
                  <Button
                    v-for="word in presetWords"
                    :key="word"
                    @click="setTestWord(word)"
                    variant="outline"
                    size="sm"
                  >
                    {{ word }}
                  </Button>
                </div>
              </div>
            </div>

            <div class="space-y-4">
              <div class="space-y-2">
                <Label>Pipeline Progress</Label>
                <div class="relative">
                  <div class="h-3 bg-muted rounded-full overflow-hidden">
                    <div
                      class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
                      :style="{ width: `${simulatedProgress}%` }"
                    />
                  </div>
                  <div class="mt-2 text-sm text-muted-foreground">
                    {{ simulatedStage }} ({{ Math.round(simulatedProgress) }}%)
                  </div>
                </div>
              </div>

              <div class="flex gap-2">
                <Button
                  @click="startTest"
                  :disabled="!testWord.trim() || isTestRunning"
                  class="flex-1"
                >
                  {{ isTestRunning ? 'Running...' : 'Test Pipeline' }}
                </Button>
                <Button
                  @click="showManualModal = true"
                  variant="outline"
                  size="sm"
                >
                  Manual
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </ThemedCard>
    </div>
  </div>

  <!-- Manual Test Modal -->
  <Modal v-model="showManualModal" :close-on-backdrop="true">
    <div class="space-y-6">
      <div class="text-center">
        <h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Manual Stage Test
        </h2>
        <p class="text-gray-600 dark:text-gray-400">
          Manually control the loading pipeline progress
        </p>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Test Word
          </label>
          <input
            v-model="manualTestWord"
            placeholder="Enter word..."
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Progress: {{ manualProgress }}%
          </label>
          <input
            v-model="manualProgress"
            type="range"
            min="0"
            max="100"
            class="w-full"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Stage
          </label>
          <select
            v-model="manualStage"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            <option v-for="stage in pipelineStages" :key="stage.key" :value="stage.key">
              {{ stage.name }}
            </option>
          </select>
        </div>

        <div class="flex justify-center gap-4">
          <Button
            @click="startManualTest"
            class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Start Manual Test
          </Button>
          <Button
            @click="showManualModal = false"
            variant="outline"
            class="px-6 py-2"
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  </Modal>

  <!-- Main Loading Modal (for testing) -->
  <LoadingModal
    v-model="isTestRunning"
    :word="currentTestWord"
    :progress="simulatedProgress"
    :current-stage="simulatedStage"
    :facts="testFacts"
  />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { BouncyToggle, Button, Modal, ThemedCard, CardContent, Input, Label } from '@/components/ui'
import LoadingModal from '@/components/LoadingModal.vue'
import type { FactItem } from '@/types'

// Pipeline mode options
const pipelineModeOptions = [
  { label: 'Realistic', value: 'realistic' },
  { label: 'Fast', value: 'fast' },
  { label: 'Manual', value: 'manual' }
]

// Reactive state
const pipelineMode = ref('realistic')
const testWord = ref('serendipity')
const isTestRunning = ref(false)
const simulatedProgress = ref(0)
const simulatedStage = ref('Ready')
const currentTestWord = ref('')
const testFacts = ref<FactItem[]>([])
const showManualModal = ref(false)

// Manual test controls
const manualTestWord = ref('serendipity')
const manualProgress = ref(0)
const manualStage = ref('search')

// Preset words for testing (reduced to 6)
const presetWords = [
  'serendipity', 'ephemeral', 'mellifluous', 'petrichor', 'wanderlust', 'eloquent'
]

// Pipeline stages configuration
const pipelineStages = [
  { key: 'search', name: 'Search', description: 'Dictionary lookup and word validation', progressRange: '0-10%' },
  { key: 'fetch', name: 'Fetch', description: 'Gathering definitions from multiple sources', progressRange: '10-40%' },
  { key: 'cluster', name: 'Cluster', description: 'AI-powered meaning analysis and clustering', progressRange: '40-50%' },
  { key: 'synthesis', name: 'Synthesis', description: 'Synthesizing comprehensive definitions', progressRange: '50-60%' },
  { key: 'examples', name: 'Examples', description: 'Generating modern usage examples', progressRange: '60-70%' },
  { key: 'synonyms', name: 'Synonyms', description: 'Finding beautiful synonyms and antonyms', progressRange: '70-75%' },
  { key: 'facts', name: 'Facts', description: 'Discovering fascinating word facts', progressRange: '75-85%' },
  { key: 'storage', name: 'Storage', description: 'Saving to knowledge base', progressRange: '85-95%' },
  { key: 'complete', name: 'Complete', description: 'Pipeline finished successfully', progressRange: '95-100%' }
]

// Computed properties
const pipelineModeDescription = computed(() => {
  switch (pipelineMode.value) {
    case 'realistic': return 'Simulate realistic API timing and progress'
    case 'fast': return 'Accelerated pipeline for quick testing'
    case 'manual': return 'Manual control over progress and stages'
    default: return ''
  }
})


// Methods
const setTestWord = (word: string) => {
  testWord.value = word
}

const startTest = async () => {
  if (!testWord.value.trim() || isTestRunning.value) return

  currentTestWord.value = testWord.value.trim()
  isTestRunning.value = true
  simulatedProgress.value = 0
  simulatedStage.value = 'search'
  
  // Generate sample facts
  testFacts.value = [
    {
      content: `The word "${currentTestWord.value}" has fascinating etymological roots.`,
      category: 'etymology',
      confidence: 0.9
    },
    {
      content: `"${currentTestWord.value}" appears in notable literary works.`,
      category: 'cultural',
      confidence: 0.85
    },
    {
      content: `The pronunciation has evolved over centuries.`,
      category: 'linguistic',
      confidence: 0.8
    }
  ]

  // Simulate pipeline based on mode
  const stages = pipelineMode.value === 'fast' 
    ? [
        { key: 'search', progress: 10, duration: 200 },
        { key: 'fetch', progress: 40, duration: 300 },
        { key: 'cluster', progress: 50, duration: 250 },
        { key: 'synthesis', progress: 60, duration: 400 },
        { key: 'examples', progress: 70, duration: 300 },
        { key: 'synonyms', progress: 75, duration: 200 },
        { key: 'facts', progress: 85, duration: 350 },
        { key: 'storage', progress: 95, duration: 150 },
        { key: 'complete', progress: 100, duration: 100 }
      ]
    : [
        { key: 'search', progress: 10, duration: 800 },
        { key: 'fetch', progress: 40, duration: 1500 },
        { key: 'cluster', progress: 50, duration: 1200 },
        { key: 'synthesis', progress: 60, duration: 2000 },
        { key: 'examples', progress: 70, duration: 1800 },
        { key: 'synonyms', progress: 75, duration: 800 },
        { key: 'facts', progress: 85, duration: 1400 },
        { key: 'storage', progress: 95, duration: 600 },
        { key: 'complete', progress: 100, duration: 300 }
      ]

  for (const stage of stages) {
    simulatedStage.value = stage.key
    simulatedProgress.value = stage.progress
    await new Promise(resolve => setTimeout(resolve, stage.duration))
  }

  await new Promise(resolve => setTimeout(resolve, 1000))
  isTestRunning.value = false
}

const startManualTest = () => {
  if (!manualTestWord.value.trim()) return

  currentTestWord.value = manualTestWord.value.trim()
  simulatedProgress.value = manualProgress.value
  simulatedStage.value = manualStage.value
  isTestRunning.value = true
  showManualModal.value = false

  testFacts.value = [
    {
      content: `Manual test: "${currentTestWord.value}" is being analyzed.`,
      category: 'test',
      confidence: 1.0
    }
  ]
}

</script>