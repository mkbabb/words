<template>
  <div>
    <!-- Mobile Toggle Button -->
    <Button
      variant="outline"
      size="sm"
      @click="store.toggleSidebar()"
      class="fixed top-4 left-4 z-50 lg:hidden rounded-xl shadow-lg hover:scale-105 transition-all duration-200 card-shadow"
    >
      <PanelLeft :size="18" />
    </Button>

    <!-- Desktop Sidebar -->
    <aside
      :class="cn(
        'fixed left-0 top-0 h-full bg-background border-r border-border transition-all duration-300 ease-in-out z-30 hidden lg:flex flex-col overflow-hidden',
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
            class="p-2 hover:scale-105 transition-all duration-200"
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
            class="p-2 hover:scale-105 transition-all duration-200"
          >
            <PanelRight :size="16" class="text-muted-foreground" />
          </Button>
        </div>
      </div>

      <!-- Content with flex layout -->
      <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
          <!-- Scrollable content area -->
          <div class="flex-1 overflow-y-auto p-4 min-h-0">
            <div v-if="!sidebarCollapsed" class="mb-4">
              <h3 class="text-sm font-medium text-muted-foreground mb-3">Recent Searches</h3>
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
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 lg:hidden"
    >
      <div
        @click="store.toggleSidebar()"
        class="fixed inset-0 bg-black/50"
      />
      
      <div class="fixed left-0 top-0 h-full w-80 bg-background border-r border-border shadow-xl flex flex-col">
        <!-- Mobile Header -->
        <div class="p-4 border-b border-border flex items-center justify-between">
          <FloridifyIcon :expanded="true" />
          <Button
            variant="ghost"
            size="sm"
            @click="store.toggleSidebar()"
            class="p-2"
          >
            <X :size="18" />
          </Button>
        </div>

        <!-- Mobile Content -->
        <div class="flex-1 flex flex-col min-h-0">
          <div class="flex-1 overflow-y-auto p-4">
            <h3 class="text-sm font-medium text-muted-foreground mb-4">Recent Searches</h3>
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
import { X, PanelLeft, PanelRight, User } from 'lucide-vue-next';

const store = useAppStore();

const sidebarOpen = computed(() => store.sidebarOpen);
const sidebarCollapsed = computed(() => store.sidebarCollapsed);
</script>