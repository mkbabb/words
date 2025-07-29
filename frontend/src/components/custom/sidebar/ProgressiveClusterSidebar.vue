<template>
  <ProgressiveSidebarBase max-height="max-h-[calc(100vh-12rem)]">
    <!-- Header with Controls -->
    <template #header>
      <div class="border-b border-border/50 bg-muted/30 rounded-t-lg">
        <div class="flex items-center justify-between px-3 py-3">
          <div class="flex items-center gap-2">
            <div class="h-2 w-2 rounded-full bg-primary"></div>
            <h3 class="text-sm font-semibold text-foreground">Clustering Controls</h3>
          </div>
          <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="ghost" size="sm" class="h-6 w-6 p-0">
              <MoreVertical class="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent 
            align="end" 
            class="w-48 transition-all duration-350 ease-apple-elastic" 
            @click.stop
          >
            <DropdownMenuLabel>Cluster by</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem @click.stop="toggleCluster('mastery')">
              <div class="flex items-center justify-between w-full">
                <span>Mastery Level</span>
                <div v-if="clusterBy.includes('mastery')" class="h-2 w-2 bg-primary rounded-full"></div>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem @click.stop="toggleCluster('frequency')">
              <div class="flex items-center justify-between w-full">
                <span>Frequency</span>
                <div v-if="clusterBy.includes('frequency')" class="h-2 w-2 bg-primary rounded-full"></div>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem @click.stop="toggleCluster('lastAccessed')">
              <div class="flex items-center justify-between w-full">
                <span>Last Accessed</span>
                <div v-if="clusterBy.includes('lastAccessed')" class="h-2 w-2 bg-primary rounded-full"></div>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem @click.stop="toggleCluster('wordCount')">
              <div class="flex items-center justify-between w-full">
                <span>Word Count</span>
                <div v-if="clusterBy.includes('wordCount')" class="h-2 w-2 bg-primary rounded-full"></div>
              </div>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem @click.stop="clearClusters">
              Clear All
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        </div>
      </div>
    </template>

    <!-- Content -->
    <template #content>
      <!-- No clustering selected -->
      <div v-if="clusterBy.length === 0" class="px-3 py-8 text-center">
        <div class="text-sm text-muted-foreground">
          <p class="mb-2">🎯 Select clustering options</p>
          <p class="text-xs">Use the dropdown above to organize your wordlist</p>
        </div>
      </div>

      <!-- Clustered view -->
      <div v-else class="space-y-1">
        <div v-for="(cluster, index) in clusteredData" :key="cluster.title">
          <!-- Cluster Header -->
          <button
            @click="toggleClusterExpanded(cluster.title)"
            :class="[
              'w-full text-left px-3 py-2 rounded-md transition-all duration-200',
              expandedClusters.includes(cluster.title)
                ? 'bg-primary/10 text-primary'
                : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <ChevronRight 
                  :class="[
                    'h-3 w-3 transition-transform',
                    expandedClusters.includes(cluster.title) ? 'rotate-90' : ''
                  ]"
                />
                <span class="text-sm font-medium">{{ cluster.title }}</span>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span>{{ cluster.items.length }}</span>
                <component :is="cluster.icon" class="h-3 w-3" />
              </div>
            </div>
          </button>

          <!-- Cluster Content with smooth animation -->
          <transition
            enter-active-class="transition ease-out duration-200"
            enter-from-class="transform opacity-0 scale-95 -translate-y-2"
            enter-to-class="transform opacity-100 scale-100 translate-y-0"
            leave-active-class="transition ease-in duration-150"
            leave-from-class="transform opacity-100 scale-100 translate-y-0"
            leave-to-class="transform opacity-0 scale-95 -translate-y-2"
          >
            <div 
              v-if="expandedClusters.includes(cluster.title)"
              class="ml-6 space-y-1 pb-2 origin-top"
            >
              <div 
                v-for="word in cluster.items" 
                :key="word.id"
                class="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/30 rounded cursor-pointer transition-colors"
                @click="$emit('word-click', word)"
              >
                <div class="flex items-center justify-between">
                  <span>{{ word.text }}</span>
                  <span class="text-xs">{{ word.frequency }}x</span>
                </div>
              </div>
            </div>
          </transition>

          <!-- Separator -->
          <hr
            v-if="index < clusteredData.length - 1"
            class="my-1 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
          />
        </div>
      </div>
    </template>
  </ProgressiveSidebarBase>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  MoreVertical, 
  ChevronRight,
  Trophy,
  Medal,
  TrendingUp,
  TrendingDown,
  Clock,
  Calendar,
  Folder,
  Ruler,
  FileText,
  Bookmark
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import ProgressiveSidebarBase from '@/components/custom/navigation/ProgressiveSidebarBase.vue';

interface WordItem {
  id: string;
  text: string;
  mastery_level: 'default' | 'bronze' | 'silver' | 'gold';
  frequency: number;
  last_visited?: string;
  temperature?: 'hot' | 'cold';
}

interface Props {
  words?: WordItem[];
}

const props = withDefaults(defineProps<Props>(), {
  words: () => []
});

const emit = defineEmits<{
  'word-click': [word: WordItem];
  'clustering-changed': [criteria: string[]];
}>();

// State
const clusterBy = ref<string[]>([]);
const expandedClusters = ref<string[]>([]);

// Methods
const toggleCluster = (type: string) => {
  if (clusterBy.value.includes(type)) {
    clusterBy.value = clusterBy.value.filter(c => c !== type);
  } else {
    clusterBy.value.push(type);
  }
};

const clearClusters = () => {
  clusterBy.value = [];
  expandedClusters.value = [];
};

const toggleClusterExpanded = (clusterTitle: string) => {
  if (expandedClusters.value.includes(clusterTitle)) {
    expandedClusters.value = expandedClusters.value.filter(c => c !== clusterTitle);
  } else {
    expandedClusters.value.push(clusterTitle);
  }
};

// Helper function to get cluster info for a single criterion
const getClusterPart = (type: string, word: WordItem) => {
  if (type === 'mastery') {
    const info = {
      default: { title: 'New', icon: FileText },
      bronze: { title: 'Learning', icon: Medal },
      silver: { title: 'Familiar', icon: Trophy }, 
      gold: { title: 'Mastered', icon: Trophy }
    }[word.mastery_level];
    return info;
  } else if (type === 'frequency') {
    if (word.frequency > 50) return { title: 'High Freq', icon: TrendingUp };
    else if (word.frequency > 20) return { title: 'Med Freq', icon: TrendingUp };
    else return { title: 'Low Freq', icon: TrendingDown };
  } else if (type === 'lastAccessed' && word.last_visited) {
    const days = Math.floor((Date.now() - new Date(word.last_visited).getTime()) / (1000 * 60 * 60 * 24));
    if (days < 7) return { title: 'Recent', icon: Clock };
    else if (days < 30) return { title: 'This Month', icon: Calendar };
    else return { title: 'Older', icon: Folder };
  } else if (type === 'wordCount') {
    const length = word.text.length;
    if (length > 8) return { title: 'Long', icon: Ruler };
    else if (length > 5) return { title: 'Medium', icon: FileText };
    else return { title: 'Short', icon: Bookmark };
  }
  return { title: 'Other', icon: FileText };
};

// Helper function to generate multi-criteria cluster info
const getMultiClusterInfo = (criteria: string[], word: WordItem) => {
  if (criteria.length === 0) return { title: 'All Words', icon: FileText };
  
  const parts = criteria.map(criterion => getClusterPart(criterion, word));
  const title = parts.map(p => p.title).join(' + ');
  const icon = parts[0].icon; // Use icon from first criterion
  
  return { title, icon };
};

// Word clustering logic with multi-criteria support
const clusteredData = computed(() => {
  if (clusterBy.value.length === 0) return [];
  
  const clusters = new Map<string, { items: WordItem[], icon: any }>();
  
  for (const word of props.words) {
    // Generate cluster info based on all selected criteria
    const clusterInfo = getMultiClusterInfo(clusterBy.value, word);
    const clusterKey = clusterInfo.title;
    
    if (!clusters.has(clusterKey)) {
      clusters.set(clusterKey, { items: [], icon: clusterInfo.icon });
    }
    clusters.get(clusterKey)!.items.push(word);
  }
  
  // Sort clusters by size (largest first) for better UX
  return Array.from(clusters.entries())
    .sort(([, a], [, b]) => b.items.length - a.items.length)
    .map(([title, data]) => ({
      title,
      items: data.items,
      icon: data.icon
    }));
});

// Watch for clustering criteria changes and emit to parent
watch(clusterBy, (newCriteria) => {
  emit('clustering-changed', [...newCriteria]);
}, { deep: true });
</script>