<template>
    <CardHeader class="relative">
        <CardTitle class="flex items-center">
            <!-- Container for invisible text and overlay -->
            <div class="relative">
                <!-- Invisible text to reserve space -->
                <span
                    class="invisible text-[clamp(1.5rem,10vw,4.5rem)] leading-tight font-bold"
                    style="font-family: 'Fraunces', serif"
                >
                    {{ word }}
                </span>

                <!-- Animated text overlay with extra space for cursor -->
                <div class="absolute top-0 left-0 w-[calc(100%+2ch)]">
                    <AnimatedTitle
                        :text="word"
                        animation-type="typewriter"
                        :animation-key="0"
                        class="block"
                    />
                </div>
            </div>

            <!-- Plus button flows after invisible text -->
            <HoverCard>
                <HoverCardTrigger as-child>
                    <button
                        @click="showAddToWordlistModal = true"
                        class="group ml-3 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-border/50 bg-muted/30 opacity-60 transition-all duration-200 hover:border-border hover:bg-muted hover:opacity-100"
                    >
                        <Plus
                            :size="14"
                            class="text-muted-foreground group-hover:text-foreground"
                        />
                    </button>
                </HoverCardTrigger>
                <HoverCardContent side="top" :sideOffset="4" class="w-48">
                    <div class="text-sm">
                        <p class="font-medium">Add to Wordlist</p>
                        <p class="mt-1 text-xs text-muted-foreground">
                            Save this word to your wordlists for study
                        </p>
                    </div>
                </HoverCardContent>
            </HoverCard>
        </CardTitle>

        <!-- Pronunciation -->
        <div
            v-if="pronunciation && hasPronunciation"
            class="flex items-center gap-3 pt-2"
        >
            <span
                class="text-lg text-muted-foreground"
                style="font-family: 'Fira Code', monospace"
            >
                {{ currentPronunciation }}
            </span>

            <button
                @click="$emit('toggle-pronunciation')"
                class="h-6 min-w-[60px] rounded-md border border-border/50 bg-muted/50 px-2 py-1 text-center text-xs text-foreground/80 transition-all duration-200 hover:border-border hover:bg-muted hover:text-foreground"
            >
                {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
            </button>

            <!-- Provider Source Icons -->
            <ProviderIcons :providers="providers" :word="word" />

            <!-- AI Synthesis Indicator -->
            <HoverCard v-if="isAISynthesized">
                <HoverCardTrigger as-child>
                    <div
                        class="relative inline-flex cursor-help items-center justify-center opacity-60"
                    >
                        <div class="relative">
                            <Sparkles
                                :size="16"
                                class="animate-pulse fill-amber-600 text-amber-600 drop-shadow-lg dark:fill-amber-400 dark:text-amber-400"
                            />
                            <Sparkles
                                :size="16"
                                class="animate-spin-slow absolute inset-0 fill-amber-300 text-amber-300 opacity-50 dark:fill-amber-600 dark:text-amber-600"
                            />
                        </div>
                    </div>
                </HoverCardTrigger>
                <HoverCardContent class="w-80" side="top" :sideOffset="4">
                    <div class="space-y-2">
                        <div class="flex items-center gap-2">
                            <Sparkles
                                :size="16"
                                class="text-amber-600 dark:text-amber-400"
                            />
                            <h4 class="font-semibold">AI Enhanced</h4>
                        </div>
                        <p class="text-sm opacity-90">
                            This content has been enhanced using AI to provide
                            clearer definitions, better examples, and improved
                            organization of meanings.
                        </p>
                    </div>
                </HoverCardContent>
            </HoverCard>
        </div>

        <!-- Add to Wordlist Modal -->
        <AddToWordlistModal
            v-model="showAddToWordlistModal"
            :word="word"
            @added="handleWordAdded"
        />
    </CardHeader>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { CardHeader, CardTitle } from '@/components/ui/card';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Sparkles, Plus } from 'lucide-vue-next';
import AnimatedTitle from './AnimatedTitle.vue';
import ProviderIcons from './ProviderIcons.vue';
import AddToWordlistModal from './AddToWordlistModal.vue';
import type { PronunciationMode } from '@/types';

interface WordHeaderProps {
    word: string;
    pronunciation?: {
        phonetic: string;
        ipa: string;
    };
    pronunciationMode: PronunciationMode;
    providers: string[];
    isAISynthesized?: boolean;
}

const props = defineProps<WordHeaderProps>();

defineEmits<{
    'toggle-pronunciation': [];
}>();

// Modal state
const showAddToWordlistModal = ref(false);

// Handle word added to wordlist
const handleWordAdded = (_wordlistName: string) => {
    showAddToWordlistModal.value = false;
};

// Check if we have valid pronunciation data
const hasPronunciation = computed(() => {
    if (!props.pronunciation) return false;
    const phoneticValid =
        props.pronunciation.phonetic &&
        props.pronunciation.phonetic !== 'unknown';
    const ipaValid =
        props.pronunciation.ipa && props.pronunciation.ipa !== 'unknown';
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
