<template>
    <!-- Time Machine Version History Overlay -->
    <TimeMachineOverlay
        :is-open="timeMachineState.isOpen"
        :word="word"
        :current-version="currentVersion"
        :versions="timeMachineState.versions"
        :selected-index="timeMachineState.selectedIndex"
        :selected-version="timeMachineState.selectedVersion"
        :version-detail="timeMachineState.versionDetail"
        :version-diff="timeMachineState.versionDiff"
        :diff-fields="timeMachineState.diffFields"
        :text-changes="timeMachineState.textChanges"
        :hydrated-entry="timeMachineState.hydratedEntry"
        :navigation-direction="timeMachineState.navigationDirection"
        :loading="timeMachineState.loading"
        :detail-loading="timeMachineState.detailLoading"
        :rolling-back="timeMachineState.rollingBack"
        :is-newest="timeMachineState.isNewest"
        :is-oldest="timeMachineState.isOldest"
        :expanded-view="timeMachineState.expandedView"
        @close="$emit('time-machine-close')"
        @select-version="$emit('time-machine-select-version', $event)"
        @navigate-next="$emit('time-machine-navigate-next')"
        @navigate-prev="$emit('time-machine-navigate-prev')"
        @rollback="$emit('time-machine-rollback')"
        @toggle-expanded="$emit('time-machine-toggle-expanded')"
    />

    <!-- Inline Word Lookup Popover -->
    <WordLookupPopover
        :selected-word="inlineLookupState.selectedWord"
        :is-pill-visible="inlineLookupState.isPillVisible"
        :is-popover-visible="inlineLookupState.isPopoverVisible"
        :position="inlineLookupState.position"
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

defineProps<{
    word?: string;
    currentVersion?: string;
    timeMachineState: {
        isOpen: boolean;
        versions: any;
        selectedIndex: number;
        selectedVersion: any;
        versionDetail: any;
        versionDiff: any;
        diffFields: any;
        textChanges: any;
        hydratedEntry: any;
        navigationDirection: any;
        loading: boolean;
        detailLoading: boolean;
        rollingBack: boolean;
        isNewest: boolean;
        isOldest: boolean;
        expandedView: boolean;
    };
    inlineLookupState: {
        selectedWord: string;
        isPillVisible: boolean;
        isPopoverVisible: boolean;
        position: any;
    };
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
