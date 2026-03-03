<template>
    <div class="border-border flex-shrink-0 border-t p-4 overflow-hidden">
        <UserMenu :collapsed="collapsed" />
    </div>
</template>

<script setup lang="ts">
import { UserMenu } from '@/components/custom/auth';

interface Props {
    collapsed: boolean;
}

defineProps<Props>();
</script>
