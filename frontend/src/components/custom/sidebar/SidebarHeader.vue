<template>
    <div class="border-border border-b px-3 py-2.5 flex items-center min-h-[3.25rem] overflow-hidden">
            <div
                v-if="!collapsed"
                key="expanded"
                class="flex w-full items-center gap-2 transition-[opacity,transform] duration-350 ease-apple-spring transform-gpu"
            >
                <!-- Floridify icon -->
                <FloridifyIcon :expanded="true" :mode="searchBarStore.getSubMode('lookup') as any" :clickable="canToggleMode" :show-subscript="canToggleMode" @toggle-mode="() => searchBarStore.setSubMode('lookup', searchBarStore.getSubMode('lookup') === 'dictionary' ? 'thesaurus' : 'dictionary')" />

                <!-- Vertical divider -->
                <div class="h-6 w-px bg-border/40 flex-shrink-0" />

                <!-- @mbabb + Dark Mode grouped -->
                <Popover>
                    <PopoverTrigger as-child>
                        <Button variant="link" class="h-auto p-0 font-mono text-sm">@mbabb</Button>
                    </PopoverTrigger>
                    <PopoverContent class="w-72">
                        <div class="flex gap-4">
                            <Avatar>
                                <AvatarImage src="https://avatars.githubusercontent.com/u/2848617?v=4" />
                            </Avatar>
                            <div>
                                <h4 class="text-sm font-medium hover:underline">
                                    <a href="https://github.com/mkbabb" class="font-mono">@mbabb</a>
                                </h4>
                                <p class="text-muted-foreground text-sm italic">
                                    Floridify your words, effloresce your communication and life thereof
                                </p>
                                <hr class="my-2 border-border/50" />
                                <a href="https://github.com/mkbabb/words" class="text-sm text-primary hover:underline block mt-2">
                                    View the project on GitHub
                                </a>
                            </div>
                        </div>
                    </PopoverContent>
                </Popover>

                <DarkModeToggle class="h-9 w-9 flex-shrink-0" />

                <!-- Spacer -->
                <div class="flex-1" />

                <!-- Vertical divider -->
                <div class="h-6 w-px bg-border/40 flex-shrink-0" />

                <!-- Hamburger / collapse -->
                <HamburgerIcon
                    :is-open="mobile ? ui.sidebarOpen : !collapsed"
                    :class="cn(
                        'transform-gpu transition-[transform,opacity] duration-250 ease-apple-smooth flex-shrink-0',
                        mobile ? 'cursor-pointer' : 'cursor-ew-resize'
                    )"
                    @toggle="mobile ? ui.toggleSidebar() : ui.setSidebarCollapsed(!collapsed)"
                />
            </div>
            <div
                v-else
                key="collapsed"
                class="flex w-full flex-col items-center gap-3 py-3 transition-[opacity,transform] duration-350 ease-apple-spring transform-gpu"
            >
                <DarkModeToggle class="h-9 w-9 flex-shrink-0" />
                <button
                    @click="ui.setSidebarCollapsed(false)"
                    class="focus-ring cursor-ew-resize rounded-xl border border-border/50 bg-background/95 p-2 transition-[background-color,border-color,box-shadow,transform] duration-250 ease-apple-spring hover:-translate-y-0.5 hover:bg-background hover:border-border/70 hover:shadow-md"
                >
                    <PanelRight :size="16" class="text-muted-foreground" />
                </button>
            </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { cn } from '@/utils';
import { FloridifyIcon, HamburgerIcon } from '@/components/custom/icons';
import { DarkModeToggle } from '@/components/custom/dark-mode-toggle';
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover';
import { Avatar, AvatarImage, Button } from '@/components/ui';
import { PanelRight } from 'lucide-vue-next';

interface Props {
    collapsed: boolean;
    mobile?: boolean;
}

defineProps<Props>();

const { ui, searchBar, content } = useStores();
const searchBarStore = useSearchBarStore();

const canToggleMode = computed(() => {
    if (searchBar.searchMode === 'wordlist') return false;
    const hasWordQuery = !!content.currentEntry;
    const hasSuggestionQuery = !!content.wordSuggestions;
    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;

    // Only allow thesaurus toggle if a dedicated thesaurus response exists
    if (!content.currentThesaurus) return false;

    return true;
});
</script>
