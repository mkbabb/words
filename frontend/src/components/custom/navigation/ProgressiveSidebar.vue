<template>
  <div 
    class="themed-card themed-shadow-lg bg-background/95 backdrop-blur-sm rounded-lg p-2 space-y-0.5 relative z-20 overflow-visible"
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
            'group flex w-full items-center rounded-md px-2 py-1 text-left text-sm transition-all duration-200',
            activeCluster === cluster.clusterId
              ? 'text-foreground font-bold'
              : 'text-foreground/80 font-normal hover:bg-muted/50 hover:text-foreground'
          ]"
        >
          <div class="flex-1 min-w-0 pr-2 overflow-hidden text-ellipsis whitespace-nowrap">
            <ShimmerText 
              v-if="activeCluster === cluster.clusterId"
              :text="cluster.clusterDescription.toUpperCase()" 
              text-class="themed-cluster-title text-left uppercase text-xs font-bold tracking-wider"
              :duration="400"
              :interval="15000"
            />
            <span 
              v-else 
              class="themed-cluster-title text-left uppercase text-xs font-bold tracking-wider"
              :title="cluster.clusterDescription.toUpperCase()"
            >
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
                    ? 'themed-word-type-bg text-foreground shadow-sm opacity-100 border border-primary/25'
                    : 'opacity-60 hover:bg-muted/30 hover:opacity-100'
                ]"
              >
                <span class="themed-word-type text-xs">{{ wordType.type }}</span>
                <span class="text-xs opacity-70">{{ wordType.count }}</span>
              </div>
            </HoverCardTrigger>
            <HoverCardContent 
              :class="cn(
                'themed-hovercard w-80 z-[80]',
                selectedCardVariant !== 'default' ? 'themed-shadow-sm' : ''
              )" 
              :data-theme="selectedCardVariant || 'default'"
            >
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <h4 class="themed-cluster-title text-sm font-semibold uppercase">
                    {{ cluster.clusterDescription }}
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

// Helper function to detect if user is at document bottom
const isAtDocumentBottom = () => {
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  const windowHeight = window.innerHeight
  const docHeight = document.documentElement.scrollHeight
  
  // Consider "at bottom" if within 50px of actual bottom, or if scrolled to max
  const atBottom = (scrollTop + windowHeight) >= (docHeight - 50)
  const atMaxScroll = scrollTop >= (docHeight - windowHeight - 10)
  
  return atBottom || atMaxScroll
}

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

// Type definition for cluster structure
type SidebarCluster = {
  clusterId: string
  clusterDescription: string
  wordTypes: Array<{ type: string; count: number }>
  maxRelevancy: number
}

// Computed sidebar data structure - MUST match DefinitionDisplay ordering exactly
const sidebarSections = computed((): SidebarCluster[] => {
  const entry = store.currentEntry
  if (!entry?.definitions) return []

  // Group by meaning cluster (same logic as DefinitionDisplay)
  const clusters = new Map<string, SidebarCluster>()

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

    const existingType = cluster.wordTypes.find(wt => wt.type === definition.part_of_speech)
    if (existingType) {
      existingType.count++
    } else {
      cluster.wordTypes.push({ type: definition.part_of_speech, count: 1 })
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
    (def.meaning_cluster || 'default') === clusterId && def.part_of_speech === wordType
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

// Helper function to find best cluster based on element positions
const findBestClusterByPosition = () => {
  if (sidebarSections.value.length === 0) return
  
  const viewportCenter = window.innerHeight / 2 + window.pageYOffset
  let closestCluster: SidebarCluster | null = null
  let closestDistance = Infinity
  
  sidebarSections.value.forEach((cluster) => {
    const element = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`)
    if (element) {
      const rect = element.getBoundingClientRect()
      const elementCenter = rect.top + rect.height / 2 + window.pageYOffset
      const distance = Math.abs(elementCenter - viewportCenter)
      
      if (distance < closestDistance) {
        closestDistance = distance
        closestCluster = cluster
      }
    }
  })
  
  if (closestCluster) {
    const cluster = closestCluster as SidebarCluster
    updateActiveCluster(cluster.clusterId)
    // Also set first word type of the cluster
    if (cluster.wordTypes.length > 0) {
      updateActiveWordType(`${cluster.clusterId}-${cluster.wordTypes[0].type}`)
    }
  }
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

  // Fallback: if no visible clusters, use robust position-based detection
  if (!bestCluster) {
    findBestClusterByPosition()
  }
  
  // Ensure word type is set for active cluster if not already set
  if (bestCluster && !bestWordType) {
    const activeClusterData = sidebarSections.value.find(c => c.clusterId === bestCluster)
    if (activeClusterData && activeClusterData.wordTypes.length > 0) {
      updateActiveWordType(`${bestCluster}-${activeClusterData.wordTypes[0].type}`)
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
  
  // Robust fallback function to set appropriate cluster based on scroll position
  const setFallbackCluster = () => {
    if (sidebarSections.value.length === 0) return
    
    const firstCluster = sidebarSections.value[0]
    const lastCluster = sidebarSections.value[sidebarSections.value.length - 1]
    
    // Get precise scroll metrics
    const scrollTop = Math.max(0, window.pageYOffset || document.documentElement.scrollTop)
    const docHeight = document.documentElement.scrollHeight
    const clientHeight = document.documentElement.clientHeight
    const maxScrollTop = Math.max(0, docHeight - clientHeight)
    const scrollProgress = maxScrollTop > 0 ? scrollTop / maxScrollTop : 0
    
    // Define bounds with hysteresis - more generous bottom threshold
    const topThreshold = 0.05  // Top 5% of document
    const bottomThreshold = 0.85  // Bottom 15% of document (more generous for last cluster)
    
    if (scrollProgress < topThreshold) {
      // Near top - activate first cluster and its first word type
      updateActiveCluster(firstCluster.clusterId)
      if (firstCluster.wordTypes.length > 0) {
        updateActiveWordType(`${firstCluster.clusterId}-${firstCluster.wordTypes[0].type}`)
      }
    } else if (scrollProgress > bottomThreshold || isAtDocumentBottom()) {
      // Near bottom or at document bottom - activate last cluster and its last word type
      updateActiveCluster(lastCluster.clusterId)
      if (lastCluster.wordTypes.length > 0) {
        const lastWordType = lastCluster.wordTypes[lastCluster.wordTypes.length - 1]
        updateActiveWordType(`${lastCluster.clusterId}-${lastWordType.type}`)
      }
    } else {
      // Middle section - find best cluster based on actual element positions
      findBestClusterByPosition()
    }
  }
  

  // Cluster observers with hysteresis
  sidebarSections.value.forEach((cluster, clusterIndex) => {
    const element = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`)
    if (element) {
      const isLastCluster = clusterIndex === sidebarSections.value.length - 1
      
      const observer = new IntersectionObserver(
        ([entry]) => {
          const rect = entry.boundingClientRect
          const rootRect = entry.rootBounds
          
          // Calculate how much of the element is in the viewport
          const viewportHeight = rootRect?.height || window.innerHeight
          const elementHeight = rect.height
          const visibleHeight = Math.min(rect.bottom, viewportHeight) - Math.max(rect.top, 0)
          const visibilityScore = Math.max(0, visibleHeight / elementHeight)
          
          if (entry.isIntersecting && visibilityScore > 0.03) {
            visibleClusters.set(cluster.clusterId, visibilityScore)
            
            // Find cluster with highest visibility score
            const bestCluster = Array.from(visibleClusters.entries())
              .sort(([, a], [, b]) => b - a)[0]
            
            if (bestCluster && bestCluster[1] > 0.05) {
              updateActiveCluster(bestCluster[0])
              
              // Reset word type when cluster changes
              const clusterData = sidebarSections.value.find(c => c.clusterId === bestCluster[0])
              if (clusterData && clusterData.wordTypes.length > 0) {
                const currentWordType = activeWordType.value
                if (!currentWordType.startsWith(bestCluster[0])) {
                  updateActiveWordType(`${bestCluster[0]}-${clusterData.wordTypes[0].type}`)
                }
              }
            }
          } else {
            visibleClusters.delete(cluster.clusterId)
            
            // If this was the active cluster, find next best or use fallback
            if (activeCluster.value === cluster.clusterId) {
              const nextBest = Array.from(visibleClusters.entries())
                .sort(([, a], [, b]) => b - a)[0]
              
              if (nextBest && nextBest[1] > 0.03) {
                updateActiveCluster(nextBest[0])
                
                // Update word type for new cluster
                const clusterData = sidebarSections.value.find(c => c.clusterId === nextBest[0])
                if (clusterData && clusterData.wordTypes.length > 0) {
                  updateActiveWordType(`${nextBest[0]}-${clusterData.wordTypes[0].type}`)
                }
              } else {
                // No visible clusters, check if we're at bottom and should activate last cluster
                if (isAtDocumentBottom() && isLastCluster) {
                  updateActiveCluster(cluster.clusterId)
                  if (cluster.wordTypes.length > 0) {
                    const lastWordType = cluster.wordTypes[cluster.wordTypes.length - 1]
                    updateActiveWordType(`${cluster.clusterId}-${lastWordType.type}`)
                  }
                } else {
                  // Use robust fallback
                  setFallbackCluster()
                }
              }
            }
          }
        },
        { 
          // Use more generous bottom margin for last cluster to catch bottom edge
          rootMargin: isLastCluster ? '-2% 0px -5% 0px' : '-2% 0px -15% 0px', 
          threshold: [0.03, 0.05, 0.1, 0.15, 0.25, 0.4, 0.6, 0.8] 
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
            
            if (entry.isIntersecting && ratio > 0.1) {
              visibleWordTypes.set(key, ratio)
              
              // Only update if we're in the active cluster
              if (activeCluster.value === cluster.clusterId) {
                const clusterWordTypes = Array.from(visibleWordTypes.entries())
                  .filter(([wt]) => wt.startsWith(cluster.clusterId))
                  .sort(([, a], [, b]) => b - a)
                
                if (clusterWordTypes.length > 0 && clusterWordTypes[0][1] > 0.15) {
                  updateActiveWordType(clusterWordTypes[0][0])
                }
              }
            } else {
              visibleWordTypes.delete(key)
              
              // If this was the active word type, find next best in cluster
              if (activeWordType.value === key && activeCluster.value === cluster.clusterId) {
                const clusterWordTypes = Array.from(visibleWordTypes.entries())
                  .filter(([wt]) => wt.startsWith(cluster.clusterId))
                  .sort(([, a], [, b]) => b - a)
                
                if (clusterWordTypes.length > 0 && clusterWordTypes[0][1] > 0.1) {
                  updateActiveWordType(clusterWordTypes[0][0])
                } else {
                  // No visible word types in cluster, set to first word type
                  const clusterData = sidebarSections.value.find(c => c.clusterId === cluster.clusterId)
                  if (clusterData && clusterData.wordTypes.length > 0) {
                    updateActiveWordType(`${cluster.clusterId}-${clusterData.wordTypes[0].type}`)
                  }
                }
              }
            }
          },
          { 
            rootMargin: '-15% 0px -25% 0px', 
            threshold: [0.1, 0.15, 0.25, 0.4, 0.6] 
          }
        )
        observer.observe(element)
        wordTypeObservers.push(observer)
      })
    })
  })
}

// Debounced scroll handler to check for bottom state
const handleScroll = debounce(() => {
  if (sidebarSections.value.length === 0) return
  
  // Check if at bottom and last cluster isn't active
  if (isAtDocumentBottom()) {
    const lastCluster = sidebarSections.value[sidebarSections.value.length - 1]
    if (activeCluster.value !== lastCluster.clusterId) {
      updateActiveCluster(lastCluster.clusterId)
      if (lastCluster.wordTypes.length > 0) {
        const lastWordType = lastCluster.wordTypes[lastCluster.wordTypes.length - 1]
        updateActiveWordType(`${lastCluster.clusterId}-${lastWordType.type}`)
      }
    }
  }
}, 100)

onMounted(() => {
  checkShowSidebar()
  window.addEventListener('resize', checkShowSidebar)
  window.addEventListener('scroll', handleScroll, { passive: true })
  
  // Setup observers when definitions are loaded
  if (sidebarSections.value.length > 0) {
    setupObservers()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkShowSidebar)
  window.removeEventListener('scroll', handleScroll)
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