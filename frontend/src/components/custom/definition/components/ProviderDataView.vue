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
          <EditableField
            v-if="editModeEnabled"
            :model-value="def.part_of_speech || 'other'"
            field-name="part of speech"
            :edit-mode="editModeEnabled"
            @update:model-value="(val: string | number | string[]) => handleFieldUpdate(def, 'part_of_speech', String(val))"
          >
            <template #display>
              <span class="text-2xl font-semibold text-primary">
                {{ def.part_of_speech || 'other' }}
              </span>
            </template>
          </EditableField>
          <span v-else class="text-2xl font-semibold text-primary">
            {{ def.part_of_speech || 'other' }}
          </span>
          <sup class="text-sm font-normal text-muted-foreground">{{
            index + 1
          }}</sup>
        </div>

        <!-- Definition text with left border accent -->
        <div class="border-l-2 border-accent pl-4">
          <EditableField
            v-if="editModeEnabled"
            :model-value="def.text"
            field-name="definition"
            :multiline="true"
            :edit-mode="editModeEnabled"
            @update:model-value="(val: string | number | string[]) => handleFieldUpdate(def, 'text', String(val))"
          >
            <template #display>
              <p class="font-serif text-base leading-relaxed">
                {{ def.text }}
              </p>
            </template>
          </EditableField>
          <p v-else class="font-serif text-base leading-relaxed">
            {{ def.text }}
          </p>

          <!-- Examples -->
          <div
            v-if="def.examples?.length"
            class="mt-3 space-y-2"
          >
            <div class="text-sm font-medium text-muted-foreground">Examples</div>
            <div
              v-for="(example, exIdx) in def.examples"
              :key="exIdx"
              class="rounded bg-muted/30 px-3 py-2"
            >
              <EditableField
                v-if="editModeEnabled"
                :model-value="example.text"
                field-name="example"
                :edit-mode="editModeEnabled"
                :can-regenerate="false"
                @update:model-value="(val: string | number | string[]) => handleExampleUpdate(def, exIdx, String(val))"
              >
                <template #display>
                  <p class="text-sm italic text-foreground/80">
                    {{ example.text }}
                  </p>
                </template>
              </EditableField>
              <p v-else class="text-sm italic text-foreground/80">
                {{ example.text }}
              </p>
              <span
                v-if="example.source"
                class="mt-0.5 block text-xs text-muted-foreground"
              >
                — {{ example.source }}
              </span>
            </div>
          </div>

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
      <h3 class="mb-3 text-subheading">Etymology</h3>
      <div class="rounded-md border border-border/30 bg-muted/5 px-3 py-2 transition-fast hover:border-border/50 hover:bg-muted/10">
        <EditableField
          v-if="editModeEnabled"
          :model-value="provider.etymology.text"
          field-name="etymology"
          :multiline="true"
          :edit-mode="editModeEnabled"
          :can-regenerate="false"
        >
          <template #display>
            <p class="font-serif text-base leading-relaxed">
              {{ provider.etymology.text }}
            </p>
          </template>
        </EditableField>
        <p v-else class="font-serif text-base leading-relaxed">
          {{ provider.etymology.text }}
        </p>
      </div>
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
import { useContentMutations } from '../composables/useContentMutations';
import EditableField from './editing/EditableField.vue';
import { logger } from '@/utils/logger';

interface Props {
  provider: ProviderEntry;
  editModeEnabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  editModeEnabled: false,
});

const mutations = useContentMutations();

type ProviderDefinition = ProviderEntry['definitions'][number];

async function handleFieldUpdate(
  def: ProviderDefinition,
  field: 'text' | 'part_of_speech',
  value: string
) {
  if (!def.id) {
    logger.warn('[ProviderDataView] Definition has no ID, cannot update');
    return;
  }
  try {
    await mutations.updateDefinition(def.id, { [field]: value });
  } catch (error) {
    logger.error('[ProviderDataView] Failed to update definition:', error);
  }
}

async function handleExampleUpdate(
  def: ProviderDefinition,
  exampleIndex: number,
  value: string
) {
  if (!def.id) {
    logger.warn('[ProviderDataView] Definition has no ID, cannot update example');
    return;
  }
  const example = def.examples?.[exampleIndex];
  if (!example) return;

  // Update via the examples API if available, otherwise patch the definition
  try {
    const exampleWithId = example as { text: string; source?: string; id?: string };
    if (exampleWithId.id) {
      await mutations.updateExample(def.id, exampleWithId.id, value);
    } else {
      // Fallback: update the example text in-place via definition patch
      const updatedExamples = [...def.examples];
      updatedExamples[exampleIndex] = { ...example, text: value };
      await mutations.updateDefinition(def.id, {
        examples: updatedExamples as any,
      });
    }
  } catch (error) {
    logger.error('[ProviderDataView] Failed to update example:', error);
  }
}
</script>
