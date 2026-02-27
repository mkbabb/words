import { cn } from '@/utils';
import { MasteryLevel } from '@/types/wordlist';
import type { CardVariant } from '@/types';

/**
 * Escapes HTML special characters to prevent XSS
 */
function escapeHTML(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Escapes special regex characters in a string
 */
function escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Formats example sentences with bold highlighting for the target word
 */
export function formatExampleHTML(example: string, word: string): string {
    // Escape both inputs before constructing HTML
    const safeExample = escapeHTML(example);
    const safeWord = escapeHTML(word);
    const regex = new RegExp(`\\b${escapeRegex(safeWord)}\\b`, 'gi');
    return safeExample.replace(
        regex,
        `<strong class="hover-word">${safeWord}</strong>`
    );
}

/**
 * Gets the appropriate heatmap color class based on similarity score
 */
export function getHeatmapClass(score: number): string {
    if (score >= 0.9) {
        return cn(
            'bg-gradient-to-br from-green-300 to-green-400 dark:from-green-700 dark:to-green-800',
            'text-green-900 dark:text-green-100',
            'border-green-400 dark:border-green-600'
        );
    } else if (score >= 0.8) {
        return cn(
            'bg-gradient-to-br from-emerald-300 to-emerald-400 dark:from-emerald-700 dark:to-emerald-800',
            'text-emerald-900 dark:text-emerald-100',
            'border-emerald-400 dark:border-emerald-600'
        );
    } else if (score >= 0.7) {
        return cn(
            'bg-gradient-to-br from-yellow-300 to-yellow-400 dark:from-yellow-700 dark:to-yellow-800',
            'text-yellow-900 dark:text-yellow-100',
            'border-yellow-400 dark:border-yellow-600'
        );
    } else if (score >= 0.6) {
        return cn(
            'bg-gradient-to-br from-orange-300 to-orange-400 dark:from-orange-700 dark:to-orange-800',
            'text-orange-900 dark:text-orange-100',
            'border-orange-400 dark:border-orange-600'
        );
    } else {
        return cn(
            'bg-gradient-to-br from-rose-300 to-rose-400 dark:from-rose-700 dark:to-rose-800',
            'text-rose-900 dark:text-rose-100',
            'border-rose-400 dark:border-rose-600'
        );
    }
}

/**
 * Gets random delay for animation cycles
 */
export function getRandomAnimationDelay(min: number, max: number): number {
    return min + Math.random() * (max - min);
}

/**
 * Maps a ranking index to a card variant based on mastery levels
 */
export function getCardVariant(index: number): CardVariant {
    switch (index) {
        case 0:
            return MasteryLevel.GOLD;
        case 1:
            return MasteryLevel.SILVER;
        case 2:
            return MasteryLevel.BRONZE;
        default:
            return MasteryLevel.DEFAULT;
    }
}

/**
 * Formats a percentage value for display
 */
export function formatPercent(value: number): string {
    return `${Math.round(value * 100)}%`;
}

/**
 * Formats example usage text with markdown-style bold syntax
 */
export function formatExampleUsage(example: string): string {
    // Escape HTML first, then convert markdown bold to HTML bold
    const safe = escapeHTML(example);
    return safe.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-foreground">$1</strong>');
}