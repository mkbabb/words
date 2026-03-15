<template>
  <div>
    <!-- Desktop Sidebar -->
    <aside
      :class="cn(
        'bg-background border-border fixed top-0 left-0 z-50 hidden h-full flex-col overflow-hidden border-r transition-[width] duration-300 ease-apple-smooth lg:flex',
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
          @click="ui.toggleSidebar()"
          class="pointer-events-auto fixed inset-0 glass-overlay"
        />
      </Transition>

      <!-- Mobile Sidebar Content -->
      <div
        :class="cn(
          'border-border pointer-events-auto fixed top-0 left-0 z-[81] flex h-full w-[min(80vw,320px)] flex-col border-r shadow-2xl glass-light transition-transform duration-400 ease-apple-smooth',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )"
        @touchstart.passive="onTouchStart"
        @touchmove.passive="onTouchMove"
        @touchend.passive="onTouchEnd"
      >
        <SidebarHeader :collapsed="false" :mobile="true" />
        <SidebarContent :collapsed="false" :mobile="true" />
        <SidebarFooter :collapsed="false" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useUIStore } from '@/stores/ui/ui-state';
import { cn } from '@/utils';
import SidebarHeader from './sidebar/SidebarHeader.vue';
import SidebarContent from './sidebar/SidebarContent.vue';
import SidebarFooter from './sidebar/SidebarFooter.vue';

const ui = useUIStore();
// CRITICAL: Use computed() to preserve reactivity from readonly refs
const sidebarOpen = computed(() => ui.sidebarOpen);
const sidebarCollapsed = computed(() => ui.sidebarCollapsed);

// Swipe-to-close gesture for mobile sidebar
const touchStartX = ref(0);
const touchCurrentX = ref(0);
const isSwiping = ref(false);
const SWIPE_THRESHOLD = 50;

const onTouchStart = (e: TouchEvent) => {
    touchStartX.value = e.touches[0].clientX;
    touchCurrentX.value = touchStartX.value;
    isSwiping.value = true;
};

const onTouchMove = (e: TouchEvent) => {
    if (!isSwiping.value) return;
    touchCurrentX.value = e.touches[0].clientX;
};

const onTouchEnd = () => {
    if (!isSwiping.value) return;
    const deltaX = touchStartX.value - touchCurrentX.value;
    // Swipe left to close
    if (deltaX > SWIPE_THRESHOLD && sidebarOpen.value) {
        ui.toggleSidebar();
    }
    isSwiping.value = false;
};
</script>

