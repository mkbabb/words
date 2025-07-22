<template>
    <div 
        v-if="entry" 
        :class="[
            'flex',
            shouldShowSidebar && groupedDefinitions.length > 1 ? 'xl:gap-4' : ''
        ]"
    >
        <!-- Progressive Sidebar - Truly sticky -->
        <div 
            v-if="shouldShowSidebar && groupedDefinitions.length > 1"
            class="hidden xl:block w-48 flex-shrink-0"
        >
            <div class="sticky top-4">
                <ProgressiveSidebar />
            </div>
        </div>

        <!-- Main Card Content -->
        <ThemedCard :variant="selectedCardVariant" class="relative flex-1">
            <!-- Card Theme Selector Dropdown - INSIDE the card -->
            <div
                v-if="isMounted"
                :class="[
                    'absolute top-2 z-50 transition-all duration-300 ease-out',
                    selectedCardVariant === 'default' ? 'right-2' : 'right-12',
                ]"
            >
                <DropdownMenu>
                    <DropdownMenuTrigger as-child>
                        <button
                            class="group rounded-lg border-2 border-border
                                bg-background/80 p-1.5 shadow-lg backdrop-blur-sm
                                transition-all duration-200 hover:scale-110
                                hover:bg-background"
                        >
                            <ChevronLeft
                                :size="14"
                                class="text-muted-foreground transition-transform
                                    duration-200 group-hover:text-foreground
                                    group-data-[state=open]:rotate-90"
                            />
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" class="min-w-[140px]">
                        <DropdownMenuLabel>Card Theme</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuRadioGroup v-model="store.selectedCardVariant">
                            <DropdownMenuRadioItem value="default">
                                Default
                            </DropdownMenuRadioItem>
                            <DropdownMenuRadioItem value="bronze">
                                Bronze
                            </DropdownMenuRadioItem>
                            <DropdownMenuRadioItem value="silver">
                                Silver
                            </DropdownMenuRadioItem>
                            <DropdownMenuRadioItem value="gold">
                                Gold
                            </DropdownMenuRadioItem>
                        </DropdownMenuRadioGroup>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
            <!-- Header Section -->
            <CardHeader>
                <div class="flex items-center justify-between">
                    <CardTitle class="themed-title transition-all duration-200">
                        <ShimmerText 
                            :text="entry.word" 
                            text-class="text-word-title"
                            :duration="2000"
                            :interval="25"
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
                    <Button
                        variant="ghost"
                        size="sm"
                        @click="togglePronunciation"
                        class="h-6 px-2 py-1 text-xs transition-all duration-200
                            hover:opacity-80"
                    >
                        {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
                    </Button>
                </div>
            </CardHeader>

            <!-- Gradient Divider -->
            <div class="relative h-px w-full overflow-hidden">
                <div
                    class="absolute inset-0 bg-gradient-to-r from-transparent
                        via-primary/30 to-transparent"
                />
            </div>

            <!-- Dictionary Mode Definitions -->
            <CardContent v-if="mode === 'dictionary'" class="grid gap-4">
            <div
                v-for="cluster in groupedDefinitions"
                :key="cluster.clusterId"
                :data-cluster-id="cluster.clusterId"
                class="space-y-4"
            >
                <!-- Cluster header with gradient divider -->
                <div v-if="groupedDefinitions.length > 1" class="pb-2">
                    <h4
                        class="mb-2 text-base font-semibold tracking-wider
                            text-foreground uppercase"
                    >
                        {{ cluster.clusterDescription }}
                    </h4>
                    <!-- Gradient HR -->
                    <hr
                        class="h-px border-0 bg-gradient-to-r from-transparent
                            via-border to-transparent"
                    />
                </div>

                <div
                    v-for="(definition, index) in cluster.definitions"
                    :key="`${cluster.clusterId}-${index}`"
                    :data-word-type="`${cluster.clusterId}-${definition.word_type}`"
                    class="space-y-3"
                >
                    <!-- Separator for all but first -->
                    <hr v-if="index > 0" class="my-2 border-border" />

                    <div class="flex items-center gap-2">
                        <span class="themed-word-type">
                            {{ definition.word_type }}
                        </span>
                        <sup
                            class="text-sm font-normal text-muted-foreground"
                            >{{ index + 1 }}</sup
                        >
                    </div>

                    <div class="border-l-2 border-accent pl-4">
                        <p class="text-definition mb-2">
                            {{ definition.definition }}
                        </p>

                        <!-- Examples -->
                        <div
                            v-if="
                                definition.examples &&
                                (definition.examples.generated.length > 0 ||
                                    definition.examples.literature.length > 0)
                            "
                            class="mb-2 space-y-1"
                        >
                            <!-- Examples header with regenerate button -->
                            <div class="mb-1 mt-3 flex items-center justify-between">
                                <span
                                    class="text-sm tracking-wider
                                        text-muted-foreground uppercase"
                                    >Examples</span
                                >
                                <button
                                    v-if="
                                        definition.examples.generated.length > 0
                                    "
                                    @click="handleRegenerateExamples(index)"
                                    :class="[
                                        'group flex items-center gap-1 rounded-md px-2 py-1',
                                        'text-sm transition-all duration-200',
                                        'hover:bg-primary/10',
                                        regeneratingIndex === index
                                            ? 'text-primary'
                                            : 'text-muted-foreground hover:text-primary',
                                    ]"
                                    :disabled="regeneratingIndex === index"
                                    title="Regenerate examples"
                                >
                                    <RefreshCw
                                        :size="12"
                                        :class="[
                                            'transition-transform duration-300',
                                            'group-hover:rotate-180',
                                            regeneratingIndex === index &&
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
                                class="text-base text-muted-foreground italic themed-example-text"
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
                                class="themed-synonym cursor-pointer"
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
                class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3"
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
                        <div class="font-medium">{{ synonym.word }}</div>
                        <div class="text-sm opacity-75">
                            {{ Math.round(synonym.score * 100) }}% similar
                        </div>
                    </CardContent>
                </Card>
            </div>
        </CardContent>

            <!-- Etymology -->
            <CardContent v-if="entry && entry.etymology" class="space-y-4">
                <h3 class="text-lg font-semibold">Etymology</h3>
                <p class="text-base text-muted-foreground">{{ entry.etymology }}</p>
            </CardContent>
        </ThemedCard>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import { Button } from '@/components/ui';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ThemedCard } from '@/components/custom/card';
import { ShimmerText } from '@/components/custom/animation';
import { ProgressiveSidebar } from '@/components/custom/navigation';
import {
    DropdownMenu,
    DropdownMenuTrigger,
    DropdownMenuContent,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu';
import { RefreshCw, ChevronLeft } from 'lucide-vue-next';

// Track mounting state for dropdown
const isMounted = ref(false);
// Track which definition is regenerating
const regeneratingIndex = ref<number | null>(null);

onMounted(() => {
    isMounted.value = true;
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

// Check if sidebar should be shown (same logic as ProgressiveSidebar)
const shouldShowSidebar = computed(() => {
  if (!entry.value?.definitions) return false;
  
  const clusters = new Set();
  entry.value.definitions.forEach(def => {
    clusters.add(def.meaning_cluster || 'default');
  });
  
  const hasMultipleClusters = clusters.size > 1;
  // We'll assume desktop for this computed, actual responsive check happens in CSS
  return hasMultipleClusters;
});

// Word type ordering for consistent display
const wordTypeOrder = {
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

// Group and sort definitions by meaning cluster and relevancy
const groupedDefinitions = computed(() => {
    if (!entry.value?.definitions) return [];

    // Group definitions by meaning cluster
    const clusters = new Map<
        string,
        {
            clusterId: string;
            clusterDescription: string;
            definitions: typeof entry.value.definitions;
            maxRelevancy: number;
        }
    >();

    entry.value.definitions.forEach((definition) => {
        const clusterId = definition.meaning_cluster || 'default';
        const clusterDescription = definition.meaning_cluster
            ? clusterId
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (l) => l.toUpperCase())
                  .replace(new RegExp(`\\b${entry.value?.word}\\b`, 'gi'), '')
                  .trim()
            : 'General';

        if (!clusters.has(clusterId)) {
            clusters.set(clusterId, {
                clusterId,
                clusterDescription,
                definitions: [],
                maxRelevancy: definition.relevancy || 1.0,
            });
        }

        const cluster = clusters.get(clusterId)!;
        cluster.definitions.push(definition);

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
                wordTypeOrder[
                    a.word_type?.toLowerCase() as keyof typeof wordTypeOrder
                ] || 999;
            const bTypeOrder =
                wordTypeOrder[
                    b.word_type?.toLowerCase() as keyof typeof wordTypeOrder
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
</script>

<style scoped>
/* Dynamic hover effects for emboldened words based on card variant */
.hover-word {
    transition: all 0.2s ease;
    cursor: default;
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
