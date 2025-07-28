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
            v-if="pronunciation && hasPronunciation"
            class="flex items-center gap-3 pt-2"
        >
            <span class="text-lg text-muted-foreground" style="font-family: 'Fira Code', monospace;">
                {{ currentPronunciation }}
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
import { computed } from 'vue';
import { CardHeader, CardTitle } from '@/components/ui/card';
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

const props = defineProps<WordHeaderProps>();

defineEmits<{
    'toggle-pronunciation': [];
}>();

// Check if we have valid pronunciation data
const hasPronunciation = computed(() => {
    if (!props.pronunciation) return false;
    const phoneticValid = props.pronunciation.phonetic && props.pronunciation.phonetic !== 'unknown';
    const ipaValid = props.pronunciation.ipa && props.pronunciation.ipa !== 'unknown';
    return phoneticValid || ipaValid;
});

// Get the current pronunciation to display
const currentPronunciation = computed(() => {
    if (!props.pronunciation) return '';
    
    const phonetic = props.pronunciation.phonetic;
    const ipa = props.pronunciation.ipa;
    
    // Check what mode we're in
    if (props.pronunciationMode === 'phonetic') {
        // If phonetic is valid, use it; otherwise fall back to IPA
        if (phonetic && phonetic !== 'unknown') {
            return phonetic;
        } else if (ipa && ipa !== 'unknown') {
            return ipa;
        }
    } else {
        // If IPA is valid, use it; otherwise fall back to phonetic
        if (ipa && ipa !== 'unknown') {
            return ipa;
        } else if (phonetic && phonetic !== 'unknown') {
            return phonetic;
        }
    }
    
    return '';
});
</script>