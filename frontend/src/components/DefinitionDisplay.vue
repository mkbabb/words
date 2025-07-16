<template>
    {{ store.selectedCardVariant }}
  <ThemedCard
    v-if="entry"
    :variant="selectedCardVariant"
    class="space-y-6"
  >
    <!-- Header Section -->
    <CardHeader>
      <div class="flex items-center justify-between">
        <CardTitle
          :class="
            cn('text-word-title transition-all duration-200', titleHoverClass)
          "
          >{{ entry.word }}</CardTitle
        >
        <!-- Tabs section for to select the card variant: either gold, silver, bronze -->
        <Tabs v-model="store.selectedCardVariant" class="w-auto">
          <TabsList class="grid w-full grid-cols-4 gap-1">
            <TabsTrigger
              value="default"
              class="hover:bg-muted/50 data-[state=active]:bg-muted text-xs transition-all"
            >
              Default
            </TabsTrigger>
            <TabsTrigger
              value="bronze"
              class="text-xs transition-all hover:bg-orange-100/30 hover:text-orange-700 data-[state=active]:bg-gradient-to-r data-[state=active]:from-orange-100/40 data-[state=active]:to-amber-100/40 data-[state=active]:text-orange-800 dark:hover:bg-orange-900/20 dark:hover:text-orange-400 dark:data-[state=active]:from-orange-900/30 dark:data-[state=active]:to-amber-900/30 dark:data-[state=active]:text-orange-300"
            >
              Bronze
            </TabsTrigger>
            <TabsTrigger
              value="silver"
              class="text-xs transition-all hover:bg-gray-100/30 hover:text-gray-700 data-[state=active]:bg-gradient-to-r data-[state=active]:from-gray-100/40 data-[state=active]:to-slate-100/40 data-[state=active]:text-gray-800 dark:hover:bg-gray-800/20 dark:hover:text-gray-300 dark:data-[state=active]:from-gray-800/30 dark:data-[state=active]:to-slate-800/30 dark:data-[state=active]:text-gray-200"
            >
              Silver
            </TabsTrigger>
            <TabsTrigger
              value="gold"
              class="text-xs transition-all hover:bg-yellow-100/30 hover:text-yellow-700 data-[state=active]:bg-gradient-to-r data-[state=active]:from-yellow-100/40 data-[state=active]:to-amber-100/40 data-[state=active]:text-yellow-800 dark:hover:bg-yellow-900/20 dark:hover:text-yellow-400 dark:data-[state=active]:from-yellow-900/30 dark:data-[state=active]:to-amber-900/30 dark:data-[state=active]:text-yellow-300"
            >
              Gold
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <!-- Pronunciation -->
      <div v-if="entry.pronunciation" class="flex items-center gap-3 pt-2">
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
          class="h-6 px-2 py-1 text-xs transition-all duration-200 hover:opacity-80"
        >
          {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
        </Button>
      </div>
    </CardHeader>

    <!-- Gradient Divider -->
    <div class="relative h-px w-full overflow-hidden">
      <div
        class="via-primary/30 absolute inset-0 bg-gradient-to-r from-transparent to-transparent"
      />
    </div>

    <!-- Dictionary Mode Definitions -->
    <CardContent v-if="mode === 'dictionary'" class="space-y-4 pt-1">
      <div
        v-for="(definition, index) in entry.definitions"
        :key="index"
        class="space-y-3"
      >
        <!-- Separator for all but first -->
        <hr v-if="index > 0" class="border-border" />

        <div class="flex items-center gap-2">
          <Badge variant="secondary" class="text-part-of-speech">
            {{ definition.word_type }}
          </Badge>
          <sup class="text-muted-foreground text-xs font-normal">{{
            index + 1
          }}</sup>
        </div>

        <div class="border-accent border-l-2 pl-4">
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
            <p
              v-for="(example, exIndex) in definition.examples.generated.concat(
                definition.examples.literature
              )"
              :key="exIndex"
              class="text-muted-foreground/70 text-sm italic"
              v-html="
                `&quot;${formatExampleHTML(example.sentence, entry.word)}&quot;`
              "
            ></p>
          </div>

          <!-- Synonyms -->
          <div
            v-if="definition.synonyms && definition.synonyms.length > 0"
            class="flex flex-wrap gap-1 pt-2"
          >
            <span class="text-muted-foreground self-center pr-2 text-xs"
              >Synonyms:</span
            >
            <Badge
              v-for="synonym in definition.synonyms"
              :key="synonym"
              variant="outline"
              class="hover:bg-accent/50 cursor-pointer text-xs transition-all duration-200 hover:font-semibold hover:opacity-80"
              @click="store.searchWord(synonym)"
            >
              {{ synonym }}
            </Badge>
          </div>
        </div>
      </div>
    </CardContent>

    <!-- Thesaurus Mode -->
    <CardContent
      v-if="mode === 'thesaurus' && thesaurusData"
      class="space-y-6 pt-6"
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
              'cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-lg',
              getHeatmapClass(synonym.score)
            )
          "
          @click="store.searchWord(synonym.word)"
        >
          <CardContent class="px-3 py-4">
            <div class="font-medium">{{ synonym.word }}</div>
            <div class="text-xs opacity-75">
              {{ Math.round(synonym.score * 100) }}% similar
            </div>
          </CardContent>
        </Card>
      </div>
    </CardContent>

    <!-- Etymology -->
    <CardContent v-if="entry && entry.etymology" class="space-y-4">
      <h3 class="text-lg font-semibold">Etymology</h3>
      <p class="text-muted-foreground text-sm">{{ entry.etymology }}</p>
    </CardContent>
  </ThemedCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import Button from '@/components/ui/Button.vue';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Badge from '@/components/ui/Badge.vue';
import ThemedCard from '@/components/ui/ThemedCard.vue';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

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

const togglePronunciation = () => {
  store.togglePronunciation();
};

// const formatExample = (example: string, word: string): string => {
//   // Create a case-insensitive regex to find the word
//   const regex = new RegExp(`\\b${word}\\b`, 'gi');
//   return example.replace(regex, `**${word}**`);
// };

const formatExampleHTML = (example: string, word: string): string => {
  // Create a case-insensitive regex to find the word and make it bold
  const regex = new RegExp(`\\b${word}\\b`, 'gi');
  return example.replace(regex, `<strong class="hover-word">${word}</strong>`);
};

// Computed classes based on store variant
const titleHoverClass = computed(() => {
  switch (selectedCardVariant.value) {
    case 'gold':
      return 'hover:text-yellow-600 dark:hover:text-yellow-400';
    case 'silver':
      return 'hover:text-slate-600 dark:hover:text-slate-400';
    case 'bronze':
      return 'hover:text-bronze-600 dark:hover:text-bronze-400';
    default:
      return 'hover:text-primary';
  }
});
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

/* Gold card word hover */
:global(.card-gold) .hover-word:hover {
  color: #ca8a04; /* yellow-600 */
}

:global(.dark .card-gold) .hover-word:hover {
  color: #facc15; /* yellow-400 */
}

/* Silver card word hover */
:global(.card-silver) .hover-word:hover {
  color: #475569; /* slate-600 */
}

:global(.dark .card-silver) .hover-word:hover {
  color: #cbd5e1; /* slate-400 */
}

/* Bronze card word hover */
:global(.card-bronze) .hover-word:hover {
  color: #b45309; /* amber-700 */
}

:global(.dark .card-bronze) .hover-word:hover {
  color: #fbbf24; /* amber-400 */
}

/* Default card word hover */
:global(.bg-card) .hover-word:hover {
  color: var(--color-primary);
}
</style>
