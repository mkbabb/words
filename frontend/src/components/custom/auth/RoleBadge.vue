<template>
  <span
    v-if="role === 'premium' || role === 'admin'"
    :class="cn(
      'inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
      role === 'admin'
        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
        : 'bg-violet-500/10 text-violet-600 dark:text-violet-400'
    )"
  >
    <Shield v-if="role === 'admin'" :size="10" />
    <Sparkles v-else :size="10" />
    {{ role === 'admin' ? 'Admin' : 'Premium' }}
  </span>
</template>

<script setup lang="ts">
import { Shield, Sparkles } from 'lucide-vue-next';
import { cn } from '@/utils';
import type { UserRole } from '@/types/api/models';

interface Props {
  role: UserRole;
}

defineProps<Props>();
</script>
