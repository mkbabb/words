<template>
    <div class="flex flex-col items-center justify-center min-h-[400px] px-6 text-center">
        <div class="mb-6">
            <div class="relative inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-muted/20">
                <component 
                    :is="emptyIcon" 
                    :size="32" 
                    class="text-muted-foreground"
                />
            </div>
        </div>
        
        <h3 class="text-xl font-semibold mb-2 text-foreground">
            {{ title }}
        </h3>
        
        <p class="text-muted-foreground mb-6 max-w-md leading-relaxed">
            {{ message }}
        </p>
        
        <!-- Action buttons slot -->
        <div v-if="$slots.actions || showSuggestions" class="flex items-center gap-3">
            <slot name="actions" />
            
            <Button 
                v-if="showSuggestions" 
                @click="$emit('suggest-alternatives')"
                variant="default"
                size="sm"
            >
                <Lightbulb :size="16" class="mr-2" />
                Suggest alternatives
            </Button>
        </div>
        
        <!-- Optional additional content -->
        <div v-if="$slots.default" class="mt-6">
            <slot />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '@/components/ui/button';
import { 
    SearchX, 
    FileText, 
    BookOpen, 
    Lightbulb 
} from 'lucide-vue-next';

interface EmptyStateProps {
    title?: string;
    message?: string;
    emptyType?: 'no-results' | 'no-definitions' | 'no-suggestions' | 'generic';
    showSuggestions?: boolean;
}

const props = withDefaults(defineProps<EmptyStateProps>(), {
    title: 'No results found',
    message: 'Try searching for a different word or check your spelling.',
    emptyType: 'no-results',
    showSuggestions: false
});

defineEmits<{
    'suggest-alternatives': [];
}>();

const emptyIcon = computed(() => {
    switch (props.emptyType) {
        case 'no-results':
            return SearchX;
        case 'no-definitions':
            return FileText;
        case 'no-suggestions':
            return BookOpen;
        default:
            return SearchX;
    }
});
</script>