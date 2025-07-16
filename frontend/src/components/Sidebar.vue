<template>
  <div>
    <!-- Mobile Toggle Button -->
    <div
      :class="
        cn(
          'fixed top-2 left-2 z-70 transition-transform duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)] lg:hidden',
          {
            'translate-x-0': !sidebarOpen,
            'translate-x-64': sidebarOpen, // Move with sidebar - w-64 = 256px to keep it within the sidebar
          }
        )
      "
    >
      <button
        @click="store.toggleSidebar()"
        class="card-shadow bg-background/90 border-border flex h-12 w-12 items-center justify-center rounded-xl border p-4 shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-105"
      >
        <!-- Hamburger/Close Icon Animation -->
        <div class="relative flex h-5 w-5 flex-col justify-center">
          <span
            :class="
              cn(
                'absolute left-0 h-0.5 w-full bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
                {
                  'top-1/2 -translate-y-px rotate-45': sidebarOpen,
                  'top-1 rotate-0': !sidebarOpen,
                }
              )
            "
          />
          <span
            :class="
              cn(
                'absolute top-1/2 left-0 h-0.5 w-full -translate-y-px bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
                {
                  'opacity-0': sidebarOpen,
                  'opacity-100': !sidebarOpen,
                }
              )
            "
          />
          <span
            :class="
              cn(
                'absolute left-0 h-0.5 w-full bg-current transition-all duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
                {
                  'top-1/2 -translate-y-px -rotate-45': sidebarOpen,
                  'bottom-1 rotate-0': !sidebarOpen,
                }
              )
            "
          />
        </div>
      </button>
    </div>

    <!-- Desktop Sidebar -->
    <aside
      :class="
        cn(
          'bg-background border-border fixed top-0 left-0 z-30 hidden h-full flex-col overflow-hidden border-r transition-all duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] lg:flex',
          {
            'w-80': !sidebarCollapsed,
            'w-16': sidebarCollapsed,
          }
        )
      "
    >
      <!-- Header -->
      <div class="border-border border-b p-4">
        <div v-if="!sidebarCollapsed" class="flex items-center justify-between">
          <FloridifyIcon :expanded="true" />
          <Button
            variant="ghost"
            size="sm"
            @click="store.setSidebarCollapsed(!sidebarCollapsed)"
            class="p-2 transition-all duration-150 ease-[cubic-bezier(0.4,0,0.2,1)] hover:scale-105"
          >
            <PanelLeft :size="16" class="text-muted-foreground" />
          </Button>
        </div>
        <div v-else class="flex items-center justify-center">
          <Button
            variant="ghost"
            size="sm"
            @click="store.setSidebarCollapsed(false)"
            class="p-2 transition-all duration-150 ease-[cubic-bezier(0.4,0,0.2,1)] hover:scale-105"
          >
            <PanelRight :size="16" class="text-muted-foreground" />
          </Button>
        </div>
      </div>

      <!-- Content with flex layout -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
        <!-- Scrollable content area -->
        <div class="min-h-0 flex-1 overflow-y-auto p-4">
          <!-- Vocabulary Suggestions -->
          <div
            v-if="!sidebarCollapsed && store.vocabularySuggestions.length > 0"
            class="mb-6"
          >
            <h3 class="text-muted-foreground mb-3 text-sm font-medium">
              Vocabulary Suggestions
            </h3>
            <div class="space-y-2">
              <div
                v-for="suggestion in store.vocabularySuggestions.slice(0, 3)"
                :key="suggestion.word"
                class="group border-border from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15 cursor-pointer rounded-lg border bg-gradient-to-br p-3 transition-all duration-200 hover:shadow-sm"
                @click="lookupSuggestion(suggestion.word)"
              >
                <div class="flex items-start justify-between">
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium">
                      {{ suggestion.word }}
                    </p>
                    <p class="text-muted-foreground mt-1 line-clamp-2 text-xs">
                      {{ suggestion.reasoning }}
                    </p>
                  </div>
                  <div class="ml-2 flex-shrink-0">
                    <span
                      class="text-primary bg-primary/20 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-medium"
                    >
                      {{ suggestion.difficulty_level }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Recent Lookups -->
          <div v-if="!sidebarCollapsed" class="mb-4">
            <h3 class="text-muted-foreground mb-3 text-sm font-medium">
              Recent Lookups
            </h3>
          </div>
          <SearchHistoryContent :collapsed="sidebarCollapsed" />
        </div>

        <!-- User Section - locked to bottom -->
        <div class="border-border flex-shrink-0 border-t p-4">
          <div v-if="!sidebarCollapsed" class="flex items-center gap-3">
            <div
              class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
            >
              <User :size="14" class="text-primary" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="truncate text-sm font-medium">Demo User</div>
              <div class="text-muted-foreground truncate text-xs">
                demo@floridify.com
              </div>
            </div>
          </div>
          <div v-else class="flex justify-center">
            <div
              class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
            >
              <User :size="14" class="text-primary" />
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Mobile Sidebar Modal -->
    <div class="pointer-events-none fixed inset-0 z-60 lg:hidden">
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
          class="pointer-events-auto fixed top-0 right-0 bottom-0 left-80 z-10 bg-black/60 backdrop-blur-sm"
        />
      </Transition>

      <!-- Sidebar Content -->
      <div
        :class="
          cn(
            'bg-background/[0.98] border-border pointer-events-auto fixed top-0 left-0 z-50 flex h-full w-80 flex-col border-r shadow-2xl backdrop-blur-sm transition-transform duration-250 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]',
            {
              'translate-x-0': sidebarOpen,
              '-translate-x-full': !sidebarOpen,
            }
          )
        "
      >
        <!-- Mobile Header -->
        <div class="border-border border-b p-4">
          <FloridifyIcon :expanded="true" />
        </div>

        <!-- Mobile Content -->
        <div class="flex min-h-0 flex-1 flex-col">
          <div class="flex-1 overflow-y-auto p-4">
            <!-- Mobile Vocabulary Suggestions -->
            <div v-if="store.vocabularySuggestions.length > 0" class="mb-6">
              <h3 class="text-muted-foreground mb-3 text-sm font-medium">
                Vocabulary Suggestions
              </h3>
              <div class="space-y-2">
                <div
                  v-for="suggestion in store.vocabularySuggestions.slice(0, 3)"
                  :key="suggestion.word"
                  class="group border-border from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15 cursor-pointer rounded-lg border bg-gradient-to-br p-3 transition-all duration-200 hover:shadow-sm"
                  @click="lookupSuggestion(suggestion.word)"
                >
                  <div class="flex items-start justify-between">
                    <div class="min-w-0 flex-1">
                      <p class="truncate text-sm font-medium">
                        {{ suggestion.word }}
                      </p>
                      <p
                        class="text-muted-foreground mt-1 line-clamp-2 text-xs"
                      >
                        {{ suggestion.reasoning }}
                      </p>
                    </div>
                    <div class="ml-2 flex-shrink-0">
                      <span
                        class="text-primary bg-primary/20 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-medium"
                      >
                        {{ suggestion.difficulty_level }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <h3 class="text-muted-foreground mb-4 text-sm font-medium">
              Recent Lookups
            </h3>
            <SearchHistoryContent :collapsed="false" />
          </div>

          <div class="border-border border-t p-4">
            <div class="flex items-center gap-3">
              <div
                class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
              >
                <User :size="14" class="text-primary" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium">Demo User</div>
                <div class="text-muted-foreground truncate text-xs">
                  demo@floridify.com
                </div>
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
import FloridifyIcon from '@/components/ui/icons/FloridifyIcon.vue';
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
