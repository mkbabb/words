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
            
            <button
                @click="$emit('toggle-pronunciation')"
                class="h-6 px-2 py-1 text-xs transition-all duration-200 rounded-md bg-muted/50 hover:bg-muted border border-border/50 hover:border-border text-foreground/80 hover:text-foreground min-w-[60px] text-center"
            >
                {{ pronunciationMode === 'phonetic' ? 'IPA' : 'Phonetic' }}
            </button>
            
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