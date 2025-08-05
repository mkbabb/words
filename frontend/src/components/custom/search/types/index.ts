import type { SearchMode, SourceConfig, LanguageConfig } from '@/types';

// Search Bar Props
export interface SearchBarProps {
    className?: string;
    shrinkPercentage?: number;
    hideDelay?: number;
    scrollThreshold?: number;
}

// Search Bar Emits
export interface SearchBarEmits {
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}

// Re-export for convenience
export type { SourceConfig, LanguageConfig };

// Search Bar State Types
export type SearchBarState = 'normal' | 'hovering' | 'focused';

// Re-export SearchMode for convenience
export type { SearchMode };

// Animation State
export interface AnimationState {
    isContainerHovered: boolean;
    isFocused: boolean;
    isShrunken: boolean;
    regenerateRotation: number;
    showErrorAnimation: boolean;
    showSparkle: boolean;
}

// Scroll State
export interface ScrollState {
    scrollProgress: number;
    scrollInflectionPoint: number;
    documentHeight: number;
    currentState: SearchBarState;
}

// Search State
export interface SearchState {
    query: string;
    autocompleteText: string;
    searchResults: any[]; // Replace with proper SearchResult type from @/types
    isSearching: boolean;
    selectedIndex: number;
    aiSuggestions: string[];
    isAIQuery: boolean;
    isInteractingWithSearchArea: boolean;
}

// Dropdown State
export interface DropdownState {
    inputFocused: boolean;
    showControls: boolean;
    showResults: boolean;
}

// Dimensions State
export interface DimensionsState {
    searchBarHeight: number;
    textareaMinHeight: number;
    expandButtonVisible: boolean;
}

// Modal State
export interface ModalState {
    showExpandModal: boolean;
    expandedQuery: string;
}

// Timer References
export interface TimerRefs {
    searchTimer?: ReturnType<typeof setTimeout>;
    scrollAnimationFrame?: number;
    globalEnterHandler?: (e: KeyboardEvent) => void;
}

// Element References
export interface ElementRefs {
    searchInput?: HTMLTextAreaElement;
    expandedTextarea?: HTMLTextAreaElement;
    searchResultsContainer?: HTMLDivElement;
    resultRefs: (HTMLButtonElement | null)[];
    searchContainer?: HTMLDivElement;
    searchBarElement?: HTMLDivElement;
    controlsDropdown?: HTMLDivElement;
    searchResultsDropdown?: HTMLDivElement;
    modalBackdrop?: HTMLDivElement;
    modalContent?: HTMLDivElement;
}