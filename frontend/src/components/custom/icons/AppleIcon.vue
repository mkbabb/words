<template>
    <svg
        :width="size"
        :height="size"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        :class="className"
    >
        <!-- Apple logo -->
        <path
            d="M16.365 1.43c0 1.14-.493 2.27-1.177 3.08-.744.9-1.99 1.57-2.987 1.57-.12 0-.23-.02-.3-.03-.08-.01-.15-.01-.21-.01-.79 0-1.57-.31-2.07-.83-.51-.53-.79-1.24-.79-2.04 0-1.14.493-2.27 1.177-3.08.744-.9 1.99-1.57 2.987-1.57.12 0 .23.02.3.03.08.01.15.01.21.01.79 0 1.57.31 2.07.83.51.53.79 1.24.79 2.04z"
            fill="currentColor"
        />
        <path
            d="M20.13 22.43c-1.235-2.14-1.866-3.82-1.866-5.03 0-1.89.744-3.47 2.232-4.73.744-.63 1.628-1.08 2.652-1.35-.744-1.14-1.628-2.04-2.652-2.7-1.024-.66-2.232-.99-3.621-.99-1.507 0-2.652.45-3.44 1.35-.744.9-1.115 2.04-1.115 3.42 0 1.38.371 2.52 1.115 3.42.788.9 1.933 1.35 3.44 1.35 1.389 0 2.597-.33 3.621-.99 1.024-.66 1.908-1.56 2.652-2.7z"
            fill="currentColor"
        />
    </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
    size?: number | string;
    className?: string;
}

const props = withDefaults(defineProps<Props>(), {
    size: 24,
    className: '',
});

const size = computed(() => 
    typeof props.size === 'number' ? `${props.size}px` : props.size
);
</script>