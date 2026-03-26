// Subdirectory re-exports
export { DefinitionCluster, DefinitionItem, DefinitionContentRenderer, DefinitionContentView } from './content';
export { EditMetadataBlock, EditableField, SynonymChooser } from './editing';
export { ProviderIcons, ProviderMetadataCard, ProviderVersionSelector } from './metadata';
export { TimeMachineOverlay, VersionHistory, VersionDiffViewer } from './versioning';
export { ImageCarousel, ImageUploader, AudioPlaybackButton } from './media';

// Top-level components
export { default as AnimatedTitle } from './AnimatedTitle.vue';
export { default as Etymology } from './Etymology.vue';
export { default as PhrasesSection } from './PhrasesSection.vue';
export { default as ThemeSelector } from './ThemeSelector.vue';
export { default as ThesaurusView } from './ThesaurusView.vue';
export { default as WordHeader } from './WordHeader.vue';
export { default as WordLookupPopover } from './WordLookupPopover.vue';
export { default as ErrorState } from './ErrorState.vue';
export { default as EmptyState } from './EmptyState.vue';
