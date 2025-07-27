<template>
    <Teleport to="body">
        <Transition
            :css="false"
            @enter="modalEnter"
            @leave="modalLeave"
        >
            <div
                v-if="show"
                class="fixed inset-0 z-[100] flex items-center justify-center p-4"
                @click="handleClose"
            >
                <!-- Backdrop -->
                <div 
                    ref="modalBackdrop"
                    class="absolute inset-0 bg-black/60 backdrop-blur-sm" 
                />
                
                <!-- Modal Content -->
                <div
                    ref="modalContent"
                    class="relative w-full max-w-2xl rounded-2xl border-2 border-border bg-background p-6 shadow-2xl cartoon-shadow-lg"
                    @click.stop
                >
                    <!-- Header -->
                    <div class="mb-4 flex items-center justify-between">
                        <h3 class="text-lg font-semibold">Describe what you're looking for</h3>
                        <button
                            class="rounded-lg p-2 hover:bg-accent/50 transition-colors"
                            @click="handleClose"
                        >
                            <X class="h-5 w-5" />
                        </button>
                    </div>
                    
                    <!-- Expanded Textarea -->
                    <textarea
                        ref="expandedTextarea"
                        v-model="localQuery"
                        class="w-full min-h-[200px] rounded-xl border border-border bg-background/50 p-4 text-lg outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                        :placeholder="placeholder"
                        @keydown.escape="handleClose"
                        @keydown.cmd.enter="handleSubmit"
                        @keydown.ctrl.enter="handleSubmit"
                    />
                    
                    <!-- Footer -->
                    <div class="mt-4 flex items-center justify-between">
                        <p class="text-sm text-muted-foreground">
                            Press <kbd class="px-1.5 py-0.5 text-xs border rounded">⌘</kbd> + <kbd class="px-1.5 py-0.5 text-xs border rounded">Enter</kbd> to search
                        </p>
                        <div class="flex gap-2">
                            <Button
                                variant="outline"
                                @click="handleClose"
                            >
                                Cancel
                            </Button>
                            <Button
                                variant="default"
                                @click="handleSubmit"
                            >
                                Search
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { X } from 'lucide-vue-next';
import { Button } from '@/components/ui';

interface ExpandModalProps {
    show: boolean;
    initialQuery: string;
}

const props = defineProps<ExpandModalProps>();

const emit = defineEmits<{
    'close': [];
    'submit': [query: string];
}>();

const localQuery = ref('');
const expandedTextarea = ref<HTMLTextAreaElement>();
const modalBackdrop = ref<HTMLDivElement>();
const modalContent = ref<HTMLDivElement>();

const placeholder = `Examples:
• Words that mean someone who's really dedicated to their craft
• I need a word for someone who pays attention to every tiny detail
• What's a good word for stubborn but in a mean way`;

// Sync with initial query when modal opens
watch(() => props.show, (newVal) => {
    if (newVal) {
        localQuery.value = props.initialQuery;
        nextTick(() => {
            expandedTextarea.value?.focus();
            expandedTextarea.value?.setSelectionRange(localQuery.value.length, localQuery.value.length);
        });
    }
});

const handleClose = () => {
    emit('close');
};

const handleSubmit = () => {
    emit('submit', localQuery.value);
};

// Smooth modal animations
const modalEnter = (_el: Element, done: () => void) => {
    const backdrop = modalBackdrop.value;
    const content = modalContent.value;
    
    if (!backdrop || !content) {
        done();
        return;
    }
    
    // Initial states
    backdrop.style.opacity = '0';
    content.style.opacity = '0';
    content.style.transform = 'scale(0.97) translateY(10px)';
    
    // Force reflow
    backdrop.offsetHeight;
    
    // Animate
    requestAnimationFrame(() => {
        // Backdrop fades in
        backdrop.style.transition = 'opacity 200ms cubic-bezier(0.25, 0.1, 0.25, 1)';
        backdrop.style.opacity = '1';
        
        // Content appears slightly after
        setTimeout(() => {
            content.style.transition = 'all 250ms cubic-bezier(0.16, 1, 0.3, 1)';
            content.style.opacity = '1';
            content.style.transform = 'scale(1) translateY(0)';
            
            setTimeout(done, 250);
        }, 50);
    });
};

const modalLeave = (_el: Element, done: () => void) => {
    const backdrop = modalBackdrop.value;
    const content = modalContent.value;
    
    if (!backdrop || !content) {
        done();
        return;
    }
    
    // Animate out
    content.style.transition = 'all 200ms cubic-bezier(0.4, 0, 1, 1)';
    content.style.opacity = '0';
    content.style.transform = 'scale(0.97) translateY(10px)';
    
    backdrop.style.transition = 'opacity 200ms cubic-bezier(0.4, 0, 1, 1)';
    backdrop.style.opacity = '0';
    
    setTimeout(done, 200);
};
</script>