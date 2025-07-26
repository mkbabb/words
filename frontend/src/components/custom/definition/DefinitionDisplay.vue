<template>
    <div v-if="entry" class="relative flex gap-4">
        <!-- Progressive Sidebar - Truly sticky -->
        <div
            v-if="shouldShowSidebar && groupedDefinitions.length > 1"
            class="hidden w-48 flex-shrink-0 xl:block"
        >
            <div class="sticky top-4 z-60">
                <ProgressiveSidebar />
            </div>
        </div>

        <!-- Main Card Content -->
        <ThemedCard :variant="selectedCardVariant" class="relative flex-1">
            <!-- Animation Selector Dropdown - absolute positioned -->
            <div v-if="isMounted" class="absolute top-2 right-20 z-40">
                <div class="relative">
                    <button
                        @click="toggleAnimationDropdown"
                        class="group mt-1 rounded-lg border-2 border-border
                            bg-background/80 p-1.5 shadow-lg backdrop-blur-sm
                            transition-all duration-200 hover:scale-110
                            hover:bg-background focus:ring-0 focus:outline-none"
                    >
                        <ChevronLeft
                            :size="14"
                            :class="[
                                'text-muted-foreground transition-transform duration-200 group-hover:text-foreground',
                                showAnimationDropdown && 'rotate-90',
                            ]"
                        />
                    </button>

                    <Transition
                        enter-active-class="transition-all duration-300 ease-apple-bounce"
                        leave-active-class="transition-all duration-250 ease-out"
                        enter-from-class="opacity-0 scale-95 -translate-y-2"
                        enter-to-class="opacity-100 scale-100 translate-y-0"
                        leave-from-class="opacity-100 scale-100 translate-y-0"
                        leave-to-class="opacity-0 scale-95 -translate-y-2"
                    >
                        <div
                            v-if="showAnimationDropdown"
                            class="absolute top-full right-0 z-50 mt-4
                                min-w-[140px] origin-top-right rounded-md border
                                bg-popover text-popover-foreground shadow-md"
                            @click.stop
                        >
                            <div class="p-1">
                                <div class="px-2 py-1.5 text-sm font-semibold">
                                    Text Animation
                                </div>
                                <div class="my-1 h-px bg-border"></div>

                                <button
                                    v-for="option in animationOptions"
                                    :key="option.value"
                                    @click="selectAnimation(option.value)"
                                    :class="[
                                        'flex w-full items-center rounded-sm px-2 py-1.5 text-sm',
                                        'transition-colors hover:bg-accent hover:text-accent-foreground',
                                        'focus:bg-accent focus:text-accent-foreground focus:outline-none',
                                        selectedAnimation === option.value &&
                                            'bg-accent text-accent-foreground',
                                    ]"
                                >
                                    <div class="flex items-center gap-2">
                                        <div
                                            :class="[
                                                'h-2 w-2 rounded-full border',
                                                selectedAnimation === option.value
                                                    ? 'border-primary bg-primary'
                                                    : 'border-muted-foreground',
                                            ]"
                                        ></div>
                                        {{ option.label }}
                                    </div>
                                </button>
                            </div>
                        </div>
                    </Transition>
                </div>
            </div>

            <!-- Card Theme Selector Dropdown - absolute positioned -->
            <div v-if="isMounted" class="absolute top-2 right-12 z-40">
                <!-- Custom dropdown with controlled animations -->
                <div class="relative">
                    <button
                        @click="toggleDropdown"
                        class="group mt-1 rounded-lg border-2 border-border
                            bg-background/80 p-1.5 shadow-lg backdrop-blur-sm
                            transition-all duration-200 hover:scale-110
                            hover:bg-background focus:ring-0 focus:outline-none"
                    >
                        <ChevronLeft
                            :size="14"
                            :class="[
                                'text-muted-foreground transition-transform duration-200 group-hover:text-foreground',
                                showThemeDropdown && 'rotate-90',
                            ]"
                        />
                    </button>

                    <Transition
                        enter-active-class="transition-all duration-300 ease-apple-bounce"
                        leave-active-class="transition-all duration-250 ease-out"
                        enter-from-class="opacity-0 scale-95 -translate-y-2"
                        enter-to-class="opacity-100 scale-100 translate-y-0"
                        leave-from-class="opacity-100 scale-100 translate-y-0"
                        leave-to-class="opacity-0 scale-95 -translate-y-2"
                    >
                        <div
                            v-if="showThemeDropdown"
                            class="absolute top-full right-0 z-50 mt-4
                                min-w-[140px] origin-top-right rounded-md border
                                bg-popover text-popover-foreground shadow-md"
                            @click.stop
                        >
                            <div class="p-1">
                                <div class="px-2 py-1.5 text-sm font-semibold">
                                    Card Theme
                                </div>
                                <div class="my-1 h-px bg-border"></div>

                                <button
                                    v-for="option in themeOptions"
                                    :key="option.value"
                                    @click="selectTheme(option.value)"
                                    :class="[
                                        'flex w-full items-center rounded-sm px-2 py-1.5 text-sm',
                                        'transition-colors hover:bg-accent hover:text-accent-foreground',
                                        'focus:bg-accent focus:text-accent-foreground focus:outline-none',
                                        store.selectedCardVariant ===
                                            option.value &&
                                            'bg-accent text-accent-foreground',
                                    ]"
                                >
                                    <div class="flex items-center gap-2">
                                        <div
                                            :class="[
                                                'h-2 w-2 rounded-full border',
                                                store.selectedCardVariant ===
                                                option.value
                                                    ? 'border-primary bg-primary'
                                                    : 'border-muted-foreground',
                                            ]"
                                        ></div>
                                        {{ option.label }}
                                    </div>
                                </button>
                            </div>
                        </div>
                    </Transition>
                </div>
            </div>
            <!-- Header Section -->
            <CardHeader class="relative">
                <div class="flex items-center justify-between">
                    <CardTitle 
                        class="themed-title transition-all duration-200"
                        style="
                            background-image: var(--paper-aged-texture);
                            background-size: 100px 100px;
                            background-repeat: repeat;
                            background-clip: text;
                            -webkit-background-clip: text;
                            background-attachment: scroll;
                            background-position: 0 0;
                        "
                    >
                        <!-- Animated Text Title -->
                        <component
                            :is="currentAnimationComponent"
                            v-bind="currentAnimationProps"
                            :key="`${selectedAnimation}-${animationKey}`"
                            class="text-word-title"
                        />
                    </CardTitle>
                </div>

                <!-- Pronunciation -->
                <div
                    v-if="entry.pronunciation"
                    class="flex items-center gap-3 pt-2"
                >
                    <span class="text-pronunciation">
                        {{
                            pronunciationMode === 'phonetic'
                                ? entry.pronunciation.phonetic
                                : entry.pronunciation.ipa
                        }}
                    </span>
                    
                    <!-- Provider Source Icons -->
                    <div v-if="usedProviders.length > 0" class="flex items-center gap-1">
                        <div
                            v-for="provider in usedProviders"
                            :key="provider"
                            :title="`Source: ${getProviderDisplayName(provider)}`"
                            class="flex h-5 w-5 items-center justify-center rounded-full bg-background/80 border border-border/50 shadow-sm hover:bg-accent/50 transition-colors"
                        >
                            <component 
                                :is="getProviderIcon(provider)" 
                                :size="12" 
                                class="text-muted-foreground"
                            />
                        </div>
                    </div>
                    
                    <Button
                        variant="ghost"
                        size="sm"
                        @click="togglePronunciation"
                        class="h-6 px-2 py-1 text-xs transition-all duration-200
                            hover:opacity-80"
                    >
                        {{
                            pronunciationMode === 'phonetic'
                                ? 'IPA'
                                : 'Phonetic'
                        }}
                    </Button>
                </div>
            </CardHeader>

            <!-- Themed Gradient Divider -->
            <div class="themed-hr -mt-2 -mb-2" />

            <!-- Mode Content with Animation -->
            <Transition
                mode="out-in"
                enter-active-class="transition-all duration-300 ease-apple-bounce"
                leave-active-class="transition-all duration-200 ease-out"
                enter-from-class="opacity-0 scale-95 translate-x-8 rotate-1"
                enter-to-class="opacity-100 scale-100 translate-x-0 rotate-0"
                leave-from-class="opacity-100 scale-100 translate-x-0 rotate-0"
                leave-to-class="opacity-0 scale-95 -translate-x-8 -rotate-1"
            >
                <div :key="mode">
                    <!-- Dictionary Mode Definitions -->
                    <CardContent
                        v-if="mode === 'dictionary'"
                        class="grid gap-4"
                    >
                        <div
                            v-for="cluster in groupedDefinitions"
                            :key="cluster.clusterId"
                            :data-cluster-id="cluster.clusterId"
                            class="space-y-4"
                        >
                            <!-- Cluster header with gradient divider -->
                            <div
                                v-if="groupedDefinitions.length > 1"
                                class="mt-6 pb-2"
                            >
                                <h4
                                    class="themed-cluster-title text-base
                                        font-bold tracking-wider uppercase"
                                >
                                    {{ cluster.clusterDescription }}
                                </h4>
                                <!-- Themed Gradient HR -->
                                <!-- <div class="themed-hr h-px" /> -->
                            </div>

                            <div
                                v-for="(
                                    definition, index
                                ) in cluster.definitions"
                                :key="`${cluster.clusterId}-${index}`"
                                :id="`${cluster.clusterId}-${definition.part_of_speech}`"
                                :data-part-of-speech="`${cluster.clusterId}-${definition.part_of_speech}`"
                                class="space-y-3"
                            >
                                <!-- Separator for all but first -->
                                <hr
                                    v-if="index > 0"
                                    class="my-2 border-border"
                                />

                                <div class="flex items-center gap-2">
                                    <span class="text-lg font-semibold text-primary">
                                        {{ definition.part_of_speech }}
                                    </span>
                                    <sup
                                        class="text-sm font-normal
                                            text-muted-foreground"
                                        >{{ index + 1 }}</sup
                                    >
                                </div>

                                <div class="border-l-2 border-accent pl-4">
                                    <p class="text-definition mb-2">
                                        {{ definition.text }}
                                    </p>

                                    <!-- Examples -->
                                    <div
                                        v-if="
                                            definition.examples &&
                                            (definition.examples.generated
                                                .length > 0 ||
                                                definition.examples.literature
                                                    .length > 0)
                                        "
                                        class="mb-2 space-y-1"
                                    >
                                        <!-- Examples header with regenerate button -->
                                        <div
                                            class="mt-3 mb-1 flex items-center
                                                justify-between"
                                        >
                                            <span
                                                class="text-sm tracking-wider
                                                    text-muted-foreground
                                                    uppercase"
                                                >Examples</span
                                            >
                                            <button
                                                v-if="
                                                    definition.examples
                                                        .generated.length > 0
                                                "
                                                @click="
                                                    handleRegenerateExamples(
                                                        index
                                                    )
                                                "
                                                :class="[
                                                    'group flex items-center gap-1 rounded-md px-2 py-1',
                                                    'text-sm transition-all duration-200',
                                                    'hover:bg-primary/10',
                                                    regeneratingIndex === index
                                                        ? 'text-primary'
                                                        : 'text-muted-foreground hover:text-primary',
                                                ]"
                                                :disabled="
                                                    regeneratingIndex === index
                                                "
                                                title="Regenerate examples"
                                            >
                                                <RefreshCw
                                                    :size="12"
                                                    :class="[
                                                        'transition-transform duration-300',
                                                        'group-hover:rotate-180',
                                                        regeneratingIndex ===
                                                            index &&
                                                            'animate-spin',
                                                    ]"
                                                />
                                            </button>
                                        </div>

                                        <p
                                            v-for="(
                                                example, exIndex
                                            ) in definition.examples.generated.concat(
                                                definition.examples.literature
                                            )"
                                            :key="exIndex"
                                            class="themed-example-text text-base
                                                text-muted-foreground italic"
                                            v-html="
                                                `&quot;${formatExampleHTML(example.sentence, entry.word)}&quot;`
                                            "
                                        ></p>
                                    </div>

                                    <!-- Synonyms -->
                                    <div
                                        v-if="
                                            definition.synonyms &&
                                            definition.synonyms.length > 0
                                        "
                                        class="flex flex-wrap gap-1 pt-2"
                                    >
                                        <!-- <span class="self-center pr-2 text-xs">Synonyms:</span> -->
                                        <span
                                            v-for="synonym in definition.synonyms"
                                            :key="synonym"
                                            class="themed-synonym
                                                cursor-pointer"
                                            @click="store.searchWord(synonym)"
                                        >
                                            {{ synonym }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>

                    <!-- Thesaurus Mode -->
                    <CardContent
                        v-if="mode === 'thesaurus' && thesaurusData"
                        class="space-y-6"
                    >
                        <div
                            v-if="thesaurusData.synonyms.length > 0"
                            class="grid grid-cols-1 gap-3 md:grid-cols-2
                                lg:grid-cols-3"
                        >
                            <Card
                                v-for="synonym in thesaurusData.synonyms"
                                :key="synonym.word"
                                :class="
                                    cn(
                                        'cursor-pointer py-2 transition-all duration-300 hover:scale-105 hover:shadow-lg',
                                        getHeatmapClass(synonym.score)
                                    )
                                "
                                @click="store.searchWord(synonym.word)"
                            >
                                <CardContent class="px-3 py-0.5">
                                    <div class="font-medium">
                                        {{ synonym.word }}
                                    </div>
                                    <div class="text-sm opacity-75">
                                        {{ Math.round(synonym.score * 100) }}%
                                        similar
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </CardContent>
                </div>
            </Transition>

            <!-- Etymology -->
            <CardContent
                v-if="entry && entry.etymology"
                class="space-y-4 px-3 sm:px-6"
            >
                <h3 class="text-lg font-semibold">Etymology</h3>
                <p class="text-base text-muted-foreground">
                    {{ entry.etymology }}
                </p>
            </CardContent>
        </ThemedCard>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import { Button } from '@/components/ui';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ThemedCard } from '@/components/custom/card';
import { TypewriterText, HandwritingText, LatexFillText } from '@/components/custom/text-animations';
import { ProgressiveSidebar } from '@/components/custom/navigation';
import { RefreshCw, ChevronLeft } from 'lucide-vue-next';
import { 
    AppleIcon,
    WiktionaryIcon, 
    OxfordIcon, 
    DictionaryIcon 
} from '@/components/custom/icons';
import type { Definition } from '@/types/api';
import type { CardVariant } from '@/types';

// Track mounting state for dropdown
const isMounted = ref(false);
// Track which definition is regenerating
const regeneratingIndex = ref<number | null>(null);

// Custom dropdown state
const showThemeDropdown = ref(false);
const themeOptions = [
    { label: 'Default', value: 'default' },
    { label: 'Bronze', value: 'bronze' },
    { label: 'Silver', value: 'silver' },
    { label: 'Gold', value: 'gold' },
];

// Animation dropdown state
const showAnimationDropdown = ref(false);
const selectedAnimation = ref('typewriter');
const animationKey = ref(0);
const animationOptions = [
    { label: 'Typewriter', value: 'typewriter' },
    { label: 'Handwriting', value: 'handwriting' },
    { label: 'LaTeX Fill', value: 'latex' },
];

// Animation component logic
const currentAnimationComponent = computed(() => {
    switch (selectedAnimation.value) {
        case 'typewriter':
            return TypewriterText;
        case 'handwriting':
            return HandwritingText;
        case 'latex':
            return LatexFillText;
        default:
            return TypewriterText;
    }
});


const currentAnimationProps = computed(() => {
    const word = entry.value?.word || '';
    
    const customStyles = {
        color: 'var(--color-foreground)',
        // Add subtle texture overlay without making text transparent
        position: 'relative',
        textShadow: '0 1px 2px rgba(0,0,0,0.1)'
    };
    
    switch (selectedAnimation.value) {
        case 'typewriter':
            return { 
                text: word,
                class: 'text-word-title',
                customStyles,
                speed: 300, 
                cursor: true 
            }; // 300ms between characters for slow, readable typing
        case 'handwriting':
            return { 
                text: word,
                class: 'text-word-title',
                customStyles,
                speed: 2, 
                strokeWidth: 2 
            };
        case 'latex':
            return { 
                content: word,
                class: 'text-word-title',
                customStyles,
                speed: 1.5, 
                fillDirection: 'center-out' as const,
                mathMode: false
            };
        default:
            return { 
                text: word,
                class: 'text-word-title',
                customStyles
            };
    }
});

// Animation cycling - run with random delay around 30 seconds
let animationTimeout: NodeJS.Timeout | null = null;

const getRandomDelay = () => {
    // Random delay between 25-35 seconds
    return 25000 + Math.random() * 10000;
};

const scheduleNextAnimation = () => {
    if (animationTimeout) clearTimeout(animationTimeout);
    
    animationTimeout = setTimeout(() => {
        // Force re-render by updating key
        animationKey.value++;
        // Schedule the next animation
        scheduleNextAnimation();
    }, getRandomDelay());
};

const startAnimationCycle = () => {
    // First animation after initial page load delay
    if (animationTimeout) clearTimeout(animationTimeout);
    
    animationTimeout = setTimeout(() => {
        animationKey.value++;
        scheduleNextAnimation();
    }, 5000); // Initial delay of 5 seconds
};

const stopAnimationCycle = () => {
    if (animationTimeout) {
        clearTimeout(animationTimeout);
        animationTimeout = null;
    }
};

onMounted(() => {
    isMounted.value = true;
    startAnimationCycle();
});

// Remove unused props interface since we're using store state
// interface DefinitionDisplayProps {
//   variant?: CardVariant;
// }

// const props = withDefaults(defineProps<DefinitionDisplayProps>(), {
//   variant: 'default',
// });

const store = useAppStore();

// PROPER SOLUTION: Use storeToRefs for reactive extraction
const { selectedCardVariant } = storeToRefs(store);

const entry = computed(() => store.currentEntry);
const thesaurusData = computed(() => store.currentThesaurus);
const mode = computed(() => store.mode);
const pronunciationMode = computed(() => store.pronunciationMode);

// Extract unique providers from definitions
const usedProviders = computed((): string[] => {
    if (!entry.value?.definitions) return [];
    
    const providers = new Set<string>();
    entry.value.definitions.forEach((def) => {
        if (def.source_attribution) {
            // Extract provider name from source attribution
            const provider = extractProviderFromAttribution(def.source_attribution);
            if (provider) {
                providers.add(provider);
            }
        }
    });
    
    return Array.from(providers);
});

// Helper function to extract provider from source attribution
function extractProviderFromAttribution(attribution: string): string | null {
    if (!attribution) return null;
    
    const lower = attribution.toLowerCase();
    if (lower.includes('wiktionary')) return 'wiktionary';
    if (lower.includes('oxford')) return 'oxford';
    if (lower.includes('dictionary.com') || lower.includes('dictionary_com')) return 'dictionary_com';
    if (lower.includes('apple') || lower.includes('apple_dictionary')) return 'apple_dictionary';
    if (lower.includes('ai') || lower.includes('gpt')) return 'ai_fallback';
    
    return null;
}

// Helper function to get provider display name
function getProviderDisplayName(provider: string): string {
    const names: Record<string, string> = {
        wiktionary: 'Wiktionary',
        oxford: 'Oxford Dictionary',
        dictionary_com: 'Dictionary.com',
        apple_dictionary: 'Apple Dictionary',
        ai_fallback: 'AI Generated',
    };
    return names[provider] || provider;
}

// Helper function to get provider icon component
function getProviderIcon(provider: string): any {
    const icons: Record<string, any> = {
        wiktionary: WiktionaryIcon,
        oxford: OxfordIcon,
        dictionary_com: DictionaryIcon,
        apple_dictionary: AppleIcon,
        ai_fallback: RefreshCw, // Use RefreshCw for AI
    };
    return icons[provider] || RefreshCw;
}

// Check if sidebar should be shown (same logic as ProgressiveSidebar)
const shouldShowSidebar = computed(() => {
    if (!entry.value?.definitions) return false;

    const clusters = new Set();
    entry.value.definitions.forEach((def) => {
        clusters.add(def.meaning_cluster?.id || 'default');
    });

    const hasMultipleClusters = clusters.size > 1;
    // We'll assume desktop for this computed, actual responsive check happens in CSS
    return hasMultipleClusters;
});

// Part of speech ordering for consistent display
const partOfSpeechOrder: Record<string, number> = {
    noun: 1,
    verb: 2,
    adjective: 3,
    adverb: 4,
    pronoun: 5,
    preposition: 6,
    conjunction: 7,
    interjection: 8,
    determiner: 9,
    article: 10,
};

// Type for transformed definition with grouped examples
interface TransformedDefinition extends Omit<Definition, 'examples'> {
    examples: {
        generated: Array<{ sentence: string; regenerable?: boolean; source?: string }>;
        literature: Array<{ sentence: string; regenerable?: boolean; source?: string }>;
    };
    definition?: string; // Alias for text field used in templates
}

// Type for grouped definitions
interface GroupedDefinition {
    clusterId: string;
    clusterDescription: string;
    definitions: TransformedDefinition[];
    maxRelevancy: number;
}

// Group and sort definitions by meaning cluster and relevancy
const groupedDefinitions = computed((): GroupedDefinition[] => {
    if (!entry.value?.definitions) return [];

    // Group definitions by meaning cluster
    const clusters = new Map<string, GroupedDefinition>();

    entry.value.definitions.forEach((definition) => {
        const clusterId = definition.meaning_cluster?.id || 'default';
        const clusterDescription = definition.meaning_cluster?.name || 'General';

        if (!clusters.has(clusterId)) {
            clusters.set(clusterId, {
                clusterId,
                clusterDescription,
                definitions: [],
                maxRelevancy: definition.relevancy || 1.0,
            });
        }

        const cluster = clusters.get(clusterId)!;
        // Cast definition since API transforms it
        const transformedDef = definition as any as TransformedDefinition;
        cluster.definitions.push(transformedDef);

        // Track highest relevancy in cluster for sorting
        if ((definition.relevancy || 1.0) > cluster.maxRelevancy) {
            cluster.maxRelevancy = definition.relevancy || 1.0;
        }
    });

    // Sort clusters by maximum relevancy (highest first)
    const sortedClusters = Array.from(clusters.values()).sort(
        (a, b) => b.maxRelevancy - a.maxRelevancy
    );

    // Sort definitions within each cluster
    sortedClusters.forEach((cluster) => {
        cluster.definitions.sort((a, b) => {
            // First, sort by word type (nouns first, verbs second, etc.)
            const aTypeOrder =
                partOfSpeechOrder[
                    a.part_of_speech?.toLowerCase() as keyof typeof partOfSpeechOrder
                ] || 999;
            const bTypeOrder =
                partOfSpeechOrder[
                    b.part_of_speech?.toLowerCase() as keyof typeof partOfSpeechOrder
                ] || 999;

            if (aTypeOrder !== bTypeOrder) {
                return aTypeOrder - bTypeOrder;
            }

            // Then sort by relevancy within the same word type (highest first)
            return (b.relevancy || 1.0) - (a.relevancy || 1.0);
        });
    });

    return sortedClusters;
});

const togglePronunciation = () => {
    store.togglePronunciation();
};

// Handle regenerating examples for a specific definition
const handleRegenerateExamples = async (definitionIndex: number) => {
    if (regeneratingIndex.value !== null) return; // Already regenerating

    regeneratingIndex.value = definitionIndex;
    try {
        await store.regenerateExamples(definitionIndex);
    } catch (error) {
        console.error('Failed to regenerate examples:', error);
    } finally {
        regeneratingIndex.value = null;
    }
};

// const formatExample = (example: string, word: string): string => {
//   // Create a case-insensitive regex to find the word
//   const regex = new RegExp(`\\b${word}\\b`, 'gi');
//   return example.replace(regex, `**${word}**`);
// };

const formatExampleHTML = (example: string, word: string): string => {
    // Create a case-insensitive regex to find the word and make it bold
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    return example.replace(
        regex,
        `<strong class="hover-word">${word}</strong>`
    );
};

// Custom dropdown handlers
const toggleDropdown = () => {
    showThemeDropdown.value = !showThemeDropdown.value;
};

const selectTheme = (theme: string) => {
    store.selectedCardVariant = theme as CardVariant;
    showThemeDropdown.value = false;
};

// Animation dropdown handlers
const toggleAnimationDropdown = () => {
    showAnimationDropdown.value = !showAnimationDropdown.value;
};

const selectAnimation = (animation: string) => {
    selectedAnimation.value = animation;
    showAnimationDropdown.value = false;
    // Trigger immediate animation restart
    animationKey.value++;
};

// Close dropdown when clicking outside
const handleClickOutside = (event: Event) => {
    const target = event.target as Element;
    if (showThemeDropdown.value && !target.closest('.relative')) {
        showThemeDropdown.value = false;
    }
    if (showAnimationDropdown.value && !target.closest('.relative')) {
        showAnimationDropdown.value = false;
    }
};

// Create a list of all parts of speech in order for keyboard navigation
const orderedPartsOfSpeech = computed((): Array<{clusterId: string, partOfSpeech: string, key: string}> => {
    const partsOfSpeech: Array<{clusterId: string, partOfSpeech: string, key: string}> = [];
    
    groupedDefinitions.value.forEach(cluster => {
        // Group by part of speech within each cluster
        const partOfSpeechGroups = new Map<string, TransformedDefinition[]>();
        cluster.definitions.forEach(def => {
            const partOfSpeech = def.part_of_speech;
            if (!partOfSpeechGroups.has(partOfSpeech)) {
                partOfSpeechGroups.set(partOfSpeech, []);
            }
            partOfSpeechGroups.get(partOfSpeech)!.push(def);
        });
        
        // Sort parts of speech within cluster
        const sortedPartsOfSpeech = Array.from(partOfSpeechGroups.keys()).sort(
            (a, b) => (partOfSpeechOrder[a] || 999) - 
                      (partOfSpeechOrder[b] || 999)
        );
        
        sortedPartsOfSpeech.forEach(partOfSpeech => {
            partsOfSpeech.push({
                clusterId: cluster.clusterId,
                partOfSpeech,
                key: `${cluster.clusterId}-${partOfSpeech}`
            });
        });
    });
    
    return partsOfSpeech;
});

// Current part of speech index for keyboard navigation
const currentPartOfSpeechIndex = computed(() => {
    // Simplified: always start from first word type
    return 0;
});

// Keyboard navigation handler for up/down arrows (always active)
const handleKeyDown = (event: KeyboardEvent) => {
    if (!entry.value?.definitions) return;
    
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        
        const currentIndex = currentPartOfSpeechIndex.value;
        let nextIndex: number;
        
        if (event.key === 'ArrowDown') {
            nextIndex = currentIndex < orderedPartsOfSpeech.value.length - 1 ? currentIndex + 1 : 0;
        } else {
            nextIndex = currentIndex > 0 ? currentIndex - 1 : orderedPartsOfSpeech.value.length - 1;
        }
        
        if (nextIndex >= 0 && nextIndex < orderedPartsOfSpeech.value.length) {
            const nextPartOfSpeech = orderedPartsOfSpeech.value[nextIndex];
            scrollToPartOfSpeech(nextPartOfSpeech.clusterId, nextPartOfSpeech.partOfSpeech);
        }
    }
};

// Scroll to part of speech function (same as used in ProgressiveSidebar)
const scrollToPartOfSpeech = (clusterId: string, partOfSpeech: string) => {
    const element = document.getElementById(`${clusterId}-${partOfSpeech}`);
    if (element) {
        element.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
        // Note: activePartOfSpeech functionality removed for KISS approach
    }
};

onMounted(() => {
    isMounted.value = true;
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeyDown);
    stopAnimationCycle();
});
</script>

<style scoped>
/* Dynamic hover effects for emboldened words based on card variant */
.hover-word {
    transition: all 0.2s ease;
    cursor: default;
}

/* Custom dropdown styling for better theme integration */
.dropdown-content {
    transform-origin: top right;
}

.hover-word:hover {
    transform: scale(1.05);
}

/* Themed card word hover */
:global([data-theme='gold']) .hover-word:hover {
    color: var(--theme-text);
}

:global([data-theme='silver']) .hover-word:hover {
    color: var(--theme-text);
}

:global([data-theme='bronze']) .hover-word:hover {
    color: var(--theme-text);
}

/* Default card word hover */
:global([data-theme='default']) .hover-word:hover {
    color: var(--color-primary);
}
</style>
