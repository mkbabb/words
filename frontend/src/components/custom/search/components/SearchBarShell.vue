<template>
    <div
        ref="shellElement"
        :class="[
            'search-bar relative flex items-center gap-2 overflow-visible px-1 py-0.5 sm:px-1',
            'shadow-cartoon-sm rounded-2xl transition-[border-color,background-color,box-shadow,backdrop-filter] duration-500 ease-apple-smooth',
            searchBar.isAIQuery && !searchBar.hasErrorAnimation
                ? 'border-2 border-amber-500 bg-amber-50 backdrop-blur-sm dark:border-amber-700/40 dark:bg-amber-950/30'
                : searchBar.hasErrorAnimation
                  ? 'border-2 border-red-400/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:border-red-600/50 dark:from-red-900/20 dark:to-red-900/10'
                  : 'border-2 border-border bg-background/90 backdrop-blur-xl',
            {
                'shadow-cartoon-sm-hover': containerHovered,
                'bg-background/95': containerHovered && !searchBar.isAIQuery,
                'shake-error': searchBar.hasErrorAnimation,
            },
        ]"
        :style="shellStyle"
    >
        <!-- Border shimmer overlay in AI mode -->
        <BorderShimmer
            v-if="searchBar.isAIQuery && !searchBar.hasErrorAnimation"
            :active="true"
            color="var(--ai-accent)"
            :thickness="3"
            :border-width="2"
            :duration="2400"
        />
        <!-- Sparkle Indicator -->
        <SparkleIndicator :show="searchBar.showSparkle" />

        <!-- Mode Toggle -->
        <ModeToggle
            :model-value="searchBar.getSubMode('lookup') as any"
            :can-toggle="canToggleMode"
            :opacity="iconOpacity"
            :show-subscript="canToggleMode"
            :ai-mode="searchBar.isAIQuery"
            @update:model-value="(value: any) => searchBar.setSubMode('lookup', value)"
        />

        <!-- Search Input Container with Autocomplete -->
        <div class="search-field-shell relative max-w-none min-w-0 flex-1 flex-grow">
            <!-- Autocomplete Overlay -->
            <AutocompleteOverlay
                :query="query"
                :suggestion="searchBar.autocompleteText"
                :text-align="iconOpacity < 0.3 && !searchBar.isAIQuery ? 'center' : 'left'"
            />

            <!-- Main Search Input -->
            <SearchInput
                ref="searchInputComponent"
                v-model="query"
                :placeholder="placeholder"
                :ai-mode="searchBar.isAIQuery"
                :max-height="searchBar.isAIQuery ? 210 : 200"
                :text-align="iconOpacity < 0.3 && !searchBar.isAIQuery ? 'center' : 'left'"
                @enter="$emit('enter')"
                @tab="$emit('tab')"
                @space="$emit('space')"
                @arrow-down="$emit('arrow-down')"
                @arrow-up="$emit('arrow-up')"
                @arrow-left="$emit('arrow-left')"
                @arrow-right="$emit('arrow-right')"
                @escape="$emit('escape')"
                @focus="$emit('focus')"
                @blur="$emit('blur')"
                @input-click="$emit('input-click', $event)"
            />

            <!-- Clear/Expand Action Buttons -->
            <SearchInputActions
                :ai-mode="searchBar.isAIQuery"
                :show-clear="query.length > 0 && searchBar.isFocused"
                :scroll-progress="scrollProgress"
                @expand="$emit('expand')"
                @clear="$emit('clear')"
            />
        </div>

        <!-- Hamburger Button -->
        <div
            class="search-hamburger-slot flex flex-shrink-0 items-center justify-center overflow-hidden transition-[opacity,transform] duration-350 ease-apple-default"
            :style="{
                opacity: iconOpacity,
                transform: `scale(${0.9 + iconOpacity * 0.1})`,
                pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            }"
        >
            <HamburgerIcon
                :is-open="searchBar.showSearchControls"
                :ai-mode="searchBar.isAIQuery"
                @toggle="$emit('toggle-controls')"
                @mousedown.prevent
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { HamburgerIcon } from '@/components/custom/icons';
import { BorderShimmer } from '@/components/custom/animation';
import SearchInput from './SearchInput.vue';
import SparkleIndicator from './SparkleIndicator.vue';
import ModeToggle from './ModeToggle.vue';
import AutocompleteOverlay from './AutocompleteOverlay.vue';
import SearchInputActions from './SearchInputActions.vue';

interface Props {
    iconOpacity: number;
    containerHovered: boolean;
    shellStyle: Record<string, string>;
    canToggleMode: boolean;
    placeholder: string;
    scrollProgress: number;
}

defineProps<Props>();

const query = defineModel<string>('query', { required: true });

defineEmits<{
    enter: [];
    tab: [];
    space: [];
    'arrow-down': [];
    'arrow-up': [];
    'arrow-left': [];
    'arrow-right': [];
    escape: [];
    focus: [];
    blur: [];
    'input-click': [event: MouseEvent];
    expand: [];
    clear: [];
    'toggle-controls': [];
}>();

const searchBar = useSearchBarStore();

const shellElement = ref<HTMLDivElement>();
const searchInputComponent = ref<any>();

defineExpose({
    shellElement,
    searchInputElement: searchInputComponent,
});
</script>

<style scoped>
.search-field-shell {
    min-height: var(--search-min-h, 48px);
    display: grid;
    align-items: stretch;
}

.search-hamburger-slot {
    width: var(--search-hamburger-width, 0rem);
    margin-left: var(--search-hamburger-gap, 0rem);
}
</style>
