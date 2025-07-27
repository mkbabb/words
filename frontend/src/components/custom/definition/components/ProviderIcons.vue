<template>
    <HoverCard v-if="providers.length > 0">
        <HoverCardTrigger as-child>
            <div 
                class="relative flex items-center ml-3 h-7 cursor-pointer"
                :style="{ width: `${Math.min(providers.length, 2) * 20 + (providers.length > 2 ? 8 : 0)}px` }"
            >
                <!-- First provider (always visible) -->
                <div 
                    class="absolute flex h-7 w-7 items-center justify-center rounded-full bg-background border border-border/50 shadow-sm"
                    :style="{ left: '0px', zIndex: 3 }"
                >
                    <component 
                        :is="getProviderIcon(providers[0])" 
                        :size="16" 
                        class="text-muted-foreground"
                    />
                </div>
                
                <!-- Second provider (if exists) -->
                <div 
                    v-if="providers.length > 1" 
                    class="absolute flex h-7 w-7 items-center justify-center rounded-full bg-background border border-border/50 shadow-sm"
                    :style="{ left: '12px', zIndex: 2 }"
                >
                    <component 
                        :is="getProviderIcon(providers[1])" 
                        :size="16" 
                        class="text-muted-foreground"
                    />
                </div>
                
                <!-- Plus indicator for additional providers -->
                <div 
                    v-if="providers.length > 2" 
                    class="absolute flex h-6 w-6 items-center justify-center rounded-full bg-muted border border-border shadow-sm"
                    :style="{ left: '24px', zIndex: 1 }"
                >
                    <span class="text-xs font-medium text-muted-foreground">+{{ providers.length - 2 }}</span>
                </div>
            </div>
        </HoverCardTrigger>
        <HoverCardContent class="w-auto max-w-xs p-2" side="top" align="center">
            <div class="space-y-1">
                <p class="text-xs font-medium text-muted-foreground mb-2">Dictionary Sources</p>
                <a
                    v-for="provider in providers"
                    :key="provider"
                    :href="getProviderSearchUrl(provider, word)"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                    <component 
                        :is="getProviderIcon(provider)" 
                        :size="14" 
                        class="flex-shrink-0"
                    />
                    <span class="text-xs">{{ getProviderDisplayName(provider) }}</span>
                </a>
            </div>
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { getProviderIcon, getProviderSearchUrl, getProviderDisplayName } from '../utils/providers';

interface ProviderIconsProps {
    providers: string[];
    word: string;
}

defineProps<ProviderIconsProps>();
</script>