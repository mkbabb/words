<template>
    <div class="flex items-center justify-evenly w-full">
        <!-- AI Mode Toggle -->
        <HoverCard :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleAIToggle"
                    @keydown.enter.stop="handleAIToggle"
                    :variant="!noAI ? 'primary' : 'default'"
                >
                    <Wand2 
                        :size="20" 
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
                        :size="20" 
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
                        :size="20" 
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
        
        <!-- PWA Install Debug -->
        <HoverCard v-if="isDevelopment" :open-delay="200" :close-delay="100">
            <HoverCardTrigger as-child>
                <ActionButton
                    @click="handleShowPWAPrompt"
                    variant="secondary"
                >
                    <Download 
                        :size="20" 
                        :class="[
                            'transition-all duration-300',
                            pwaInstallAnimating && 'animate-bounce-in'
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
                            'transition-all duration-300',
                            notificationAnimating && 'animate-ring'
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
                            'transition-all duration-300',
                            notificationPromptAnimating && 'animate-pulse'
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
import { ref, onMounted, onUnmounted } from 'vue';
import { Trash2, RefreshCw, Wand2, Download, Bell, BellDot } from 'lucide-vue-next';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import ActionButton from './ActionButton.vue';
// import { usePWA } from '@/composables';
import { useStores } from '@/stores';

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

// PWA composables
// const { subscribeToPush } = usePWA();
const { notifications } = useStores();

// Reactive window width for potential future use
const windowWidth = ref(window.innerWidth);

// Animation states
const aiAnimating = ref(false);
const trashAnimating = ref(false);
const refreshAnimating = ref(false);
const pwaInstallAnimating = ref(false);
const notificationAnimating = ref(false);
const notificationPromptAnimating = ref(false);

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
                message: 'Notifications not supported'
            });
            return;
        }
        
        // Request permission if needed
        if (Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                notifications.showNotification({
                    type: 'error',
                    message: 'Notification permission denied'
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
            message: 'Notifications are enabled! 🎉'
        });
    } catch (error) {
        console.error('Notification error:', error);
        notifications.showNotification({
            type: 'error',
            message: 'Failed to send notification'
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

// Test push notification via service worker
// const handleTestPushNotification = async () => {
//     try {
//         // Check if we have a push subscription
//         const registration = await navigator.serviceWorker.ready;
//         const subscription = await registration.pushManager.getSubscription();
//         
//         if (!subscription) {
//             store.showNotification({
//                 type: 'error',
//                 message: 'No push subscription. Enable notifications first!'
//             });
//             return;
//         }
//         
//         // Send test push via backend
//         const response = await fetch(`${window.location.origin}/notifications/api/test`, {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json'
//             },
//             body: JSON.stringify({
//                 endpoint: subscription.endpoint
//             })
//         });
//         
//         if (response.ok) {
//             store.showNotification({
//                 type: 'success',
//                 message: 'Push notification sent! Check your notifications.'
//             });
//         } else {
//             throw new Error('Failed to send push');
//         }
//     } catch (error) {
//         console.error('Push test error:', error);
//         store.showNotification({
//             type: 'error',
//             message: 'Failed to send push notification'
//         });
//     }
// };

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
    0%, 100% {
        transform: rotate(0deg);
    }
    10%, 30% {
        transform: rotate(-10deg);
    }
    20%, 40% {
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