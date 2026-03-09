<template>
    <CardHeader class="relative">
        <CardTitle class="flex items-center">
            <!-- Container for invisible text and overlay -->
            <div class="relative">
                <!-- Invisible text to reserve space -->
                <span
                    class="invisible text-[clamp(1.5rem,10vw,4.5rem)] leading-tight font-bold font-serif"
                >
                    {{ word }}
                </span>

                <!-- Animated text overlay with extra space for cursor -->
                <div class="absolute top-0 left-0 whitespace-nowrap">
                    <AnimatedTitle
                        :text="word"
                        class="inline"
                    />
                </div>
            </div>

            <!-- Plus button flows after invisible text -->
            <HoverCard>
                <HoverCardTrigger as-child>
                    <button
                        @click="showAddToWordlistModal = true"
                        class="group ml-5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-border/50 bg-muted/30 opacity-60 transition-all duration-200 hover:border-border hover:bg-muted hover:opacity-100"
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

        <!-- Pronunciation & Audio Row -->
        <div class="flex items-center gap-3 pt-2">
            <!-- Language badges, inline — stacked when multiple -->
            <template v-if="languages?.length">
                <!-- Single language: simple badge -->
                <span
                    v-if="languages.length === 1"
                    class="inline-flex items-center rounded-md bg-muted/60 px-2 py-0.5 text-xs font-medium text-muted-foreground"
                >
                    {{ languages[0] }}
                </span>
                <!-- Multiple languages: overlapping pill stack -->
                <Popover v-else>
                    <PopoverTrigger as-child>
                        <button class="flex items-center cursor-pointer">
                            <span
                                v-for="(lang, i) in languages.slice(0, 3)"
                                :key="lang"
                                :class="[
                                    'inline-flex items-center rounded-md bg-muted/70 border border-background px-2 py-0.5 text-xs font-medium text-muted-foreground shadow-sm',
                                    i > 0 ? '-ml-3' : '',
                                ]"
                                :style="{ zIndex: languages.length - i }"
                            >
                                {{ lang }}
                            </span>
                            <span
                                v-if="languages.length > 3"
                                class="-ml-2 inline-flex items-center rounded-md bg-muted/50 border border-background px-1.5 py-0.5 text-xs text-muted-foreground/60"
                            >
                                +{{ languages.length - 3 }}
                            </span>
                        </button>
                    </PopoverTrigger>
                    <PopoverContent
                        side="bottom"
                        align="start"
                        :side-offset="6"
                        class="w-auto min-w-32 rounded-lg border border-border/30 bg-background/80 p-2 shadow-xl backdrop-blur-xl"
                    >
                        <div
                            v-for="lang in languages"
                            :key="lang"
                            class="rounded-md px-3 py-1.5 text-sm text-foreground"
                        >
                            {{ lang }}
                        </div>
                    </PopoverContent>
                </Popover>
            </template>

            <!-- Pronunciation text with clickable mode label -->
            <template v-if="pronunciation && hasPronunciation">
                <span class="text-lg text-muted-foreground font-mono">
                    {{ currentPronunciation }}
                </span>
                <!-- Clickable mode label (toggles) or static label -->
                <button
                    v-if="hasMultiplePronunciations"
                    @click="$emit('toggle-pronunciation')"
                    class="cursor-pointer text-xs text-muted-foreground/60 underline-offset-2 transition-colors duration-150 hover:text-muted-foreground hover:underline"
                    :title="`Switch to ${pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic'}`"
                >
                    {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? 'IPA' : 'Phonetic' }}
                </button>
                <span v-else class="text-xs text-muted-foreground/60">
                    {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? 'IPA' : 'Phonetic' }}
                </span>
            </template>

            <!-- Audio Playback Button — always visible -->
            <AudioPlaybackButton
                :state="audioState"
                :error-message="audioError"
                @play="playAudio"
            />

            <!-- Vertical divider between pronunciation area and provider icons -->
            <div
                v-if="(providers.length > 0 || isAISynthesized) && hasPronunciation"
                class="mx-1.5 h-7 w-[2px] bg-border/70"
            />

            <!-- Provider Source Icons (clickable source switcher) -->
            <ProviderIcons
                :providers="providers"
                :active-source="activeSource"
                :show-synthesis="isAISynthesized"
                :interactive="!sourceSelectionDisabled"
                :source-entries="sourceEntries"
                @select-source="$emit('select-source', $event)"
            />
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
import { computed, ref, toRef } from 'vue';
import { CardHeader, CardTitle } from '@/components/ui/card';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { Plus } from 'lucide-vue-next';
import AnimatedTitle from './AnimatedTitle.vue';
import AudioPlaybackButton from './AudioPlaybackButton.vue';
import ProviderIcons from './ProviderIcons.vue';
import AddToWordlistModal from './AddToWordlistModal.vue';
import { useAudioPlayback } from '../composables/useAudioPlayback';
import type { PronunciationMode } from '@/types';
import type { AudioFile, SourceReference } from '@/types/api';

interface WordHeaderProps {
    word: string;
    languages: string[];
    pronunciation?: {
        phonetic: string;
        ipa: string;
        audio_files?: AudioFile[];
    };
    pronunciationMode: PronunciationMode;
    providers: string[];
    isAISynthesized?: boolean;
    activeSource?: string;
    sourceSelectionDisabled?: boolean;
    sourceEntries?: SourceReference[];
}

const props = defineProps<WordHeaderProps>();

defineEmits<{
    'toggle-pronunciation': [];
    'select-source': [source: string];
}>();

// Modal state
const showAddToWordlistModal = ref(false);

// Handle word added to wordlist
const handleWordAdded = (_wordlistName: string) => {
    showAddToWordlistModal.value = false;
};

// Audio playback
const wordRef = toRef(props, 'word');
const audioFilesRef = computed(() => props.pronunciation?.audio_files);
const languageRef = toRef(() => props.languages[0]);
const { state: audioState, errorMessage: audioError, play: playAudio } = useAudioPlayback(wordRef, audioFilesRef, languageRef);

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

// Only show toggle when both formats exist and differ
const hasMultiplePronunciations = computed(() => {
    if (!props.pronunciation) return false;
    const pValid = props.pronunciation.phonetic && props.pronunciation.phonetic !== 'unknown';
    const iValid = props.pronunciation.ipa && props.pronunciation.ipa !== 'unknown';
    return pValid && iValid;
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
