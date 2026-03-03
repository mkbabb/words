<template>
  <div class="space-y-2 py-2">
    <!-- Flat definition list matching AI Synthesis style -->
    <template
      v-for="(def, index) in provider.definitions"
      :key="def.id || index"
    >
      <hr v-if="index > 0" class="my-2 border-border/50" />

      <div class="space-y-2">
        <!-- POS heading + superscript number -->
        <div class="flex items-center gap-2">
          <span class="text-2xl font-semibold text-primary">
            {{ def.part_of_speech || 'other' }}
          </span>
          <sup class="text-sm font-normal text-muted-foreground">{{
            index + 1
          }}</sup>
        </div>

        <!-- Definition text with left border accent -->
        <div class="border-l-2 border-accent pl-4">
          <p class="font-serif text-base leading-relaxed">
            {{ def.text }}
          </p>

          <!-- Synonyms -->
          <div
            v-if="def.synonyms?.length"
            class="mt-2 flex flex-wrap gap-1"
          >
            <span
              v-for="syn in def.synonyms"
              :key="syn"
              class="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
            >
              {{ syn }}
            </span>
          </div>
        </div>
      </div>
    </template>

    <!-- Etymology (shown below definitions, matching AI Synthesis layout) -->
    <div v-if="provider.etymology?.text" class="border-t border-border/50 pt-4">
      <h3 class="mb-3 font-serif text-xl font-semibold">Etymology</h3>
      <blockquote class="border-l-2 border-accent pl-4">
        <p class="font-serif text-base leading-relaxed">
          {{ provider.etymology.text }}
        </p>
      </blockquote>
    </div>

    <!-- Empty state -->
    <div
      v-if="!provider.definitions.length"
      class="py-4 text-center text-sm text-muted-foreground"
    >
      No definitions available from this provider.
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProviderEntry } from '@/api/providers';

interface Props {
  provider: ProviderEntry;
}

defineProps<Props>();
</script>
