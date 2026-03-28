<template>
    <div
        @drop="onDrop"
        @dragover.prevent="isDragging = true"
        @dragenter.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        :class="[
            'relative flex min-h-[56svh] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition-spring sm:p-10',
            isDragging
                ? 'border-primary bg-primary/8 shadow-cartoon-sm scale-[1.01]'
                : 'border-muted-foreground/25 bg-background/40 hover:border-muted-foreground/45 hover:bg-background/55',
        ]"
        @click="fileInput?.click()"
    >
        <button
            type="button"
            class="group/info absolute right-4 top-4 z-content inline-flex h-8 w-8 items-center justify-center rounded-full glass-subtle text-muted-foreground shadow-sm transition-fast hover:text-foreground"
            aria-label="Supported formats"
            @click.stop
        >
            <Info class="h-4 w-4" />
            <div
                class="pointer-events-none absolute right-0 top-10 z-controls w-64 translate-y-1 opacity-0 transition-fast group-hover/info:translate-y-0 group-hover/info:opacity-100"
            >
                <div class="popover-surface space-y-2 p-3 text-left text-xs">
                    <p class="font-medium text-foreground">Supported formats</p>
                    <ul class="space-y-1 text-muted-foreground">
                        <li><span class="font-medium text-foreground">.txt</span> One word per line</li>
                        <li><span class="font-medium text-foreground">.csv</span> word,frequency,notes</li>
                        <li><span class="font-medium text-foreground">.json</span> Array of words or word objects</li>
                    </ul>
                </div>
            </div>
        </button>

        <input
            ref="fileInput"
            type="file"
            accept=".txt,.csv,.json"
            @change="onFileChange"
            class="hidden"
            multiple
        />

        <div class="space-y-4">
            <div class="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary shadow-sm">
                <Upload class="h-8 w-8" />
            </div>
            <div class="space-y-1">
                <p class="text-subheading">
                    Drop wordlist files here
                </p>
                <p class="text-sm text-muted-foreground">
                    or click to browse your device
                </p>
            </div>
            <p
                v-if="uploadedFiles.length > 0"
                class="inline-flex items-center rounded-full bg-muted/70 px-3 py-1 text-xs font-medium text-muted-foreground"
            >
                {{ uploadedFiles.length }} file{{ uploadedFiles.length === 1 ? '' : 's' }} ready
            </p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Info, Upload } from 'lucide-vue-next';

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
