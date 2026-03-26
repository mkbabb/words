<template>
    <Dialog :open="show" @update:open="handleOpenChange">
        <DialogContent
            class="max-w-2xl"
            @close-auto-focus.prevent
        >
            <div class="mb-4 flex items-center justify-between">
                <h3 class="text-subheading">
                    Describe what you're looking for
                </h3>
            </div>

            <Textarea
                ref="expandedTextarea"
                v-model="localQuery"
                class="min-h-[200px] bg-background/60 text-lg"
                :placeholder="placeholder"
                @keydown.escape="handleClose"
                @keydown.cmd.enter="handleSubmit"
                @keydown.ctrl.enter="handleSubmit"
            />

            <div class="mt-4 flex items-center justify-between">
                <p class="text-sm text-muted-foreground">
                    Press
                    <kbd class="rounded border px-1.5 py-0.5 text-xs">⌘</kbd>
                    +
                    <kbd class="rounded border px-1.5 py-0.5 text-xs">Enter</kbd>
                    to search
                </p>
                <div class="flex gap-2">
                    <Button variant="outline" @click="handleClose">
                        Cancel
                    </Button>
                    <Button variant="default" @click="handleSubmit">
                        Search
                    </Button>
                </div>
            </div>
        </DialogContent>
    </Dialog>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { Button } from '@/components/ui';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface ExpandModalProps {
    show: boolean;
    initialQuery: string;
}

const props = defineProps<ExpandModalProps>();

const emit = defineEmits<{
    close: [];
    submit: [query: string];
}>();

const localQuery = ref('');
const expandedTextarea = ref<{ $el?: HTMLTextAreaElement } | HTMLTextAreaElement>();

const placeholder = `Examples:
• Words that mean someone who's really dedicated to their craft
• I need a word for someone who pays attention to every tiny detail
• What's a good word for stubborn but in a mean way`;

watch(
    () => props.show,
    (newVal) => {
        if (newVal) {
            localQuery.value = props.initialQuery;
            nextTick(() => {
                const textarea =
                    expandedTextarea.value instanceof HTMLTextAreaElement
                        ? expandedTextarea.value
                        : expandedTextarea.value?.$el;
                textarea?.focus();
                textarea?.setSelectionRange(
                    localQuery.value.length,
                    localQuery.value.length
                );
            });
        }
    }
);

const handleOpenChange = (open: boolean) => {
    if (!open) {
        handleClose();
    }
};

const handleClose = () => {
    emit('close');
};

const handleSubmit = () => {
    emit('submit', localQuery.value);
};
</script>
