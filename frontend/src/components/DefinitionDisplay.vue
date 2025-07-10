<template>
  <ThemedCard v-if="entry" :variant="props.variant" class="space-y-6">
    <!-- Header Section -->
    <CardHeader>
      <div class="flex items-center justify-between">
        <CardTitle class="text-word-title">{{ entry.word }}</CardTitle>
       
      </div>

      <!-- Pronunciation -->
      <div v-if="entry.pronunciation" class="flex items-center gap-3 pt-2">
        <span class="text-pronunciation font-mono text-sm">
          {{ pronunciationMode === 'phonetic' 
            ? entry.pronunciation.phonetic 
            : entry.pronunciation.ipa 
          }}
        </span>
        <Button
          variant="ghost"
          size="sm"
          @click="togglePronunciation"
          class="text-xs px-2 py-1 h-6 transition-all duration-200 hover:opacity-80"
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
          <sup class="text-xs font-normal text-muted-foreground">{{ index + 1 }}</sup>
        </div>
        
        <div class="pl-4 border-l-2 border-accent">
          <p class="text-definition mb-2">
            {{ definition.definition }}
          </p>

          <!-- Examples -->
          <div v-if="definition.examples && (definition.examples.generated.length > 0 || definition.examples.literature.length > 0)" class="space-y-1 mb-2">
            <p 
              v-for="(example, exIndex) in definition.examples.generated.concat(definition.examples.literature)"
              :key="exIndex"
              class="text-sm text-muted-foreground/70 italic"
              v-html="`&quot;${formatExampleHTML(example.sentence, entry.word)}&quot;`"
            ></p>
          </div>

          <!-- Synonyms -->
          <div v-if="definition.synonyms && definition.synonyms.length > 0" class="flex flex-wrap gap-1 pt-2">
            <span class="text-xs text-muted-foreground self-center pr-2">Synonyms:</span>
            <Badge
              v-for="synonym in definition.synonyms"
              :key="synonym"
              variant="outline"
              class="text-xs cursor-pointer transition-all duration-200 hover:opacity-80 hover:bg-accent/50 hover:font-semibold"
              @click="store.searchWord(synonym)"
            >
              {{ synonym }}
            </Badge>
          </div>
        </div>
      </div>
    </CardContent>

    <!-- Thesaurus Mode -->
    <CardContent v-if="mode === 'thesaurus' && thesaurusData" class="space-y-6 pt-6">
      <div v-if="thesaurusData.synonyms.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <Card
          v-for="synonym in thesaurusData.synonyms"
          :key="synonym.word"
          :class="cn(
            'cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-105',
            getHeatmapClass(synonym.score)
          )"
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
      <p class="text-sm text-muted-foreground">{{ entry.etymology }}</p>
    </CardContent>
  </ThemedCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { cn, getHeatmapClass } from '@/utils';
import Button from '@/components/ui/Button.vue';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Badge from '@/components/ui/Badge.vue';
import ThemedCard from '@/components/ui/ThemedCard.vue';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface DefinitionDisplayProps {
  variant?: CardVariant;
}

const props = withDefaults(defineProps<DefinitionDisplayProps>(), {
  variant: 'default'
});

const store = useAppStore();

const entry = computed(() => store.currentEntry);
const thesaurusData = computed(() => store.currentThesaurus);
const mode = computed(() => store.mode);
const pronunciationMode = computed(() => store.pronunciationMode);

const toggleMode = () => {
  store.toggleMode();
};

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
  return example.replace(regex, `<strong>${word}</strong>`);
};

</script>