<template>
    <div class="border-border border-b p-4 flex items-center min-h-[4rem] overflow-hidden">
        <Transition
            mode="out-in"
            enter-active-class="transition-opacity duration-200 ease-apple-smooth"
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            leave-active-class="transition-opacity duration-150 ease-apple-smooth"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
        >
            <div v-if="!collapsed" key="expanded" class="flex items-center justify-between w-full">
                <!-- Left: Floridify + @mbabb -->
                <div class="flex items-center gap-3">
                    <FloridifyIcon :expanded="true" :mode="searchBarStore.getSubMode('lookup') as any" clickable @toggle-mode="() => searchBarStore.setSubMode('lookup', searchBarStore.getSubMode('lookup') === 'dictionary' ? 'thesaurus' : 'dictionary')" />
                    <HoverCard :open-delay="600">
                        <HoverCardTrigger>
                            <Button variant="link" class="h-auto p-0 font-mono text-sm">@mbabb</Button>
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
                                    <p class="text-muted-foreground text-sm italic">
                                        Floridify your words, effloresce your communication and life thereof
                                    </p>
                                    <hr class="my-2 border-border/50" />
                                    <a href="https://github.com/mkbabb/words" class="text-sm text-primary hover:underline block mt-2">
                                        View the project on GitHub
                                    </a>
                                </div>
                            </div>
                        </HoverCardContent>
                    </HoverCard>
                </div>
                <!-- Right: Dark Mode + Hamburger -->
                <div class="flex items-center gap-3">
                    <DarkModeToggle class="h-7 w-7" />
                    <HamburgerIcon
                        :is-open="mobile ? ui.sidebarOpen : !collapsed"
                        :class="cn(
                            'transition-all duration-300 ease-apple-smooth',
                            mobile ? 'cursor-pointer' : 'cursor-ew-resize'
                        )"
                        @toggle="mobile ? ui.toggleSidebar() : ui.setSidebarCollapsed(!collapsed)"
                    />
                </div>
            </div>
            <div v-else key="collapsed" class="flex items-center justify-between w-full">
                <DarkModeToggle class="h-7 w-7" />
                <button
                    @click="ui.setSidebarCollapsed(false)"
                    class="cursor-ew-resize hover:bg-muted/50 rounded-lg p-2 transition-all duration-300 ease-apple-smooth hover:scale-105"
                >
                    <PanelRight :size="16" class="text-muted-foreground" />
                </button>
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { cn } from '@/utils';
import { FloridifyIcon, HamburgerIcon } from '@/components/custom/icons';
import { DarkModeToggle } from '@/components/custom/dark-mode-toggle';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';
import { Avatar, AvatarImage, Button } from '@/components/ui';
import { PanelRight } from 'lucide-vue-next';

interface Props {
    collapsed: boolean;
    mobile?: boolean;
}

defineProps<Props>();

const { ui } = useStores();
const searchBarStore = useSearchBarStore();
</script>