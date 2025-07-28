<template>
    <div class="flex gap-3 items-center">
        <!-- Sidebar Toggle (Mobile Only) -->
        <ActionButton
            v-if="isMobile"
            @click="$emit('toggle-sidebar')"
            title="Toggle Sidebar"
            variant="default"
        >
            <PanelLeft :size="18" />
        </ActionButton>
        
        <!-- AI Mode Toggle -->
        <ActionButton
            @click="handleAIToggle"
            :title="!noAI ? 'AI synthesis enabled' : 'Raw provider data only'"
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
        
        <!-- Force Refresh Toggle -->
        <ActionButton
            v-if="showRefreshButton"
            @click="handleRefreshClick"
            :title="forceRefreshMode ? 'Force refresh mode ON' : 'Toggle force refresh mode'"
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
        
        <!-- Clear Storage (Debug) -->
        <ActionButton
            v-if="isDevelopment"
            @click="handleClearStorage"
            title="Clear All Storage"
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
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Trash2, PanelLeft, RefreshCw, Wand2 } from 'lucide-vue-next';
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