<template>
    <!-- Time Machine Version History Overlay -->
    <TimeMachineOverlay
        :is-open="tmIsOpen"
        :word="word"
        :current-version="currentVersion"
        :versions="tmVersions"
        :selected-index="tmSelectedIndex"
        :selected-version="tmSelectedVersion"
        :version-detail="tmVersionDetail"
        :version-diff="tmVersionDiff"
        :diff-fields="tmDiffFields"
        :text-changes="tmTextChanges"
        :hydrated-entry="tmHydratedEntry"
        :navigation-direction="tmNavigationDirection"
        :loading="tmLoading"
        :detail-loading="tmDetailLoading"
        :rolling-back="tmRollingBack"
        :is-newest="tmIsNewest"
        :is-oldest="tmIsOldest"
        :expanded-view="tmExpandedView"
        @close="$emit('time-machine-close')"
        @select-version="$emit('time-machine-select-version', $event)"
        @navigate-next="$emit('time-machine-navigate-next')"
        @navigate-prev="$emit('time-machine-navigate-prev')"
        @rollback="$emit('time-machine-rollback')"
        @toggle-expanded="$emit('time-machine-toggle-expanded')"
    />

    <!-- Inline Word Lookup Popover -->
    <WordLookupPopover
        :selected-word="ilSelectedWord"
        :is-pill-visible="ilIsPillVisible"
        :is-popover-visible="ilIsPopoverVisible"
        :position="ilPosition"
        @show-popover="$emit('inline-show-popover')"
        @dismiss="$emit('inline-dismiss')"
        @lookup="$emit('inline-lookup', $event)"
        @add-to-wordlist="$emit('inline-add-to-wordlist', $event)"
    />

    <!-- Add to Wordlist Modal -->
    <AddToWordlistModal
        v-model="wordlistModalOpen"
        :word="wordToAdd"
        @added="$emit('word-added-to-list', $event)"
    />
</template>

<script setup lang="ts">
import TimeMachineOverlay from './versioning/TimeMachineOverlay.vue';
import WordLookupPopover from './WordLookupPopover.vue';
import AddToWordlistModal from './AddToWordlistModal.vue';
import type { VersionSummary, VersionDetailResponse } from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import type { VersionDiff, TextChange } from '../composables/useTimeMachine';

defineProps<{
    word?: string;
    currentVersion?: string;
    // Time Machine props (individual, not bundled)
    tmIsOpen: boolean;
    tmVersions: VersionSummary[];
    tmSelectedIndex: number;
    tmSelectedVersion: VersionSummary | null;
    tmVersionDetail: VersionDetailResponse | null;
    tmVersionDiff: VersionDiff | null;
    tmDiffFields: Set<string>;
    tmTextChanges: Map<string, TextChange[]>;
    tmHydratedEntry: SynthesizedDictionaryEntry | null;
    tmNavigationDirection: 'forward' | 'backward';
    tmLoading: boolean;
    tmDetailLoading: boolean;
    tmRollingBack: boolean;
    tmIsNewest: boolean;
    tmIsOldest: boolean;
    tmExpandedView: boolean;
    // Inline lookup props (individual, not bundled)
    ilSelectedWord: string;
    ilIsPillVisible: boolean;
    ilIsPopoverVisible: boolean;
    ilPosition: { x: number; y: number };
    // Wordlist
    wordToAdd: string;
}>();

const wordlistModalOpen = defineModel<boolean>('showWordlistModal', { required: true });

defineEmits<{
    'time-machine-close': [];
    'time-machine-select-version': [version: any];
    'time-machine-navigate-next': [];
    'time-machine-navigate-prev': [];
    'time-machine-rollback': [];
    'time-machine-toggle-expanded': [];
    'inline-show-popover': [];
    'inline-dismiss': [];
    'inline-lookup': [word: string];
    'inline-add-to-wordlist': [word: string];
    'word-added-to-list': [wordlistName: string];
}>();
</script>
