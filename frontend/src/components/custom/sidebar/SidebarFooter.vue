<template>
    <div class="border-border flex-shrink-0 border-t p-4 overflow-hidden">
        <!-- Authenticated user -->
        <template v-if="auth.isAuthenticated">
            <Transition
                mode="out-in"
                enter-active-class="transition-opacity duration-200 ease-apple-smooth"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
                leave-active-class="transition-opacity duration-150 ease-apple-smooth"
                leave-from-class="opacity-100"
                leave-to-class="opacity-0"
            >
                <div v-if="!collapsed" key="expanded" class="flex items-center gap-3">
                    <div
                        class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border bg-gradient-to-br"
                    >
                        <img
                            v-if="auth.user?.avatar"
                            :src="auth.user.avatar"
                            :alt="auth.user.name"
                            class="h-full w-full rounded-full object-cover"
                        />
                        <User v-else :size="14" class="text-primary" />
                    </div>
                    <div class="min-w-0 flex-1">
                        <div class="truncate text-sm font-medium">{{ auth.user?.name }}</div>
                        <div class="text-muted-foreground truncate text-xs">
                            {{ auth.user?.email }}
                        </div>
                    </div>
                </div>
                <div v-else key="collapsed" class="flex justify-center">
                    <div
                        class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
                    >
                        <User :size="14" class="text-primary" />
                    </div>
                </div>
            </Transition>
        </template>

        <!-- Guest user: Yoshi avatar -->
        <template v-else>
            <Transition
                mode="out-in"
                enter-active-class="transition-opacity duration-200 ease-apple-smooth"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
                leave-active-class="transition-opacity duration-150 ease-apple-smooth"
                leave-from-class="opacity-100"
                leave-to-class="opacity-0"
            >
                <div v-if="!collapsed" key="expanded" class="flex items-center gap-3">
                    <YoshiAvatar size="2rem" />
                    <div class="min-w-0 flex-1">
                        <div class="truncate text-sm font-medium">Guest</div>
                        <div class="text-muted-foreground truncate text-xs">
                            Not signed in
                        </div>
                    </div>
                </div>
                <div v-else key="collapsed" class="flex justify-center">
                    <YoshiAvatar size="2rem" />
                </div>
            </Transition>
        </template>
    </div>
</template>

<script setup lang="ts">
import { User } from 'lucide-vue-next';
import { useAuthStore } from '@/stores/auth';
import YoshiAvatar from './YoshiAvatar.vue';

interface Props {
    collapsed: boolean;
}

defineProps<Props>();

const auth = useAuthStore();
</script>
