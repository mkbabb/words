<template>
  <div v-if="entry" class="space-y-8">
    <!-- Word Header -->
    <Card>
      <CardHeader>
        <div class="flex items-center justify-between">
          <CardTitle class="text-word-title">{{ entry.word }}</CardTitle>
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              @click="toggleMode"
            >
              {{ mode === 'dictionary' ? 'Thesaurus' : 'Dictionary' }}
            </Button>
          </div>
        </div>

        <!-- Pronunciation -->
        <div v-if="entry.pronunciation" class="flex items-center gap-4 pt-2">
          <span class="text-pronunciation">
            {{ pronunciationMode === 'phonetic' 
              ? entry.pronunciation.phonetic 
              : entry.pronunciation.ipa 
            }}
          </span>
          <Button
            variant="ghost"
            size="sm"
            @click="togglePronunciation"
            class="text-xs"
          >
            {{ pronunciationMode === 'phonetic' ? 'Show IPA' : 'Show Phonetic' }}
          </Button>
        </div>
      </CardHeader>
    </Card>

    <!-- Dictionary Mode -->
    <div v-if="mode === 'dictionary'" class="space-y-6">
      <Card
        v-for="(meaning, index) in entry.meanings"
        :key="index"
      >
        <CardHeader>
          <div class="flex items-center gap-2">
            <Badge variant="secondary" class="text-part-of-speech">
              {{ meaning.partOfSpeech }}
            </Badge>
            <sup class="text-xs font-normal text-muted-foreground">{{ index + 1 }}</sup>
          </div>
        </CardHeader>
        
        <CardContent class="space-y-4">
          <div
            v-for="(definition, defIndex) in meaning.definitions"
            :key="definition.id"
            class="space-y-3"
          >
            <div class="pl-4 border-l-2 border-accent">
              <p class="text-definition mb-2">
                {{ definition.text }}
              </p>

              <!-- Example -->
              <p v-if="definition.example" class="text-sm text-muted-foreground italic mb-2">
                "{{ definition.example }}"
              </p>

              <!-- Synonyms -->
              <div v-if="definition.synonyms && definition.synonyms.length > 0" class="flex flex-wrap gap-1">
                <span class="text-xs text-muted-foreground">Synonyms:</span>
                <Badge
                  v-for="synonym in definition.synonyms"
                  :key="synonym"
                  variant="outline"
                  class="text-xs cursor-pointer hover:bg-accent"
                  @click="searchWord(synonym)"
                >
                  {{ synonym }}
                </Badge>
              </div>
            </div>
            
            <Separator v-if="defIndex < meaning.definitions.length - 1" />
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Thesaurus Mode -->
    <div v-if="mode === 'thesaurus' && thesaurusData" class="space-y-6">
      <!-- Synonyms -->
      <Card v-if="thesaurusData.synonyms.length > 0">
        <CardHeader>
          <CardTitle>Synonyms</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            <Card
              v-for="synonym in thesaurusData.synonyms"
              :key="synonym.word"
              :class="cn(
                'cursor-pointer transition-all hover:shadow-md',
                getHeatmapClass(synonym.similarity)
              )"
              @click="searchWord(synonym.word)"
            >
              <CardContent class="p-3">
                <div class="font-medium">{{ synonym.word }}</div>
                <div class="text-xs opacity-75">
                  {{ Math.round(synonym.similarity * 100) }}% similar
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      <!-- Antonyms -->
      <Card v-if="thesaurusData.antonyms.length > 0">
        <CardHeader>
          <CardTitle>Antonyms</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            <Card
              v-for="antonym in thesaurusData.antonyms"
              :key="antonym.word"
              class="cursor-pointer transition-all hover:shadow-md bg-secondary hover:bg-secondary/80"
              @click="searchWord(antonym.word)"
            >
              <CardContent class="p-3">
                <div class="font-medium">{{ antonym.word }}</div>
                <div class="text-xs opacity-75">
                  {{ antonym.partOfSpeech }}
                </div>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Etymology -->
    <Card v-if="entry.etymology">
      <CardHeader>
        <CardTitle>Etymology</CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-sm text-muted-foreground">{{ entry.etymology }}</p>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { useSearch } from '@/composables/useSearch';
import { cn, getHeatmapClass } from '@/utils';
import Button from '@/components/ui/Button.vue';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import Badge from '@/components/ui/Badge.vue';
import Separator from '@/components/ui/Separator.vue';

const store = useAppStore();
const { searchWord } = useSearch();

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
</script>