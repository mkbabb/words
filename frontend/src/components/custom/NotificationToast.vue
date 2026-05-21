<template>
  <Teleport to="body">
    <TransitionGroup
      name="notification"
      tag="div"
      class="fixed bottom-6 right-6 z-toast space-y-3 max-w-sm"
    >
      <div
        v-for="notification in notificationList"
        :key="notification.id"
        role="alert"
        aria-live="polite"
        :class="[
          'shadow-cartoon-sm rounded-2xl p-4 backdrop-blur-xl border-2',
          'transition-normal hover-lift cursor-pointer',
          notificationClasses[notification.type]
        ]"
        @click="removeNotification(notification.id)"
      >
        <div class="flex items-start gap-3">
          <component
            :is="notificationIcons[notification.type]"
            :class="['h-5 w-5 flex-shrink-0', iconClasses[notification.type]]"
          />
          <p class="text-sm font-medium">{{ notification.message }}</p>
        </div>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CheckCircle2, XCircle, Info, AlertTriangle } from '@lucide/vue';
import { useNotifications, type Notification } from '@/stores/composables/useNotifications';

const notifications = useNotifications();

const notificationList = computed<Notification[]>(() => {
  const items = notifications.notifications;
  return Array.isArray(items) ? [...items] : [];
});
const removeNotification = (id: string) => notifications.removeNotification(id);

const notificationIcons = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle
};

const notificationClasses = {
  success: 'bg-[var(--color-success)]/10 border-[var(--color-success)]/30',
  error: 'bg-destructive/10 border-destructive/30',
  info: 'bg-[var(--color-info)]/10 border-[var(--color-info)]/30',
  warning: 'bg-[var(--color-gold)]/10 border-[var(--color-gold)]/30'
};

const iconClasses = {
  success: 'text-[var(--color-success)]',
  error: 'text-destructive',
  info: 'text-[var(--color-info)]',
  warning: 'text-[var(--color-gold)]'
};
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: opacity 0.3s var(--spring-bouncy), transform 0.3s var(--spring-bouncy);
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}

.notification-move {
  transition: transform 0.3s var(--spring-bouncy);
}
</style>