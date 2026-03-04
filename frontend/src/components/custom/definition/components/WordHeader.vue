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

        <!-- Pronunciation & Audio Row -->
        <div class="flex items-center gap-3 pt-2">
            <!-- Pronunciation text (only when available) -->
            <template v-if="pronunciation && hasPronunciation">
                <span class="text-lg text-muted-foreground font-mono">
                    {{ currentPronunciation }}
                </span>
                <span v-if="!hasMultiplePronunciations" class="text-xs text-muted-foreground/60">
                    {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? '(IPA)' : '(Phonetic)' }}
                </span>
            </template>

            <!-- Audio Playback Button — always visible -->
            <AudioPlaybackButton
                :state="audioState"
                :error-message="audioError"
                @play="playAudio"
            />

            <button
                v-if="hasMultiplePronunciations"
                @click="$emit('toggle-pronunciation')"
                class="h-6 min-w-[60px] rounded-md border border-border/50 bg-muted/50 px-2 py-1 text-center text-xs text-foreground/80 transition-all duration-200 hover:border-border hover:bg-muted hover:text-foreground"
            >
                {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
            </button>

            <!-- Provider Source Icons (clickable source switcher) -->
            <ProviderIcons
                :providers="providers"
                :active-source="activeSource"
                :show-synthesis="isAISynthesized"
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
import { Plus } from 'lucide-vue-next';
import AnimatedTitle from './AnimatedTitle.vue';
import AudioPlaybackButton from './AudioPlaybackButton.vue';
import ProviderIcons from './ProviderIcons.vue';
import AddToWordlistModal from './AddToWordlistModal.vue';
import { useAudioPlayback } from '../composables/useAudioPlayback';
import type { PronunciationMode } from '@/types';
import type { AudioFile } from '@/types/api';

interface WordHeaderProps {
    word: string;
    language?: string;
    pronunciation?: {
        phonetic: string;
        ipa: string;
        audio_files?: AudioFile[];
    };
    pronunciationMode: PronunciationMode;
    providers: string[];
    isAISynthesized?: boolean;
    activeSource?: string;
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
const languageRef = toRef(() => props.language ?? 'en');
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

