<template>
    <CardHeader class="relative pr-36 sm:pr-44 md:pr-52">
        <div class="flex items-center justify-between">
            <CardTitle>
                <AnimatedTitle
                    :text="word"
                    :animation-type="animationType"
                    :animation-key="animationKey"
                />
            </CardTitle>
        </div>

        <!-- Pronunciation -->
        <div
            v-if="pronunciation && hasPronunciation"
            class="flex items-center gap-3 pt-2"
        >
            <span class="text-lg text-muted-foreground" style="font-family: 'Fira Code', monospace;">
                {{ currentPronunciation }}
            </span>
            
            <button
                @click="$emit('toggle-pronunciation')"
                class="h-6 px-2 py-1 text-xs transition-all duration-200 rounded-md bg-muted/50 hover:bg-muted border border-border/50 hover:border-border text-foreground/80 hover:text-foreground min-w-[60px] text-center"
            >
                {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
            </button>
            
            <!-- Provider Source Icons -->
            <ProviderIcons
                :providers="providers"
                :word="word"
            />
            
            <!-- AI Synthesis Indicator -->
            <HoverCard v-if="isAISynthesized">
                <HoverCardTrigger as-child>
                    <div class="relative inline-flex items-center justify-center cursor-help opacity-60">
                        <div class="relative">
                            <Sparkles 
                                :size="16" 
                                class="text-amber-600 dark:text-amber-400 animate-pulse drop-shadow-lg fill-amber-600 dark:fill-amber-400"
                            />
                            <Sparkles 
                                :size="16" 
                                class="absolute inset-0 text-amber-300 dark:text-amber-600 opacity-50 animate-spin-slow fill-amber-300 dark:fill-amber-600"
                            />
                        </div>
                    </div>
                </HoverCardTrigger>
                <HoverCardContent class="w-80" side="top" :sideOffset="4">
                    <div class="space-y-2">
                        <div class="flex items-center gap-2">
                            <Sparkles :size="16" class="text-amber-600 dark:text-amber-400" />
                            <h4 class="font-semibold">AI Enhanced</h4>
                        </div>
                        <p class="text-sm opacity-90">
                            This content has been enhanced using AI to provide clearer definitions, 
                            better examples, and improved organization of meanings.
                        </p>
                    </div>
                </HoverCardContent>
            </HoverCard>
        </div>
    </CardHeader>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CardHeader, CardTitle } from '@/components/ui/card';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Sparkles } from 'lucide-vue-next';
import AnimatedTitle from './AnimatedTitle.vue';
import ProviderIcons from './ProviderIcons.vue';

interface WordHeaderProps {
    word: string;
    pronunciation?: {
        phonetic: string;
        ipa: string;
    };
    pronunciationMode: 'phonetic' | 'ipa';
    providers: string[];
    animationType: string;
    animationKey: number;
    isAISynthesized?: boolean;
}

const props = defineProps<WordHeaderProps>();

defineEmits<{
    'toggle-pronunciation': [];
}>();

// Check if we have valid pronunciation data
const hasPronunciation = computed(() => {
    if (!props.pronunciation) return false;
    const phoneticValid = props.pronunciation.phonetic && props.pronunciation.phonetic !== 'unknown';
    const ipaValid = props.pronunciation.ipa && props.pronunciation.ipa !== 'unknown';
    return phoneticValid || ipaValid;
});

// Get the current pronunciation to display
const currentPronunciation = computed(() => {
    if (!props.pronunciation) return '';
    
    const phonetic = props.pronunciation.phonetic;
    const ipa = props.pronunciation.ipa;
    
    // Check what mode we're in
    if (props.pronunciationMode === 'phonetic') {
        // If phonetic is valid, use it; otherwise fall back to IPA
        if (phonetic && phonetic !== 'unknown') {
            return phonetic;
        } else if (ipa && ipa !== 'unknown') {
            return ipa;
        }
    } else {
        // If IPA is valid, use it; otherwise fall back to phonetic
        if (ipa && ipa !== 'unknown') {
            return ipa;
        } else if (phonetic && phonetic !== 'unknown') {
            return phonetic;
        }
    }
    
    return '';
});
</script>

<style scoped>
@keyframes spin-slow {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.animate-spin-slow {
    animation: spin-slow 3s linear infinite;
}
</style>

