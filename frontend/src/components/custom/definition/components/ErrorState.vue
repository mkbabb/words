<template>
    <div class="flex flex-col items-center justify-center min-h-[400px] px-6 text-center">
        <div class="mb-6">
            <div class="relative inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-destructive/10">
                <component 
                    :is="errorIcon" 
                    :size="32" 
                    class="text-destructive"
                />
            </div>
        </div>
        
        <h3 class="text-xl font-semibold mb-2 text-foreground">
            {{ title }}
        </h3>
        
        <p class="text-muted-foreground mb-6 max-w-md leading-relaxed">
            {{ message }}
        </p>
        
        <div class="flex items-center gap-3">
            <Button 
                v-if="retryable" 
                @click="$emit('retry')"
                variant="default"
                size="sm"
                class="min-w-[80px]"
            >
                <RotateCcw :size="16" class="mr-2" />
                Try Again
            </Button>
            
            <Button 
                v-if="showHelp" 
                @click="$emit('help')"
                variant="outline"
                size="sm"
            >
                <HelpCircle :size="16" class="mr-2" />
                Get Help
            </Button>
        </div>
        
        <!-- Optional additional content slot -->
        <div v-if="$slots.default" class="mt-6">
            <slot />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '@/components/ui/button';
import { 
    AlertTriangle, 
    Wifi, 
    Search, 
    ServerCrash, 
    RotateCcw, 
    HelpCircle 
} from 'lucide-vue-next';

interface ErrorStateProps {
    title?: string;
    message?: string;
    errorType?: 'network' | 'not-found' | 'server' | 'ai-failed' | 'empty' | 'unknown';
    retryable?: boolean;
    showHelp?: boolean;
}

const props = withDefaults(defineProps<ErrorStateProps>(), {
    title: 'Something went wrong',
    message: 'An unexpected error occurred. Please try again.',
    errorType: 'unknown',
    retryable: true,
    showHelp: false
});

defineEmits<{
    retry: [];
    help: [];
}>();

const errorIcon = computed(() => {
    switch (props.errorType) {
        case 'network':
            return Wifi;
        case 'not-found':
        case 'empty':
            return Search;
        case 'server':
            return ServerCrash;
        case 'ai-failed':
            return AlertTriangle;
        default:
            return AlertTriangle;
    }
});
</script>