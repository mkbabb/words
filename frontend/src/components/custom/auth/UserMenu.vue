<template>
  <!-- Signed out: Sign in button -->
  <template v-if="!auth.isAuthenticated">
    <router-link
      to="/login"
      :class="cn(
        'inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5',
        'text-sm font-medium text-foreground/80 transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        collapsed && 'justify-center px-2'
      )"
    >
      <LogIn :size="16" />
      <span v-if="!collapsed">Sign in</span>
    </router-link>
  </template>

  <!-- Signed in: User info + menu -->
  <template v-else>
    <DropdownMenu>
      <DropdownMenuTrigger as-child>
        <button
          :class="cn(
            'flex w-full items-center gap-3 rounded-lg p-1.5 transition-colors',
            'hover:bg-accent text-left',
            collapsed && 'justify-center'
          )"
        >
          <YoshiAvatar size="2rem" :is-admin="auth.isAdmin" @click.stop />

          <div v-if="!collapsed" class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="truncate text-sm font-medium">{{ displayName }}</span>
              <RoleBadge :role="auth.role" />
            </div>
            <div v-if="auth.user?.email" class="text-muted-foreground truncate text-xs">
              {{ auth.user.email }}
            </div>
          </div>
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" class="w-56">
        <DropdownMenuLabel>
          <div class="flex items-center gap-2">
            <span>{{ displayName }}</span>
            <RoleBadge :role="auth.role" />
          </div>
          <div v-if="auth.user?.email" class="text-muted-foreground text-xs font-normal">{{ auth.user.email }}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem v-if="auth.isAdmin" @click="$router.push('/admin')">
          <Shield :size="14" class="mr-2" />
          Admin Panel
        </DropdownMenuItem>
        <DropdownMenuItem @click="signOut">
          <LogOut :size="14" class="mr-2" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { LogIn, LogOut, Shield } from 'lucide-vue-next';
import { YoshiAvatar } from '@/components/custom/sidebar';
import { useClerk } from '@clerk/vue';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/utils';
import RoleBadge from './RoleBadge.vue';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface Props {
  collapsed?: boolean;
}

const { collapsed = false } = defineProps<Props>();

const auth = useAuthStore();
const clerk = useClerk();

const isDevAdmin = import.meta.env.DEV && import.meta.env.VITE_DEV_ADMIN === 'true';
const displayName = computed(() => auth.user?.name || (isDevAdmin ? 'Yoshi' : 'User'));

function signOut() {
  auth.clearProfile();
  clerk.value?.signOut();
}
</script>
