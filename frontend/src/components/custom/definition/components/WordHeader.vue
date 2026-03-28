<template>
    <CardHeader class="relative">
        <!-- Word + controls: all on one line, wrapping only when needed -->
        <CardTitle>
            <div class="flex flex-wrap items-center gap-x-2 gap-y-2" style="overflow-wrap: anywhere;" lang="en">
                <!-- Word title — inline, takes natural width -->
                <AnimatedTitle
                    :text="word"
                    class="inline"
                />

                <!-- Audio + Add buttons -->
                <AudioPlaybackButton
                    :state="audioState"
                    :error-message="audioError"
                    class="flex-shrink-0"
                    size="md"
                    @play="playAudio"
                />
                <HoverCard>
                    <HoverCardTrigger as-child>
                        <button
                            @click="showAddToWordlistModal = true"
                            class="group flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-border/40 bg-background/96 shadow-sm opacity-80 transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-250 ease-apple-spring hover:-translate-y-0.5 hover:border-border/60 hover:bg-background hover:opacity-100 hover:shadow-md"
                        >
                            <Plus
                                :size="16"
                                class="text-muted-foreground group-hover:text-foreground"
                            />
                        </button>
                    </HoverCardTrigger>
                    <HoverCardContent side="top" :sideOffset="4" class="w-48">
                        <div class="text-small">
                            <p class="font-medium">Add to Wordlist</p>
                            <p class="mt-1 text-caption">
                                Save this word to your wordlists for study
                            </p>
                        </div>
                    </HoverCardContent>
                </HoverCard>

                <!-- Spacer pushes providers right -->
                <div class="flex-1" />

                <!-- Provider Icons — right-justified, same row -->
                <ProviderIcons
                    v-if="providers && (providers.length > 0 || showSynthesis)"
                    :providers="providers"
                    :active-source="activeSource"
                    :show-synthesis="showSynthesis"
                    :interactive="interactive"
                    :source-entries="sourceEntries"
                    :word="word"
                    layout="horizontal"
                    class="flex-shrink-0"
                    @select-source="$emit('select-source', $event)"
                />
            </div>
        </CardTitle>

        <!-- Row 2: Language badges + Pronunciation pill -->
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1 pt-2">
            <!-- Language badges — h-10 w-10, big and beautiful -->
            <template v-if="languages?.length">
                <!-- Single language: tooltip only -->
                <Tooltip v-if="languages.length === 1">
                    <TooltipTrigger as-child>
                        <span
                            :class="[
                                'flex h-10 w-10 items-center justify-center rounded-full border-2 border-background bg-background/96 font-semibold uppercase text-muted-foreground shadow-sm transform-gpu transition-[background-color,color,transform,box-shadow,opacity] duration-250 ease-apple-spring',
                                languages[0].length > 2 ? 'text-[10px]' : 'text-xs',
                            ]"
                        >
                            {{ languages[0] }}
                        </span>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" :side-offset="6">
                        {{ getLanguageDisplayName(languages[0]) }}
                    </TooltipContent>
                </Tooltip>
                <!-- Multiple languages: stacked badges, click stack opens dropdown -->
                <Popover v-else>
                    <PopoverTrigger as-child>
                        <button class="group/lang flex items-center cursor-pointer">
                            <span
                                v-for="(lang, i) in orderedLanguages.slice(0, 2)"
                                :key="lang"
                                :class="[
                                    'flex h-10 w-10 items-center justify-center rounded-full border-2 border-background bg-background/96 font-semibold uppercase shadow-sm transform-gpu transition-[background-color,color,transform,box-shadow,opacity] duration-250 ease-apple-spring',
                                    lang.length > 2 ? 'text-[10px]' : 'text-xs',
                                    i > 0 ? '-ml-2 group-hover/lang:translate-x-2 group-hover/lang:scale-105' : '',
                                    lang === audioLanguage ? 'ring-2 ring-primary/30 bg-primary/10' : '',
                                ]"
                                :style="{ zIndex: orderedLanguages.length - i }"
                            >
                                <span :class="lang === audioLanguage ? 'text-primary' : 'text-muted-foreground'">
                                    {{ lang }}
                                </span>
                            </span>
                            <!-- Overflow count for 3+ languages -->
                            <span
                                v-if="orderedLanguages.length > 2"
                                :class="[
                                    'flex h-10 w-10 items-center justify-center rounded-full border-2 border-background bg-background/96 text-xs font-semibold text-muted-foreground/60 shadow-sm transform-gpu transition-[background-color,color,transform,box-shadow] duration-250 ease-apple-spring hover:bg-background hover:text-muted-foreground hover:shadow-md',
                                    '-ml-2 group-hover/lang:translate-x-2 group-hover/lang:scale-105',
                                ]"
                            >
                                +{{ orderedLanguages.length - 2 }}
                            </span>
                        </button>
                    </PopoverTrigger>
                    <InlinePopoverContent
                        side="bottom"
                        align="start"
                        :side-offset="12"
                        class="z-popover w-44 rounded-xl border border-border/40 bg-background/96 p-1.5 shadow-cartoon-lg backdrop-blur-xl"
                    >
                        <div
                            v-for="lang in languages"
                            :key="lang"
                            :class="[
                                'flex items-center gap-3 rounded-lg px-2.5 py-2 cursor-pointer transition-[background-color,color,box-shadow,transform] duration-200 ease-apple-smooth',
                                lang === audioLanguage
                                    ? 'bg-primary/10 font-medium text-foreground hover:bg-primary/15 hover:shadow-sm'
                                    : 'bg-background/96 text-foreground/80 hover:bg-background hover:text-foreground hover:shadow-sm',
                            ]"
                            @click="selectAudioLanguage(lang)"
                        >
                            <span
                                :class="[
                                    'flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold uppercase shadow-sm',
                                    lang === audioLanguage
                                        ? 'bg-primary/15 text-primary'
                                        : 'bg-background/95 text-muted-foreground',
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

            <!-- Pronunciation trigger as pill badge — text truncates with ellipsis -->
            <template v-if="pronunciation && hasPronunciation">
                <Popover>
                    <PopoverTrigger as-child>
                        <button
                        class="group/pron flex items-center gap-1.5 rounded-full border border-border/40 bg-background/96 px-2.5 py-1 text-xs font-medium text-muted-foreground shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-smooth hover:-translate-y-0.5 hover:bg-background hover:text-foreground hover:border-border/60 hover:shadow-md cursor-pointer min-w-0"
                        >
                            <span class="font-mono text-sm max-w-[120px] sm:max-w-[200px] truncate">{{ displayPronunciation }}</span>
                            <span
                                v-if="allPronunciationVariants.length > 1"
                                class="text-micro font-sans text-muted-foreground/50 group-hover/pron:text-muted-foreground flex-shrink-0"
                            >+{{ allPronunciationVariants.length - 1 }}</span>
                            <span class="rounded bg-background/95 px-1 py-0.5 text-micro font-sans font-medium text-muted-foreground/60 flex-shrink-0 shadow-sm">
                                {{ pronunciationMode === 'ipa' || (!pronunciation?.phonetic || pronunciation?.phonetic === 'unknown') ? 'IPA' : 'Ph.' }}
                            </span>
                        </button>
                    </PopoverTrigger>
                    <PopoverContent
                        side="bottom"
                        align="start"
                        :side-offset="8"
                        class="w-72 max-h-60 overflow-y-auto scrollbar-thin rounded-xl p-2"
                    >
                        <!-- IPA section -->
                        <div v-if="pronunciation.ipa && pronunciation.ipa !== 'unknown'" class="mb-1">
                            <div class="flex items-center gap-2 px-2 py-1">
                                <span class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">IPA</span>
                                <button
                                    v-if="pronunciationMode !== 'ipa'"
                                    @click="$emit('toggle-pronunciation')"
                                    class="text-[10px] text-primary/70 hover:text-primary font-medium cursor-pointer"
                                >use</button>
                            </div>
                            <div
                                v-for="(variant, vi) in splitVariants(pronunciation.ipa)"
                                :key="'ipa-' + vi"
                                :class="[
                                    'flex items-center gap-2 rounded-lg px-2.5 py-2 font-mono text-sm transition-[background-color,color,box-shadow] duration-200 ease-apple-smooth',
                                    pronunciationMode === 'ipa' ? 'bg-primary/5 text-foreground shadow-sm' : 'bg-background/96 text-foreground/70',
                                ]"
                            >
                                <span class="flex-1">{{ variant }}</span>
                            </div>
                        </div>
                        <!-- Phonetic section -->
                        <div v-if="pronunciation.phonetic && pronunciation.phonetic !== 'unknown'">
                            <div class="flex items-center gap-2 px-2 py-1" :class="pronunciation.ipa && pronunciation.ipa !== 'unknown' ? 'border-t border-border/30 mt-1 pt-2' : ''">
                                <span class="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">Phonetic</span>
                                <button
                                    v-if="pronunciationMode !== 'phonetic'"
                                    @click="$emit('toggle-pronunciation')"
                                    class="text-[10px] text-primary/70 hover:text-primary font-medium cursor-pointer"
                                >use</button>
                            </div>
                            <div
                                v-for="(variant, vi) in splitVariants(pronunciation.phonetic)"
                                :key="'ph-' + vi"
                                :class="[
                                    'flex items-center gap-2 rounded-lg px-2.5 py-2 font-mono text-sm transition-[background-color,color,box-shadow] duration-200 ease-apple-smooth',
                                    pronunciationMode === 'phonetic' ? 'bg-primary/5 text-foreground shadow-sm' : 'bg-background/96 text-foreground/70',
                                ]"
                            >
                                <span class="flex-1">{{ variant }}</span>
                            </div>
                        </div>
                    </PopoverContent>
                </Popover>
            </template>

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
import { CardHeader, CardTitle, HoverCard, HoverCardContent, HoverCardTrigger, Popover, PopoverTrigger, PopoverContent, Tooltip, TooltipTrigger, TooltipContent } from '@mkbabb/glass-ui';
import {
    PopoverContent as InlinePopoverContent,
} from 'reka-ui';
import { Plus } from 'lucide-vue-next';
import AnimatedTitle from './AnimatedTitle.vue';
import AudioPlaybackButton from './media/AudioPlaybackButton.vue';
import AddToWordlistModal from './AddToWordlistModal.vue';
import ProviderIcons from './metadata/ProviderIcons.vue';
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
    // Provider props (optional — omit to hide provider icons)
    providers?: string[];
    activeSource?: string;
    showSynthesis?: boolean;
    interactive?: boolean;
    sourceEntries?: SourceReference[];
}

const props = withDefaults(defineProps<WordHeaderProps>(), {
    providers: () => [],
    activeSource: 'synthesis',
    showSynthesis: false,
    interactive: true,
    sourceEntries: () => [],
});

const emit = defineEmits<{
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

// Stable language order — never reorder on selection to avoid DOM shuffling/flash
const orderedLanguages = computed(() => {
    return props.languages ?? [];
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

// Split comma-separated pronunciation variants into an array
function splitVariants(text: string): string[] {
    return text.split(',').map(v => v.trim()).filter(Boolean);
}

// All pronunciation variants across both IPA and phonetic
const allPronunciationVariants = computed(() => {
    if (!props.pronunciation) return [];
    const variants: string[] = [];
    if (props.pronunciation.ipa && props.pronunciation.ipa !== 'unknown') {
        variants.push(...splitVariants(props.pronunciation.ipa));
    }
    if (props.pronunciation.phonetic && props.pronunciation.phonetic !== 'unknown') {
        variants.push(...splitVariants(props.pronunciation.phonetic));
    }
    return variants;
});

// Display pronunciation — show first variant only if multiple comma-separated
const displayPronunciation = computed(() => {
    const full = currentPronunciation.value;
    if (!full) return '';
    // If contains comma (multiple variants), show just the first
    if (full.includes(',')) {
        return full.split(',')[0].trim();
    }
    return full;
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
