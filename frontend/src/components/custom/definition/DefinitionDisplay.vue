<template>
  <ThemedCard  v-if="entry" :variant="selectedCardVariant">
    <!-- Card Theme Selector Dropdown - INSIDE the card -->
    <div v-if="isMounted" class="absolute top-2 right-12 z-50">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <button class="bg-background/80 backdrop-blur-sm border-2 border-border rounded-lg p-1.5 shadow-lg hover:bg-background transition-all duration-200 hover:scale-110 group">
            <ChevronLeft
              :size="14"
              class="transition-transform duration-200 text-muted-foreground group-hover:text-foreground group-data-[state=open]:rotate-90"
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
        <CardTitle class="text-word-title themed-title transition-all duration-200">
          {{ entry.word }}
        </CardTitle>
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
    <CardContent v-if="mode === 'dictionary'" class="grid gap-4">
      <div
        v-for="(definition, index) in entry.definitions"
        :key="index"
        class="space-y-3"
      >
        <!-- Separator for all but first -->
        <hr v-if="index > 0" class="border-border my-2" />

        <div class="flex items-center gap-2">
          <span class="themed-word-type">
            {{ definition.word_type }}
          </span>
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
            <!-- Examples header with regenerate button -->
            <div class="flex items-center justify-between mb-1">
              <span class="text-muted-foreground text-xs uppercase tracking-wider">Examples</span>
              <button
                v-if="definition.examples.generated.length > 0"
                @click="handleRegenerateExamples(index)"
                :class="[
                  'group flex items-center gap-1 rounded-md px-2 py-1',
                  'text-xs transition-all duration-200',
                  'hover:bg-primary/10',
                  regeneratingIndex === index
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-primary'
                ]"
                :disabled="regeneratingIndex === index"
                title="Regenerate examples"
              >
                <RefreshCw
                  :size="12"
                  :class="[
                    'transition-transform duration-300',
                    'group-hover:rotate-180',
                    regeneratingIndex === index && 'animate-spin'
                  ]"
                />
              </button>
            </div>
            
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
          <CardContent class="px-3 py-2">
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
import { computed, ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import { Button } from '@/components/ui';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ThemedCard } from '@/components/custom/card';
import { 
  DropdownMenu, 
  DropdownMenuTrigger, 
  DropdownMenuContent, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuRadioGroup, 
  DropdownMenuRadioItem 
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
  return example.replace(regex, `<strong class="hover-word">${word}</strong>`);
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
:global([data-theme="gold"]) .hover-word:hover {
  color: var(--theme-text);
}

:global([data-theme="silver"]) .hover-word:hover {
  color: var(--theme-text);
}

:global([data-theme="bronze"]) .hover-word:hover {
  color: var(--theme-text);
}

/* Default card word hover */
:global([data-theme="default"]) .hover-word:hover {
  color: var(--color-primary);
}
</style>
