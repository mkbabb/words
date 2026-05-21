<template>
  <span
    v-if="role === 'premium' || role === 'admin'"
    :class="cn(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium align-middle',
      role === 'admin'
        ? 'bg-[var(--color-gold)]/10 text-[var(--color-gold)]'
        : 'bg-violet-500/10 text-violet-600 dark:text-violet-400'
    )"
  >
    <Shield v-if="role === 'admin'" :size="12" />
    <Sparkles v-else :size="12" />
    {{ role === 'admin' ? 'Admin' : 'Premium' }}
  </span>
</template>

<script setup lang="ts">
import { Shield, Sparkles } from '@lucide/vue';
import { cn } from '@mkbabb/glass-ui';
import type { UserRole } from '@/types/api';

interface Props {
  role: UserRole;
}

defineProps<Props>();
</script>
