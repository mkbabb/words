<template>
    <div class="flex gap-3 items-center">
        <!-- Sidebar Toggle (Mobile Only) -->
        <HoverCard v-if="isMobile" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="$emit('toggle-sidebar')"
                    variant="default"
                >
                    <PanelLeft :size="18" />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Toggle Sidebar</p>
            </HoverCardContent>
        </HoverCard>
            
        <!-- AI Mode Toggle -->
        <HoverCard :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleAIToggle"
                    @keydown.enter.stop="handleAIToggle"
                    :variant="!noAI ? 'primary' : 'default'"
                >
                    <Wand2 
                        :size="18" 
                        :class="[
                            'transition-all duration-300',
                            aiAnimating && 'animate-sparkle'
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">{{ !noAI ? 'AI synthesis enabled' : 'Raw provider data only' }}</p>
            </HoverCardContent>
        </HoverCard>
            
        <!-- Force Refresh Toggle -->
        <HoverCard v-if="showRefreshButton" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleRefreshClick"
                    @keydown.enter.stop="handleRefreshClick"
                    :variant="forceRefreshMode ? 'primary' : 'default'"
                >
                    <RefreshCw 
                        :size="18" 
                        :class="[
                            'transition-all duration-300',
                            'group-hover:rotate-180',
                            refreshAnimating && 'animate-rotate-once'
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">{{ forceRefreshMode ? 'Force refresh mode ON' : 'Toggle force refresh mode' }}</p>
            </HoverCardContent>
        </HoverCard>
            
        <!-- Clear Storage (Debug) -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleClearStorage"
                    variant="danger"
                >
                    <Trash2 
                        :size="18" 
                        :class="[
                            'transition-all duration-300',
                            trashAnimating && 'animate-wiggle'
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Clear All Storage</p>
            </HoverCardContent>
        </HoverCard>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Trash2, PanelLeft, RefreshCw, Wand2 } from 'lucide-vue-next';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import ActionButton from './ActionButton.vue';

interface ActionsRowProps {
    showRefreshButton?: boolean;
    forceRefreshMode?: boolean;
    isDevelopment?: boolean;
}

defineProps<ActionsRowProps>();

const noAI = defineModel<boolean>('noAI', { required: true });

const emit = defineEmits<{
    'clear-storage': [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
}>();

// Reactive window width
const windowWidth = ref(window.innerWidth);

// Check if mobile
const isMobile = computed(() => windowWidth.value < 768);

// Animation states
const aiAnimating = ref(false);
const trashAnimating = ref(false);
const refreshAnimating = ref(false);

// Event handlers
const handleAIToggle = () => {
    noAI.value = !noAI.value;
    aiAnimating.value = true;
    setTimeout(() => {
        aiAnimating.value = false;
    }, 600);
};

const handleClearStorage = () => {
    trashAnimating.value = true;
    setTimeout(() => {
        trashAnimating.value = false;
        emit('clear-storage');
    }, 600);
};

const handleRefreshClick = () => {
    refreshAnimating.value = true;
    setTimeout(() => {
        refreshAnimating.value = false;
    }, 300);
    emit('toggle-refresh');
};

// Handle window resize
const handleResize = () => {
    windowWidth.value = window.innerWidth;
};

// Set up resize listener
onMounted(() => {
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
@keyframes sparkle {
    0%, 100% {
        transform: scale(1) rotate(0deg);
        filter: brightness(1);
    }
    25% {
        transform: scale(1.1) rotate(5deg);
        filter: brightness(1.2);
    }
    50% {
        transform: scale(1.2) rotate(-5deg);
        filter: brightness(1.5);
    }
    75% {
        transform: scale(1.1) rotate(5deg);
        filter: brightness(1.2);
    }
}

@keyframes wiggle {
    0%, 100% {
        transform: rotate(0deg);
    }
    10% {
        transform: rotate(-10deg);
    }
    20% {
        transform: rotate(10deg);
    }
    30% {
        transform: rotate(-10deg);
    }
    40% {
        transform: rotate(10deg);
    }
    50% {
        transform: rotate(0deg);
    }
}

@keyframes rotate-once {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.animate-sparkle {
    animation: sparkle 0.6s ease-in-out;
}

.animate-wiggle {
    animation: wiggle 0.6s ease-in-out;
}

.animate-rotate-once {
    animation: rotate-once 0.3s ease-in-out;
}
</style>