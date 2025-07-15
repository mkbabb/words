<template>
  <div>
    <!-- Mobile Toggle Button -->
    <div 
      :class="cn(
        'fixed top-2 left-2 z-50 lg:hidden transition-transform duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
        {
          'translate-x-0': !sidebarOpen,
          'translate-x-64': sidebarOpen, // Move with sidebar - w-64 = 256px to keep it within the sidebar
        }
      )"
    >
      <button
        @click="store.toggleSidebar()"
        class="rounded-xl shadow-lg hover:scale-105 transition-all duration-200 card-shadow bg-background/90 backdrop-blur-sm border border-border p-4 flex items-center justify-center w-12 h-12"
      >
        <!-- Hamburger/Close Icon Animation -->
        <div class="w-5 h-5 relative flex flex-col justify-center">
          <span 
            :class="cn(
              'absolute left-0 h-0.5 w-full bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
              {
                'top-1/2 rotate-45 -translate-y-px': sidebarOpen,
                'top-1 rotate-0': !sidebarOpen,
              }
            )"
          />
          <span 
            :class="cn(
              'absolute left-0 top-1/2 h-0.5 w-full bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)] -translate-y-px',
              {
                'opacity-0': sidebarOpen,
                'opacity-100': !sidebarOpen,
              }
            )"
          />
          <span 
            :class="cn(
              'absolute left-0 h-0.5 w-full bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
              {
                'top-1/2 -rotate-45 -translate-y-px': sidebarOpen,
                'bottom-1 rotate-0': !sidebarOpen,
              }
            )"
          />
        </div>
      </button>
    </div>

    <!-- Desktop Sidebar -->
    <aside
      :class="cn(
        'fixed left-0 top-0 h-full bg-background border-r border-border transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] z-30 hidden lg:flex flex-col overflow-hidden',
        {
          'w-80': !sidebarCollapsed,
          'w-16': sidebarCollapsed,
        }
      )"
    >
      <!-- Header -->
      <div class="p-4 border-b border-border">
        <div v-if="!sidebarCollapsed" class="flex items-center justify-between">
          <FloridifyIcon :expanded="true" />
          <Button
            variant="ghost"
            size="sm"
            @click="store.setSidebarCollapsed(!sidebarCollapsed)"
            class="p-2 hover:scale-105 transition-all duration-150 ease-[cubic-bezier(0.4,0,0.2,1)]"
          >
            <PanelLeft :size="16" class="text-muted-foreground" />
          </Button>
        </div>
        <div
          v-else
          class="flex items-center justify-center"
        >
          <Button
            variant="ghost"
            size="sm"
            @click="store.setSidebarCollapsed(false)"
            class="p-2 hover:scale-105 transition-all duration-150 ease-[cubic-bezier(0.4,0,0.2,1)]"
          >
            <PanelRight :size="16" class="text-muted-foreground" />
          </Button>
        </div>
      </div>

      <!-- Content with flex layout -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
          <!-- Scrollable content area -->
          <div class="flex-1 overflow-y-auto p-4 min-h-0">
            <!-- Vocabulary Suggestions -->
            <div v-if="!sidebarCollapsed && store.vocabularySuggestions.length > 0" class="mb-6">
              <h3 class="text-sm font-medium text-muted-foreground mb-3">Vocabulary Suggestions</h3>
              <div class="space-y-2">
                <div
                  v-for="suggestion in store.vocabularySuggestions.slice(0, 3)"
                  :key="suggestion.word"
                  class="group p-3 rounded-lg border border-border bg-gradient-to-br from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15 cursor-pointer transition-all duration-200 hover:shadow-sm"
                  @click="lookupSuggestion(suggestion.word)"
                >
                  <div class="flex items-start justify-between">
                    <div class="min-w-0 flex-1">
                      <p class="font-medium text-sm truncate">{{ suggestion.word }}</p>
                      <p class="text-xs text-muted-foreground mt-1 line-clamp-2">{{ suggestion.reasoning }}</p>
                    </div>
                    <div class="ml-2 flex-shrink-0">
                      <span class="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-primary bg-primary/20 rounded-full">
                        {{ suggestion.difficulty_level }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            
            <!-- Recent Lookups -->
            <div v-if="!sidebarCollapsed" class="mb-4">
              <h3 class="text-sm font-medium text-muted-foreground mb-3">Recent Lookups</h3>
            </div>
            <SearchHistoryContent :collapsed="sidebarCollapsed" />
          </div>

          <!-- User Section - locked to bottom -->
          <div class="border-t border-border p-4 flex-shrink-0">
            <div v-if="!sidebarCollapsed" class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/20">
                <User :size="14" class="text-primary" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate">Demo User</div>
                <div class="text-xs text-muted-foreground truncate">demo@floridify.com</div>
              </div>
            </div>
            <div v-else class="flex justify-center">
              <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/20">
                <User :size="14" class="text-primary" />
              </div>
            </div>
          </div>
      </div>
    </aside>

    <!-- Mobile Sidebar Modal -->
    <div class="fixed inset-0 z-40 lg:hidden pointer-events-none">
      <!-- Overlay that darkens only the non-sidebar area -->
      <Transition
        enter-active-class="transition-opacity duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-200 ease-[cubic-bezier(0.55,0.06,0.68,0.19)]"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="sidebarOpen"
          @click="store.toggleSidebar()"
          class="fixed left-80 top-0 right-0 bottom-0 bg-black/60 backdrop-blur-sm z-10 pointer-events-auto"
        />
      </Transition>
      
      <!-- Sidebar Content -->
      <div 
        :class="cn(
          'fixed left-0 top-0 h-full w-80 bg-background/[0.98] backdrop-blur-sm border-r border-border shadow-2xl flex flex-col z-50 transition-transform duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)] pointer-events-auto',
          {
            'translate-x-0': sidebarOpen,
            '-translate-x-full': !sidebarOpen,
          }
        )"
      >
            <!-- Mobile Header -->
            <div class="p-4 border-b border-border">
              <FloridifyIcon :expanded="true" />
            </div>

            <!-- Mobile Content -->
            <div class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-y-auto p-4">
                <!-- Mobile Vocabulary Suggestions -->
                <div v-if="store.vocabularySuggestions.length > 0" class="mb-6">
                  <h3 class="text-sm font-medium text-muted-foreground mb-3">Vocabulary Suggestions</h3>
                  <div class="space-y-2">
                    <div
                      v-for="suggestion in store.vocabularySuggestions.slice(0, 3)"
                      :key="suggestion.word"
                      class="group p-3 rounded-lg border border-border bg-gradient-to-br from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15 cursor-pointer transition-all duration-200 hover:shadow-sm"
                      @click="lookupSuggestion(suggestion.word)"
                    >
                      <div class="flex items-start justify-between">
                        <div class="min-w-0 flex-1">
                          <p class="font-medium text-sm truncate">{{ suggestion.word }}</p>
                          <p class="text-xs text-muted-foreground mt-1 line-clamp-2">{{ suggestion.reasoning }}</p>
                        </div>
                        <div class="ml-2 flex-shrink-0">
                          <span class="inline-flex items-center justify-center w-5 h-5 text-xs font-medium text-primary bg-primary/20 rounded-full">
                            {{ suggestion.difficulty_level }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <h3 class="text-sm font-medium text-muted-foreground mb-4">Recent Lookups</h3>
                <SearchHistoryContent :collapsed="false" />
              </div>

              <div class="border-t border-border p-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/20">
                    <User :size="14" class="text-primary" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium truncate">Demo User</div>
                    <div class="text-xs text-muted-foreground truncate">demo@floridify.com</div>
                  </div>
                </div>
              </div>
            </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import Button from '@/components/ui/Button.vue';
import SearchHistoryContent from '@/components/SearchHistoryContent.vue';
import FloridifyIcon from '@/components/FloridifyIcon.vue';
import { PanelLeft, PanelRight, User } from 'lucide-vue-next';

const store = useAppStore();

const sidebarOpen = computed(() => store.sidebarOpen);
const sidebarCollapsed = computed(() => store.sidebarCollapsed);

const lookupSuggestion = async (word: string) => {
  store.searchQuery = word;
  await store.searchWord(word);
  // Close mobile sidebar after lookup
  if (store.sidebarOpen) {
    store.toggleSidebar();
  }
};
</script>