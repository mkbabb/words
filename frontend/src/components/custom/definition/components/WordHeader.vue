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
            <!-- Language badges — overlapping stack with dropdown select (mirrors ProviderIcons) -->
            <template v-if="languages?.length">
                <!-- Single language: tooltip only -->
                <Tooltip v-if="languages.length === 1">
                    <TooltipTrigger as-child>
                        <span
                            class="flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 text-[10px] font-bold uppercase text-muted-foreground shadow-sm"
                        >
                            {{ languages[0] }}
                        </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" :side-offset="6">
                        Language: {{ languages[0] }}
                    </TooltipContent>
                </Tooltip>
                <!-- Multiple languages: overlapping stack → popover dropdown on click -->
                <Popover v-else>
                    <PopoverTrigger as-child>
                        <button class="group/lang flex items-center cursor-pointer focus:outline-none focus:ring-0">
                            <div
                                v-for="(lang, i) in orderedLanguages.slice(0, 3)"
                                :key="lang"
                                :class="[
                                    'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 text-[10px] font-bold uppercase shadow-sm transition-all duration-200 ease-apple-spring',
                                    i > 0 ? '-ml-2 group-hover/lang:ml-0.5' : '',
                                    lang === audioLanguage ? 'ring-2 ring-primary/30 bg-muted' : '',
                                ]"
                                :style="{ zIndex: orderedLanguages.length - i }"
                            >
                                <span :class="lang === audioLanguage ? 'text-primary' : 'text-muted-foreground'">
                                    {{ lang }}
                                </span>
                            </div>
                            <div
                                v-if="orderedLanguages.length > 3"
                                :class="[
                                    'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/50 text-[10px] font-medium text-muted-foreground/60 transition-all duration-200 ease-apple-spring',
                                    '-ml-2 group-hover/lang:ml-0.5',
                                ]"
                            >
                                +{{ orderedLanguages.length - 3 }}
                            </div>
                        </button>
                    </PopoverTrigger>
                    <InlinePopoverContent
                        side="bottom"
                        align="start"
                        :side-offset="20"
                        class="w-44 rounded-xl border border-border/30 bg-background/92 p-1.5 shadow-lg backdrop-blur-md"
                    >
                        <div
                            v-for="lang in languages"
                            :key="lang"
                            :class="[
                                'flex items-center gap-3 rounded-lg px-2.5 py-2 cursor-pointer transition-colors duration-150 hover:bg-muted/60',
                                lang === audioLanguage
                                    ? 'bg-primary/10 font-medium text-foreground'
                                    : 'text-foreground/80',
                            ]"
                            @click="selectAudioLanguage(lang)"
                        >
                            <span
                                :class="[
                                    'flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-bold uppercase',
                                    lang === audioLanguage
                                        ? 'bg-primary/15 text-primary'
                                        : 'bg-muted text-muted-foreground',
                                ]"
                            >{{ lang }}</span>
                            <span class="text-sm flex-1">{{ getLanguageDisplayName(lang) }}</span>
                            <div
                                v-if="lang === audioLanguage"
                                class="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0"
                            />
                        </div>
                    </InlinePopoverContent>
                </Popover>
            </template>

            <!-- Audio Playback Button -->
            <AudioPlaybackButton
                :state="audioState"
                :error-message="audioError"
                @play="playAudio"
            />

            <!-- Pronunciation text with toggle button -->
            <template v-if="pronunciation && hasPronunciation">
                <span class="text-lg text-muted-foreground font-mono">
                    {{ currentPronunciation }}
                </span>
                <!-- Toggle between Ph./IPA — only when both exist -->
                <Tooltip v-if="hasMultiplePronunciations">
                    <TooltipTrigger as-child>
                        <button
                            @click="$emit('toggle-pronunciation')"
                            class="cursor-pointer rounded-md bg-muted/40 px-1.5 py-0.5 text-xs font-semibold text-muted-foreground/70 transition-all duration-150 hover:bg-muted hover:text-muted-foreground active:scale-[0.95]"
                        >
                            {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? 'IPA' : 'Ph.' }}
                        </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" :side-offset="6">
                        Switch to {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
                    </TooltipContent>
                </Tooltip>
                <span v-else class="rounded-md bg-muted/40 px-1.5 py-0.5 text-xs font-semibold text-muted-foreground/60">
                    {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? 'IPA' : 'Ph.' }}
                </span>
            </template>

            <!-- Vertical divider between pronunciation area and provider icons -->
            <div
                v-if="(providers.length > 0 || isAISynthesized) && hasPronunciation"
                class="mx-1.5 h-5 w-px bg-border/50"
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
import { computed, ref, toRef, watch } from 'vue';
import { CardHeader, CardTitle } from '@/components/ui/card';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import {
    Popover,
    PopoverTrigger,
} from '@/components/ui/popover';
import {
    PopoverContent as InlinePopoverContent,
} from 'reka-ui';
import {
    Tooltip,
    TooltipTrigger,
    TooltipContent,
} from '@/components/ui/tooltip';
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

// Audio playback with language selection
const wordRef = toRef(props, 'word');
const audioFilesRef = computed(() => props.pronunciation?.audio_files);
const audioLanguage = ref(props.languages[0] ?? 'en');
const { state: audioState, errorMessage: audioError, play: playAudio } = useAudioPlayback(wordRef, audioFilesRef, audioLanguage);

function selectAudioLanguage(lang: string) {
    audioLanguage.value = lang;
}

// Reorder languages so the selected one is always first in the stack
const orderedLanguages = computed(() => {
    const langs = props.languages;
    if (!langs || langs.length <= 1) return langs;
    const selected = audioLanguage.value;
    if (langs[0] === selected) return langs;
    return [selected, ...langs.filter(l => l !== selected)];
});

const LANGUAGE_NAMES: Record<string, string> = {
    en: 'English',
    fr: 'French',
    es: 'Spanish',
    de: 'German',
    it: 'Italian',
    ja: 'Japanese',
    zh: 'Mandarin',
    hi: 'Hindi',
    pt: 'Portuguese',
    la: 'Latin',
    grc: 'Greek',
};

function getLanguageDisplayName(code: string): string {
    return LANGUAGE_NAMES[code] ?? code.toUpperCase();
}

// Reset audio language when word changes (new entry might have different languages)
watch(() => props.languages, (newLangs) => {
    if (newLangs?.length && !newLangs.includes(audioLanguage.value)) {
        audioLanguage.value = newLangs[0];
    }
});

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
