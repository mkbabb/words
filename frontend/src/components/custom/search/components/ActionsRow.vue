<template>
    <div class="flex w-full items-center justify-evenly">
        <!-- AI Mode Toggle -->
        <HoverCard :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleAIToggle"
                    @keydown.enter.stop="handleAIToggle"
                    :variant="!noAI && isPremium ? 'primary' : 'default'"
                    :disabled="!isPremium"
                >
                    <Lock v-if="!isPremium" :size="20" class="text-muted-foreground" />
                    <Wand2
                        v-else
                        :size="20"
                        :class="[
                            'transition-normal',
                            aiAnimating && 'animate-sparkle',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">
                    {{
                        !isPremium
                            ? 'Upgrade to Premium for AI synthesis'
                            : !noAI
                              ? 'AI synthesis enabled'
                              : 'Raw provider data only'
                    }}
                </p>
            </HoverCardContent>
        </HoverCard>

        <!-- Force Refresh Toggle (premium only) -->
        <HoverCard
            v-if="showRefreshButton && isPremium"
            :open-delay="200"
            :close-delay="100"
        >
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleRefreshClick"
                    @keydown.enter.stop="handleRefreshClick"
                    :variant="forceRefreshMode ? 'primary' : 'default'"
                >
                    <RefreshCw
                        :size="20"
                        :class="[
                            'transition-normal',
                            'group-hover:rotate-180',
                            refreshAnimating && 'animate-rotate-once',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">
                    {{
                        forceRefreshMode
                            ? 'Force refresh mode ON'
                            : 'Toggle force refresh mode'
                    }}
                </p>
            </HoverCardContent>
        </HoverCard>

        <!-- Clear Storage (Debug) -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton @click="handleClearStorage" variant="danger">
                    <Trash2
                        :size="20"
                        :class="[
                            'transition-normal',
                            trashAnimating && 'animate-wiggle',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Clear All Storage</p>
            </HoverCardContent>
        </HoverCard>

        <!-- PWA Install Debug -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton @click="handleShowPWAPrompt" variant="secondary">
                    <Download
                        :size="20"
                        :class="[
                            'transition-normal',
                            pwaInstallAnimating && 'animate-bounce-in',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Show PWA Install Prompt</p>
            </HoverCardContent>
        </HoverCard>

        <!-- Test Notification Debug -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleSendNotification"
                    variant="secondary"
                >
                    <Bell
                        :size="20"
                        :class="[
                            'transition-normal',
                            notificationAnimating && 'animate-ring',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Send Test Notification</p>
            </HoverCardContent>
        </HoverCard>

        <!-- Notification Prompt Debug -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleShowNotificationPrompt"
                    variant="secondary"
                >
                    <BellDot
                        :size="20"
                        :class="[
                            'transition-normal',
                            notificationPromptAnimating && 'animate-pulse',
                        ]"
                    />
                </ActionButton>
            </HoverCardTrigger>
            <HoverCardContent class="w-auto p-2" side="top">
                <p class="text-sm">Show Notification Permission Prompt</p>
            </HoverCardContent>
        </HoverCard>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Trash2, RefreshCw, Wand2, Download, Bell, BellDot, Lock } from 'lucide-vue-next';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import ActionButton from './ActionButton.vue';
import { useStores } from '@/stores';
import { useAuthStore } from '@/stores/auth';
import { logger } from '@/utils/logger';

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

// Auth
const auth = useAuthStore();
const isPremium = auth.isPremium;

// PWA composables
// const { subscribeToPush } = usePWA();
const { notifications } = useStores();

// Animation states
const aiAnimating = ref(false);
const trashAnimating = ref(false);
const refreshAnimating = ref(false);
const pwaInstallAnimating = ref(false);
const notificationAnimating = ref(false);
const notificationPromptAnimating = ref(false);

// Event handlers
const handleAIToggle = () => {
    if (!isPremium) return;
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

// PWA Debug handlers
const handleShowPWAPrompt = () => {
    pwaInstallAnimating.value = true;
    setTimeout(() => {
        pwaInstallAnimating.value = false;
    }, 600);

    // Force show PWA install prompt
    const event = new Event('show-pwa-prompt');
    window.dispatchEvent(event);
};

const handleSendNotification = async () => {
    notificationAnimating.value = true;

    try {
        // Check if notifications are supported
        if (!('Notification' in window)) {
            notifications.showNotification({
                type: 'error',
                message: 'Notifications not supported',
            });
            return;
        }

        // Request permission if needed
        if (Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                notifications.showNotification({
                    type: 'error',
                    message: 'Notification permission denied',
                });
                return;
            }
        }

        // Send test notification
        // new Notification('Floridify Test', {
        //     body: 'PWA notifications are working! 🎉',
        //     icon: '/favicon-256.png',
        //     badge: '/favicon-128.png',
        //     tag: 'test-notification',
        //     renotify: true
        // });

        // Just show in-app notification
        notifications.showNotification({
            type: 'success',
            message: 'Notifications are enabled! 🎉',
        });
    } catch (error) {
        logger.error('Notification error:', error);
        notifications.showNotification({
            type: 'error',
            message: 'Failed to send notification',
        });
    } finally {
        setTimeout(() => {
            notificationAnimating.value = false;
        }, 600);
    }
};

const handleShowNotificationPrompt = () => {
    notificationPromptAnimating.value = true;
    setTimeout(() => {
        notificationPromptAnimating.value = false;
    }, 600);

    // Show notification permission prompt
    const event = new Event('show-notification-prompt');
    window.dispatchEvent(event);
};

</script>

<style scoped>
@keyframes sparkle {
    0%,
    100% {
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
    0%,
    100% {
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

@keyframes bounce-in {
    0% {
        transform: scale(0.3);
        opacity: 0;
    }
    50% {
        transform: scale(1.1);
    }
    70% {
        transform: scale(0.9);
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}

@keyframes ring {
    0%,
    100% {
        transform: rotate(0deg);
    }
    10%,
    30% {
        transform: rotate(-10deg);
    }
    20%,
    40% {
        transform: rotate(10deg);
    }
}

.animate-bounce-in {
    animation: bounce-in 0.6s ease-out;
}

.animate-ring {
    animation: ring 0.6s ease-in-out;
}
</style>
