/**
 * Scroll Progress and Animation Utilities
 * 
 * Functions for calculating scroll progress and icon opacity
 */

import type { SearchBarState, ScrollState } from '../types';

/**
 * Calculates document height for scroll calculations
 * @returns The maximum document height
 */
export function calculateDocumentHeight(): number {
    return Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.clientHeight,
        document.documentElement.scrollHeight,
        document.documentElement.offsetHeight
    );
}

/**
 * Calculates scroll progress as a percentage
 * @param scrollY Current scroll position
 * @param documentHeight Total document height
 * @returns Scroll progress from 0 to 1
 */
export function calculateScrollProgress(scrollY: number, documentHeight: number): number {
    const maxScroll = Math.max(documentHeight - window.innerHeight, 1);
    
    // Don't engage scrolling behavior if there's nothing to scroll
    if (maxScroll <= 10) {
        return 0;
    }
    
    // Simple continuous progress calculation
    return Math.min(scrollY / maxScroll, 1);
}

/**
 * Calculates icon opacity based on scroll progress and state
 * @param scrollState The current scroll state
 * @param isFocused Whether the search bar is focused
 * @param isHovered Whether the search bar is hovered
 * @param showControls Whether controls dropdown is visible
 * @param showResults Whether results dropdown is visible
 * @returns Icon opacity from 0.1 to 1
 */
export function calculateIconOpacity(
    scrollState: ScrollState,
    isFocused: boolean,
    isHovered: boolean,
    showControls: boolean,
    showResults: boolean
): number {
    // Always full opacity when focused or hovered
    if (isFocused || isHovered) {
        return 1;
    }

    // Don't fade when either dropdown is showing
    if (showControls || showResults) {
        return 1;
    }

    // Continuous fade based on scroll progress relative to inflection point
    const progress = Math.min(
        scrollState.scrollProgress / scrollState.scrollInflectionPoint,
        1
    );

    // Start fading at 40% of the way to inflection point, fully hidden at 85%
    const fadeStart = 0.4;
    const fadeEnd = 0.85;

    if (progress <= fadeStart) {
        return 1; // Full opacity
    } else if (progress >= fadeEnd) {
        return 0.1; // Nearly hidden but still interactive
    } else {
        // Smooth cubic easing for natural fade
        const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart);
        const easedProgress = 1 - Math.pow(1 - fadeProgress, 3); // Cubic ease-out
        return 1 - easedProgress * 0.9; // Fade from 1 to 0.1
    }
}

/**
 * Calculates container style properties based on scroll progress
 * @param scrollState The current scroll state
 * @param isFocused Whether the search bar is focused
 * @param isHovered Whether the search bar is hovered
 * @param showControls Whether controls dropdown is visible
 * @param showResults Whether results dropdown is visible
 * @returns Container style object
 */
export function calculateContainerStyle(
    scrollState: ScrollState,
    isFocused: boolean,
    isHovered: boolean,
    showControls: boolean,
    showResults: boolean
): Record<string, string> {
    const progress = Math.min(
        scrollState.scrollProgress / scrollState.scrollInflectionPoint,
        1
    );

    // Use smaller responsive widths for better desktop experience
    const responsiveMaxWidth = 'min(32rem, calc(100vw - 2rem))';

    // Focused/hovered states or dropdowns shown: full size but responsive
    if (isFocused || isHovered || showControls || showResults) {
        return {
            maxWidth: responsiveMaxWidth,
            transform: 'scale(1)',
            opacity: '1',
            transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        };
    }

    // Smooth continuous shrinking based on scroll progress
    const clampedProgress = Math.max(0, Math.min(progress, 1));

    // Continuous scale transition from 1.0 to 0.88
    const scale = 1 - clampedProgress * 0.12;

    // Continuous opacity transition from 1.0 to 0.92
    const opacity = 1 - clampedProgress * 0.08;

    // Continuous width interpolation between responsiveMaxWidth and minWidth
    // Parse the rem values to interpolate numerically
    const maxWidthStart = 32; // 32rem
    const maxWidthEnd = 24; // 24rem
    const interpolatedWidth =
        maxWidthStart - clampedProgress * (maxWidthStart - maxWidthEnd);
    const currentMaxWidth = `min(${interpolatedWidth}rem, calc(100vw - ${2 + clampedProgress * 2}rem))`;

    return {
        maxWidth: currentMaxWidth,
        transform: `scale(${scale})`,
        opacity: opacity.toString(),
        transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    };
}

/**
 * Determines the next state based on current conditions
 * @param currentState The current search bar state
 * @param isFocused Whether the search bar is focused
 * @param isHovered Whether the search bar is hovered
 * @returns The next state or null if no change needed
 */
export function determineNextState(
    currentState: SearchBarState,
    isFocused: boolean,
    isHovered: boolean
): SearchBarState | null {
    if (isFocused && currentState !== 'focused') {
        return 'focused';
    } else if (isHovered && currentState !== 'hovering' && !isFocused) {
        return 'hovering';
    } else if (!isFocused && !isHovered && (currentState === 'focused' || currentState === 'hovering')) {
        return 'normal';
    }
    
    return null;
}