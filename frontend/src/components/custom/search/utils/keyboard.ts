/**
 * Keyboard Navigation and Input Utilities
 * 
 * Functions for handling keyboard interactions and navigation
 */

import type { SearchResult } from '@/types';

/**
 * Navigates search results based on direction
 * @param currentIndex Current selected index
 * @param direction Direction to navigate (+1 for down, -1 for up)
 * @param totalResults Total number of results
 * @returns New selected index
 */
export function calculateNavigationIndex(
    currentIndex: number,
    direction: number,
    totalResults: number
): number {
    if (totalResults === 0) return 0;
    
    return Math.max(
        0,
        Math.min(
            totalResults - 1,
            currentIndex + direction
        )
    );
}

/**
 * Scrolls the selected result into view
 * @param selectedElement The selected HTML element
 * @param container The container element
 */
export function scrollResultIntoView(
    selectedElement: HTMLElement | null,
    container: HTMLElement | null
): void {
    if (selectedElement && container) {
        selectedElement.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
        });
    }
}

/**
 * Determines if autocomplete should be accepted based on cursor position
 * @param cursorPosition Current cursor position
 * @param queryLength Current query length
 * @returns True if autocomplete should be accepted
 */
export function shouldAcceptAutocomplete(
    cursorPosition: number,
    queryLength: number
): boolean {
    return cursorPosition > queryLength;
}

/**
 * Updates textarea height based on content
 * @param textarea The textarea element
 * @returns The calculated height for the search bar
 */
export function calculateTextareaHeight(textarea: HTMLTextAreaElement | null): number {
    if (!textarea) return 64; // Default height
    
    // Reset height to auto to get the natural height
    textarea.style.height = 'auto';
    
    // Get the scroll height (content height)
    const scrollHeight = textarea.scrollHeight;
    
    // Set the textarea height directly
    textarea.style.height = `${scrollHeight}px`;
    
    // Simple height calculation
    const padding = 32; // Account for search bar padding
    return Math.max(64, scrollHeight + padding);
}

/**
 * Determines if expand button should be visible
 * @param isAIQuery Whether this is an AI query
 * @param queryLength The query text length
 * @param hasNewlines Whether the query contains newlines
 * @returns True if expand button should be visible
 */
export function shouldShowExpandButton(
    isAIQuery: boolean,
    queryLength: number,
    hasNewlines: boolean
): boolean {
    return isAIQuery || queryLength > 80 || hasNewlines;
}

/**
 * Finds the best autocomplete match from search results
 * @param query The current query
 * @param results The search results
 * @returns The autocomplete text or empty string
 */
export function findAutocompleteMatch(
    query: string,
    results: SearchResult[]
): string {
    if (!query || query.length < 2 || !results.length) {
        return '';
    }

    // Take the top match (highest score)
    const topMatch = results[0];

    // Check if the top match starts with the current query (case insensitive)
    const queryLower = query.toLowerCase();
    const wordLower = topMatch.word.toLowerCase();

    if (wordLower.startsWith(queryLower) && topMatch.word.length > query.length) {
        // Use the top match for completion
        return topMatch.word;
    }
    
    // No suitable completion available
    return '';
}

/**
 * Handles space key with autocomplete
 * @param hasAutocomplete Whether autocomplete is available
 * @param currentQuery The current query
 * @param autocompleteText The autocomplete text
 * @returns Object with preventDefault flag and new query
 */
export function handleSpaceKeyPress(
    hasAutocomplete: boolean,
    currentQuery: string,
    autocompleteText: string
): { preventDefault: boolean; newQuery: string } {
    if (hasAutocomplete && autocompleteText) {
        return {
            preventDefault: true,
            newQuery: autocompleteText + ' '
        };
    }
    
    return {
        preventDefault: false,
        newQuery: currentQuery
    };
}

/**
 * Handles arrow key navigation with autocomplete
 * @param key The key pressed ('ArrowLeft' or 'ArrowRight')
 * @param cursorPosition Current cursor position
 * @param queryLength Current query length
 * @param hasAutocomplete Whether autocomplete is available
 * @returns True if autocomplete should be filled
 */
export function handleArrowKeyPress(
    key: string,
    cursorPosition: number,
    queryLength: number,
    hasAutocomplete: boolean
): boolean {
    // If it's a right arrow and we're at the end of the current text
    if (key === 'ArrowRight' && cursorPosition === queryLength && hasAutocomplete) {
        return true;
    }
    
    return false;
}

/**
 * Validates if a search query meets minimum requirements
 * @param query The search query
 * @returns True if query is valid for search
 */
export function isValidSearchQuery(query: string): boolean {
    return query.trim().length >= 2;
}

/**
 * Determines which dropdown(s) should close based on click target
 * @param clickTarget The element that was clicked
 * @param searchContainer The search container element
 * @returns Object indicating which dropdowns to close
 */
export function getDropdownsToClose(
    clickTarget: Element,
    searchContainer: Element | null
): { closeControls: boolean; closeResults: boolean } {
    if (!searchContainer || !searchContainer.contains(clickTarget)) {
        // Click completely outside - close both
        return { closeControls: true, closeResults: true };
    }

    // Check specific dropdown areas for targeted closing
    const controlsArea = clickTarget.closest('[ref="controlsDropdown"]');
    const resultsArea = clickTarget.closest('[ref="searchResultsDropdown"]');

    return {
        closeControls: !controlsArea,
        closeResults: !resultsArea
    };
}