<template>
    <div
        v-if="synonyms && synonyms.length > 0"
        class="mt-5 flex flex-wrap gap-1.5"
    >
        <span
            v-for="(synonym, index) in synonyms"
            :key="index"
            class="group relative cursor-pointer rounded-md border border-border/50 bg-muted/50 px-2 py-1 text-sm text-foreground/80 transition-fast hover:border-border hover:bg-muted hover:text-foreground"
            @click="!editMode && $emit('synonym-click', synonym)"
            @dblclick="editMode && editSynonym(index)"
        >
            {{ synonym }}

            <!-- Edit/Delete buttons -->
            <span
                v-if="editMode"
                class="pointer-events-none absolute -top-2 -right-2 flex gap-0.5 opacity-0 transition-opacity duration-150 group-hover:opacity-100"
            >
                <button
                    @click.stop="editSynonym(index)"
                    class="pointer-events-auto rounded-full border border-border bg-background p-0.5 shadow-sm transition-colors hover:bg-muted"
                    title="Edit synonym"
                >
                    <Edit2 class="h-3.5 w-3.5 text-muted-foreground" />
                </button>
                <button
                    @click.stop="deleteSynonym(index)"
                    class="pointer-events-auto rounded-full border border-border bg-background p-0.5 shadow-sm transition-colors hover:border-destructive hover:bg-destructive hover:text-destructive-foreground"
                    title="Delete synonym"
                >
                    <X class="h-3.5 w-3.5 text-muted-foreground" />
                </button>
            </span>
        </span>

        <!-- Add / Regenerate — inline with synonym pills -->
        <span v-if="editMode" class="inline-flex items-center gap-1">
            <button
                @click="addSynonym"
                class="flex h-7 w-7 items-center justify-center rounded-full border border-border/40 bg-background text-muted-foreground shadow-sm transition-micro hover:border-border hover:bg-muted hover:text-foreground hover:scale-110"
                title="Add synonym"
            >
                <Plus class="h-3.5 w-3.5" />
            </button>
            <button
                v-if="canRegenerate"
                @click="$emit('regenerate')"
                :disabled="isRegenerating"
                class="flex h-7 w-7 items-center justify-center rounded-full border border-border/40 bg-background text-muted-foreground shadow-sm transition-micro hover:border-border hover:bg-muted hover:text-foreground hover:scale-110 disabled:opacity-50 disabled:hover:scale-100"
                title="Regenerate synonyms"
            >
                <RefreshCw :class="['h-3.5 w-3.5', isRegenerating && 'animate-spin']" />
            </button>
        </span>
    </div>

    <!-- Edit dialog -->
    <div
        v-if="editingIndex !== null"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
        <div
            class="w-full max-w-sm rounded-lg border border-border bg-background p-4 shadow-lg"
        >
            <h3 class="mb-2 text-sm font-medium">Edit Synonym</h3>
            <input
                v-model="editingValue"
                @keydown.enter="saveEdit"
                @keydown.escape="cancelEdit"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:outline-none"
                placeholder="Enter synonym..."
                ref="editInput"
            />
            <div class="mt-3 flex justify-end gap-2">
                <button
                    @click="cancelEdit"
                    class="rounded-md px-3 py-1 text-sm hover:bg-muted"
                >
                    Cancel
                </button>
                <button
                    @click="saveEdit"
                    class="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground hover:bg-primary/90"
                >
                    Save
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { Edit2, X, Plus, RefreshCw } from 'lucide-vue-next';

interface Props {
    synonyms: string[];
    editMode?: boolean;
    canRegenerate?: boolean;
    isRegenerating?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'update:synonyms': [synonyms: string[]];
    regenerate: [];
    'synonym-click': [synonym: string];
}>();

const editingIndex = ref<number | null>(null);
const editingValue = ref('');
const editInput = ref<HTMLInputElement>();

function editSynonym(index: number) {
    editingIndex.value = index;
    editingValue.value = props.synonyms[index];
    nextTick(() => {
        editInput.value?.focus();
        editInput.value?.select();
    });
}

function saveEdit() {
    if (editingIndex.value !== null && editingValue.value.trim()) {
        const newSynonyms = [...props.synonyms];
        newSynonyms[editingIndex.value] = editingValue.value.trim();
        emit('update:synonyms', newSynonyms);
    }
    cancelEdit();
}

function cancelEdit() {
    editingIndex.value = null;
    editingValue.value = '';
}

function deleteSynonym(index: number) {
    const newSynonyms = props.synonyms.filter((_, i) => i !== index);
    emit('update:synonyms', newSynonyms);
}

function addSynonym() {
    const newSynonyms = [...props.synonyms, 'new synonym'];
    emit('update:synonyms', newSynonyms);
    // Immediately edit the new synonym
    nextTick(() => {
        editSynonym(newSynonyms.length - 1);
    });
}
</script>
