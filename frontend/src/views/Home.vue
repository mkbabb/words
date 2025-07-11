<template>
  <!-- Sidebar -->
  <Sidebar />

  <div 
    :class="cn(
      'min-h-screen transition-all duration-300 ease-in-out',
      {
        'lg:ml-80': !store.sidebarCollapsed,
        'lg:ml-16': store.sidebarCollapsed,
      }
    )"
  >
    <!-- Main View -->
    <div class="min-h-screen">
      <Tabs v-model="activeTab" class="w-full">
        <!-- Fixed Header with Tabs and Search -->
        <div class="sticky top-0 z-40 bg-background/95 backdrop-blur-3xl border-b">
          <div class="container mx-auto px-4 py-4">
            <div class="max-w-5xl mx-auto space-y-4">
              <!-- Header with Author Card -->
              <div class="flex justify-between items-center">
                <div class="flex-1" />
                <div class="flex-1 flex justify-center">
                  <TabsList>
                    <TabsTrigger value="definition" style="font-family: 'Fraunces', serif;">Dictionary</TabsTrigger>
                    <TabsTrigger value="visualizer" style="font-family: 'Fraunces', serif;">Visualizer</TabsTrigger>
                  </TabsList>
                </div>
                <div class="flex-1 flex justify-end">
                  <HoverCard :open-delay="0">
                    <HoverCardTrigger>
                      <Button variant="link" class="p-0 h-auto font-mono text-sm">@mbabb</Button>
                    </HoverCardTrigger>
                    <HoverCardContent>
                      <div class="flex gap-4">
                        <Avatar>
                          <AvatarImage src="https://avatars.githubusercontent.com/u/2848617?v=4" />
                        </Avatar>
                        <div>
                          <h4 class="text-sm font-semibold hover:underline">
                            <a href="https://github.com/mkbabb" class="font-mono">@mbabb</a>
                          </h4>
                          <p class="text-sm text-muted-foreground">
                            Legendre polynomial visualization and dictionary system
                          </p>
                        </div>
                      </div>
                    </HoverCardContent>
                  </HoverCard>
                </div>
              </div>
              
              <!-- Search Bar -->
              <div class="search-container">
                <SearchBar />
              </div>
            </div>
          </div>
        </div>

        <!-- Content Area -->
        <div class="container mx-auto px-4 py-8">
          <div class="max-w-5xl mx-auto">
            <!-- Definition Tab Content -->
            <TabsContent value="definition">
              <!-- Loading State -->
              <div v-if="isSearching" class="space-y-8">
                <DefinitionSkeleton />
              </div>

              <!-- Definition Display -->
              <div v-else-if="currentEntry" class="space-y-8">
                <DefinitionDisplay variant="default" />
              </div>

              <!-- Empty State -->
              <div v-else class="text-center py-16">
                <!-- Empty state - no text -->
              </div>
            </TabsContent>

            <!-- Visualizer Tab Content -->
            <TabsContent value="visualizer">
              <div class="space-y-6">
                <div>
                  <h2 class="text-3xl font-bold tracking-tight" style="font-family: 'Fraunces', serif;">Legendre Polynomial System</h2>
                  <p class="text-muted-foreground/70 mt-2 italic dark:text-muted-foreground/50" style="font-family: 'Fraunces', serif;">Interactive visualization and series approximation using Legendre polynomials</p>
                </div>
                
                <LegendreVisualization />
              </div>
            </TabsContent>
          </div>
        </div>
      </Tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import SearchBar from '@/components/SearchBar.vue';
import DefinitionDisplay from '@/components/DefinitionDisplay.vue';
import DefinitionSkeleton from '@/components/DefinitionSkeleton.vue';
import Sidebar from '@/components/Sidebar.vue';
import LegendreVisualization from '@/components/LegendreVisualization.vue';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import HoverCard from '@/components/ui/HoverCard.vue';
import HoverCardTrigger from '@/components/ui/HoverCardTrigger.vue';
import HoverCardContent from '@/components/ui/HoverCardContent.vue';
import Avatar from '@/components/ui/Avatar.vue';
import AvatarImage from '@/components/ui/AvatarImage.vue';
import Button from '@/components/ui/Button.vue';

const store = useAppStore();
const activeTab = ref<'definition' | 'visualizer'>('definition');

onMounted(async () => {
  console.log('Home component mounted');
  console.log('Has searched:', store.hasSearched);
  console.log('Search results:', store.searchResults);
  
  // Ensure vocabulary suggestions are loaded
  if (store.vocabularySuggestions.length === 0) {
    await store.refreshVocabularySuggestions();
  }
});

const isSearching = computed(() => store.isSearching);
const currentEntry = computed(() => store.currentEntry);

</script>