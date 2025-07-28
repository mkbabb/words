<template>
    <div v-if="synonyms && synonyms.length > 0" class="flex flex-wrap gap-1.5 mt-5">
        <span
            v-for="(synonym, index) in synonyms"
            :key="index"
            class="group relative text-sm px-2 py-1 rounded-md bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground cursor-pointer transition-all duration-200 border border-border/50 hover:border-border"
            @click="!editMode && $emit('synonym-click', synonym)"
            @dblclick="editMode && editSynonym(index)"
        >
            {{ synonym }}
            
            <!-- Edit/Delete buttons -->
            <span
                v-if="editMode"
                class="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-150 flex gap-0.5 pointer-events-none"
            >
                <button
                    @click.stop="editSynonym(index)"
                    class="pointer-events-auto rounded-full bg-background border border-border p-0.5 shadow-sm hover:bg-muted transition-colors"
                    title="Edit synonym"
                >
                    <Edit2 class="h-2.5 w-2.5 text-muted-foreground" />
                </button>
                <button
                    @click.stop="deleteSynonym(index)"
                    class="pointer-events-auto rounded-full bg-background border border-border p-0.5 shadow-sm hover:bg-destructive hover:text-destructive-foreground hover:border-destructive transition-colors"
                    title="Delete synonym"
                >
                    <X class="h-2.5 w-2.5 text-muted-foreground" />
                </button>
            </span>
        </span>
        
        <!-- Add synonym button -->
        <button
            v-if="editMode"
            @click="addSynonym"
            class="text-sm px-2 py-1 rounded-md bg-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-all duration-200 border border-dashed border-border/50 hover:border-border"
        >
            <Plus class="h-3 w-3" />
        </button>
        
        <!-- Regenerate button -->
        <button
            v-if="editMode && canRegenerate"
            @click="$emit('regenerate')"
            :disabled="isRegenerating"
            class="text-sm px-2 py-1 rounded-md bg-transparent hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-all duration-200 border border-dashed border-border/50 hover:border-border disabled:opacity-50"
        >
            <RefreshCw :class="['h-3 w-3', isRegenerating && 'animate-spin']" />
        </button>
    </div>
    
    <!-- Edit dialog -->
    <div v-if="editingIndex !== null" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
        <div class="bg-background border border-border rounded-lg p-4 shadow-lg max-w-sm w-full">
            <h3 class="text-sm font-medium mb-2">Edit Synonym</h3>
            <input
                v-model="editingValue"
                @keydown.enter="saveEdit"
                @keydown.escape="cancelEdit"
                class="w-full px-3 py-2 text-sm border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                placeholder="Enter synonym..."
                ref="editInput"
            />
            <div class="flex justify-end gap-2 mt-3">
                <button
                    @click="cancelEdit"
                    class="px-3 py-1 text-sm rounded-md hover:bg-muted"
                >
                    Cancel
                </button>
                <button
                    @click="saveEdit"
                    class="px-3 py-1 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
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
    'regenerate': [];
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