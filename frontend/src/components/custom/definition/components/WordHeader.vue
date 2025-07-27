<template>
    <CardHeader class="relative">
        <div class="flex items-center justify-between">
            <CardTitle>
                <AnimatedTitle
                    :text="word"
                    :animation-type="animationType"
                    :animation-key="animationKey"
                />
            </CardTitle>
        </div>

        <!-- Pronunciation -->
        <div
            v-if="pronunciation"
            class="flex items-center gap-3 pt-2"
        >
            <span class="text-lg text-muted-foreground" style="font-family: 'Fira Code', monospace;">
                {{ pronunciationMode === 'phonetic' ? pronunciation.phonetic : pronunciation.ipa }}
            </span>
            
            <Button
                variant="ghost"
                size="sm"
                @click="$emit('toggle-pronunciation')"
                class="h-6 px-2 py-1 text-xs transition-all duration-200 hover:opacity-80"
            >
                {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
            </Button>
            
            <!-- Provider Source Icons -->
            <ProviderIcons
                :providers="providers"
                :word="word"
            />
        </div>
    </CardHeader>
</template>

<script setup lang="ts">
import { CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui';
import AnimatedTitle from './AnimatedTitle.vue';
import ProviderIcons from './ProviderIcons.vue';

interface WordHeaderProps {
    word: string;
    pronunciation?: {
        phonetic: string;
        ipa: string;
    };
    pronunciationMode: 'phonetic' | 'ipa';
    providers: string[];
    animationType: string;
    animationKey: number;
}

defineProps<WordHeaderProps>();

defineEmits<{
    'toggle-pronunciation': [];
}>();
</script>