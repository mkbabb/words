<template>
  <Teleport to="body">
    <TransitionGroup
      name="notification"
      tag="div"
      class="fixed bottom-6 right-6 z-50 space-y-3 max-w-sm"
    >
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="[
          'cartoon-shadow-sm rounded-xl p-4 backdrop-blur-xl border-2',
          'transition-all duration-300 hover-lift cursor-pointer',
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
import { CheckCircle2, XCircle, Info, AlertTriangle } from 'lucide-vue-next';
import { useAppStore } from '@/stores';

const store = useAppStore();

const notifications = computed(() => store.notifications);
const removeNotification = (id: string) => store.removeNotification(id);

const notificationIcons = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
  warning: AlertTriangle
};

const notificationClasses = {
  success: 'bg-green-50/90 dark:bg-green-950/90 border-green-300 dark:border-green-700',
  error: 'bg-red-50/90 dark:bg-red-950/90 border-red-300 dark:border-red-700',
  info: 'bg-blue-50/90 dark:bg-blue-950/90 border-blue-300 dark:border-blue-700',
  warning: 'bg-amber-50/90 dark:bg-amber-950/90 border-amber-300 dark:border-amber-700'
};

const iconClasses = {
  success: 'text-green-600 dark:text-green-400',
  error: 'text-red-600 dark:text-red-400',
  info: 'text-blue-600 dark:text-blue-400',
  warning: 'text-amber-600 dark:text-amber-400'
};
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
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
  transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
</style>