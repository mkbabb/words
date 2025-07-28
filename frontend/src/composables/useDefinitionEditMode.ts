import { ref, reactive, computed, watch, toRaw, type Ref } from 'vue';
import { useAppStore } from '@/stores';
import type { Definition, DefinitionResponse } from '@/types/api';
import { useDebounce } from '@vueuse/core';

interface EditableField<T = any> {
  value: T;
  originalValue: T;
  isDirty: boolean;
  errors: string[];
  touched: boolean;
  isRegenerating?: boolean;
}

interface EditModeOptions {
  autosave?: boolean;
  debounceMs?: number;
  onSave?: (data: Partial<Definition>) => Promise<void>;
  onCancel?: () => void;
  onRegenerate?: (component: string) => Promise<void>;
  validation?: Record<string, (value: any) => string | undefined>;
}

// AI-regeneratable components
const REGENERATABLE_COMPONENTS = new Set([
  'synonyms',
  'antonyms',
  'examples',
  'cefr_level',
  'frequency_band',
  'language_register',
  'domain',
  'grammar_patterns',
  'collocations',
  'usage_notes',
  'regional_variants'
]);

export function useDefinitionEditMode(
  definition: Ref<Definition | DefinitionResponse>,
  options: EditModeOptions = {}
) {
  const store = useAppStore();
  const { debounceMs = 500 } = options;

  // Core state
  const isEditMode = ref(false);
  const isSaving = ref(false);
  const activeFieldId = ref<string | null>(null);
  
  // Editable fields matching backend Definition model
  const fields = reactive<{
    text: EditableField<string>;
    part_of_speech: EditableField<string>;
    cefr_level: EditableField<'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | null>;
    language_register: EditableField<'formal' | 'informal' | 'neutral' | 'slang' | 'technical' | null>;
    synonyms: EditableField<string[]>;
    meaning_cluster_name: EditableField<string | null>;
  }>({
    text: createField(definition.value.text),
    part_of_speech: createField(definition.value.part_of_speech),
    cefr_level: createField(definition.value.cefr_level ?? null),
    language_register: createField(definition.value.language_register ?? null),
    synonyms: createField(definition.value.synonyms || []),
    meaning_cluster_name: createField(definition.value.meaning_cluster?.name ?? null),
  });

  // Helper to create field
  function createField<T>(value: T): EditableField<T> {
    return {
      value: structuredClone(toRaw(value)),
      originalValue: structuredClone(toRaw(value)),
      isDirty: false,
      errors: [],
      touched: false,
    };
  }

  // Track overall dirty state
  const isDirty = computed(() => 
    Object.values(fields).some(field => field.isDirty)
  );

  // Track validation state
  const hasErrors = computed(() =>
    Object.values(fields).some(field => field.errors.length > 0)
  );

  // Watch for changes and mark as dirty
  Object.keys(fields).forEach(key => {
    watch(() => fields[key as keyof typeof fields].value, (newVal) => {
      const field = fields[key as keyof typeof fields];
      field.touched = true;
      field.isDirty = JSON.stringify(newVal) !== JSON.stringify(field.originalValue);
      
      // Run validation if provided
      if (options.validation?.[key]) {
        const error = options.validation[key](newVal);
        field.errors = error ? [error] : [];
      }
    }, { deep: true });
  });

  // Debounced autosave
  const debouncedSave = useDebounce(async () => {
    if (options.autosave && isDirty.value && !hasErrors.value) {
      await save();
    }
  }, debounceMs);

  // Watch for changes to trigger autosave
  if (options.autosave) {
    watch(() => Object.values(fields).map(f => f.value), () => {
      debouncedSave();
    }, { deep: true });
  }

  // Start edit mode
  function startEdit() {
    isEditMode.value = true;
    // Reset fields to current definition values
    fields.text.value = definition.value.text;
    fields.text.originalValue = fields.text.value;
    fields.part_of_speech.value = definition.value.part_of_speech;
    fields.part_of_speech.originalValue = fields.part_of_speech.value;
    fields.cefr_level.value = definition.value.cefr_level ?? null;
    fields.cefr_level.originalValue = fields.cefr_level.value;
    fields.language_register.value = definition.value.language_register ?? null;
    fields.language_register.originalValue = fields.language_register.value;
    fields.synonyms.value = [...(definition.value.synonyms || [])];
    fields.synonyms.originalValue = [...fields.synonyms.value];
    fields.meaning_cluster_name.value = definition.value.meaning_cluster?.name ?? null;
    fields.meaning_cluster_name.originalValue = fields.meaning_cluster_name.value;
  }

  // Cancel edit mode
  function cancel() {
    if (options.onCancel) {
      options.onCancel();
    }
    
    // Revert all fields
    Object.keys(fields).forEach(key => {
      const field = fields[key as keyof typeof fields];
      field.value = structuredClone(field.originalValue);
      field.isDirty = false;
      field.errors = [];
      field.touched = false;
    });
    
    isEditMode.value = false;
    activeFieldId.value = null;
  }

  // Save changes
  async function save() {
    console.log('[useDefinitionEditMode] save() called');
    console.log('[useDefinitionEditMode] hasErrors:', hasErrors.value, 'isDirty:', isDirty.value);
    console.log('[useDefinitionEditMode] fields.text.isDirty:', fields.text.isDirty, 'value:', fields.text.value);
    
    if (hasErrors.value || !isDirty.value) {
      console.log('[useDefinitionEditMode] Skipping save - hasErrors or not dirty');
      return;
    }

    isSaving.value = true;

    try {
      // Prepare update data
      const updateData: Partial<Definition> = {};
      
      if (fields.text.isDirty) {
        updateData.text = fields.text.value;
      }
      if (fields.part_of_speech.isDirty) {
        updateData.part_of_speech = fields.part_of_speech.value;
      }
      if (fields.cefr_level.isDirty) {
        updateData.cefr_level = fields.cefr_level.value || undefined;
      }
      if (fields.language_register.isDirty) {
        updateData.language_register = fields.language_register.value || undefined;
      }
      if (fields.synonyms.isDirty) {
        updateData.synonyms = fields.synonyms.value;
      }
      if (fields.meaning_cluster_name.isDirty && fields.meaning_cluster_name.value !== null) {
        updateData.meaning_cluster = {
          ...(definition.value.meaning_cluster || {}),
          name: fields.meaning_cluster_name.value
        };
      }

      console.log('[useDefinitionEditMode] updateData:', updateData);

      // Call save handler or default store method
      if (options.onSave) {
        console.log('[useDefinitionEditMode] Calling onSave handler');
        await options.onSave(updateData);
      } else {
        console.log('[useDefinitionEditMode] Calling default store method');
        await store.updateDefinition(definition.value.id, updateData);
      }

      // Update original values on success
      Object.keys(fields).forEach(key => {
        const field = fields[key as keyof typeof fields];
        // Handle arrays and objects differently to avoid structuredClone issues
        if (Array.isArray(field.value)) {
          field.originalValue = [...field.value];
        } else if (typeof field.value === 'object' && field.value !== null) {
          field.originalValue = { ...field.value };
        } else {
          field.originalValue = field.value;
        }
        field.isDirty = false;
      });

      isEditMode.value = false;
      activeFieldId.value = null;
    } catch (error) {
      console.error('Failed to save definition:', error);
      throw error;
    } finally {
      isSaving.value = false;
    }
  }

  // Add synonym
  function addSynonym(synonym: string) {
    if (synonym && !fields.synonyms.value.includes(synonym)) {
      fields.synonyms.value = [...fields.synonyms.value, synonym];
    }
  }

  // Remove synonym
  function removeSynonym(index: number) {
    fields.synonyms.value = fields.synonyms.value.filter((_, i) => i !== index);
  }

  // Keyboard shortcut handler
  function handleKeydown(event: KeyboardEvent) {
    if (!isEditMode.value) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      cancel();
    } else if ((event.metaKey || event.ctrlKey) && event.key === 's') {
      event.preventDefault();
      save();
    }
  }

  // Regenerate AI component
  async function regenerateComponent(component: string) {
    if (!REGENERATABLE_COMPONENTS.has(component)) {
      console.warn(`Component ${component} is not regeneratable`);
      return;
    }

    const field = fields[component as keyof typeof fields];
    if (!field) return;

    field.isRegenerating = true;

    try {
      if (options.onRegenerate) {
        await options.onRegenerate(component);
      } else {
        await store.regenerateDefinitionComponent(definition.value.id, component);
      }

      // Refresh definition data
      const updated = await store.fetchDefinition(definition.value.id);
      if (updated) {
        // Update field with new value
        const newValue = updated[component as keyof Definition];
        field.value = structuredClone(toRaw(newValue));
        field.originalValue = structuredClone(toRaw(newValue));
        field.isDirty = false;
      }
    } catch (error) {
      console.error(`Failed to regenerate ${component}:`, error);
      throw error;
    } finally {
      field.isRegenerating = false;
    }
  }

  // Check if component can be regenerated
  function canRegenerate(component: string): boolean {
    return REGENERATABLE_COMPONENTS.has(component);
  }

  return {
    // State
    isEditMode,
    isSaving,
    isDirty,
    hasErrors,
    fields,
    activeFieldId,
    
    // Actions
    startEdit,
    cancel,
    save,
    addSynonym,
    removeSynonym,
    handleKeydown,
    regenerateComponent,
    canRegenerate,
    
    // Constants
    REGENERATABLE_COMPONENTS,
  };
}