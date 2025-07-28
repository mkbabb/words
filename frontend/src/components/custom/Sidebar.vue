<template>
  <div>
    <!-- Desktop Sidebar -->
    <aside
      :class="cn(
        'bg-background border-border fixed top-0 left-0 z-30 hidden h-full flex-col overflow-hidden border-r transition-all duration-500 ease-apple-smooth lg:flex',
        sidebarCollapsed ? 'w-16' : 'w-80'
      )"
    >
      <SidebarHeader :collapsed="sidebarCollapsed" />
      <SidebarContent :collapsed="sidebarCollapsed" />
      <SidebarFooter :collapsed="sidebarCollapsed" />
    </aside>

    <!-- Mobile Sidebar Modal -->
    <div class="pointer-events-none fixed inset-0 z-60 lg:hidden">
      <!-- Overlay -->
      <Transition
        enter-active-class="transition-opacity duration-400 ease-apple-smooth"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-300 ease-apple-smooth"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="sidebarOpen"
          @click="store.toggleSidebar()"
          class="pointer-events-auto fixed inset-0 bg-black/60 backdrop-blur-sm"
        />
      </Transition>

      <!-- Mobile Sidebar Content -->
      <div
        :class="cn(
          'bg-background/[0.98] border-border pointer-events-auto fixed top-0 left-0 z-50 flex h-full w-80 flex-col border-r shadow-2xl backdrop-blur-sm transition-transform duration-400 ease-apple-smooth',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )"
      >
        <SidebarHeader :collapsed="false" :mobile="true" />
        <SidebarContent :collapsed="false" :mobile="true" />
        <SidebarFooter :collapsed="false" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import SidebarHeader from './sidebar/SidebarHeader.vue';
import SidebarContent from './sidebar/SidebarContent.vue';
import SidebarFooter from './sidebar/SidebarFooter.vue';

const store = useAppStore();
const sidebarOpen = computed(() => store.sidebarOpen);
const sidebarCollapsed = computed(() => store.sidebarCollapsed);
</script>