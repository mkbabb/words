<template>
  <div>
    <!-- Mobile Toggle Button - Small Arrow inline with search bar -->
    <div
      :class="
        cn(
          'fixed top-[50%] z-70 transition-all duration-400 ease-apple-smooth lg:hidden',
          {
            
            'hidden': sidebarOpen
          }
        )
      "
    >
      <button
        @click="store.toggleSidebar()"
        :class="
          cn(
            'bg-background/80 border-border flex items-center justify-center border-2 shadow-lg backdrop-blur-sm transition-all duration-200',
            sidebarOpen 
              ? 'card-shadow rounded-xl h-12 w-12 p-4 hover:scale-105' 
              : 'rounded-lg h-8 w-8 p-1.5 hover:scale-110'
          )
        "
      >
        <!-- Arrow Icon when closed -->
        <div v-if="!sidebarOpen" class="flex items-center justify-center">
          <ChevronLeft 
            :size="12" 
            class="text-muted-foreground transition-colors duration-200 rotate-180"
          />
        </div>
        
        <!-- Hamburger Icon when opened - same as desktop -->
        <div v-else class="relative flex h-5 w-5 flex-col justify-center">
          <span
            :class="
              cn(
                'absolute left-0 h-0.5 w-full bg-current transition-all duration-400 ease-apple-smooth',
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
                'absolute top-1/2 left-0 h-0.5 w-full -translate-y-px bg-current transition-all duration-400 ease-apple-smooth',
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
                'absolute left-0 h-0.5 w-full bg-current transition-all duration-400 ease-apple-smooth',
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
          'bg-background border-border fixed top-0 left-0 z-30 hidden h-full flex-col overflow-hidden border-r transition-all duration-500 ease-apple-smooth lg:flex',
          {
            'w-80': !sidebarCollapsed,
            'w-16': sidebarCollapsed,
          }
        )
      "
    >
      <!-- Header -->
      <div class="border-border border-b p-4 flex items-center min-h-[4rem]">
        <div v-if="!sidebarCollapsed" class="flex items-center justify-between w-full">
          <!-- Left unit: Floridify + @mbabb grouped together -->
          <div class="flex items-center gap-3">
            <FloridifyIcon :expanded="true" :mode="store.mode" clickable @toggle-mode="store.toggleMode()" />
            <HoverCard :open-delay="600">
              <HoverCardTrigger>
                <Button variant="link" class="h-auto p-0 font-mono text-sm">@mbabb</Button>
              </HoverCardTrigger>
              <HoverCardContent>
                <div class="flex gap-4">
                  <Avatar>
                    <AvatarImage
                      src="https://avatars.githubusercontent.com/u/2848617?v=4"
                    />
                  </Avatar>
                  <div>
                    <h4 class="text-sm font-semibold hover:underline">
                      <a href="https://github.com/mkbabb" class="font-mono">@mbabb</a>
                    </h4>
                    <p class="text-muted-foreground text-sm">
                      AI-enhanced dictionary system
                    </p>
                  </div>
                </div>
              </HoverCardContent>
            </HoverCard>
          </div>
          <!-- Right: Dark Mode Toggle + Controls -->
          <div class="flex items-center gap-3">
            <DarkModeToggle class="h-7 w-7 transition-all duration-500 ease-apple-smooth" />
            <HamburgerIcon
              :is-open="!sidebarCollapsed"
              class="cursor-ew-resize hover:bg-muted/50 rounded-lg p-1 transition-all duration-300 ease-apple-smooth"
              @toggle="store.setSidebarCollapsed(!sidebarCollapsed)"
            />
          </div>
        </div>
        <div v-else class="flex items-center justify-between w-full">
          <DarkModeToggle class="h-7 w-7" />
          <button
            @click="store.setSidebarCollapsed(false)"
            class="cursor-ew-resize hover:bg-muted/50 rounded-lg p-2 transition-all duration-300 ease-apple-smooth hover:scale-105"
          >
            <PanelRight :size="16" class="text-muted-foreground" />
          </button>
        </div>
      </div>

      <!-- Content with flex layout -->
      <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
        <!-- Scrollable content area -->
        <div class="min-h-0 flex-1 overflow-y-auto p-4 overscroll-contain">
          <!-- Vocabulary Suggestions -->
          <Transition
            enter-active-class="transition-all duration-400 ease-apple-smooth"
            leave-active-class="transition-all duration-300 ease-apple-smooth"
            enter-from-class="opacity-0 -translate-y-4"
            enter-to-class="opacity-100 translate-y-0"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-4"
          >
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
          </Transition>

          <!-- Recent Lookups -->
          <Transition
            enter-active-class="transition-all duration-400 ease-apple-smooth"
            leave-active-class="transition-all duration-300 ease-apple-smooth"
            enter-from-class="opacity-0 -translate-y-4"
            enter-to-class="opacity-100 translate-y-0"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 -translate-y-4"
          >
            <div v-if="!sidebarCollapsed" class="mb-4">
              <h3 class="text-muted-foreground mb-3 text-sm font-medium">
                Recent Lookups
              </h3>
            </div>
          </Transition>
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
        enter-active-class="transition-all duration-400 ease-apple-smooth"
        enter-from-class="opacity-0 translate-x-full"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition-all duration-300 ease-apple-smooth"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-full"
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
            'bg-background/[0.98] border-border pointer-events-auto fixed top-0 left-0 z-50 flex h-full w-80 flex-col border-r shadow-2xl backdrop-blur-sm transition-transform duration-400 ease-apple-smooth',
            {
              'translate-x-0': sidebarOpen,
              '-translate-x-full': !sidebarOpen,
            }
          )
        "
      >
        <!-- Mobile Header -->
        <div class="border-border border-b p-4 flex items-center justify-center min-h-[4rem]">
          <div class="flex items-center justify-between w-full">
            <!-- Left unit: Floridify + @mbabb grouped together -->
            <div class="flex items-center gap-3">
              <FloridifyIcon :expanded="true" :mode="store.mode" clickable @toggle-mode="store.toggleMode()" />
              <HoverCard :open-delay="0">
                <HoverCardTrigger>
                  <Button variant="link" class="h-auto p-0 font-mono text-sm">@mbabb</Button>
                </HoverCardTrigger>
                <HoverCardContent>
                  <div class="flex gap-4">
                    <Avatar>
                      <AvatarImage
                        src="https://avatars.githubusercontent.com/u/2848617?v=4"
                      />
                    </Avatar>
                    <div>
                      <h4 class="text-sm font-semibold hover:underline">
                        <a href="https://github.com/mkbabb" class="font-mono">@mbabb</a>
                      </h4>
                      <p class="text-muted-foreground text-sm">
                        AI-enhanced dictionary system
                      </p>
                    </div>
                  </div>
                </HoverCardContent>
              </HoverCard>
            </div>
            
            <!-- Right: Dark Mode Toggle + Hamburger -->
            <div class="flex items-center gap-3">
              <DarkModeToggle class="h-7 w-7 transition-all duration-500 ease-apple-smooth" />
              <HamburgerIcon
                :is-open="true"
                class="cursor-pointer hover:bg-muted/50 rounded-lg p-1 transition-all duration-300 ease-apple-smooth"
                @toggle="store.toggleSidebar()"
              />
            </div>
          </div>
        </div>

        <!-- Mobile Content -->
        <div class="flex min-h-0 flex-1 flex-col">
          <div class="flex-1 overflow-y-auto p-4 overscroll-contain">
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
import { SearchHistoryContent } from '@/components/custom/search';
import { FloridifyIcon, HamburgerIcon } from '@/components/custom/icons';
import { DarkModeToggle } from '@/components/custom/dark-mode-toggle';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';
import { Avatar, AvatarImage, Button } from '@/components/ui';
import { PanelRight, User, ChevronLeft } from 'lucide-vue-next';

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
