<template>
  <div class="bg-background/95 backdrop-blur-sm rounded-lg p-3 space-y-2">
    <!-- Navigation Sections -->
    <nav class="space-y-2">
      <div
        v-for="(cluster, clusterIndex) in sidebarSections"
        :key="cluster.clusterId"
        class="space-y-1"
      >
        <!-- Cluster Section -->
        <button
          @click="scrollToCluster(cluster.clusterId)"
          :class="[
            'group flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm font-medium transition-all duration-200',
            activeCluster === cluster.clusterId
              ? 'bg-primary/10 text-primary sidebar-shimmer'
              : 'text-foreground/80 hover:bg-muted/50 hover:text-foreground'
          ]"
        >
          <span class="truncate text-left">{{ cluster.clusterDescription }}</span>
          <div
            v-if="activeCluster === cluster.clusterId"
            class="h-1.5 w-1.5 rounded-full bg-primary animate-pulse"
          />
        </button>

        <!-- Word Type Sub-sections -->
        <div class="ml-3 space-y-1">
          <div
            v-for="wordType in cluster.wordTypes"
            :key="`${cluster.clusterId}-${wordType.type}`"
            @click="scrollToWordType(cluster.clusterId, wordType.type)"
            :class="[
              'flex w-full items-center justify-between cursor-pointer rounded-md px-2 py-1 transition-all duration-200',
              activeWordType === `${cluster.clusterId}-${wordType.type}`
                ? 'bg-accent/15 opacity-100'
                : 'opacity-60 hover:bg-muted/30 hover:opacity-100'
            ]"
          >
            <span class="themed-word-type text-xs">{{ wordType.type }}</span>
            <span class="text-xs opacity-70">{{ wordType.count }}</span>
          </div>
        </div>

        <!-- Gradient Divider between clusters -->
        <div
          v-if="clusterIndex < sidebarSections.length - 1"
          class="my-3 h-px w-full gradient-hr"
        />
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useAppStore } from '@/stores'

const store = useAppStore()

// Active tracking
const activeCluster = ref<string>('')
const activeWordType = ref<string>('')

// Responsive behavior
const shouldShowSidebar = ref(false)

// Intersection observers
let clusterObservers: IntersectionObserver[] = []
let wordTypeObservers: IntersectionObserver[] = []

// Computed sidebar data structure
const sidebarSections = computed(() => {
  const entry = store.currentEntry
  if (!entry?.definitions) return []

  // Group by meaning cluster
  const clusters = new Map<string, {
    clusterId: string
    clusterDescription: string
    wordTypes: Array<{ type: string; count: number }>
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
        wordTypes: []
      })
    }

    const cluster = clusters.get(clusterId)!
    const existingType = cluster.wordTypes.find(wt => wt.type === definition.word_type)
    if (existingType) {
      existingType.count++
    } else {
      cluster.wordTypes.push({ type: definition.word_type, count: 1 })
    }
  })

  return Array.from(clusters.values())
})

// Check if we should show sidebar (desktop with enough space)
const checkShowSidebar = () => {
  const hasMultipleClusters = sidebarSections.value.length > 1
  const isDesktop = window.innerWidth >= 1280 // xl breakpoint
  const hasVerticalSpace = window.innerHeight >= 600
  
  shouldShowSidebar.value = hasMultipleClusters && isDesktop && hasVerticalSpace
}

// Scroll functions
const scrollToCluster = (clusterId: string) => {
  const element = document.querySelector(`[data-cluster-id="${clusterId}"]`)
  if (element) {
    element.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'start',
      inline: 'nearest'
    })
  }
}

const scrollToWordType = (clusterId: string, wordType: string) => {
  const element = document.querySelector(`[data-word-type="${clusterId}-${wordType}"]`)
  if (element) {
    element.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'start',
      inline: 'nearest'
    })
  }
}

// Setup intersection observers with improved tracking
const setupObservers = async () => {
  await nextTick()

  // Clear existing observers
  clusterObservers.forEach(observer => observer.disconnect())
  wordTypeObservers.forEach(observer => observer.disconnect())
  clusterObservers = []
  wordTypeObservers = []

  // Track visible clusters
  const visibleClusters = new Set<string>()
  const visibleWordTypes = new Set<string>()

  // Cluster observers with better logic
  sidebarSections.value.forEach((cluster) => {
    const element = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`)
    if (element) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting && entry.intersectionRatio > 0.1) {
            visibleClusters.add(cluster.clusterId)
            // Set as active if it's the first visible or has higher visibility
            if (!activeCluster.value || entry.intersectionRatio > 0.3) {
              activeCluster.value = cluster.clusterId
            }
          } else {
            visibleClusters.delete(cluster.clusterId)
            // If this was active and no longer visible, find next best
            if (activeCluster.value === cluster.clusterId && visibleClusters.size > 0) {
              activeCluster.value = Array.from(visibleClusters)[0]
            }
          }
        },
        { rootMargin: '-10% 0px -40% 0px', threshold: [0.1, 0.3, 0.5] }
      )
      observer.observe(element)
      clusterObservers.push(observer)
    }

    // Word type observers within cluster  
    cluster.wordTypes.forEach((wordType) => {
      const elements = document.querySelectorAll(`[data-word-type="${cluster.clusterId}-${wordType.type}"]`)
      elements.forEach((element) => {
        const observer = new IntersectionObserver(
          ([entry]) => {
            const key = `${cluster.clusterId}-${wordType.type}`
            if (entry.isIntersecting && entry.intersectionRatio > 0.2) {
              visibleWordTypes.add(key)
              if (activeCluster.value === cluster.clusterId) {
                activeWordType.value = key
              }
            } else {
              visibleWordTypes.delete(key)
              if (activeWordType.value === key && visibleWordTypes.size > 0) {
                // Find another visible word type in the same cluster
                const clusterWordTypes = Array.from(visibleWordTypes).filter(wt => 
                  wt.startsWith(cluster.clusterId)
                )
                if (clusterWordTypes.length > 0) {
                  activeWordType.value = clusterWordTypes[0]
                }
              }
            }
          },
          { rootMargin: '-20% 0px -30% 0px', threshold: [0.2, 0.5] }
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
/* Active shimmer animation for current cluster */
.sidebar-shimmer {
  background: linear-gradient(
    -45deg,
    var(--shimmer-base) 35%,
    var(--shimmer-highlight) 50%,
    var(--shimmer-base) 65%
  );
  background-size: 200%;
  background-position-x: 100%;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  animation: sidebar-shimmer-move 2s ease-in-out infinite;
  
  /* Light mode colors - use design system */
  --shimmer-base: hsl(var(--primary));
  --shimmer-highlight: hsl(var(--primary-foreground) / 0.8);
}

/* Dark mode - highlight should still be lighter */
:global(.dark) .sidebar-shimmer {
  --shimmer-base: hsl(var(--primary));
  --shimmer-highlight: hsl(var(--primary-foreground) / 0.9);
}

@keyframes sidebar-shimmer-move {
  0% {
    background-position-x: 100%;
  }
  15% {
    background-position-x: 85%;
  }
  85% {
    background-position-x: 15%;
  }
  100% {
    background-position-x: 0%;
  }
}

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