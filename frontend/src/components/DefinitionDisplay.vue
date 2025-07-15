<template>
  <ThemedCard v-if="entry" :variant="selectedVariant" class="space-y-6">
    <!-- Header Section -->
    <CardHeader>
      <div class="flex items-center justify-between">
        <CardTitle class="text-word-title">{{ entry.word }}</CardTitle>
        <!-- Tabs section for to select the card variant: either gold, silver, bronze -->
        <Tabs
          :default-value="selectedVariant"
          :model-value="selectedVariant"
          @update:model-value="handleVariantChange"
          class="w-auto"
        >
          <TabsList class="grid w-full grid-cols-4">
            <TabsTrigger value="default" class="text-xs">Default</TabsTrigger>
            <TabsTrigger value="bronze" class="text-xs">Bronze</TabsTrigger>
            <TabsTrigger value="silver" class="text-xs">Silver</TabsTrigger>
            <TabsTrigger value="gold" class="text-xs">Gold</TabsTrigger>
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
import { computed, ref } from 'vue';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import Button from '@/components/ui/Button.vue';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Badge from '@/components/ui/Badge.vue';
import ThemedCard from '@/components/ui/ThemedCard.vue';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface DefinitionDisplayProps {
  variant?: CardVariant;
}

const props = withDefaults(defineProps<DefinitionDisplayProps>(), {
  variant: 'default',
});

const store = useAppStore();

// Local state for the selected variant
const selectedVariant = ref<CardVariant>(props.variant);

const entry = computed(() => store.currentEntry);
const thesaurusData = computed(() => store.currentThesaurus);
const mode = computed(() => store.mode);
const pronunciationMode = computed(() => store.pronunciationMode);

const togglePronunciation = () => {
  store.togglePronunciation();
};

const handleVariantChange = (value: string | number) => {
  selectedVariant.value = value as CardVariant;
};

// const formatExample = (example: string, word: string): string => {
//   // Create a case-insensitive regex to find the word
//   const regex = new RegExp(`\\b${word}\\b`, 'gi');
//   return example.replace(regex, `**${word}**`);
// };

const formatExampleHTML = (example: string, word: string): string => {
  // Create a case-insensitive regex to find the word and make it bold
  const regex = new RegExp(`\\b${word}\\b`, 'gi');
  return example.replace(regex, `<strong>${word}</strong>`);
};
</script>
