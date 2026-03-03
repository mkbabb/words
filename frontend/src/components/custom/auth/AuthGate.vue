<template>
  <!-- Access granted -->
  <slot v-if="hasAccess" />

  <!-- Access denied -->
  <slot v-else name="locked">
    <div class="flex flex-col items-center gap-2 rounded-lg border border-border/50 bg-muted/30 p-4 text-center">
      <Lock :size="20" class="text-muted-foreground" />
      <p class="text-muted-foreground text-sm">{{ message }}</p>
      <router-link
        v-if="!auth.isAuthenticated"
        to="/login"
        class="mt-1 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Sign in
      </router-link>
      <span
        v-else
        class="text-muted-foreground text-xs"
      >
        {{ upgradeText }}
      </span>
    </div>
  </slot>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Lock } from 'lucide-vue-next';
import { useAuthStore } from '@/stores/auth';

interface Props {
  requireAuth?: boolean;
  requirePremium?: boolean;
  requireAdmin?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  requireAuth: false,
  requirePremium: false,
  requireAdmin: false,
});

const auth = useAuthStore();

const hasAccess = computed(() => {
  if (props.requireAdmin) return auth.isAdmin;
  if (props.requirePremium) return auth.isPremium;
  if (props.requireAuth) return auth.isAuthenticated;
  return true;
});

const message = computed(() => {
  if (!auth.isAuthenticated) return 'Sign in to access this feature';
  if (props.requireAdmin) return 'Admin access required';
  if (props.requirePremium) return 'Premium access required';
  return 'Access restricted';
});

const upgradeText = computed(() => {
  if (props.requireAdmin) return 'Contact an admin for access';
  return 'Upgrade to Premium for this feature';
});
</script>
