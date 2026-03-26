<template>
    <!-- Collapsed View -->
    <Transition
        enter-active-class="transition-fast"
        leave-active-class="transition-fast"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
    >
        <div
            v-if="collapsed"
            key="collapsed"
            class="flex h-full w-full flex-col"
        >
            <!-- Collapsed view - compact cards -->
            <div class="relative min-h-0 flex-1">
                <div class="absolute inset-0">
                    <div
                        class="max-h-full space-y-1 overflow-y-auto overscroll-contain"
                    >
                        <TransitionGroup
                            enter-active-class="transition-smooth"
                            leave-active-class="transition-normal"
                            enter-from-class="opacity-0 -translate-y-4 scale-95"
                            enter-to-class="opacity-100 translate-y-0 scale-100"
                            leave-from-class="opacity-100 translate-y-0 scale-100"
                            leave-to-class="opacity-0 translate-y-4 scale-95"
                            move-class="transition-transform duration-300 ease-apple-smooth"
                            tag="div"
                            class="space-y-1"
                        >
                            <div
                                v-for="entry in limitedLookups"
                                :key="entry.id"
                            >
                                <SearchHistoryItem
                                    :entry="entry"
                                    @lookup="lookupWord"
                                />
                            </div>
                        </TransitionGroup>
                    </div>
                </div>
            </div>
        </div>

        <!-- Expanded View -->
        <div v-else key="expanded" class="space-y-1">
            <!-- Expanded view - simple scrollable list -->
            <div v-if="recentLookups.length > 0" class="space-y-1">
                <TransitionGroup
                    enter-active-class="transition-smooth"
                    leave-active-class="transition-normal"
                    enter-from-class="opacity-0 -translate-x-4"
                    enter-to-class="opacity-100 translate-x-0"
                    leave-from-class="opacity-100 translate-x-0"
                    leave-to-class="opacity-0 translate-x-4"
                    move-class="transition-transform duration-300 ease-apple-smooth"
                    tag="div"
                    class="space-y-1"
                >
                    <div
                        v-for="entry in recentLookups"
                        :key="entry.id"
                        :class="
                            cn(
                                'group hover-lift flex cursor-pointer items-center justify-between rounded-lg px-2 py-2',
                                'hover:bg-accent hover:pl-3'
                            )
                        "
                        @click="lookupWord(entry.word)"
                    >
                        <div class="flex min-w-0 items-center gap-3">
                            <History
                                :size="14"
                                class="shrink-0 text-muted-foreground"
                            />
                            <span class="truncate text-sm">{{
                                entry.word
                            }}</span>
                        </div>
                        <span
                            class="text-xs text-muted-foreground opacity-0 transition-opacity duration-200 group-hover:opacity-100"
                        >
                            {{ formatDate(entry.timestamp) }}
                        </span>
                    </div>
                </TransitionGroup>
            </div>

            <div v-else class="py-4 text-center">
                <p class="text-xs text-muted-foreground">No recent lookups</p>
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { formatDate, cn } from '@/utils';
import { History } from 'lucide-vue-next';
import SearchHistoryItem from './SearchHistoryItem.vue';

interface Props {
    collapsed: boolean;
}

defineProps<Props>();

const { history } = useStores();
const searchBarStore = useSearchBarStore();
const router = useRouter();
const recentLookups = computed(() => history.recentLookups);

const limitedLookups = computed(() => {
    return recentLookups.value.slice(0, 20); // Limit to prevent performance issues
});

const lookupWord = (word: string) => {
    searchBarStore.setQuery(word);
    // Navigate — the route watcher in Home.vue handles the fetch
    const subMode = searchBarStore.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word } });
};
</script>

<style scoped>
/* Hide scrollbar by default */
.scrollbar-none::-webkit-scrollbar {
    width: 0;
    display: none;
}

/* Show thin scrollbar on hover */
.scrollbar-thin::-webkit-scrollbar {
    width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
    background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
    background: hsl(var(--muted));
    border-radius: 2px;
}

/* Vue transition classes use inline Tailwind classes in template */
</style>
