<template>
    <div class="space-y-4">
        <div
            @drop="onDrop"
            @dragover.prevent
            @dragenter.prevent
            :class="[
                'cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors',
                isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-muted-foreground/25 hover:border-muted-foreground/50',
            ]"
            @click="fileInput?.click()"
        >
            <input
                ref="fileInput"
                type="file"
                accept=".txt,.csv,.json"
                @change="onFileChange"
                class="hidden"
                multiple
            />

            <div class="space-y-2">
                <Upload class="mx-auto h-8 w-8 text-muted-foreground" />
                <div>
                    <p class="font-medium">
                        Drop files here or click to browse
                    </p>
                    <p class="text-sm text-muted-foreground">
                        Supports .txt, .csv, and .json files
                    </p>
                </div>
            </div>
        </div>

        <!-- File Format Instructions -->
        <div class="space-y-1 text-xs text-muted-foreground">
            <p><strong>Supported formats:</strong></p>
            <ul class="ml-2 list-inside list-disc space-y-0.5">
                <li><strong>.txt:</strong> One word per line</li>
                <li>
                    <strong>.csv:</strong> word,frequency,notes (headers
                    optional)
                </li>
                <li><strong>.json:</strong> Array of words or word objects</li>
            </ul>
        </div>

        <!-- File Preview -->
        <div v-if="uploadedFiles.length > 0" class="space-y-3">
            <h3 class="font-medium">Uploaded Files</h3>
            <div class="max-h-32 space-y-2 overflow-y-auto">
                <div
                    v-for="file in uploadedFiles"
                    :key="file.name"
                    class="flex items-center justify-between rounded-md bg-muted/50 p-2"
                >
                    <div class="flex items-center gap-2">
                        <FileText class="h-4 w-4" />
                        <span class="text-sm">{{ file.name }}</span>
                    </div>
                    <Button
                        @click="$emit('remove-file', file)"
                        variant="ghost"
                        size="sm"
                        class="h-6 w-6 p-0"
                    >
                        <X class="h-3 w-3" />
                    </Button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Upload, X, FileText } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';

defineProps<{
    uploadedFiles: File[];
}>();

const emit = defineEmits<{
    'add-files': [files: File[]];
    'remove-file': [file: File];
}>();

const fileInput = ref<HTMLInputElement>();
const isDragging = ref(false);

const onDrop = (event: DragEvent) => {
    event.preventDefault();
    isDragging.value = false;

    const files = Array.from(event.dataTransfer?.files || []);
    emit('add-files', files);
};

const onFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = Array.from(target.files || []);
    emit('add-files', files);
};
</script>
