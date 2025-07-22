<template>
  <div 
    class="themed-card themed-shadow-lg bg-background/95 backdrop-blur-sm rounded-lg p-2 space-y-0.5"
    :data-theme="selectedCardVariant || 'default'"
  >
    <!-- Navigation Sections -->
    <nav class="space-y-0.5">
      <div
        v-for="(cluster, clusterIndex) in sidebarSections"
        :key="cluster.clusterId"
        class="space-y-0"
      >
        <!-- Cluster Section -->
        <button
          @click="scrollToCluster(cluster.clusterId)"
          :class="[
            'group flex w-full items-center rounded-md px-2 py-1 text-left text-sm font-medium transition-all duration-200',
            activeCluster === cluster.clusterId
              ? 'text-foreground'
              : 'text-foreground/80 hover:bg-muted/50 hover:text-foreground'
          ]"
        >
          <div class="flex-1 min-w-0">
            <ShimmerText 
              v-if="activeCluster === cluster.clusterId"
              :text="cluster.clusterDescription.toUpperCase()" 
              text-class="themed-cluster-title truncate text-left uppercase text-xs font-bold tracking-wider"
              :duration="400"
              :interval="15000"
            />
            <span v-else class="themed-cluster-title truncate text-left uppercase text-xs font-bold tracking-wider">
              {{ cluster.clusterDescription.toUpperCase() }}
            </span>
          </div>
          <div
            v-if="activeCluster === cluster.clusterId"
            class="ml-2 h-1.5 w-1.5 rounded-full bg-primary animate-pulse flex-shrink-0"
          />
        </button>

        <!-- Word Type Sub-sections with HoverCards -->
        <div class="ml-2 space-y-0">
          <HoverCard
            v-for="wordType in cluster.wordTypes"
            :key="`${cluster.clusterId}-${wordType.type}`"
            :open-delay="200"
            :close-delay="100"
          >
            <HoverCardTrigger>
              <div
                @click="scrollToWordType(cluster.clusterId, wordType.type)"
                :class="[
                  'flex w-full items-center justify-between cursor-pointer rounded-md px-2 py-0.5 transition-all duration-200',
                  activeWordType === `${cluster.clusterId}-${wordType.type}`
                    ? 'bg-muted/70 text-foreground shadow-sm opacity-100'
                    : 'opacity-60 hover:bg-muted/30 hover:opacity-100'
                ]"
              >
                <span class="themed-word-type text-xs">{{ wordType.type }}</span>
                <span class="text-xs opacity-70">{{ wordType.count }}</span>
              </div>
            </HoverCardTrigger>
            <HoverCardContent 
              :class="cn(
                'themed-hovercard w-80',
                selectedCardVariant !== 'default' ? 'themed-shadow-sm' : ''
              )" 
              :data-theme="selectedCardVariant || 'default'"
            >
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <h4 class="themed-cluster-title text-sm font-semibold">
                    Definitions
                  </h4>
                  <span class="themed-word-type text-xs">{{ wordType.count }}</span>
                </div>
                <div class="space-y-2">
                  <div
                    v-for="(definition, idx) in getDefinitionsForWordType(cluster.clusterId, wordType.type).slice(0, 2)"
                    :key="idx"
                    class="space-y-1"
                  >
                    <p class="text-sm leading-relaxed themed-definition-text">{{ definition.definition }}</p>
                    <div v-if="definition.examples?.generated?.[0] || definition.examples?.literature?.[0]" class="themed-example-text text-xs italic opacity-75">
                      "{{ (definition.examples.generated[0] || definition.examples.literature[0])?.sentence }}"
                    </div>
                  </div>
                  <div v-if="getDefinitionsForWordType(cluster.clusterId, wordType.type).length > 2" class="text-xs opacity-60">
                    +{{ getDefinitionsForWordType(cluster.clusterId, wordType.type).length - 2 }} more definitions
                  </div>
                </div>
              </div>
            </HoverCardContent>
          </HoverCard>
        </div>

        <!-- Themed gradient HR between clusters -->
        <div
          v-if="clusterIndex < sidebarSections.length - 1"
          class="my-2 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent themed-hr"
        />
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores'
import { cn } from '@/utils'
import { ShimmerText } from '@/components/custom/animation'
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui'

const store = useAppStore()
const { selectedCardVariant } = storeToRefs(store)

// Active tracking with hysteresis
const activeCluster = ref<string>('')
const activeWordType = ref<string>('')
const pendingActiveCluster = ref<string>('')
const pendingActiveWordType = ref<string>('')


// Responsive behavior
const shouldShowSidebar = ref(false)

// Debounce helper
const debounce = (func: Function, wait: number) => {
  let timeout: NodeJS.Timeout
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Intersection observers
let clusterObservers: IntersectionObserver[] = []
let wordTypeObservers: IntersectionObserver[] = []

// Word type ordering for consistent display (same as DefinitionDisplay)
const wordTypeOrder = {
  noun: 1,
  verb: 2,
  adjective: 3,
  adverb: 4,
  pronoun: 5,
  preposition: 6,
  conjunction: 7,
  interjection: 8,
  determiner: 9,
  article: 10,
}

// Computed sidebar data structure - MUST match DefinitionDisplay ordering exactly
const sidebarSections = computed(() => {
  const entry = store.currentEntry
  if (!entry?.definitions) return []

  // Group by meaning cluster (same logic as DefinitionDisplay)
  const clusters = new Map<string, {
    clusterId: string
    clusterDescription: string
    wordTypes: Array<{ type: string; count: number }>
    maxRelevancy: number
  }>()

  entry.definitions.forEach((definition) => {
    const clusterId = definition.meaning_cluster || 'default'
    const clusterDescription = definition.meaning_cluster
      ? clusterId
          .replace(/_/g, ' ')
          .replace(/\b\w/g, (l) => l.toUpperCase())
          .replace(new RegExp(`\\b${entry.word}\\b`, 'gi'), '')
          .trim()
      : 'General'

    if (!clusters.has(clusterId)) {
      clusters.set(clusterId, {
        clusterId,
        clusterDescription,
        wordTypes: [],
        maxRelevancy: definition.relevancy || 1.0
      })
    }

    const cluster = clusters.get(clusterId)!
    
    // Track highest relevancy for sorting
    if ((definition.relevancy || 1.0) > cluster.maxRelevancy) {
      cluster.maxRelevancy = definition.relevancy || 1.0
    }

    const existingType = cluster.wordTypes.find(wt => wt.type === definition.word_type)
    if (existingType) {
      existingType.count++
    } else {
      cluster.wordTypes.push({ type: definition.word_type, count: 1 })
    }
  })

  // Sort clusters by maximum relevancy (highest first) - SAME AS DefinitionDisplay
  const sortedClusters = Array.from(clusters.values()).sort(
    (a, b) => b.maxRelevancy - a.maxRelevancy
  )

  // Sort word types within each cluster - SAME AS DefinitionDisplay
  sortedClusters.forEach((cluster) => {
    cluster.wordTypes.sort((a, b) => {
      const aTypeOrder = wordTypeOrder[a.type?.toLowerCase() as keyof typeof wordTypeOrder] || 999
      const bTypeOrder = wordTypeOrder[b.type?.toLowerCase() as keyof typeof wordTypeOrder] || 999
      return aTypeOrder - bTypeOrder
    })
  })

  return sortedClusters
})

// Get definitions for a specific word type in a cluster
const getDefinitionsForWordType = (clusterId: string, wordType: string) => {
  const entry = store.currentEntry
  if (!entry?.definitions) return []

  return entry.definitions.filter(def => 
    (def.meaning_cluster || 'default') === clusterId && def.word_type === wordType
  ).sort((a, b) => (b.relevancy || 1.0) - (a.relevancy || 1.0))
}

// Check if we should show sidebar (desktop with enough space)
const checkShowSidebar = () => {
  const hasMultipleClusters = sidebarSections.value.length > 1
  const isDesktop = window.innerWidth >= 1280 // xl breakpoint
  const hasVerticalSpace = window.innerHeight >= 600
  
  shouldShowSidebar.value = hasMultipleClusters && isDesktop && hasVerticalSpace
}

// Scroll functions with margin offset
const scrollToCluster = (clusterId: string) => {
  const element = document.querySelector(`[data-cluster-id="${clusterId}"]`)
  if (element) {
    const elementRect = element.getBoundingClientRect()
    const offset = 80 // Add 80px margin from top
    const bodyRect = document.body.getBoundingClientRect()
    const elementPosition = elementRect.top - bodyRect.top
    const offsetPosition = elementPosition - offset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
  }
}

const scrollToWordType = (clusterId: string, wordType: string) => {
  const element = document.querySelector(`[data-word-type="${clusterId}-${wordType}"]`)
  if (element) {
    const elementRect = element.getBoundingClientRect()
    const offset = 80 // Add 80px margin from top
    const bodyRect = document.body.getBoundingClientRect()
    const elementPosition = elementRect.top - bodyRect.top
    const offsetPosition = elementPosition - offset

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    })
  }
}

// Immediate update functions for responsive UI
const updateActiveCluster = (clusterId: string) => {
  activeCluster.value = clusterId
  pendingActiveCluster.value = clusterId
}

const updateActiveWordType = (wordTypeKey: string) => {
  activeWordType.value = wordTypeKey  
  pendingActiveWordType.value = wordTypeKey
}


// Initialize active states based on current scroll position
const initializeActiveStates = () => {
  if (sidebarSections.value.length === 0) return

  let bestCluster = ''
  let bestClusterScore = 0
  let bestWordType = ''
  let bestWordTypeScore = 0

  // Check each cluster's visibility
  sidebarSections.value.forEach((cluster) => {
    const element = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`)
    if (element) {
      const rect = element.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      
      // Calculate visibility score
      const visibleHeight = Math.min(rect.bottom, viewportHeight) - Math.max(rect.top, 0)
      const visibilityScore = Math.max(0, visibleHeight / rect.height)
      
      // Check if element is reasonably visible (at least 10% visible)
      if (visibilityScore > 0.1 && visibilityScore > bestClusterScore) {
        bestCluster = cluster.clusterId
        bestClusterScore = visibilityScore
      }

      // Check word types within this cluster if it's the current best
      if (bestCluster === cluster.clusterId) {
        cluster.wordTypes.forEach((wordType) => {
          const wordTypeElements = document.querySelectorAll(`[data-word-type="${cluster.clusterId}-${wordType.type}"]`)
          wordTypeElements.forEach((wtElement) => {
            const wtRect = wtElement.getBoundingClientRect()
            const wtVisibleHeight = Math.min(wtRect.bottom, viewportHeight) - Math.max(wtRect.top, 0)
            const wtVisibilityScore = Math.max(0, wtVisibleHeight / wtRect.height)
            
            if (wtVisibilityScore > 0.3 && wtVisibilityScore > bestWordTypeScore) {
              bestWordType = `${cluster.clusterId}-${wordType.type}`
              bestWordTypeScore = wtVisibilityScore
            }
          })
        })
      }
    }
  })

  // Set initial active states if we found visible elements
  if (bestCluster && bestClusterScore > 0.1) {
    updateActiveCluster(bestCluster)
  }
  
  if (bestWordType && bestWordTypeScore > 0.3) {
    updateActiveWordType(bestWordType)
  }

  // Fallback: if no visible clusters, determine based on scroll position
  if (!bestCluster) {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight
    const viewportHeight = window.innerHeight
    
    if (scrollTop < 200) {
      // Near top, activate first cluster
      const firstCluster = sidebarSections.value[0]
      updateActiveCluster(firstCluster.clusterId)
    } else if (scrollTop >= docHeight - 200 || (scrollTop + viewportHeight >= document.documentElement.scrollHeight - 50)) {
      // Near bottom or at bottom, activate last cluster
      const lastCluster = sidebarSections.value[sidebarSections.value.length - 1]
      updateActiveCluster(lastCluster.clusterId)
    }
  }
}

// Setup intersection observers with hysteresis
const setupObservers = async () => {
  await nextTick()

  // Clear existing observers
  clusterObservers.forEach(observer => observer.disconnect())
  wordTypeObservers.forEach(observer => observer.disconnect())
  clusterObservers = []
  wordTypeObservers = []

  // Initialize active states based on current scroll position
  initializeActiveStates()

  // Track visible elements with scores
  const visibleClusters = new Map<string, number>()
  const visibleWordTypes = new Map<string, number>()
  
  // Fallback function to set top/bottom cluster when no clusters are visible
  const setFallbackCluster = () => {
    if (sidebarSections.value.length === 0) return
    
    const firstCluster = sidebarSections.value[0]
    const lastCluster = sidebarSections.value[sidebarSections.value.length - 1]
    
    // Check scroll position to determine if we're at top or bottom
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop
    const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight
    const viewportHeight = window.innerHeight
    
    if (scrollTop < 200) {
      // Near top, activate first cluster
      updateActiveCluster(firstCluster.clusterId)
    } else if (scrollTop >= docHeight - 200 || (scrollTop + viewportHeight >= document.documentElement.scrollHeight - 50)) {
      // Near bottom or at bottom, activate last cluster
      updateActiveCluster(lastCluster.clusterId)
    }
  }

  // Cluster observers with hysteresis
  sidebarSections.value.forEach((cluster) => {
    const element = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`)
    if (element) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          const rect = entry.boundingClientRect
          const rootRect = entry.rootBounds
          
          // Calculate how much of the element is in the viewport
          const viewportHeight = rootRect?.height || window.innerHeight
          const elementHeight = rect.height
          const visibleHeight = Math.min(rect.bottom, viewportHeight) - Math.max(rect.top, 0)
          const visibilityScore = Math.max(0, visibleHeight / elementHeight)
          
          if (entry.isIntersecting && visibilityScore > 0.05) {
            visibleClusters.set(cluster.clusterId, visibilityScore)
            
            // Find cluster with highest visibility score
            const bestCluster = Array.from(visibleClusters.entries())
              .sort(([, a], [, b]) => b - a)[0]
            
            if (bestCluster && bestCluster[1] > 0.1) {
              updateActiveCluster(bestCluster[0])
            }
          } else {
            visibleClusters.delete(cluster.clusterId)
            
            // If this was the active cluster, find next best
            if (activeCluster.value === cluster.clusterId) {
              const nextBest = Array.from(visibleClusters.entries())
                .sort(([, a], [, b]) => b - a)[0]
              
              if (nextBest && nextBest[1] > 0.08) {
                updateActiveCluster(nextBest[0])
              } else {
                // No visible clusters, use fallback
                setFallbackCluster()
              }
            }
          }
        },
        { 
          rootMargin: '-5% 0px -20% 0px', 
          threshold: [0.05, 0.1, 0.15, 0.25, 0.4, 0.6, 0.8] 
        }
      )
      observer.observe(element)
      clusterObservers.push(observer)
    }

    // Word type observers with hysteresis
    cluster.wordTypes.forEach((wordType) => {
      const elements = document.querySelectorAll(`[data-word-type="${cluster.clusterId}-${wordType.type}"]`)
      elements.forEach((element) => {
        const observer = new IntersectionObserver(
          ([entry]) => {
            const key = `${cluster.clusterId}-${wordType.type}`
            const ratio = entry.intersectionRatio
            
            if (entry.isIntersecting && ratio > 0.2) {
              visibleWordTypes.set(key, ratio)
              
              // Only update if we're in the active cluster
              if (activeCluster.value === cluster.clusterId) {
                const clusterWordTypes = Array.from(visibleWordTypes.entries())
                  .filter(([wt]) => wt.startsWith(cluster.clusterId))
                  .sort(([, a], [, b]) => b - a)
                
                if (clusterWordTypes.length > 0 && clusterWordTypes[0][1] > 0.3) {
                  updateActiveWordType(clusterWordTypes[0][0])
                }
              }
            } else {
              visibleWordTypes.delete(key)
            }
          },
          { 
            rootMargin: '-20% 0px -30% 0px', 
            threshold: [0.2, 0.3, 0.5, 0.7] 
          }
        )
        observer.observe(element)
        wordTypeObservers.push(observer)
      })
    })
  })
}

onMounted(() => {
  checkShowSidebar()
  window.addEventListener('resize', checkShowSidebar)
  
  // Setup observers when definitions are loaded
  if (sidebarSections.value.length > 0) {
    setupObservers()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkShowSidebar)
  clusterObservers.forEach(observer => observer.disconnect())
  wordTypeObservers.forEach(observer => observer.disconnect())
})

// Watch for definition changes to setup new observers
watch(() => store.currentEntry?.definitions, () => {
  if (sidebarSections.value.length > 0) {
    nextTick(() => setupObservers())
  }
}, { deep: true })
</script>

<style scoped>
/* Gradient support for both themes */
.gradient-hr {
  background: linear-gradient(
    to right,
    transparent,
    hsl(var(--primary) / 0.2),
    transparent
  );
}

/* Ensure proper theme contrast for gradients */
:global(.dark) .gradient-hr {
  background: linear-gradient(
    to right,
    transparent,
    hsl(var(--primary) / 0.3),
    transparent
  );
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .sidebar-shimmer {
    animation: none !important;
    color: hsl(var(--primary)) !important;
    background: none !important;
  }
  
  * {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}

/* Custom scrollbar for sidebar */
::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-primary);
}
</style>