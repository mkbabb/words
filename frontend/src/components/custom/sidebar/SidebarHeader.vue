<template>
    <div class="border-border border-b p-4 flex items-center min-h-[4rem]">
        <div v-if="!collapsed" class="flex items-center justify-between w-full">
            <!-- Left: Floridify + @mbabb -->
            <div class="flex items-center gap-3">
                <FloridifyIcon :expanded="true" :mode="store.mode" clickable @toggle-mode="store.toggleMode()" />
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
                                <p class="text-muted-foreground text-sm">
                                    AI-enhanced dictionary system
                                </p>
                            </div>
                        </div>
                    </HoverCardContent>
                </HoverCard>
            </div>
            <!-- Right: Dark Mode + Hamburger -->
            <div class="flex items-center gap-3">
                <DarkModeToggle class="h-7 w-7 transition-all duration-500 ease-apple-smooth" />
                <HamburgerIcon
                    :is-open="mobile || !collapsed"
                    :class="cn(
                        'transition-all duration-300 ease-apple-smooth',
                        mobile ? 'cursor-pointer' : 'cursor-ew-resize'
                    )"
                    @toggle="mobile ? store.toggleSidebar() : store.setSidebarCollapsed(!collapsed)"
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
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores';
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

const store = useAppStore();
</script>